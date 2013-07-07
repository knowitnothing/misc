#
# Browserless Bot for collecting data from just-dice.com
#

import time
from browserless_driver import load_justdice, JustDiceSocket

class GetStats(JustDiceSocket):
    def __init__(self, *args):
        super(GetStats, self).__init__(*args)

    def on_result(self, result):
        print result['stats']


print "Connecting.."
response = load_justdice()
justdice = GetStats(response, None)
justdice.sock.wait()
