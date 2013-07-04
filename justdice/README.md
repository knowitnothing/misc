What are these things ?
=======================

Around here you will find things for testing gambling strategies that
can be directly applied in https://just-dice.com (the current code can
be modified to perform other tasks in that site too). The gambling is
performed using Python and Selenium (you might need to
`easy_install selenium` if you don't have it).

Everything is mostly undocumented for the moment, feel free to find out
how it works by yourself. If you hit any issues, you are welcome to report
them.


Testing a gambling strategy
===========================

So you have a new wonderful gambling strategy and want to find out how
it performs ? Excellent. In order to do that, this repository provides
an [example strategy](strategy_weirdo.py), a dummy selenium driver
that mimics the behavior that matters from https://just-dice.com, and
a [basic plot](game_performance.py) using Matplotlib.

The output from the strategy can directly used as input to the plotter,
as in:

	python strategy_weirdo.py user pwd -d | python game_performance perf.png

The username and password passed to "strategy\_weirdo.py" is irrelevant when
the "-d" flag is passed, since this flag uses the dummy driver which does not
ever touch the actual gambling site. The resulting PNG file (in this example)
might look like this:

	![takecare](https://raw.github.com/knowitnothing/misc/justdice/img/perf.png)

In this example, the starting bank roll had 1 Bitcoin, the target was set to 1.6 BTC,
and the blue line indicates the balance after each roll. This strategy employed
a crazy betting of 0.001 BTC at 0.2% winning chance, which worked (this time).

After you are convinced your strategy can work, all you need to do is
drop the "-d" flag and then it will be applied in the actual site.
