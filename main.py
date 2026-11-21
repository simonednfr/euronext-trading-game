import hashlib
import os
import tempfile
import sys
from pathlib import Path

import pandas as pd

def check_issuer_limits(weights):
    tolerance = 1e-12
    clustered = weights[weights > 0.05 + tolerance].sum()
    return weights.max() <= 0.10 + tolerance, clustered, clustered <= 0.40 + tolerance


def test_issuer_limits():
    # Weights are percentages of total NAV; the remaining allocation is cash.
    cases = [
        ("Exactly 5% excluded", [5, 5], True, 0, True),
        ("Above 5% counts in full", [5.01, 5], True, 5.01, True),
        ("Exactly 10% and 40%", [10, 10, 10, 10, 5], True, 40, True),
        ("Single issuer above 10%", [10.01], False, 10.01, True),
        ("Six issuers at 6%", [6] * 6, True, 36, True),
        ("Seven issuers at 6%", [6] * 7, True, 42, False),
    ]
    for name, percentages, issuer_ok, combined, aggregate_ok in cases:
        actual_issuer, actual_weight, actual_aggregate = check_issuer_limits(pd.Series(percentages) / 100)
        if (actual_issuer != issuer_ok or abs(actual_weight * 100 - combined) > 1e-9
                or actual_aggregate != aggregate_ok):
            raise AssertionError(f"{name}: unexpected result {(actual_issuer, actual_weight, actual_aggregate)}")
        print(f"PASS | {name} | combined {actual_weight:.2%}")
    print(f"All {len(cases)} synthetic scenarios matched expectations.")


if __name__ == "__main__" and sys.argv[1:] == ["--check-51040"]:
    test_issuer_limits()
    sys.exit(0)


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
phase_in = 0.50  # Portfolio-wide decision for held positions: 0.50 or 1.00.
starting_cash = 50_000
equity_budget = 0.90
stock_cap = 0.06
sector_cap = 0.20
no_trade_tolerance = 0.005


