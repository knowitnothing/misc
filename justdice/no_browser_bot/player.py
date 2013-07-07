#
# Browserless Bot for playing at just-dice.com
#
# Create your own strategy by redifining the "play" function.
#

import sys
from decimal import Decimal

from browserless_player import main, roll_dice

def play(justdice):
    # XXX Define your strategy here.
    win = 0     # Win count.
    nroll = 40  # Roll n times.

    amount = Decimal('0')     # Amount in BTC to bet.
    roll_hi = False
    win_chance = Decimal('2') # %.

    for _ in xrange(nroll):
        if roll_dice(justdice, win_chance, amount, roll_hi, True)[0]:
            win += 1

    sys.stderr.write("\nWin ratio: %d/%d = %s\n" % (
        win, nroll, Decimal(win) / nroll if nroll else 0))


if __name__ == "__main__":
    main(play)
