#
# Browserless Bot for playing at just-dice.com
#
# This is an example for the standard Martingale strategy.
#
from decimal import Decimal

from browserless_player import main, run_strategy


def martingale(justdice):
    # Settings for this strategy.
    win_chance = Decimal('50')  # %
    to_bet =   Decimal('0.001') # Starting BTC amount to bet.
    lose_multiplier = Decimal('2') # Multiply bet by this amount on a lose.
    reset_on_win = True         # Reset to_bet to its original value on a win.
    # Basic settings.
    bankroll = Decimal('1.0')   # BTC
    target =   Decimal('1.6')   # Amount to reach in BTC.
    getout =   Decimal('0.1')   # Stopping condition in BTC.
    # Other settings.
    strat_name = u'Martingale'  # Strategy name.
    roll_high = True            # Roll high ?
    simulation = True # Only 0 BTC bets will be performed when this is True.
    #
    run_strategy(justdice, locals())

main(martingale)
