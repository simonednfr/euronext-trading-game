from pathlib import Path

import pandas as pd

workbook = Path(__file__).resolve().parent / "data" / "market_data.xlsx"

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