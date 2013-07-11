from decimal import Decimal

from browserless_player import main, Strategy

class MyStrategy(Strategy):
    def __init__(self, justdice, kwargs):
        super(MyStrategy, self).__init__(justdice, kwargs)
        self.max_losses_in_row = kwargs['max_losses_in_row']
        self.max_wins_in_row = kwargs['max_wins_in_row']
        self.stage_one_left = kwargs['stage_one_left']
        self.max_bet_pct = kwargs['max_bet_pct']
        self.consec_win = 0
        self.consec_lose = 0

    def win(self):
        self.consec_win += 1
        self.consec_lose = 0

        if self.consec_win >= self.max_wins_in_row:
            self.consec_win = 0
            self.to_bet = self.start_bet
            self.stage_one_left -= 1
            if self.stage_one_left <= 0:
                # Stop now.
                self.nrolls = 0
                return
        else:
            self.to_bet *= self.win_multiplier

        # Limit the risk.
        bet_size = self.to_bet / self.bankroll
        if bet_size > self.max_bet_pct:
            self.to_bet = self.start_bet

    def lose(self):
        self.consec_win = 0
        self.consec_lose += 1
        if self.consec_lose >= self.max_losses_in_row:
            self.consec_lose = 0
            self.to_bet = self.start_bet


def strategy(justdice):

    strat_name = u'karma.coin'

    bankroll = Decimal('1')      # BTC
    win_chance = Decimal('85')   # %
    to_bet = Decimal('0.000001') # BTC
    win_multiplier = Decimal('2')
    roll_high = False

    # Custom options for this strategy.
    max_losses_in_row = 1        # Reset to the initial bet.
    max_wins_in_row = 20         # Reset to the initial bet.
    stage_one_left = 2
    max_bet_pct = Decimal('0.01')# Bet at max 1% of the current bankroll.

    # Other settings.
    simulation = True # Only 0 BTC bets will be performed when this is True.

    strat = MyStrategy(justdice, locals())
    strat.run()


if __name__ == "__main__":
    main(strategy, new_seed=True)
