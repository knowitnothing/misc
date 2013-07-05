import sys
from decimal import Decimal

from justdice_selenium import Justdice


def _handle_win(data):
    if data['reset_on_win']:
        data['to_bet'] = data['start_bet']
    else:
        data['to_bet'] *= data['win_multiplier']

def _handle_loss(data):
    if data['reset_on_lose']:
        data['to_bet'] = data['start_bet']
    else:
        data['to_bet'] *= data['lose_multiplier']

def run_strategy(justdice, roll, kwargs):
    data = {}
    # Required parameters.
    data['win_chance'] = kwargs['win_chance']
    data['to_bet'] = kwargs['to_bet']
    data['bankroll'] = kwargs['bankroll']
    data['target'] = kwargs['target']
    # Optional parameters.
    data['simulation'] = kwargs.get('simulation', True)
    data['roll_high'] = kwargs.get('roll_high', True)
    data['getout'] = kwargs.get('getout', Decimal('0'))
    data['strat_name'] = kwargs.get('strat_name', 'no name')
    data['lose_multiplier'] = kwargs.get('lose_multiplier', 1)
    data['win_multiplier'] = kwargs.get('win_multiplier', 1)
    data['reset_on_win'] = kwargs.get('reset_on_win', False)
    data['reset_on_lose'] = kwargs.get('reset_on_lose', False)


    data['start_bet'] = kwargs['to_bet']
    data['payout'] = (Decimal(100) - justdice.house_edge) / data['win_chance']

    # Game stats
    unknown = 0
    win = 0
    total = 0

    sys.stdout.write("Strategy: %s\n" % data['strat_name'].encode('utf-8'))
    sys.stdout.write("Starting with BANK of %s BTC\n" % format(
        data['bankroll'], '.8f'))
    sys.stdout.write("Target: %s BTC\n" % format(data['target'], '.8f'))

    # Keep rolling.
    try:
        # Press Control-C to stop early.

        while (data['bankroll'] >= data['to_bet'] and
                (data['bankroll'] - data['to_bet']) >= data['getout']):
            if data['bankroll'] >= data['target']:
                # Ok, I got enough (you wish).
                break

            sys.stdout.write('Bet: %s BTC\n' % format(data['to_bet'], '.8f'))

            roll_mode = 'HIGH' if data['roll_high'] else 'LOW'
            result, num = roll(
                    win_chance=data['win_chance'],
                    btc_to_bet=0 if data['simulation'] else data['to_bet'],
                    high=data['roll_high'])
            if not result:
                sys.stderr.write('Bet took too long, reloading.\n')
                justdice.reload_page()
                roll = justdice.bet_prepare()
                unknown += 1
                continue

            total += 1
            if result > 0: # Win
                win += 1
                data['bankroll'] += (data['to_bet'] * data['payout'] -
                                     data['to_bet'])
                _handle_win(data)
            else:
                data['bankroll'] -= data['to_bet']
                _handle_loss(data)

            r = 'W' if result > 0 else 'L'
            sys.stdout.write('%s %s (%s)\n' % (r, num, roll_mode))
            sys.stdout.write('BANK: %s\n' % format(data['bankroll'], '.8f'))
            sys.stdout.flush()
            sys.stderr.write(r)
            sys.stderr.flush()

    except KeyboardInterrupt:
        pass

    sys.stderr.write('\nWin ratio: %d/%d = %g\n' % (win, total,
            float(win)/total) if total else 0)
    sys.stderr.write("Final bank roll: %s\n" % data['bankroll'])
    return data['bankroll']


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