def weekly_order_sheet(book, sector, positions, marks, cash, nav):
    # Include out-of-universe holdings in projected issuer and sector exposures.
    sheet = book.join(signals[["Valuation", "Quality", "Eligible", "Peer group"]])
    outside = positions.index.difference(sheet.index)
    for ticker in outside:
        sheet.loc[ticker, ["Quantity", "Close", "Trade shares", "Action"]] = [
            positions[ticker], marks[ticker], 0, "Outside pool"
        ]
    sheet.index.name = "Ticker"
    sheet["Sector"] = sector.reindex(sheet.index)
    sheet.loc[sheet.index == "ENX.PA", "Sector"] = "financial"
    if sheet["Sector"].isna().any():
        raise ValueError("Assign a platform sector to every holding before checking limits.")
    trade_value = sheet["Trade shares"] * sheet["Close"]
    sheet["Projected quantity"] = sheet["Quantity"] + sheet["Trade shares"]
    weight = sheet["Projected quantity"] * sheet["Close"] / nav
    sheet["Projected issuer weight"] = weight
    sector_weight = weight.groupby(sheet["Sector"]).transform("sum")
    sheet["Projected sector weight"] = sector_weight
    sheet["Above stock cap"] = weight > stock_cap + 1e-12
    sheet["Above sector cap"] = sector_weight > sector_cap + 1e-12
    issuer_ok, clustered, aggregate_ok = check_issuer_limits(weight)
    projected_cash = cash - trade_value.sum()
    sheet["Projected cash EUR"] = projected_cash
    sheet["Cash sufficient"] = projected_cash >= -0.005
    sheet["Largest issuer within 10%"] = issuer_ok
    sheet["Weight in issuers above 5%"] = clustered
    sheet["Within 40% limit"] = aggregate_ok
    sheet["5/10/40 result"] = "PASS" if issuer_ok and aggregate_ok else "BREACH"
    sheet["Trade value EUR"] = trade_value
    order = sheet["Trade shares"].map(lambda qty: 0 if qty < 0 else 1 if qty > 0 else 2)
    sheet = sheet.loc[order.sort_values(kind="stable").index]
    sheet.insert(0, "Review date", prices.index[-1].date())
    for label, path in [("Workbook", workbook), ("Fills", trade_path), ("Code", Path(__file__))]:
        sheet[label + " SHA256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    payload = sheet.to_csv().encode()
    revision = hashlib.sha256(payload).hexdigest()[:16]
    folder = workbook.parent.parent / "reports" / "decisions"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{prices.index[-1]:%Y-%m-%d}_{revision}.csv"
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=folder, delete=False) as tmp:
            tmp.write(payload)
        try:
            os.replace(tmp.name, target)
        finally:
            Path(tmp.name).unlink(missing_ok=True)
    print(f"Decision sheet: {target}")
    print("Projected 5/10/40:", "PASS" if issuer_ok and aggregate_ok else "BREACH")
    print(f"Projected cash EUR {projected_cash:,.2f} | largest issuer {weight.max():.2%} | "
          f"largest sector {sector_weight.max():.2%} | issuers above 5% combined {clustered:.2%}")
    if (not sheet["Cash sufficient"].all() or sheet["Above stock cap"].any()
            or sheet["Above sector cap"].any() or not sheet["Largest issuer within 10%"].all()
            or not sheet["Within 40% limit"].all()):
        print("Review projected limit breaches before execution.")


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
    held_position = book["Quantity"].gt(0)
    fraction = pd.Series(0.50, index=book.index).where(~held_position, phase_in)
    book["Tranche fraction"] = fraction.where(active)
    phased = (fraction * full).clip(lower=current).clip(upper=full)
    book["Phased weight"] = phased
    target_qty = (phased * nav / book["Close"]).astype("int64")
    within_tolerance = book["Quantity"].gt(0) & phased.gt(0) & (current - phased).abs().lt(no_trade_tolerance)
    book["Trade shares"] = (target_qty - book["Quantity"]).where(~within_tolerance, 0)
    trade = book["Trade shares"]
    book["Action"] = "No trade"
    book.loc[trade.gt(0) & ~held_position, "Action"] = "First tranche"
    book.loc[trade.gt(0) & held_position, "Action"] = "Top-up" if phase_in == 1 else "Add to first tranche"
    book.loc[trade.lt(0), "Action"] = "Reduce"
    book.loc[trade.lt(0) & book["Signal"].eq("Sell All"), "Action"] = "Sell all"
    print(f"\nNew entries 50% | held target {phase_in:.0%} | portfolio EUR {nav:,.2f} | cash EUR {cash:,.2f}")
    print(book.to_string(formatters={"Full weight": "{:.2%}".format, "Phased weight": "{:.2%}".format}))
    weekly_order_sheet(book, sector, positions, marks, cash, nav)
    return book


tranche_orders = size_tranche()


