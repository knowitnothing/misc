#
# See this strategy at
# http://wizardofodds.com/gambling/betting-systems/cancellation/
#
import sys
from decimal import Decimal

from browserless_player import main, Strategy

class MyStrategy(Strategy):
    def __init__(self, justdice, kwargs):
        super(MyStrategy, self).__init__(justdice, kwargs)
        self.paper = kwargs['paper']
        self.betting = 2

    def pre_roll(self):
        if not self.paper:
            # Win!!
            self.nrolls = 0
            return

        # Wager the sum of the number on the left and the number on the right.
        if len(self.paper)>1 and self.bankroll >= self.paper[0]+self.paper[-1]:
            self.betting = 2
            to_bet = self.paper[0] + self.paper[-1]
        elif self.bankroll >= self.paper[0]:
            self.betting = 1
            to_bet = self.paper[0]
        else:
            self.betting = 0
            to_bet = self.bankroll
        self.to_bet = to_bet

    def win(self):
        super(MyStrategy, self).win()
        # Cross the number on the left and the number on the right.
        if self.betting == 2:
            self.paper.pop(0)
            self.paper.pop()
        elif self.betting == 1:
            self.paper.pop(0)
        else:
            self.paper[0] -= self.to_bet

    def lose(self):
        super(MyStrategy, self).lose()
        # Place the sum at the end on the right.
        if self.betting == 2:
            self.paper.append(self.to_bet)
        elif self.betting == 1:
            self.paper[-1] += self.to_bet
        # otherwise your bankroll is gone :/


def strategy(justdice):

    strat_name = u'Cancellation/Labouchere'

    win_chance = Decimal('49.5')# 2x payout.
    bankroll = Decimal('1.0')   # BTC
    target = Decimal('2.0')     # BTC
    # Goal is to win x = (target - bankroll) bitcoins. For this example,
    # a unit will be x / num_units.
    num_units = 10
    to_bet = (target - bankroll) / num_units
    paper = [to_bet] * num_units

    # Other settings.
    roll_high = True
    simulation = True # Only 0 BTC bets will be performed when this is True.

    strat = MyStrategy(justdice, locals())
    strat.run()


if __name__ == "__main__":
    main(strategy)
