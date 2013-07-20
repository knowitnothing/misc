import ttk
import time
import Queue
import sqlite3
import Tkinter
from decimal import Decimal
from optparse import OptionParser
from collections import defaultdict

from browserless_driver import JustDiceSocket, load_justdice
from browserless_player import login, handle_input

BGCOLOR_WIN = '#90CA77'
BGCOLOR_LOSE = '#FDA0A4'

DB = 'sqldata.db'

class TrackResultSocket(JustDiceSocket):
    def __init__(self, *args, **kwargs):
        super(TrackResultSocket, self).__init__(*args, **kwargs)
        self.db_conn = None
        self.db = None
        self.queue = None
        self.tracked = None

    def _setup_db(self, db_conn):
        self.db_conn = db_conn
        self.db = db_conn.cursor()
        sql_aggregate_table = """CREATE TABLE IF NOT EXISTS [track_summ] (
                uid INTEGER PRIMARY KEY,
                total_profit INTEGER, total_wagered INTEGER)"""
        self.db.execute(sql_aggregate_table)
        sql_name_table = """CREATE TABLE IF NOT EXISTS [name] (
                uid INTEGER, nickname TEXT,
                PRIMARY KEY(uid, nickname))"""
        self.db.execute(sql_name_table)
        sql_track_table = """CREATE TABLE IF NOT EXISTS [track] (
                betid INTEGER PRIMARY KEY,
                uid INTEGER,
                win INTEGER,
                date INTEGER,
                rolled INTEGER,
                roll_hi INTEGER,
                bet INTEGER, payout INTEGER, profit INTEGER,
                FOREIGN KEY(uid) REFERENCES track_summ(uid))"""
        self.db.execute(sql_track_table)
        self.db.execute("CREATE INDEX IF NOT EXISTS uid_index ON track(uid)")
        sql_trigger = """CREATE TRIGGER IF NOT EXISTS [track_update]
                AFTER INSERT ON [track] BEGIN
                    UPDATE track_summ SET
                        total_profit = total_profit + NEW.profit,
                        total_wagered = total_wagered + NEW.bet
                        WHERE uid = NEW.uid;
                END"""
        self.db.execute(sql_trigger)

        self.tracked = self._track_list()
        self.user_name = defaultdict(set)
        self._tracked_name()


    def track(self, userid, update_list=True):
        if self._is_tracked(userid):
            # Already being tracked.
            return
        self.db.execute("""INSERT INTO track_summ
                (uid, total_profit, total_wagered) VALUES (?, 0, 0)""",
                (userid, ))
        if update_list:
            self.tracked = self._track_list()
        self.db_conn.commit()

    def untrack(self, userid, update_list=True):
        if self._is_tracked(userid) is None:
            # User is not being tracked.
            return
        self.db.execute("DELETE FROM track WHERE uid = ?", (userid, ))
        self.db.execute("DELETE FROM track_summ WHERE uid = ?", (userid, ))
        if update_list:
            self.tracked = self._track_list()
        self.db_conn.commit()

    def bet_data(self, userid):
        if self._is_tracked(userid) is None:
            # No data.
            return None
        return self.db.execute("""SELECT
            uid, date, betid, rolled, roll_hi, bet, payout, win, profit
            FROM track WHERE uid = ? ORDER BY betid""", (userid, )).fetchall()

    def summary_data(self, userid):
        return self._is_tracked(userid)

    def bet_add(self, bet):
        self.db.execute("""INSERT INTO track
                (uid, date, betid, rolled, roll_hi, bet, payout, win, profit)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""", bet)
        self.db_conn.commit()

    def name_add(self, (uid, name)):
        try:
            self.db.execute("""INSERT INTO name
                    (uid, nickname) VALUES (?, ?)""", (uid, name))
        except sqlite3.IntegrityError:
            # Name already present
            pass
        else:
            self.db_conn.commit()
            self.user_name[uid].add(name)

    def _is_tracked(self, userid):
        query = "SELECT * FROM track_summ WHERE uid = ?"
        return self.db.execute(query, (userid, )).fetchone()

    def _track_list(self):
        return [t[0] for t in self.db.execute(
                "SELECT uid FROM track_summ ORDER BY uid")]

    def _tracked_name(self):
        query = "SELECT uid, nickname FROM name"
        for uid, name in self.db.execute(query):
            self.user_name[uid].add(name)


    def on_result(self, result):
        uid = int(result['uid'])
        if self.tracked is None or uid not in self.tracked:
            # User is not being tracked.
            return

        name = result['name']
        name = name[:name.rfind('(', 1)-1] # Remove (userid) from name.
        profit = int(Decimal(result['this_profit']) * Decimal('1e8'))
        bet = int(Decimal(result['bet']) * Decimal('1e8'))
        payout = int(Decimal(result['payout']) * Decimal('1e8'))

        new_bet = (uid, result['date'], int(result['betid']), result['lucky'],
                int(result['high']), bet, payout, result['win'], profit)

        if self.queue:
            self.queue.put(new_bet)
            self.queue.put((uid, name))


