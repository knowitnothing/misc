import ttk
import time
import Queue
import shelve
import Tkinter
from decimal import Decimal
from optparse import OptionParser

from browserless_driver import JustDiceSocket, load_justdice
from browserless_player import login

BGCOLOR_WIN = '#90CA77'
BGCOLOR_LOSE = '#FDA0A4'

DB = 'data.db'

class TrackResultSocket(JustDiceSocket):
    def __init__(self, *args, **kwargs):
        super(TrackResultSocket, self).__init__(*args, **kwargs)
        self.db = shelve.open(DB)
        self.queue = None
        if not 'track' in self.db:
            self.db['track'] = {}

    def track(self, userid):
        userid = str(userid)
        if userid in self.db['track']:
            # Already being tracked.
            return
        data = self.db['track']
        data[userid] = {'profit': 0, 'wagered': 0, 'name': set(), 'bet': []}
        self.db['track'] = data
        self.db.sync()

    def untrack(self, userid):
        userid = str(userid)
        if userid not in self.db['track']:
            return
        data = self.db['track']
        data.pop(userid)
        self.db['track'] = data
        self.db.sync()

    def on_result(self, result):
        if result['uid'] not in self.db['track']:
            return
        data = self.db['track']

        uid = result['uid']
        name = result['name']
        name = name[:name.rfind('(', 1)-1] # Remove (userid) from name.
        data[uid]['name'].add(name)
        profit = Decimal(result['this_profit'])
        data[uid]['profit'] += profit
        bet = Decimal(result['bet'])
        data[uid]['wagered'] += bet

        payout = Decimal(result['payout'])
        new_bet = (uid, result['date'], result['betid'], result['lucky'],
                result['high'], bet, payout, result['win'], profit)
        if self.queue:
            self.queue.put((uid, data[uid]['profit'], data[uid]['wagered']))
            self.queue.put(new_bet)
        data[uid]['bet'].append(new_bet)

        self.db['track'] = data
        self.db.sync()


class GUI:
    def __init__(self, root, trackid, justdice, queue_check=50):
        self.root = root
        self.trackid = trackid
        self.justdice = justdice
        self.queue = justdice.queue
        self.queue_check = queue_check # check each n milliseconds

        self._setup_gui()
        self._preload()
        self._update_display()

    def _setup_gui(self):
        pad = {'padx': 6, 'pady': 6}
        # Basic information.
        info = ttk.Frame()
        title = ttk.Label(text=u'Tracking user %s' % self.trackid)
        reset_btn = ttk.Button(text=u'Reset', command=self._reset_tracking)
        self.wagered = ttk.Label(text=u'Wagered: 0')
        self.profit = ttk.Label(text=u'Profit: 0')
        title.grid(column=0, row=0, in_=info, **pad)
        reset_btn.grid(column=1, row=0, in_=info, **pad)
        self.wagered.grid(column=0, row=1, columnspan=2, sticky='ew', in_=info,
                **pad)
        self.profit.grid(column=0, row=2, columnspan=2, sticky='ew', in_=info,
                **pad)
        info.pack(fill='x')

        # Bets.
        container = ttk.Frame()
        container.pack(fill='both', expand=True)
        tree_columns = (u'Date', u'Bet Id', u'Roll', u'Target', u'Bet',
                u'Payout', u'Profit')
        column_width = (180, 80, 70, 90, 100, 100, 100)
        self.results = ttk.Treeview(columns=tree_columns, show='headings')
        for col, width in zip(tree_columns, column_width):
            self.results.heading(col, text=col)
            self.results.column(col, minwidth=0, width=width)
        self.results.tag_configure('win', background=BGCOLOR_WIN)
        self.results.tag_configure('lose', background=BGCOLOR_LOSE)
        vsb = ttk.Scrollbar(orient='vertical', command=self.results.yview)
        self.results.configure(yscrollcommand=vsb.set)
        self.results.grid(column=0, row=0, sticky='nsew', in_=container)
        vsb.grid(column=1, row=0, sticky='nse', in_=container)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

    def _update_display(self):
        try:
            data = self.queue.get(block=False)
        except Queue.Empty:
            pass
        else:
            if data[0] == self.trackid:
                self._update_results(data)
        self.root.after(self.queue_check, self._update_display)

    def _preload(self):
        # Load data stored in database.
        data = self.justdice.db['track'][self.trackid]
        self._update_results((None, data['profit'], data['wagered']))
        for bet in data['bet']:
            self._update_results(bet)

    def _update_results(self, data):
        if len(data) == 3:
            _, total_profit, total_wagered = data
            self.wagered['text'] = u'Wagered: %s' % format(total_wagered, '.8f')
            self.profit['text'] = u'Profit: %s' % format(total_profit, '.8f')
            return

        _, date, betid, lucky, roll_hi, bet, payout, win, profit = data

        house_edge = 1 # 1 %
        win_chance = (100 - house_edge) / payout
        roll_for = Decimal('99.9999') - win_chance if roll_hi else win_chance

        result = (time.ctime(date), betid, format(lucky / 10000., '07.4f'),
                '%s %s' % ('>' if roll_hi else '<', format(roll_for, '07.4f')),
                format(bet, '.8f'), '%sx' % format(payout, '.8f'),
                '%s%s' % ('+' if win else '', format(profit, '.8f')))
        print result[1:]
        self.results.insert('', '0', values=result,
                tag='win' if win else 'lose')

    def _reset_tracking(self):
        self.justdice.untrack(self.trackid)
        child = self.results.get_children('')
        if child:
            self.results.delete(*child)
        self.wagered['text'] = u'Wagered: 0'
        self.profit['text'] = u'Profit: 0'
        print "Reset"
        self.justdice.track(self.trackid)


def main():
    parser = OptionParser()
    parser.add_option('-t', '--track', help='User id to track')
    # Login
    parser.add_option('-s', '--secret', help='Pass a secret url')
    parser.add_option('-u', '--user', help='User name for login')
    parser.add_option('-p', '--password', help='User password')
    parser.add_option('-g', '--gauth', help='2FA code')

    options, args = parser.parse_args()
    if options.track is None:
        parser.error("--track is required")
        return

    print "Connecting.."
    response = load_justdice(secret_url=options.secret)
    justdice = login(False, response, options.user, options.password,
            options.gauth, options.secret, TrackResultSocket)
    if justdice is None:
        # Login failed.
        return

    justdice.queue = Queue.Queue()
    justdice.track(options.track)
    root = Tkinter.Tk()
    root.wm_title(u'just-dice tracking')
    gui = GUI(root, options.track, justdice)
    root.mainloop()


if __name__ == "__main__":
    main()
