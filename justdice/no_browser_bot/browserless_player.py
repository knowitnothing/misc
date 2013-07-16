import sys
import time
import urllib
import urllib2
from decimal import Decimal
from optparse import OptionParser

from browserless_driver import login_on_secret_url

def handle_input(args=None, enable_dummy=True):
    parser = OptionParser(usage="usage: %prog user password [ga] [options]")
    if enable_dummy:
        parser.add_option('-d', '--dummy', action='store_true', dest='dummy',
                default=False, help='Run offline (user/password not required)')
    parser.add_option('-s', dest='secret', help='Pass a secret url')
    parser.add_option('-u', dest='user', help='User name for login')
    parser.add_option('-p', dest='password', help='User password')
    parser.add_option('-g', dest='gauth', help='2FA code')
    parser.add_option('-x', '--proxy', help='Connect through a HTTPS proxy')

    options, args = parser.parse_args(args)

    google_2fa = None
    user, pwd = None, None

    if not enable_dummy:
        options.dummy = False

    if options.secret:
        sys.stderr.write("Using secret url.\n")
    if options.proxy:
        sys.stderr.write("Using proxy.\n")
        options.proxy = {'https': options.proxy}

    if len(args) == 3:
        options.user, options.password, options.gauth = args
    elif len(args) == 2:
        options.user, options.password = args
    elif not options.secret and not options.dummy:
        sys.stderr.write("WARNING user and password were not specified.\n")
        sys.stderr.write("Expected usage: %s user password [ga] [-dummy]\n" %
                sys.argv[0])
        sys.stderr.write("***" * 15 + '\n')

    return options


def login(response, options, JustDiceSocket):
    sys.stderr.write("Logging in...")
    sys.stderr.flush()

    dummy, secret_url = options.dummy, options.secret
    user, pwd, google_2fa = options.user, options.password, options.gauth
    # When using secret url, we need to POST the login data.
    if not dummy and secret_url is not None and user is not None:
        response = login_on_secret_url(options)

    if user is not None:
        login_info = {'user': user, 'pwd': pwd, '2fa': google_2fa}
    else:
        login_info = None
    justdice = JustDiceSocket(response, login=login_info)
    max_login_wait = 15 # seconds
    now = time.time()
    while not justdice.logged_in:
        if time.time() - now > max_login_wait:
            # Timed out.
            justdice.logged_in = None
        if justdice.logged_in is None:
            # Could not login.
            sys.stderr.write(" Couldn't log in\n")
            justdice.sock.emit('disconnect')
            return
        sys.stderr.write('.')
        sys.stderr.flush()
        time.sleep(0.75)
    sys.stderr.write('\n')

    return justdice


def main(play, new_seed=True, **kwargs):
    options = handle_input(sys.argv[1:])

    if options.dummy:
        from browserless_dummy import load_justdice, JustDiceSocket
    else:
        from browserless_driver import load_justdice, JustDiceSocket
    if 'justdice' in kwargs:
        JustDiceSocket = kwargs['justdice']

    sys.stderr.write("Connecting...\n")
    if (not options.dummy and options.secret is not None and
            options.user is not None):
        response = None
    else:
        response = load_justdice(secret_url=options.secret, proxy=options.proxy)
    justdice = login(response, options, JustDiceSocket)
    if justdice is None:
        # Login failed.
        return

    if new_seed:
        sys.stderr.write("Generating new server seed..")
        justdice.randomize()
        while justdice.waiting_seed:
            sys.stderr.write('.')
            sys.stderr.flush()
            time.sleep(0.1)
        sys.stderr.write('\n')

    try:
        play(justdice)
    finally:
        sys.stderr.write('Leaving..\n')
        justdice.sock.emit('disconnect')


def roll_dice(justdice, win_chance, amount, roll_hi, verbose=False):
    if verbose:
        roll_for = Decimal('99.9999') - win_chance if roll_hi else win_chance
        sys.stdout.write("Rolling dice for %s %s ..." % (
            ">" if roll_hi else "<", format(roll_for, '07.4f')))
        sys.stdout.flush()
    justdice.bet(win_chance=win_chance, amount=amount, roll_hi=roll_hi)
    while justdice.waiting_bet_result:
        if not justdice.sock.connected:
            justdice.waiting_bet_result = None
            break
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()
        time.sleep(0.1)
    if justdice.waiting_bet_result is None:
        # Could not place the bet.
        raise Exception
    if verbose:
        print " %s %s" % (format(justdice.last_bet["lucky_number"], '07.4f'),
                "win!" if justdice.last_bet['win'] else "lose :/")

    return justdice.last_bet['win'], justdice.last_bet['lucky_number']



