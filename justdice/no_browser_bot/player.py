#
# Browserless Bot for playing at just-dice.com
#
# Create your own strategy by redifining the "play" function.
#

import sys
import time
import random
import urllib2
import cookielib
from decimal import Decimal

from socketio import SocketIO

BASE_DOMAIN = 'just-dice.com'
BASE_URL = 'https://%s' % BASE_DOMAIN

cj = cookielib.CookieJar()
def load_justdice():
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
    opener.addheaders.append(('Origin', BASE_URL))

    opener.open(BASE_URL)
    req = opener.open('%s/socket.io/1' % BASE_URL)
    response = req.read()
    return response


class JustDiceSocket(object):
    def __init__(self, response, login):
        self.login = login
        self._setup_sock(response)

    def _setup_sock(self, response):
        self.csrf = None
        self.user_id = None
        self.logged_in = False
        self.waiting_bet_result = False
        self.last_bet = None

        origin = BASE_URL
        self.sock = SocketIO(BASE_DOMAIN, origin, response, secure=True)

        self.sock.on('init', self.on_init)
        self.sock.on('set_hash', self.on_set_hash)
        self.sock.on('reload', self.on_reload)
        self.sock.on('result', self.on_result)


    def bet(self, win_chance, amount, roll_hi):
        if self.waiting_bet_result:
            raise Exception("Still waiting for last bet result")
        which = 'hi' if roll_hi else 'lo'
        self.sock.emit('bet', self.csrf, {'chance': '%s' % str(win_chance),
            'bet': format(amount, '.8f'), 'which': '%s' % which})
        self.waiting_bet_result = True

    def randomize(self, user_seed=None):
        # user_seed must be a string.
        self.sock.emit('random', self.csrf)
        if user_seed is None:
            user_seed = str(random.randint(0, int('9' * 24)))
        self.sock.emit('seed', self.csrf, user_seed, True)

    def on_result(self, result):
        if result['uid'] == self.user_id:
            self.last_bet = {
                    'win': result['win'],
                    'roll_high': result['high'],
                    'lucky_number': Decimal(result['lucky']) / 10000}
            self.waiting_bet_result = False

    def on_reload(self):
        self.sock.emit('disconnect')
        response = load_justdice()
        self._setup_sock(response)

    def on_set_hash(self, new_cookie_hash):
        for cookie in cj:
            if cookie.name == 'hash':
                cookie.value = new_cookie_hash
                break

    def on_init(self, data):
        self.csrf = data[u'csrf']
        self.user_id = data[u'uid']
        self.house_edge = data[u'edge']

        if data['username'] is None and self.login:
            self.sock.emit('login', self.csrf,
                    self.login['user'], self.login['pwd'], '')
        else:
            self.logged_in = True


def main(user=None, pwd=None, new_seed=True):
    print "Connecting..."
    response = load_justdice()
    login_info = {'user': user, 'pwd': pwd} if user is not None else None
    justdice = JustDiceSocket(response, login=login_info)
    sys.stdout.write("Logging in...")
    sys.stdout.flush()
    while not justdice.logged_in:
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(0.75)
    print

    if new_seed:
        print "Generating new server seed.."
        justdice.randomize('')
        print

    win, total = play(justdice)
    print "\nWin ratio: %d/%d = %s" % (win, total, Decimal(win) / total)

    justdice.sock.emit('disconnect')

def roll_dice(justdice, win_chance, amount, roll_hi):
    roll_for = Decimal('99.9999') - win_chance if roll_hi else win_chance
    sys.stdout.write("Rolling dice for %s %s ..." % (
        ">" if roll_hi else "<", format(roll_for, '07.4f')))
    sys.stdout.flush()
    justdice.bet(win_chance=win_chance, amount=amount, roll_hi=roll_hi)
    while justdice.waiting_bet_result:
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(0.1)
    print " %s %s" % (format(justdice.last_bet["lucky_number"], '07.4f'),
        "win!" if justdice.last_bet['win'] else "lose :/")

    return justdice.last_bet['win']


def play(justdice):
    # XXX Define your strategy here.
    win = 0     # Win count.
    nroll = 40  # Roll n times.

    amount = Decimal('0')     # Amount in BTC to bet.
    roll_hi = False
    win_chance = Decimal('2') # %.

    for _ in xrange(nroll):
        if roll_dice(justdice, win_chance, amount, roll_hi):
            win += 1

    return win, nroll


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "WARNING user and password were not specified."
        print "Expected usage: %s user password" % sys.argv[0]
        print "***" * 15
    main(*sys.argv[1:3])
