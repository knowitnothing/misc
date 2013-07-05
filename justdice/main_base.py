import sys
from decimal import Decimal

from justdice_selenium import Justdice

def run_strategy(justdice, roll, kwargs):
    # Required parameters.
    win_chance = kwargs['win_chance']
    to_bet = kwargs['to_bet']
    bankroll = kwargs['bankroll']
    target = kwargs['target']
    simulation = kwargs['simulation']
    # Optional parameters.
    roll_high = kwargs.get('roll_high', True)
    getout = kwargs.get('getout', Decimal('0'))
    strat_name = kwargs.get('strat_name', 'no name')
    lose_multiplier = kwargs.get('lose_multiplier', 1)
    win_multiplier = kwargs.get('win_multiplier', 1)
    reset_on_win = kwargs.get('reset_on_win', False)
    reset_on_lose = kwargs.get('reset_on_lose', False)


    start_bet = kwargs['to_bet']
    payout = (Decimal(100) - justdice.house_edge) / win_chance

    # Game stats
    unknown = 0
    win = 0
    total = 0

    sys.stdout.write("Strategy: %s\n" % strat_name.encode('utf-8'))
    sys.stdout.write("Starting with BANK of %s BTC\n" % format(bankroll,'.8f'))
    sys.stdout.write("Target: %s BTC\n" % format(target, '.8f'))

    # Keep rolling.
    try:
        # Press Control-C to stop early.

        while bankroll >= to_bet and (bankroll - to_bet) >= getout:
            if bankroll >= target:
                # Ok, I got enough (you wish).
                break

            sys.stdout.write('Bet: %s BTC\n' % format(to_bet, '.8f'))

            roll_mode = 'HIGH' if roll_high else 'LOW'
            result, num = roll(
                    win_chance=win_chance,
                    btc_to_bet=0 if simulation else to_bet,
                    high=roll_high)
            if not result:
                sys.stderr.write('Bet took too long, reloading.\n')
                justdice.reload_page()
                roll = justdice.bet_prepare()
                unknown += 1
                continue

            total += 1
            if result > 0: # Win
                win += 1
                bankroll += to_bet * payout - to_bet
                to_bet *= win_multiplier
                if reset_on_win:
                    to_bet = start_bet
            else:
                bankroll -= to_bet
                to_bet *= lose_multiplier
                if reset_on_lose:
                    to_bet = start_bet

            sys.stdout.write('%s %s (%s)\n' % ('W' if result > 0 else 'L',
                num, roll_mode))
            sys.stdout.write('BANK: %s\n' % format(bankroll, '.8f'))
            sys.stdout.flush()
            sys.stderr.write('.')
            sys.stderr.flush()

    except KeyboardInterrupt:
        pass

    sys.stderr.write('\nWin ratio: %d/%d = %g\n' % (win, total,
            float(win)/total) if total else 0)
    sys.stderr.write("Final bank roll: %s\n" % bankroll)
    return bankroll


def main(args, func):
    if len(args) < 3:
        sys.stderr.write('Usage: %s username password [-dummy]\n' % args[0])
        raise SystemExit

    user, pwd = args[1:3]

    if len(sys.argv) == 4 and args[3].startswith('-d'):
        from justdice_dummy_driver import DummyDriver
        driver = DummyDriver()
    else:
        from selenium import webdriver
        driver = webdriver.Firefox()

    try:
        justdice = Justdice(driver)
        justdice.login(user, pwd)

        roll = justdice.bet_prepare(new_seed='1')
        func(justdice, roll)
    finally:
        sys.stderr.write('Leaving..\n')
        driver.quit()

