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

enterprise_value = pd.to_numeric(industrials["Enterprise Value"])
ebit = pd.to_numeric(industrials["EBIT"])
ebitda = pd.to_numeric(industrials["EBITDA"])
net_income = pd.to_numeric(industrials["NET INCOME"])
common_equity = pd.to_numeric(industrials["COMMON SH. EQUITY"])
eps_growth = pd.to_numeric(industrials["Yearly EPS growth"])

industrials["EV/EBIT"] = enterprise_value / ebit.replace(0, float("nan"))
industrials["EV/EBITDA"] = enterprise_value / ebitda.replace(0, float("nan"))
industrials["ROE"] = net_income / common_equity.replace(0, float("nan"))
# The workbook uses trailing P/E and expresses growth in percentage points.
industrials["PEG"] = industrials["Trailing P/E"] / (100 * eps_growth.replace(0, float("nan")))

industrials.columns.name = None
industrials.index.name = "Ticker"
ratio_columns = ["Trailing P/E", "Forward P/E", "EV/EBIT", "EV/EBITDA", "ROE", "PEG"]
print("\nIndustrial ratios")
print(industrials[ratio_columns].to_string(
    float_format="{:.2f}".format,
    formatters={"ROE": "{:.2%}".format},
    na_rep="n.a.",
))
