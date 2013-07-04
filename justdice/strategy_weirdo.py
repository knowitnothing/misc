import sys
from decimal import Decimal

from main_base import main

def strategy(justdice, roll):

    # Settings for this strategy.
    strat_name = u'weirdo 0.2%' # Some funny name for your strategy.
    win_chance = Decimal('0.2')  # %
    bankroll = Decimal('1.0')   # BTC
    target =   Decimal('1.6')   # Amount to reach in BTC.
    getout =   Decimal('0.1')   # Stopping condition in BTC.
    to_bet =   Decimal('0.001') # BTC
    roll_high = True
    simulation = True # Only 0 BTC bets will be performed when this is True.
    #

    payout = (Decimal(100) - justdice.house_edge) / win_chance

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
            else:
                bankroll -= to_bet

            sys.stdout.write('Bet: %s BTC\n' % format(to_bet, '.8f'))
            sys.stdout.write('%s %s (%s)\n' % ('W' if result > 0 else 'L',
                num, roll_mode))
            sys.stdout.write('BANK: %s\n' % format(bankroll, '.8f'))
            sys.stdout.flush()
            sys.stderr.write('\n')

    except KeyboardInterrupt:
        pass

    sys.stderr.write('Win ratio: %d/%d = %g\n' % (win, total,
            float(win)/total) if total else 0)


if __name__ == "__main__":
    main(sys.argv, strategy)
