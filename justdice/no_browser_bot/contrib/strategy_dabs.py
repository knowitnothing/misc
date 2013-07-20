from decimal import Decimal

from browserless_player import main, run_strategy

def calc_tobet(bankroll, to_bet, multiplier):
    n = 0
    while to_bet < bankroll:
        n += 1
        print to_bet
        to_bet *= multiplier
    return n

#calc_tobet(Decimal('1.0'), Decimal('0.00001659'), Decimal('8.8219'))
#raise SystemExit

def dabs(justdice):
    # Settings for this strategy.
    win_chance = Decimal('87.7779')             # %
    bankroll = Decimal('1')                     # BTC
    to_bet =   Decimal('0.00001658') * bankroll # Starting BTC amount to bet.
    lose_multiplier = Decimal('8.8219') # Multiply bet by this amount on a lose.
    reset_on_win = True         # Reset to_bet to its original value on a win.

    target =   Decimal('2')     # Amount to reach in BTC.
    # Other settings.
    strat_name = u'Dabs'  # Strategy name.
    roll_high = True      # Roll high ?
    simulation = True # Only 0 BTC bets will be performed when this is True.
    #
    run_strategy(justdice, locals())

main(dabs)
