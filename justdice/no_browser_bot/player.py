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
        if roll_dice(justdice, win_chance, amount, roll_hi):
            win += 1

    return win, nroll


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print "WARNING user and password were not specified."
        print "Expected usage: %s user password [-dummy]" % sys.argv[0]
        print "***" * 15

    dummy = False
    if len(sys.argv) == 4 and sys.argv[3].startswith('-d'):
        dummy = True
    main(play, *sys.argv[1:3], dummy=dummy)
