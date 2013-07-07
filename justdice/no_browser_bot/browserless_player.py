import sys
import time
from decimal import Decimal

def main(play):
    new_seed = True
    args = sys.argv

    if len(args) < 3:
        sys.stderr.write("WARNING user and password were not specified.\n")
        sys.stderr.write("Expected usage: %s user password [-dummy]\n"%args[0])
        sys.stderr.write("***" * 15 + '\n')
        user, pwd = None, None
    else:
        user, pwd = args[1:3]

    if len(sys.argv) == 4 and args[3].startswith('-d'):
        from browserless_dummy import load_justdice, JustDiceSocket
    else:
        from browserless_driver import load_justdice, JustDiceSocket

    sys.stderr.write("Connecting...\n")
    response = load_justdice()
    login_info = {'user': user, 'pwd': pwd} if user is not None else None
    justdice = JustDiceSocket(response, login=login_info)
    sys.stderr.write("Logging in...")
    sys.stderr.flush()
    while not justdice.logged_in:
        if justdice.logged_in is None:
            # Could not login.
            justdice.sock.emit('disconnect')
            return
        sys.stderr.write('.')
        sys.stderr.flush()
        time.sleep(0.75)
    sys.stderr.write('\n')

    if new_seed:
        sys.stderr.write("Generating new server seed..\n")
        justdice.randomize()
        sys.stderr.write('\n')

    try:
        play(justdice)
        #win, total = play(justdice)
        #sys.stderr.write("\nWin ratio: %d/%d = %s\n" % (
        #    win, total, Decimal(win) / total if total else 0))
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
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()
        time.sleep(0.1)
    if verbose:
        print " %s %s" % (format(justdice.last_bet["lucky_number"], '07.4f'),
                "win!" if justdice.last_bet['win'] else "lose :/")

    return justdice.last_bet['win'], justdice.last_bet['lucky_number']



class Strategy(object):
    def __init__(self, justdice, kwargs):
        self.justdice = justdice
        self.house_edge = justdice.house_edge
        self.payout = None

        # Required parameters.
        self.win_chance = kwargs['win_chance']
        self.to_bet = kwargs['to_bet']
        self.bankroll = kwargs['bankroll']
        # Optional parameters.
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

        # Game stats
        self.unknown = 0
        self.nwin = 0
        self.total = 0


    def run(self):
        sys.stdout.write("Strategy: %s\n" % self.strat_name.encode('utf-8'))
        sys.stdout.write("Starting with BANK of %s BTC\n" % format(
            self.bankroll, '.8f'))
        sys.stdout.write("Target: %s BTC\n" % format(self.target, '.8f'))

        # Keep rolling.
        # Press Control-C to stop early.
        try:
            while self.nrolls:
                self.nrolls -= 1
                self._roll()
        except KeyboardInterrupt:
            pass

        sys.stderr.write('\nWin ratio: %d/%d = %g\n' % (self.nwin, self.total,
            float(self.nwin)/self.total) if self.total else 0)
        sys.stderr.write("Final bank roll: %s\n" % self.bankroll)
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
        if self.bankroll < self.to_bet or (
                self.bankroll - self.to_bet) < self.getout:
            # Can't play :/
            self.nrolls = 0
            return
        elif self.bankroll >= self.target:
            # Ok, I got enough (you wish).
            self.nrolls = 0
            return

        self.pre_roll()

        sys.stdout.write('Bet: %s BTC\n' % format(self.to_bet, '.8f'))
        roll_mode = 'HIGH' if self.roll_high else 'LOW'
        won_bet, num = roll_dice(self.justdice,
                win_chance=self.win_chance,
                amount=0 if self.simulation else self.to_bet,
                roll_hi=self.roll_high)

        self.total += 1
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