def build_portfolio_history(prices, fills, initial_cash):
    """Value executed positions at each session close from the first fill."""
    if fills.empty:
        return pd.DataFrame()
    dates = prices.index[prices.index >= fills["Date"].min()]
    if not dates.is_unique or not fills["Date"].isin(dates).all():
        raise ValueError("Check the price calendar: each fill needs a unique trading session.")
    if fills["Price"].isna().any() or fills["Price"].le(0).any():
        raise ValueError("Portfolio history requires a positive execution or gift price for each fill.")

    changes = fills.pivot_table(index="Date", columns="Ticker", values="Signed quantity", aggfunc="sum")
    holdings = changes.reindex(dates).fillna(0).cumsum()
    if holdings.lt(0).any().any():
        raise ValueError("Trade history produces a negative end-of-day position.")
    marks = prices.reindex(index=dates, columns=holdings.columns).copy()
    gifts = fills["Operation"].eq("Gift")
    gift_reference_used = pd.Series(False, index=dates)
    if "ENX.PA" in holdings:
        gift_prices = fills.loc[gifts & fills["Ticker"].eq("ENX.PA")].groupby("Date")["Price"].last()
        reference = gift_prices.reindex(dates).ffill()
        gift_reference_used = holdings["ENX.PA"].gt(0) & marks["ENX.PA"].isna() & reference.notna()
        marks["ENX.PA"] = marks["ENX.PA"].fillna(reference)
    unavailable = holdings.gt(0) & (marks.isna() | marks.le(0))
    if unavailable.any().any():
        date, ticker = unavailable.stack().loc[lambda missing: missing].index[0]
        raise ValueError(f"Missing closing price for held position {ticker} on {date:%Y-%m-%d}.")

    amounts = fills["Signed quantity"] * fills["Price"]
    cash_flow = -amounts.where(~gifts, 0).groupby(fills["Date"]).sum()
    contributions = amounts.where(gifts, 0).groupby(fills["Date"]).sum()
    history = pd.DataFrame(index=dates)
    history["Cash"] = initial_cash + cash_flow.reindex(dates, fill_value=0).cumsum()
    history["Securities"] = (holdings * marks).sum(axis=1)
    history["Total value"] = history["Cash"] + history["Securities"]
    history["Gift contribution"] = contributions.reindex(dates, fill_value=0)
    history["Contributed capital"] = initial_cash + history["Gift contribution"].cumsum()
    history["P&L"] = history["Total value"] - history["Contributed capital"]
    # Treat gifts as contributions available at the start of the session.
    previous_value = history["Total value"].shift(1, fill_value=initial_cash)
    history["Daily return"] = history["Total value"] / (previous_value + history["Gift contribution"]) - 1
    history["Cumulative return"] = (1 + history["Daily return"]).cumprod() - 1
    history["Gift reference price used"] = gift_reference_used
    sector_map = screen_inputs["Sheet"].to_dict()
    sector_map.update({"AI.PA": "materials", "ORA.PA": "communications", "KPN.AS": "communications", "ENX.PA": "financial"})
    market_values = (holdings * marks).fillna(0)
    weights = market_values.div(history["Securities"].replace(0, float("nan")), axis=0)
    sectors = weights.T.groupby([sector_map[t] for t in weights.columns]).sum().T
    concentration = weights.pow(2).sum(axis=1, min_count=1)
    history["Stock HHI"] = 10_000 * concentration
    history["Effective holdings"] = 1 / concentration
    history["Sector HHI"] = (10_000 * sectors.pow(2).sum(axis=1)).where(history["Securities"] > 0)
    history["Holdings"] = holdings.gt(0).sum(axis=1)
    history["Sectors held"] = sectors.gt(0).sum(axis=1)

    # PF RISK models screened equities only, using each valuation date's weights.
    risk_returns = prices.pct_change(fill_method=None)
    ratios = []
    risk_paths = []
    for date, allocation in weights.iterrows():
        active = allocation[allocation.gt(0) & allocation.index.isin(screen_inputs.index)]
        window = risk_returns.loc[:date, active.index].tail(60)
        ratio = float("nan")
        risk = [float("nan")] * 3
        if not active.empty and len(window) == 60 and window.notna().all().all():
            invested_returns = window @ active
            basket_vol = invested_returns.std()
            portfolio_returns = invested_returns * history.at[date, "Securities"] / history.at[date, "Total value"]
            path = (1 + portfolio_returns).cumprod()
            risk = [portfolio_returns.std() * 252 ** 0.5, path.iloc[-1] - 1,
                    (path / path.cummax().clip(lower=1) - 1).min()]
            if basket_vol > 0:
                ratio = window.std().dot(active) / basket_vol
        ratios.append(ratio)
        risk_paths.append(risk)
    history[["Pro forma volatility", "Pro forma 60d return", "Pro forma 60d max drawdown"]] = risk_paths
    history["Diversification ratio"] = ratios
    return history


portfolio_history = build_portfolio_history(prices, executed, starting_cash)
if not portfolio_history.empty:
    history_path = workbook.parent.parent / "reports" / "portfolio_history.csv"
    history_path.parent.mkdir(exist_ok=True)
    portfolio_history.to_csv(history_path, index_label="Date")
    print("\nDaily portfolio history")
    print(portfolio_history[["Cash", "Securities", "Total value", "P&L", "Cumulative return"]].to_string(
        float_format="{:,.2f}".format, formatters={"Cumulative return": "{:.2%}".format}
    ))
    print(f"Saved {history_path}")



