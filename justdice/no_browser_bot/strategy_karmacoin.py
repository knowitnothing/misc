from decimal import Decimal
from collections import deque

from browserless_player import main, Strategy

class MyStrategy(Strategy):
    def __init__(self, justdice, kwargs):
        super(MyStrategy, self).__init__(justdice, kwargs)
        self.setup()

    def setup(self):
        super(MyStrategy, self).setup()

        kwargs = self._orig_params

        self.max_losses_in_row = kwargs['max_losses_in_row']
        self.max_wins_in_row = kwargs['max_wins_in_row']
        self.num_rounds = kwargs['num_rounds']
        self.max_bet_pct = kwargs['max_bet_pct']
        self.breaker_pattern = kwargs['breaker_pattern']

        self.rem_rounds = self.num_rounds
        self.consec_win = 0
        self.consec_lose = 0
        self.max_patt_len = max(len(patt) for patt in self.breaker_pattern)

        self._bet_before_pat = None
        self._init_pattern()


    def _init_pattern(self):
        self.active_pattern = None
        self.curr_pattern = deque(maxlen=self.max_patt_len)
        self.rem_pattern_bet = 0

    def _update_pattern(self, win):
        self.curr_pattern.append(win)

        if not self.active_pattern:
            for patt in self.breaker_pattern:
                if len(patt) > len(self.curr_pattern):
                    continue
                for a, b in zip(reversed(self.curr_pattern), reversed(patt)):
                    if a != b:
                        break
                else:
                    # Found a matching pattern.
                    self.active_pattern = self.breaker_pattern[patt]
                    break
            if self.active_pattern is not None:
                # Hit the pattern!
                self._bet_before_pat = self.to_bet
                self.rem_pattern_bet = self.active_pattern['bets']
                self.to_bet = self.active_pattern['amount']

        if self.active_pattern:
            if self.rem_pattern_bet == 0:
                # Resume the strategy.
                self.to_bet = self._bet_before_pat
                self._init_pattern()
            else:
                self.rem_pattern_bet -= 1
            return False
        else:
            return True

    def win(self):
        if not self._update_pattern(True):
            return

        self.consec_win += 1
        self.consec_lose = 0

        if self.consec_win >= self.max_wins_in_row:
            self.consec_win = 0
            self.to_bet = self.start_bet
            self.rem_rounds -= 1
            if self.rem_rounds <= 0:
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
        if not self._update_pattern(False):
            return

        self.consec_win = 0
        self.consec_lose += 1
        if self.consec_lose >= self.max_losses_in_row:
            self.consec_lose = 0
            self.to_bet = self.start_bet


def strategy(justdice):

    strat_name = u'karma.coin'

    bankroll = Decimal('1')      # BTC
    win_chance = Decimal('80')   # %
    to_bet = Decimal('0.00015')  # Initial bet size (BTC)
    win_multiplier = Decimal('6')
    roll_high = False

    # Custom options for this strategy.
    max_losses_in_row = 4        # Reset to the initial bet.
    max_wins_in_row = 2          # Reset to the initial bet.
    num_rounds = 24
    max_bet_pct = Decimal('0.8') # Bet at max 80% of the current bankroll.

    breaker_pattern = {
            (False, True, False, True): {
                'bets': 7, 'amount': Decimal('0.000075')},
            (False, False): {
                'bets': 5, 'amount': Decimal('0')}
    }

    # Other settings.
    simulation = True # Only 0 BTC bets will be performed when this is True.

    strat = MyStrategy(justdice, locals())
    strat.run()


if __name__ == "__main__":
    main(strategy, new_seed=True)
