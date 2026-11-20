from pathlib import Path

import pandas as pd

#storing the market data file

workbook = Path(__file__).resolve().parent / "data" / "market_data.xlsx"

#reading and extraction of prices

prices = pd.read_excel(
    workbook,
    sheet_name="ADJ CLOSE",
    header=2,
    index_col="Date",
    parse_dates=True,
).sort_index()

latest = prices.iloc[-1]
print(f"Latest trading date: {latest.name:%d %B %Y}")
print(f"Trading dates: {len(prices)}")
print(f"Prices available: {latest.count()} of {len(latest)}")

# daily returns, SMA100, Vol60

daily_returns = prices.pct_change(fill_method=None)
sma_100 = prices.rolling(window=100).mean()
vol_60 = daily_returns.rolling(window=60).std(ddof=1) * (252 ** 0.5)

summary = pd.DataFrame({
    "Adjusted close | ": prices.iloc[-1],
    "Daily return | ": daily_returns.iloc[-1],
    "100-day SMA | ": sma_100.iloc[-1],
    "Distance from SMA | ": prices.iloc[-1] / sma_100.iloc[-1] - 1,
    "Annualised volatility | ": vol_60.iloc[-1],
})
summary.index.name = "Ticker"

print(f"\nMarket summary | {prices.index[-1]:%d %B %Y}")
print(summary.to_string(formatters={
    "Adjusted close": "{:.2f}".format,
    "Daily return": "{:.2%}".format,
    "100-day SMA": "{:.2f}".format,
    "Distance from SMA": "{:+.2%}".format,
    "Annualised volatility": "{:.2%}".format,
}))

industrials = pd.read_excel(
    workbook,
    sheet_name="industrial",
    header=2,
    index_col="Ticker",
).T

price = pd.to_numeric(industrials["ADJ CLOSE"], errors="raise")
trailing_eps = pd.to_numeric(industrials["trailing EPS"], errors="raise")
forward_eps = pd.to_numeric(industrials["forward EPS"], errors="raise")

industrials["Trailing P/E"] = price / trailing_eps.where(trailing_eps > 0)
industrials["Forward P/E"] = price / forward_eps.where(forward_eps > 0)

print(industrials[["Trailing P/E", "Forward P/E"]].round(2))

industrials.index.name = "Ticker"
