from decimal import Decimal

from browserless_player import main, run_strategy

def strategy(justdice):
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

    run_strategy(justdice, locals())


if __name__ == "__main__":
    main(strategy)
