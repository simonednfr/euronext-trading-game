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

def calculate_standard_ratios(data):
    price = pd.to_numeric(data["ADJ CLOSE"], errors="raise")
    trailing_eps = pd.to_numeric(data["trailing EPS"], errors="raise")
    forward_eps = pd.to_numeric(data["forward EPS"], errors="raise")

    data["Trailing P/E"] = price / trailing_eps.where(trailing_eps > 0)
    data["Forward P/E"] = price / forward_eps.where(forward_eps > 0)

    enterprise_value = pd.to_numeric(data["Enterprise Value"])
    ebit = pd.to_numeric(data["EBIT"])
    ebitda = pd.to_numeric(data["EBITDA"])
    net_income = pd.to_numeric(data["NET INCOME"])
    common_equity = pd.to_numeric(data["COMMON SH. EQUITY"])
    eps_growth = pd.to_numeric(data["Yearly EPS growth"])

    data["EV/EBIT"] = enterprise_value / ebit.replace(0, float("nan"))
    data["EV/EBITDA"] = enterprise_value / ebitda.replace(0, float("nan"))
    data["ROE"] = net_income / common_equity.replace(0, float("nan"))
    # The workbook uses trailing P/E and expresses growth in percentage points.
    data["PEG"] = data["Trailing P/E"] / (100 * eps_growth.replace(0, float("nan")))

    data.columns.name = None
    data.index.name = "Ticker"
    return data


ratio_columns = ["Trailing P/E", "Forward P/E", "EV/EBIT", "EV/EBITDA", "ROE", "PEG"]
sector_sheets = ["industrial", "technology", "health care", "energy", "consumer", "utilities", "others"]
sector_ratios = {}
for sector in sector_sheets:
    data = pd.read_excel(workbook, sheet_name=sector, header=2, index_col="Ticker").T
    sector_ratios[sector] = calculate_standard_ratios(data)[ratio_columns]
    print(f"\n{sector.title()} ratios")
    print(sector_ratios[sector].to_string(
        float_format="{:.2f}".format,
        formatters={"ROE": "{:.2%}".format},
        na_rep="n.a.",
    ))


# Bank capital benchmark used in the reference workbook (RATIOS!C47).
cet1_benchmark = 0.112


def calculate_bank_ratios(data):
    price = pd.to_numeric(data["ADJ CLOSE"])
    tbv_per_share = pd.to_numeric(data["Tangible Book Value xSh"])
    net_income = pd.to_numeric(data["NET INCOME"])
    tangible_equity = pd.to_numeric(data["tangible common equity"])
    cet1 = pd.to_numeric(data["CET1 ratio (latest)"])

    ratios = pd.DataFrame(index=data.index)
    ratios.index.name = "Ticker"
    ratios["P/TBV"] = price / tbv_per_share.replace(0, float("nan"))
    ratios["ROTE"] = net_income / tangible_equity.replace(0, float("nan"))
    ratios["CET1"] = cet1
    ratios["CET1 headroom (pp)"] = (cet1 - cet1_benchmark) * 100
    return ratios


banks = pd.read_excel(workbook, sheet_name="financial", header=2, index_col="Ticker").T
sector_ratios["financial"] = calculate_bank_ratios(banks)

print("\nBank ratios")
print(sector_ratios["financial"].to_string(
    float_format="{:.2f}".format,
    formatters={"ROTE": "{:.2%}".format, "CET1": "{:.2%}".format},
    na_rep="n.a.",
))
