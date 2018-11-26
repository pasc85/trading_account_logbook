# trading_account_logbook

This package allows to keep track of activities, gains, and losses of a
investment portfolio. Use commands to log purchase and sales of shares,
dividends, and to update the value of the portfolio.

The basic feature of the package is that it can produce tables containing
the relative value of each share. This takes into account the purchase date,
purchase price and fee, dividends that were paid, the current value of the
shares, the sales fee, and the number of days for which the investment was
held. A relative value of p means that the investment is equivalent to having
put the purchase amount into a savings account with continously compounded
interest of p percent per year.

A number of additional tools are provided, e.g. a method that computes bond
prices. The significance of p values can be understood by analysing historic
data, cf. the demo notebook. The notebook ta_work can be used for working on
the account -- it contains a list of all callable functions (for which the
docstrings can be displayed).
