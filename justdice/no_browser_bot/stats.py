#
# Browserless Bot for collecting data from just-dice.com
#

import sys
import time

from browserless_driver import load_justdice, JustDiceSocket

class GetStats(JustDiceSocket):
    def __init__(self, output, *args):
        super(GetStats, self).__init__(*args)
        self.out = open(output, 'a')
        self.fields = ['timestamp', 'bets', 'profit', 'purse', 'wagered']
        self.got_result = False
        self._working = False

    def on_result(self, result):
        if self._working:
            return
        self._working = True
        stats = result['stats']
        stats['timestamp'] = int(time.time())
        line = ','.join(map(str, [stats[field] for field in self.fields]))
        self.out.write("%s\n" % line)
        self.got_result = True

print "Connecting.."
response, _ = load_justdice()
sys.stdout.write("Waiting for result..")
justdice = GetStats('out.csv', response, None)
now = time.time()
max_wait_time = 10 # seconds
while not justdice.got_result and time.time() - now < max_wait_time:
    sys.stdout.write('.')
    sys.stdout.flush()
    time.sleep(0.1)
print
if not justdice.got_result:
    print "No results this time"
