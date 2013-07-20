from decimal import Decimal

from browserless_player import main, Strategy

class MyStrat(Strategy):
    def __init__(self, *args, **kwargs):
        super(MyStrat, self).__init__(*args, **kwargs)
        self._bet = [1, 3, 7, 15, 32]
        self._curr_bet = 0

    def win(self):
        self._curr_bet = 0
        self.to_bet = self._bet[self._curr_bet]

    def lose(self):
        self._curr_bet = (self._curr_bet + 1) % len(self._bet)
        self.to_bet = self._bet[self._curr_bet]

def kaiousama(justdice):
    # Settings for this strategy.
    win_chance = Decimal('49.5')   # %
    to_bet =   Decimal('1')        # Starting BTC amount to bet.
    # Basic settings.
    bankroll = Decimal('500')      # BTC
    target = Decimal('1000')       # BTC
    getout =   Decimal('100')      # Stopping condition in BTC.
    # Other settings.
    strat_name = u'kaiousama'      # Strategy name.
    roll_high = True               # Roll high ?
    simulation = True # Only 0 BTC bets will be performed when this is True.
    #
    strat = MyStrat(justdice, locals())
    strat.run()

main(kaiousama)
