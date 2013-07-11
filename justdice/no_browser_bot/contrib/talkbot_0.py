#
# Browserless Bot for chatting at just-dice.com.
#
import re
import time
import shelve
import random
import urllib2
import hashlib
from decimal import Decimal
from bs4 import BeautifulSoup

import util
from browserless_player import main
from browserless_driver import JustDiceSocket
from browserless_dummy import dice_roll, gen_server_seed

ROLL = "https://just-dice.com/roll/%s"
DB = "data.db"

class ChatSocket(JustDiceSocket):
    def __init__(self, *args, **kwargs):
        self.delim = '/'
        self.name_pat = re.compile('^\<(.*?)\>')
        self.bet_pat = re.compile('https://just-dice.com/roll/(\d*)')
        self.name = 'botty'
        self._bet_pending = []
        self._last_roll = 0

        self.mem = shelve.open(DB)
        if not 'top3_win' in self.mem:
            self.mem['top3_win'] = []
        if not 'top3_lose' in self.mem:
            self.mem['top3_lose'] = []
        if not 'user' in self.mem:
            self.mem['user'] = {}
        if not 'track' in self.mem:
            self.mem['track'] = {}

        to_remove = []
        two_weeks = 60*60*24*7*2
        for uid, info in self.mem['track'].iteritems():
            if 'when' not in info:
                continue
            elif time.time() - info['when'] > two_weeks:
                to_remove.append(uid)
        track = self.mem['track']
        for uid in to_remove:
            del track[uid]
        self.mem['track'] = track
        self.mem.sync()

        print self.mem['user']
        print self.mem['track']
        print self.mem['top3_win'], "top3 win"
        print self.mem['top3_lose'], "top3 lose"
        self.top3_limit = 180 # show at max each n seconds
        self.top3_lastseen = [0, 0] # never

        super(ChatSocket, self).__init__(*args, **kwargs)

        self.user_seed = '0'
        self.cmd_randomize()

    def on_init(self, data):
        super(ChatSocket, self).on_init(data)
        self.sock.emit('name', self.csrf, self.name)

    def on_result(self, result):
        when = result['date']
        betid = result['betid']
        profit = Decimal(result['this_profit'])
        chance = Decimal(result['chance'])
        uid = result['uid']
        won = result['win']
        if uid == self.user_id and self._bet_pending:
            self.waiting_bet_result = False
            print 'got result from my own bet'
            bet_userid, bet_chance, bet_fakeamount = self._bet_pending.pop(0)
            roll_typ = 'HI' if result['high'] else 'LO'
            if won:
                payout = (Decimal(100) - self.house_edge) / Decimal(bet_chance)
                extra = ". I would've won %s BTC." % (
                        format(Decimal(bet_fakeamount) * payout -
                        Decimal(bet_fakeamount), '.8f'))
            else:
                extra = ''
            self.sock.emit('chat', self.csrf,
                '%s: I %s-rolled %s and %s at win chance of %s%%%s' % (
                    bet_userid, roll_typ, format(result['lucky'] / 10000., '07.4f'),
                    'won' if won else 'lost', bet_chance, extra))
            if self._bet_pending:
                self.cmd_bet(self._bet_pending[0][2], self._bet_pending[0][1])
        try:
            name = result['name'].rsplit(' ', 1)[0]
            self._add(uid, name.encode('utf8'))
        except Exception, e:
            print "split failed on: %s, %s" % (result['name'], e)
        if uid in self.mem['track']:
            print 'new bet from', uid
            data = self.mem['track']
            data[uid]['last'] = when
            data[uid]['profit'] += profit
            data[uid]['wagered'] += Decimal(result['bet'])
            if won:
                data[uid]['win'] += 1
            else:
                data[uid]['lose'] += 1
            self.mem['track'] = data
            self.mem.sync()
        if abs(profit) < 0.001:
            # Less than 0.001 BTC does not get in the list.
            return

        new = (profit, -chance, betid)
        changed = False
        if profit > 0:
            data = self.mem['top3_win']
            if not data or new > data[-1]:
                changed = True
                data.append(new)
                data.sort(reverse=True)
            if len(data) > 3:
                changed = True
                data.pop()
            self.mem['top3_win'] = data
        else:
            data = self.mem['top3_lose']
            if not data or new < data[-1]:
                changed = True
                data.append(new)
                data.sort()
            if len(data) > 3:
                changed = True
                data.pop()
            self.mem['top3_lose'] = data
        if changed:
            self.mem.sync()
            print self.mem['top3_win']
            print self.mem['top3_lose']


    def _add(self, user_id, name):
        if user_id not in self.mem['user']:
            data = self.mem['user']
            data[user_id] = set([name])
            self.mem['user'] = data
            self.mem.sync()
        elif name not in self.mem['user'][user_id]:
            data = self.mem['user']
            data[user_id].add(name)
            self.mem['user'] = data
            self.mem.sync()

    def on_chat(self, msg, timestamp):
        user_id, msg = msg.split(' ', 1)
        user_id = user_id[1:-1].encode('utf8')
        if user_id == self.user_id:
            return

        _, name, text = self.name_pat.split(msg, maxsplit=1)
        self._add(user_id, name)

        text = text.lstrip()
        print text
        if text.startswith('%sshow' % self.delim):
            try:
                bet = text.split()[1]
                self.cmd_showbet(bet)
            except Exception, e:
                print "showbet err", e
        elif text.startswith('%swhois' % self.delim):
            try:
                look = text.split()[1].encode('utf8')
                self.cmd_whois(look)
            except Exception, e:
                print "whois err", e
        elif text.startswith('%shelp' % self.delim):
            self.cmd_help()
        elif text.startswith('%strack' % self.delim):
            try:
                trackinfo = text.split()[1:]
                if len(trackinfo) == 2:
                    userid, method = trackinfo
                    int(userid)
                    if method in ('start', 'stop', 'info'):
                        self.cmd_track(userid, method)
                elif len(trackinfo) == 1 and trackinfo[0] in ('list', 'sum'):
                    self.cmd_track(None, trackinfo[0])
            except Exception, e:
                print "track err", e
        elif text.startswith('%sbet' % self.delim):
            try:
                amount, chance = text.split()[1:]
                if self.cmd_bet(amount.encode('utf8'), chance.encode('utf8')):
                    self._bet_pending.append((user_id, chance, amount))
            except Exception, e:
                print 'bet err', e
        elif text.startswith('%sbot' % self.delim):
            return self.sock.emit('chat', self.csrf,
                    "https://github.com/knowitnothing/misc/tree/master/"
                    "justdice/no_browser_bot")
        elif text.startswith('%stop3' % self.delim):
            try:
                typ = text.split(' ', 1)[1]
                typ = True if typ.lower().startswith('win') else False
            except Exception, e:
                print "prev cmd_top3 err", e
            else:
                self.cmd_top3(typ)
        elif text.startswith('%sroll' % self.delim):
            self.cmd_roll(user_id)
        elif text.startswith('%shash' % self.delim):
            self.sock.emit('chat', self.csrf, 'USeed: %s; SHash: %s' % (
                self.user_seed, self.server_hash))
        elif text.startswith('%srand' % self.delim):
            self.sock.emit('chat', self.csrf, 'Nonce: %d; Seed: %s' % (
                self.nonce, self.server_seed))
            self.cmd_randomize()
        elif text.startswith('%smem' % self.delim):
            try:
                uid, msg = text.split(' ', 1)[1].split(' ', 1)
                uid = uid.encode('utf8')
                print int(uid), msg
                if uid not in self.mem:
                    self.mem[uid] = []
                m = self.mem[uid]
                m.append((user_id, timestamp, msg))
                if len(m) > 5:
                    m.pop(0)
                self.mem[uid] = m
                self.mem.sync()
                self.sock.emit('chat', self.csrf, '%s: recorded' % user_id)
            except Exception, e:
                print "mem err", e, "<<<"
                pass
        elif text.startswith('%sread' % self.delim):
            print 'reading for', user_id
            self.cmd_read(user_id)
        else:
            for bet in self.bet_pat.findall(text):
                print bet
                try:
                    self.cmd_showbet(bet)
                except Exception, e:
                    print "err showbet", e

    def cmd_bet(self, amount, chance):
        if time.time() - self._last_roll < 2:
            return
        self._last_roll = time.time() # This is shared with cmd_roll.

        roll_hi = random.choice([True, False])
        if float(chance) < 1e-4 or float(chance) > 98:
            return False
        add_it = True
        try:
            self.bet(chance, 0, roll_hi)
        finally:
            return add_it

    def cmd_whois(self, uid):
        if uid in self.mem['user']:
            data = self.mem['user'][uid]
            self.sock.emit('chat', self.csrf, "%s: %s" % (uid,
                ' | '.join(data)))

    def cmd_track(self, uid, method):
        if method == 'start':
            if uid not in self.mem['track']:
                data = self.mem['track']
                data[uid] = {'profit': 0, 'win': 0, 'lose': 0, 'wagered': 0,
                        'lastbet': 0, 'last': 0}
                self.mem['track'] = data
                self.mem.sync()
                self.sock.emit('chat', self.csrf, 'tracking bets from %s..' % uid)
        elif method == 'list':
            uids = sorted(map(int, self.mem['track'].keys()))
            print uids
            self.sock.emit('chat', self.csrf, "I'm tracking %s" %
                (', '.join(map(str, uids))))
        elif method == 'sum':
            total_profit = sum([info['profit'] for info in
                    self.mem['track'].values()])
            self.sock.emit('chat', self.csrf,
                "In total, the players I'm tracking have made a profit of"
                " %s" % total_profit)
        elif method == 'info':
            print 'info'
            self.mem.sync()
            if uid in self.mem['track']:
                info = self.mem['track'][uid]
                result = ('So far, player %s profited %s after wagering %s '
                        'through %d bets.' % (uid, info['profit'], info['wagered'],
                    info['win'] + info['lose']))
                self.sock.emit('chat', self.csrf, result)
        elif method == 'stop':
            self.mem.sync()
            if uid in self.mem['track']:
                data = self.mem['track']
                info = data.pop(uid)
                self.mem['track'] = data
                print self.mem['track'], "<<"
                self.mem.sync()
                result = ('Player %s profitted %s after wagering %s '
                          'through %d bets.' %
                    (uid, info['profit'], info['wagered'],
                        info['win'] + info['lose']))
                self.sock.emit('chat', self.csrf, result)

    def cmd_top3(self, topwin):
        if time.time() - self.top3_lastseen[topwin] < self.top3_limit:
            return
        self.top3_lastseen[topwin] = time.time()
        # Show Top 3 in the last 24 hours.
        if topwin:
            data = self.mem['top3_win']
        else:
            data = self.mem['top3_lose']
        if not data:
            return
        s = 'winning' if topwin else 'losing'
        for bet in reversed(data):
            self.cmd_showbet(bet[-1])

    def cmd_randomize(self):
        self.server_seed = gen_server_seed()
        self.server_hash = hashlib.sha256(self.server_seed).hexdigest()
        self.nonce = 0

    def cmd_help(self):
        self.sock.emit('chat', self.csrf, 'Help is coming! /show betid ;'
                ' /roll ; /hash ; /randomize ;'
                ' /mem userid message ; /read ; /top3 (win | lose) ;'
                ' /math doyourmagic ; /whois userid '
                ' /bet amount chance ; /track (list | sum) ;'
                ' /track userid (start | stop | info) ; /bot')

    def cmd_read(self, uid):
        try:
            for i, msg in enumerate(self.mem[uid], start=1):
                print msg
                self.sock.emit('chat', self.csrf, "#%d: %s> %s (%s)" % (
                    i, msg[0], msg[2], msg[1]))
        except:
            pass
        self.mem[uid] = []
        self.mem.sync()

    def cmd_roll(self, uid):
        if time.time() - self._last_roll < 2:
            return
        self._last_roll = time.time()
        self.nonce += 1
        result = dice_roll(self.server_seed, self.user_seed, self.nonce)
        self.sock.emit('chat', self.csrf, "%s: %s" % (uid, format(result,
            '07.4f')))

    def cmd_showbet(self, num):
        text = ("Bet %(id)d %(win)s %(profit)s. "
                "%(lucky)s %(gt)s %(target)s. Player: %(user)s [%(ago)s]")
        data = urllib2.urlopen(ROLL % num).read()
        if data.lower().startswith('there is no'):
            # Nothing to see.
            return

        soup = BeautifulSoup(data)
        timestamp = soup.findAll('script')[2].text
        ts_where = timestamp.find('moment')
        timestamp = util.pretty_date(int(timestamp[ts_where+8:ts_where+18]))

        labels = soup.findAll(attrs={'class': 'slabel'})
        data = soup.findAll('span')
        userid = data[2].text.strip()
        win = 'won' if data[9].text.strip()[0] == 'w' else 'lost'
        gt = labels[7].text[-1]
        params = {'id': int(data[0].text.strip()), 'win': win,
                  'profit': data[5].text.strip(),
                  'lucky': data[8].text.strip(), 'gt': gt,
                  'target': data[7].text.strip(), 'user': userid,
                  'ago': timestamp}
        print 'show bet %d' % int(num)
        self.sock.emit('chat', self.csrf, (text % params).encode('utf8'))


def bot(justdice):
    while True:
        time.sleep(0.05)

if __name__ == "__main__":
    main(bot, new_seed=False, justdice=ChatSocket)