def build_position_tracker(fills, closing_prices, portfolio_value):
    balances = {}
    sales = []
    marks = closing_prices.copy()
    for fill in fills.sort_values("Date", kind="stable").itertuples():
        ticker = fill.Ticker
        shares, basis = balances.get(ticker, (0, 0.0))
        if fill.Operation == "Sell":
            if fill.Quantity > shares:
                raise ValueError(f"Sale exceeds shares held: {ticker} on {fill.Date:%Y-%m-%d}")
            sold_basis = basis * (fill.Quantity / shares)
            proceeds = fill.Price * fill.Quantity
            sales.append([ticker, fill.Date, fill.Quantity, fill.Price, sold_basis, proceeds - sold_basis])
            shares -= fill.Quantity
            basis = basis - sold_basis if shares else 0.0
        else:
            shares += fill.Quantity
            basis += fill.Quantity * fill.Price
            if fill.Operation == "Gift" and ticker == "ENX.PA" and pd.isna(closing_prices.get(ticker)):
                marks[ticker] = fill.Price
        balances[ticker] = shares, basis

    positions = []
    for ticker, (shares, basis) in balances.items():
        if shares > 0:
            price = marks[ticker]
            value = price * shares
            positions.append([ticker, shares, basis / shares, price, value, value / portfolio_value, value - basis])

    open_positions = pd.DataFrame(positions, columns=[
        "Ticker", "Quantity", "Average cost", "Latest price", "Market value", "Weight", "Unrealised P&L"
    ]).set_index("Ticker")
    closed_trades = pd.DataFrame(sales, columns=[
        "Ticker", "Sale date", "Quantity sold", "Sale price", "Cost basis sold", "Realised P&L"
    ])
    return open_positions, closed_trades


if not portfolio_history.empty:
    closing = portfolio_history.iloc[-1]
    open_positions, closed_trades = build_position_tracker(executed, latest, closing["Total value"])
    realised = closed_trades["Realised P&L"].sum()
    unrealised = open_positions["Unrealised P&L"].sum()
    if abs(realised + unrealised - closing["P&L"]) > 0.005:
        raise ValueError("Position tracker P&L does not reconcile to portfolio history.")
    open_positions.to_csv(history_path.with_name("open_positions.csv"))
    closed_trades.to_csv(history_path.with_name("closed_trades.csv"), index=False)
    print(f"\nOpen positions | {closing.name:%d %B %Y}")
    print(open_positions.to_string(float_format="{:,.2f}".format, formatters={"Weight": "{:.2%}".format}))
    print("\nClosed trades")
    print(closed_trades.to_string(index=False, float_format="{:,.2f}".format))
    print(f"Realised EUR {realised:,.2f} | Unrealised EUR {unrealised:,.2f} | Total EUR {realised + unrealised:,.2f}")


