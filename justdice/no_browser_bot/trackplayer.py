import ttk
import time
import Queue
import shelve
import Tkinter
from decimal import Decimal
from optparse import OptionParser

from browserless_driver import JustDiceSocket, load_justdice
from browserless_player import login, handle_input

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
    def __init__(self, root, justdice, queue_check=50):
        self.root = root
        self._tracked_users = sorted(map(int, justdice.db['track'].keys()))
        if self._tracked_users:
            self.trackid = self._tracked_users[0]
        else:
            self.trackid = 0 # No user being tracked for now.
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
        title = ttk.Label(text=u'Tracking user')# %s' % self.trackid)
        self.track_cb = ttk.Combobox(height=15, values=self._tracked_users)
        self.track_cb.set(self._tracked_users[0])
        self.track_cb.bind('<Return>', self._add_tracking)
        self.track_cb.bind('<<ComboboxSelected>>', self._change_tracking)
        track_add = ttk.Button(text=u'Add', command=self._add_tracking)
        reset_btn = ttk.Button(text=u'Reset', command=self._reset_tracking)
        remove_btn = ttk.Button(text=u'Remove', command=self._remove_tracking)
        self.wagered = ttk.Label(text=u'Wagered: 0')
        self.profit = ttk.Label(text=u'Profit: 0')
        title.grid(column=0, row=0, in_=info, **pad)
        self.track_cb.grid(column=1, row=0, in_=info, **pad)
        track_add.grid(column=2, row=0, in_=info, **pad)
        reset_btn.grid(column=3, row=0, in_=info, **pad)
        remove_btn.grid(column=4, row=0, in_=info, **pad)
        self.wagered.grid(column=0, row=1, columnspan=5, sticky='ew', in_=info,
                **pad)
        self.profit.grid(column=0, row=2, columnspan=5, sticky='ew', in_=info,
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
        data = self.justdice.db['track'][str(self.trackid)]
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
        self._clear_display()
        self.justdice.track(self.trackid)

    def _remove_tracking(self):
        self.justdice.untrack(self.trackid)
        self._clear_display()
        self._tracked_users = sorted(map(int, self.justdice.db['track'].keys()))
        self.track_cb['values'] = self._tracked_users
        self.trackid = self._tracked_users[0]
        self.track_cb.set(self.trackid)
        self._preload()

    def _clear_display(self):
        child = self.results.get_children('')
        if child:
            self.results.delete(*child)
        self.wagered['text'] = u'Wagered: 0'
        self.profit['text'] = u'Profit: 0'

    def _add_tracking(self, event=None):
        new_id = self.track_cb.get()
        try:
            int(new_id)
        except Exception:
            # Not an integer.
            return
        if new_id != self.trackid:
            self.trackid = new_id
            self.justdice.track(self.trackid)
            self._tracked_users = sorted(map(int,
                self.justdice.db['track'].keys()))
            self.track_cb['values'] = self._tracked_users
            self._clear_display()
            self._preload()

    def _change_tracking(self, event):
        new_id = event.widget.get()
        if new_id != self.trackid:
            self.trackid = new_id
            self._clear_display()
            self._preload()


def main():
    options = handle_input(enable_dummy=False)

    print "Connecting.."
    response = load_justdice(secret_url=options.secret, proxy=options.proxy)
    justdice = login(response, options, TrackResultSocket)
    if justdice is None:
        # Login failed.
        return

    justdice.queue = Queue.Queue()
    root = Tkinter.Tk()
    root.wm_title(u'just-dice tracking')
    gui = GUI(root, justdice)
    root.lift()
    root.mainloop()


if __name__ == "__main__":
    main()
