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


def calculate_insurance_ratios(data):
    price = pd.to_numeric(data["ADJ CLOSE"])
    book_value_per_share = pd.to_numeric(data["Book Value x Share"])
    net_income = pd.to_numeric(data["NET INCOME"])
    common_equity = pd.to_numeric(data["COMMON SH. EQUITY"])
    tangible_equity = pd.to_numeric(data["tangible common equity"])

    ratios = pd.DataFrame(index=data.index)
    ratios.index.name = "Ticker"
    ratios["P/B"] = price / book_value_per_share.replace(0, float("nan"))
    ratios["ROE"] = net_income / common_equity.replace(0, float("nan"))
    ratios["ROTE"] = net_income / tangible_equity.replace(0, float("nan"))
    return ratios


insurers = pd.read_excel(workbook, sheet_name="insurance", header=2, index_col="Ticker").T
sector_ratios["insurance"] = calculate_insurance_ratios(insurers)

print("\nInsurance ratios")
print(sector_ratios["insurance"].to_string(
    float_format="{:.2f}".format,
    formatters={"ROE": "{:.2%}".format, "ROTE": "{:.2%}".format},
    na_rep="n.a.",
))


# Peer groups used only for fundamental screening.
other_peers = {"AI.PA": "industrial", "ORA.PA": "utilities", "KPN.AS": "utilities"}
screen_inputs = pd.concat(sector_ratios, names=["Sheet", "Ticker"]).reset_index("Sheet")
screen_inputs["Peer group"] = screen_inputs["Sheet"]
other = screen_inputs["Sheet"].eq("others")
screen_inputs.loc[other, "Peer group"] = [other_peers[ticker] for ticker in screen_inputs.index[other]]

screen_tables = []
peer_z_scores = {}
for peer, members in screen_inputs.groupby("Peer group", sort=False):
    valuation = ["Trailing P/E", "Forward P/E", "EV/EBIT", "EV/EBITDA", "PEG"]
    quality = ["ROE"]
    if peer == "financial":
        valuation, quality = ["P/TBV"], ["ROTE"]
    elif peer == "insurance":
        valuation, quality = ["P/B"], ["ROE", "ROTE"]

    inputs = members[valuation + quality].copy()
    if "PEG" in inputs:
        inputs["PEG"] = inputs["PEG"].where(inputs["PEG"] > 0)

    deviations = inputs - inputs.median()
    mad = deviations.abs().median()
    z = (deviations / (1.4826 * mad.replace(0, float("nan")))).clip(-3, 3)
    peer_z_scores[peer] = z

    scores = members[["Sheet", "Peer group"]].copy()
    scores["Valuation"] = z[valuation].mean(axis=1)
    scores["Quality"] = z[quality].mean(axis=1)
    eligible = (scores["Valuation"] <= 0.5) & (scores["Quality"] >= -1)
    if peer == "financial":
        eligible &= members["CET1 headroom (pp)"] >= 1.0
    scores["Eligible"] = eligible.astype("boolean").mask(scores[["Valuation", "Quality"]].isna().any(axis=1))
    scores["Peer rank"] = scores["Valuation"].rank(method="min").astype("Int64")
    screen_tables.append(scores)

fundamental_screen = pd.concat(screen_tables)
print("\nFundamental entry screen")
print(fundamental_screen.to_string(float_format="{:.3f}".format, na_rep="n.a."))