class GUI:
    def __init__(self, root, justdice, queue_check=100):
        self.db = sqlite3.connect(DB)
        justdice._setup_db(self.db)

        self.root = root
        self.sock_status = 'disconnected'
        self.trackid = justdice.tracked[0] if justdice.tracked else 0
        self.justdice = justdice
        self.reconnecting = False
        self.reconnect_timeout = 5000 # milliseconds, * 2, * 4, * 8, * 16, * 1
        self.queue = Queue.Queue()
        self.queue_check = queue_check # check each n milliseconds
        justdice.queue = self.queue

        self._rec_mul = 4
        self._rec_orig_timeout = (self.reconnect_timeout, 4)
        self._setup_gui()
        self._preload()
        self._update_title()
        self._update_display()

    def _setup_gui(self):
        pad = {'padx': 6, 'pady': 6}
        # Basic information.
        info = ttk.Frame()
        title = ttk.Label(text=u'Tracking user')
        self.track_cb = ttk.Combobox(height=15, values=self.justdice.tracked)
        self.track_cb.set(self.trackid)
        self.track_cb.bind('<Return>', self._add_tracking)
        self.track_cb.bind('<<ComboboxSelected>>', self._change_tracking)
        track_add = ttk.Button(text=u'Add', command=self._add_tracking)
        reset_btn = ttk.Button(text=u'Reset', command=self._reset_tracking)
        remove_btn = ttk.Button(text=u'Remove', command=self._remove_tracking)
        self.wagered = ttk.Label(text=u'Wagered: 0')
        self.profit = ttk.Label(text=u'Profit: 0')
        self.player_name = ttk.Label(text=u'Name: -')
        title.grid(column=0, row=0, in_=info, **pad)
        self.track_cb.grid(column=1, row=0, in_=info, **pad)
        track_add.grid(column=2, row=0, in_=info, **pad)
        reset_btn.grid(column=3, row=0, in_=info, **pad)
        remove_btn.grid(column=4, row=0, in_=info, **pad)
        self.player_name.grid(column=0, row=1, columnspan=4, sticky='ew',
                in_=info, **pad)
        self.profit.grid(column=0, row=2, columnspan=2, sticky='ew', in_=info,
                **pad)
        self.wagered.grid(column=2, row=2, columnspan=3, sticky='ew', in_=info,
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

    def _update_title(self):
        conn = 'connected'
        if not self.justdice.sock.connected:
            conn = 'dis' + conn
            self.root.wm_title(u'just-dice tracking - %s' % conn)
            if not self.reconnecting:
                try:
                    self.justdice.sock.emit('disconnect')
                except Exception, e:
                    print 'emit disconnect failed: %s' % e
                self._reconnect()
        elif self.justdice.sock.connected:
            self.reconnecting = False
            self.reconnect_timeout, self._rec_mul = self._rec_orig_timeout

        if conn != self.sock_status:
            self.sock_status = conn
            self.root.wm_title(u'just-dice tracking - %s' % conn)
        self.root.after(1000, self._update_title)

    def _update_display(self):
        if self.reconnecting:
            self.root.after(self.queue_check, self._update_display)
            return

        try:
            data = self.queue.get(block=False)
        except Queue.Empty:
            pass
        else:
            if len(data) > 2:
                self.justdice.bet_add(data)
                if data[0] == self.trackid:
                    self._update_results(data)
            else:
                self.justdice.name_add(data)
                if data[0] == self.trackid:
                    self._update_name()
        self.root.after(self.queue_check, self._update_display)

    def _preload(self):
        # Load data stored in database.
        data = self.justdice.bet_data(self.trackid)
        for bet in data or []:
            self._update_results(bet)
        self._update_name()

    def _update_results(self, data):
        uid, date, betid, lucky, roll_hi, bet, payout, win, profit = data
        _, total_profit, total_wagered = self.justdice.summary_data(uid)
        total_profit = format(total_profit/1e8, '.8f')
        total_wagered = format(total_wagered/1e8, '.8f')
        self.wagered['text'] = u'Wagered: %s' % total_wagered
        self.profit['text'] = u'Profit: %s' % total_profit

        house_edge = 1 # 1 %
        payout = Decimal(payout) / Decimal('1e8')
        win_chance = (100 - house_edge) / payout
        roll_for = Decimal('99.9999') - win_chance if roll_hi else win_chance

        result = (time.ctime(date), betid, format(lucky / 10000., '07.4f'),
                '%s %s' % ('>' if roll_hi else '<', format(roll_for, '07.4f')),
                format(bet/1e8, '.8f'), '%sx' % format(payout, '.8f'),
                '%s%s' % ('+' if win else '', format(profit/1e8, '.8f')))
        self.results.insert('', '0', values=result,
                tag='win' if win else 'lose')

    def _update_name(self):
        name = self.justdice.user_name[self.trackid]
        self.player_name['text'] = u'Name: %s' % (', '.join(name))

    def _reset_tracking(self):
        self.justdice.untrack(self.trackid, update_list=False)
        self._clear_display()
        self.justdice.track(self.trackid, update_list=False)

    def _remove_tracking(self):
        self.justdice.untrack(self.trackid)
        self._clear_display()
        self.track_cb['values'] = self.justdice.tracked
        self.trackid = self.justdice.tracked[0] if self.justdice.tracked else 0
        self.track_cb.set(self.trackid)
        self._preload()

    def _clear_display(self):
        child = self.results.get_children('')
        if child:
            self.results.delete(*child)
        self.wagered['text'] = u'Wagered: 0'
        self.profit['text'] = u'Profit: 0'
        self.player_name['text'] = u'Name: -'

    def _add_tracking(self, event=None):
        new_id = self.track_cb.get()
        try:
            new_id = int(new_id)
        except Exception:
            # Not an integer.
            return
        if new_id != self.trackid:
            self.trackid = new_id
            self.justdice.track(self.trackid)
            self.track_cb['values'] = self.justdice.tracked
            self._clear_display()
            self._preload()

    def _change_tracking(self, event):
        new_id = int(event.widget.get())
        if new_id != self.trackid:
            self.trackid = new_id
            self._clear_display()
            self._preload()


    def _reconnect(self):
        print "Trying to reconnect.."
        self.reconnecting = True
        options = self.justdice.options
        try:
            self.justdice.sock.disconnect()
            response = load_justdice(secret_url=options.secret,
                proxy = options.proxy)
            new_justdice = login(response, options, TrackResultSocket)
        except Exception, e:
            print 'error reconnecting: %s' % e
            new_justdice = None
        if new_justdice is None:
            print ("Reconnect failed, retrying in %g miliseconds" %
                    self.reconnect_timeout)
            self.root.after(self.reconnect_timeout, self._reconnect)
            self.reconnect_timeout *= 2
            self._rec_mul -= 1
            if self._rec_mul < 0:
                self.reconnect_timeout, self._rec_mul = self._rec_orig_timeout
        else:
            new_justdice.options = options
            new_justdice.queue = self.queue
            del self.justdice
            self.justdice = new_justdice
            self.justdice._setup_db(self.db)
            print "Reconnected!"


def main():
    options = handle_input(enable_dummy=False)

    print "Connecting.."
    response = load_justdice(secret_url=options.secret, proxy=options.proxy)
    justdice = login(response, options, TrackResultSocket)
    if justdice is None:
        # Login failed.
        return

    justdice.options = options
    root = Tkinter.Tk()
    gui = GUI(root, justdice)
    root.lift()
    root.mainloop()


if __name__ == "__main__":
    main()
