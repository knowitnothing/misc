from decimal import Decimal

from browserless_player import main, Strategy

class MyStrategy(Strategy):
    def __init__(self, justdice, kwargs):
        super(MyStrategy, self).__init__(justdice, kwargs)
        self.double_after_n = kwargs['double_after_n']
        self.consec_lose = 0

    def win(self):
        super(MyStrategy, self).win()
        self.consec_lose = 0

    def lose(self):
        super(MyStrategy, self).lose()
        self.consec_lose += 1
        if not self.consec_lose % self.double_after_n:
            self.to_bet *= 2

def syphen(justdice):
    # Settings for this strategy.
    win_chance = Decimal('16')  # %
    to_bet =   Decimal('0.01')  # Starting BTC amount to bet.
    reset_on_win = True         # Reset to_bet to its original value on a win.
    # Basic settings.
    bankroll = Decimal('1.0')   # BTC
    target =   Decimal('1.5')   # Amount to reach in BTC.
    getout =   Decimal('0.8')   # Stopping condition in BTC.
    # Other settings.
    strat_name = u'Syphen'      # Strategy name.
    roll_high = True            # Roll high ?
    simulation = True # Only 0 BTC bets will be performed when this is True.
    # Custom settings.
    double_after_n = 4  # Double bet after lossing n times.
    #

    strat = MyStrategy(justdice, locals())
    strat.run()

main(syphen)