if not portfolio_history.empty:
    returns = portfolio_history["Daily return"]
    wealth_index = 100 * (1 + portfolio_history["Cumulative return"])
    peak = wealth_index.cummax().clip(lower=100)
    drawdown = wealth_index / peak - 1
    weeks = returns.index.to_period("W-FRI")
    weekly = pd.DataFrame({
        "Through date": returns.index.to_series().groupby(weeks).last(),
        "Sessions this week": returns.groupby(weeks).count(),
        "Weekly return": (1 + returns).groupby(weeks).prod() - 1,
        "Since inception return": portfolio_history["Cumulative return"].groupby(weeks).last(),
        "Closing drawdown": drawdown.groupby(weeks).last(),
        "Maximum drawdown to date": drawdown.cummin().groupby(weeks).last(),
    }).set_index("Through date")
    annualisation = 252 ** 0.5
    weekly["Realised volatility since inception"] = returns.expanding(min_periods=2).std() * annualisation
    weekly["Realised volatility 60 sessions"] = returns.rolling(60).std() * annualisation
    compounded = (1 + weekly["Weekly return"]).cumprod() - 1
    if (compounded - weekly["Since inception return"]).abs().max() > 1e-10:
        raise ValueError("Weekly returns do not reconcile to daily portfolio history.")
    diversification_columns = ["Holdings", "Sectors held", "Stock HHI", "Sector HHI", "Effective holdings", "Diversification ratio"]
    risk_columns = ["Pro forma volatility", "Pro forma 60d return", "Pro forma 60d max drawdown"]
    weekly = weekly.join(portfolio_history[diversification_columns + risk_columns], how="left")
    weekly.to_csv(history_path.with_name("weekly_performance.csv"))
    print("\nWeekly portfolio performance and risk")
    print(weekly.drop(columns=diversification_columns).to_string(float_format="{:.2%}".format, na_rep="n.a."))
    print("\nWeekly diversification")
    print(weekly[diversification_columns].to_string(float_format="{:.2f}".format, na_rep="n.a."))

    readme_path = workbook.parent.parent / "README.md"
    start_marker = "<!-- portfolio:start -->"
    end_marker = "<!-- portfolio:end -->"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""
    if readme.count(start_marker) == readme.count(end_marker) == 1 and readme.index(start_marker) < readme.index(end_marker):
        first = portfolio_history.iloc[0]
        last_week = weekly.iloc[-1]
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        curve = portfolio_history["Cumulative return"] * 100
        chart_path = history_path.with_name("portfolio_performance.svg")
        with plt.rc_context({"svg.hashsalt": "euronext-performance", "svg.fonttype": "none",
                             "font.family": "DejaVu Sans", "font.size": 10}):
            fig, ax = plt.subplots(figsize=(10, 2.8), layout="constrained")
            fig.patch.set_facecolor("#f5f8f7")
            ax.set_facecolor("#f5f8f7")
            ax.axhline(0, color="#71857f", linewidth=0.9)
            ax.fill_between(curve.index, curve, 0, color="#c4ded5", alpha=0.8)
            ax.plot(curve.index, curve, color="#146751", linewidth=2.3)
            ax.scatter(curve.index[-1], curve.iloc[-1], color="#146751", s=30, zorder=3)
            ax.set_title("Cumulative portfolio return", loc="left", weight="bold", color="#183d33")
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda value, _: f"{value:g}%"))
            locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
            ax.grid(axis="y", color="#d9e3df", linewidth=0.7)
            ax.set_axisbelow(True)
            ax.spines[:].set_visible(False)
            ax.tick_params(length=0, pad=6, colors="#405c53")
            fig.savefig(chart_path, format="svg", metadata={"Date": None})
            plt.close(fig)

        def euros(value):
            return f"{'−' if value < 0 else ''}€{abs(value):,.2f}"

        vol = last_week["Realised volatility since inception"]
        vol_label = f"{vol:.2%}" if pd.notna(vol) else "Pending second session"
        hhi = closing["Stock HHI"]
        hhi_label = f"{hhi:,.2f}" if pd.notna(hhi) else "No invested holdings"
        lines = [
            f"**At the close of {closing.name:%d %B %Y}** · {len(returns)} trading sessions",
            "",
            "| Portfolio value | Total P&L | Return since inception |",
            "| ---: | ---: | ---: |",
            f"| **{euros(closing['Total value'])}** | **{euros(closing['P&L'])}** | **{closing['Cumulative return']:.2%}** |",
            "",
            "![Daily cumulative portfolio return since inception](reports/portfolio_performance.svg)",
            "",
            "| Capital and earnings | EUR | Risk and diversification | Value |",
            "| --- | ---: | --- | ---: |",
            f"| Starting cash | {euros(starting_cash)} | Annualised realised volatility | {vol_label} |",
            f"| Starting capital with gift | {euros(first['Contributed capital'])} | Current drawdown | {last_week['Closing drawdown']:.2%} |",
            f"| Realised P&L | {euros(realised)} | Maximum drawdown | {last_week['Maximum drawdown to date']:.2%} |",
            f"| Unrealised P&L | {euros(unrealised)} | Stock HHI | {hhi_label} |",
            "",
        ]
        before = readme.split(start_marker, 1)[0]
        after = readme.split(end_marker, 1)[1]
        updated = before + start_marker + "\n" + "\n".join(lines) + "\n" + end_marker + after
        if updated != readme:
            readme_path.write_text(updated, encoding="utf-8")
