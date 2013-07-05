import sys
from matplotlib import pylab

strat_name = None
bank_start = None
target = None
bank = [] # bank over time

for line in sys.stdin:
    line = line.rstrip()
    if bank_start is not None and target is not None:
        if line.startswith('BANK:'):
            bank.append(float(line.split()[-1]))
    elif bank_start is not None:
        target = float(line.split()[-2])
    elif strat_name is not None:
        bank_start = float(line.split()[-2])
    else:
        strat_name = line

#print bank
print bank_start, target, bank[-1]

x_data = range(1 + len(bank))
y_data = [bank_start] + bank

pylab.plot(x_data, y_data)
pylab.axhline(y=bank_start, color='k', ls='--')
pylab.axhline(y=target, color='g', ls='--', lw=2)

pylab.xlim(x_data[0], x_data[-1] + 10)
pylab.ylim(min(y_data) - 0.01, max(y_data + [target]) + 0.01)

pylab.title(strat_name)
pylab.ylabel(u'BTC')
pylab.xlabel(u'Round')

if len(sys.argv) > 1:
    pylab.savefig(sys.argv[1], bbox_tight=True)
else:
    pylab.show()
