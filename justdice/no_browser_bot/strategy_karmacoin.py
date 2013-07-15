from decimal import Decimal

from browserless_player import main, Strategy

class MyStrategy(Strategy):
    def __init__(self, justdice, kwargs):
        super(MyStrategy, self).__init__(justdice, kwargs)
        self.max_losses_in_row = kwargs['max_losses_in_row']
        self.max_wins_in_row = kwargs['max_wins_in_row']
        self.num_rounds = kwargs['num_rounds']
        self.max_bet_pct = kwargs['max_bet_pct']
        self.breaker_pattern = kwargs['breaker_pattern']
        self.breaker_bets = kwargs['breaker_bets']
        self.breaker_bet_amount = kwargs['breaker_bet_amount']

        self.consec_win = 0
        self.consec_lose = 0

        self._bet_before_pat = None
        self._init_pattern()


    def _init_pattern(self):
        self.hit_pattern = False
        self.n_pat = 0
        self.curr_pattern = [None] * len(self.breaker_pattern)
        self.rem_pattern_bet = 0

    def _update_pattern(self, win):
        self.curr_pattern[self.n_pat] = win
        self.n_pat = (self.n_pat + 1) % len(self.breaker_pattern)
        if not self.n_pat and self.curr_pattern == self.breaker_pattern:
            if not self.hit_pattern:
                # Hit the pattern!
                self._bet_before_pat = self.to_bet
                self.rem_pattern_bet = self.breaker_bets
                self.hit_pattern = True

        if self.hit_pattern:
            self.to_bet = self.breaker_bet_amount
            if self.rem_pattern_bet == 0:
                # Resume the strategy.
                self.to_bet = self._bet_before_pat
                self._init_pattern()
            else:
                self.rem_pattern_bet -= 1

    def win(self):
        self._update_pattern(True)
        if self.hit_pattern:
            return

        self.consec_win += 1
        self.consec_lose = 0

        if self.consec_win >= self.max_wins_in_row:
            self.consec_win = 0
            self.to_bet = self.start_bet
            self.num_rounds -= 1
            if self.num_rounds <= 0:
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
        self._update_pattern(False)
        if self.hit_pattern:
            return

        self.consec_win = 0
        self.consec_lose += 1
        if self.consec_lose >= self.max_losses_in_row:
            self.consec_lose = 0
            self.to_bet = self.start_bet


def strategy(justdice):

    strat_name = u'karma.coin'

    bankroll = Decimal('1')      # BTC
    win_chance = Decimal('65')   # %
    to_bet = Decimal('0.000001') # Initial bet size (BTC)
    win_multiplier = Decimal('3')
    roll_high = False

    # Custom options for this strategy.
    max_losses_in_row = 4        # Reset to the initial bet.
    max_wins_in_row = 2          # Reset to the initial bet.
    num_rounds = 240
    max_bet_pct = Decimal('0.01')# Bet at max 1% of the current bankroll.
    breaker_pattern = [False, True, False] # Loss, Win, Loss
    breaker_bets = 4 # Number of bets to do after hitting the pattern above.
    breaker_bet_amount = 0#Decimal('0.0001') # BTC

    # Other settings.
    simulation = True # Only 0 BTC bets will be performed when this is True.

    strat = MyStrategy(justdice, locals())
    strat.run()


if __name__ == "__main__":
    main(strategy, new_seed=True)
