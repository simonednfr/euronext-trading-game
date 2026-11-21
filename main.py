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



# Net executed fills through the market date. Gifts count as shares held.
trade_path = workbook.parent / "trades.csv"
trades = (pd.read_csv(trade_path) if trade_path.exists() else
          pd.DataFrame(columns=["Date", "Ticker", "Operation", "Quantity"]))
trades["Date"] = pd.to_datetime(trades["Date"], format="%Y-%m-%d", errors="raise")
if trades[["Date", "Ticker", "Operation", "Quantity"]].isna().any().any():
    raise ValueError("A trade is missing its date, ticker, operation or quantity.")
direction = trades["Operation"].map({"Buy": 1, "Gift": 1, "Sell": -1})
if direction.isna().any() or not trades["Quantity"].gt(0).all():
    raise ValueError("Trades require Buy, Sell or Gift and a positive quantity.")
trades["Signed quantity"] = trades["Quantity"] * direction
executed = trades.loc[trades["Date"] <= prices.index[-1]]
quantities = executed.groupby("Ticker")["Signed quantity"].sum()
if quantities.lt(0).any():
    raise ValueError("The trade register contains a negative net position.")

signals = fundamental_screen.copy()
signals["Quantity"] = quantities.reindex(signals.index, fill_value=0)
signals["Close"] = prices.iloc[-1]
signals["SMA100"] = sma_100.iloc[-1]
signals["Lower"] = 0.99 * signals["SMA100"]
signals["Upper"] = 1.01 * signals["SMA100"]
above = signals["Close"] > signals["Upper"]
below = signals["Close"] < signals["Lower"]
held = signals["Quantity"] > 0
hold_ok = (signals["Valuation"] <= 1.0) & (signals["Quality"] >= -1.5)
bank = signals["Sheet"] == "financial"
headroom = sector_ratios["financial"]["CET1 headroom (pp)"].reindex(signals.index)
hold_ok &= ~bank | headroom.ge(0)

signals["Signal"] = "Stay Out"
signals.loc[~held & signals["Eligible"] & above, "Signal"] = "Eligible"
signals.loc[held, "Signal"] = "Stay In"
signals.loc[held & above, "Signal"] = "Retain and Size"
signals.loc[held & (~hold_ok | below), "Signal"] = "Sell All"
missing = signals[["Close", "SMA100", "Eligible"]].isna().any(axis=1)
signals.loc[missing | (bank & headroom.isna()), "Signal"] = "Check data"

if not trade_path.exists():
    signals["Quantity"] = pd.NA
    signals["Signal"] = "Load trade register"

print(f"\nEntry and exit signals | {prices.index[-1]:%d %B %Y}")
print(signals[["Quantity", "Close", "Lower", "Upper", "Signal"]].to_string(
    float_format="{:.2f}".format, na_rep="n.a."
))


# Weekly execution settings from PORTFOLIO and VOL. SIZING.
phase_in = 0.50  # Set to 1.00 for the second tranche.
starting_cash = 50_000
equity_budget = 0.90
stock_cap = 0.06
sector_cap = 0.20
no_trade_tolerance = 0.005


def size_tranche():
    if not trade_path.exists() or signals["Signal"].eq("Check data").any():
        print("Sizing pending: check the trade register and signal inputs.")
        return
    positions = quantities[quantities > 0]
    marks = latest.reindex(positions.index).copy()
    gift_fills = executed.loc[executed["Operation"].eq("Gift") & executed["Ticker"].eq("ENX.PA")]
    if "ENX.PA" in positions and pd.isna(marks["ENX.PA"]) and not gift_fills.empty:
        marks["ENX.PA"] = gift_fills["Price"].iloc[-1]
        print(f"ENX.PA valued at gift reference price: EUR {marks['ENX.PA']:.2f}")
    fills = executed.loc[executed["Operation"].ne("Gift")]
    if marks.isna().any() or marks.le(0).any() or fills["Price"].isna().any() or fills["Price"].le(0).any():
        print("Sizing pending: missing or invalid holding or execution price.")
        return
    cash = starting_cash - (fills["Signed quantity"] * fills["Price"]).sum()
    nav = cash + (positions * marks).sum()
    if nav <= 0:
        print("Sizing pending: portfolio value must be positive.")
        return

    book = signals[["Signal", "Quantity", "Close"]].copy()
    active = book["Signal"].isin(["Eligible", "Retain and Size", "Stay In"])
    vol = vol_60.iloc[-1].reindex(book.index)
    if (active & (vol.isna() | vol.le(0))).any() or book["Close"].le(0).any():
        print("Sizing pending: check prices and active-stock volatility.")
        return
    inverse_vol = 1 / vol.where(active)
    capped = (equity_budget * inverse_vol / inverse_vol.sum()).fillna(0).clip(upper=stock_cap)
    sector = signals["Sheet"].replace({"others": "communications"}).copy()
    sector.loc[sector.index == "AI.PA"] = "materials"
    sector_total = capped.groupby(sector).transform("sum")
    book["Full weight"] = capped * (sector_cap / sector_total.where(sector_total > 0)).fillna(1).clip(upper=1)

    current = book["Quantity"] * book["Close"] / nav
    full = book["Full weight"]
    phased = (phase_in * full).clip(lower=current).clip(upper=full)
    book["Phased weight"] = phased
    target_qty = (phased * nav / book["Close"]).astype("int64")
    within_tolerance = book["Quantity"].gt(0) & phased.gt(0) & (current - phased).abs().lt(no_trade_tolerance)
    book["Trade shares"] = (target_qty - book["Quantity"]).where(~within_tolerance, 0)
    print(f"\nWeekly tranche {phase_in:.0%} | portfolio EUR {nav:,.2f} | cash EUR {cash:,.2f}")
    print(book.to_string(formatters={"Full weight": "{:.2%}".format, "Phased weight": "{:.2%}".format}))
    return book


tranche_orders = size_tranche()
