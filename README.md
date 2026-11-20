# Euronext Trading Game

I present to you the Python implementation of my equity strategy for the Euronext Trading Game. The strategy combines sector-specific fundamental screening with price trends and volatility to guide weekly portfolio decisions.

## Current implementation

Running [main.py](main.py) prints two tables. The first summarises the latest trading session across the stock universe. The second compares trailing and forward earnings multiples for industrial companies.

| Measure | Calculation |
| --- | --- |
| Daily return | Percentage change in adjusted close from the preceding session |
| 100-day moving average | Arithmetic mean of the last 100 adjusted closes |
| Distance from moving average | Latest adjusted close divided by the 100-day average, minus one |
| Annualised volatility | Sample standard deviation of the last 60 daily returns, multiplied by √252 |
| Industrial trailing and forward P/E | Adjusted close divided by trailing or forecast earnings per share, respectively. A multiple is reported only for positive earnings. |

The market summary also reports the latest date and the number of tickers with a price on that date. Missing prices are left unfilled when calculating returns. A rolling measure requires a complete window of observations.

## Run locally

With the project’s Python environment active, run these commands from the repository root:

```bash
python -m pip install pandas openpyxl
python main.py
```

In PyCharm, select the same interpreter and run `main.py` to see the tables in the Run window.

## Weekly data update

1. Open [the market data workbook](data/market_data.xlsx). Add the new trading dates and adjusted closes to the `ADJ CLOSE` sheet under the existing ticker headers. Update fundamentals when new figures are available.
2. Save the workbook and run `main.py`. Check the printed date and price count against the new entries before using the results.
3. Commit the workbook with the market date in the commit message and push it to GitHub. The commit identifies the input snapshot used for that week’s analysis.

## Reporting scope

The Python implementation currently covers the market summary and industrial P/E calculations. The broader strategy also includes sector rankings, position sizing, and a ledger of opened and closed trades. Bringing those components into Python will connect each weekly decision to its inputs for the final trading-game report.