class Strategy(object):
    def __init__(self, justdice, kwargs):
        self.justdice = justdice
        self.house_edge = justdice.house_edge
        self.payout = None

        self._orig_params = kwargs.copy()
        self.setup()


    def setup(self):
        kwargs = self._orig_params

        # Required parameters.
        self.win_chance = kwargs['win_chance']
        self.to_bet = kwargs['to_bet']
        self.bankroll = kwargs['bankroll']
        # Optional parameters.
        self.careful = kwargs.get('careful', False) # Press enter for a bet.
        self.target = kwargs.get('target', float('inf')) # Greedy!
        self.nrolls = kwargs.get('nrolls', -1) # infinity rolls by default.
        self.simulation = kwargs.get('simulation', True)
        self.roll_high = kwargs.get('roll_high', True)
        self.getout = kwargs.get('getout', Decimal('0'))
        self.strat_name = kwargs.get('strat_name', 'no name')
        self.lose_multiplier = kwargs.get('lose_multiplier', 1)
        self.win_multiplier = kwargs.get('win_multiplier', 1)
        self.reset_on_win = kwargs.get('reset_on_win', False)
        self.reset_on_lose = kwargs.get('reset_on_lose', False)

        self.start_bet = kwargs['to_bet']


    def run(self):
        # Game stats
        self.wagered = 0
        self.unknown = 0
        self.nwin = 0
        self.total = 0

        sys.stdout.write("Strategy: %s\n" % self.strat_name.encode('utf-8'))
        sys.stdout.write("Starting with BANK of %s BTC\n" % format(
            self.bankroll, '.8f'))
        sys.stdout.write("Target: %s BTC\n" % format(self.target, '.8f'))

        # Keep rolling.
        # Press Control-C to stop early.
        try:
            while self.nrolls:
                if self.careful:
                    raw_input("Press enter for betting once.")
                self.nrolls -= 1
                self._roll()
        except KeyboardInterrupt:
            pass

        sys.stderr.write('\nWin ratio: %d/%d = %g\n' % (self.nwin, self.total,
            float(self.nwin)/self.total if self.total else 0))
        if self.unknown > 0:
            sys.stderr.write("Unknown outcomes: %d\n" % self.unknown)
        sys.stderr.write("Wagered: %s\n" % self.wagered)
        sys.stderr.write("Final bank roll: %s\n" % format(self.bankroll,'.8f'))
        return self.bankroll


    @property
    def win_chance(self):
        return self._win_chance
    @win_chance.setter
    def win_chance(self, value):
        self._win_chance = value
        self.payout = (Decimal(100) - self.house_edge) / value

    # You might want to override the following methods to do
    # whatever your strategy needs.
    def pre_roll(self):
        pass

    def win(self):
        if self.reset_on_win: self.to_bet = self.start_bet
        else: self.to_bet *= self.win_multiplier

    def lose(self):
        if self.reset_on_lose: self.to_bet = self.start_bet
        else: self.to_bet *= self.lose_multiplier
    #


    def _roll(self):
        self.pre_roll()

        if not self.bankroll or self.bankroll < self.to_bet or (
                self.bankroll - self.to_bet) < self.getout:
            # Can't play :/
            self.nrolls = 0
            return
        elif self.bankroll >= self.target or not self.nrolls:
            # Ok, I got enough (you wish).
            self.nrolls = 0
            return

        sys.stdout.write('Bet: %s BTC\n' % format(self.to_bet, '.8f'))
        self.wagered += self.to_bet
        roll_mode = 'HIGH' if self.roll_high else 'LOW'
        self.total += 1
        self.unknown += 1
        won_bet, num = roll_dice(self.justdice,
                win_chance=self.win_chance,
                amount=0 if self.simulation else self.to_bet,
                roll_hi=self.roll_high)
        self.unknown -= 1

        if won_bet:
            self.nwin += 1
            self.bankroll += (self.to_bet * self.payout - self.to_bet)
            self.win()
        else:
            self.bankroll -= self.to_bet
            self.lose()

        r = 'W' if won_bet else 'L'
        sys.stdout.write('%s %s (%s)\n' % (r, num, roll_mode))
        sys.stdout.write('BANK: %s\n' % format(self.bankroll, '.8f'))
        sys.stdout.flush()
        sys.stderr.write(r)
        sys.stderr.flush()


def run_strategy(func, params):
    strat = Strategy(func, params)
    strat.run()
    return strat
