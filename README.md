# Euronext Trading Game

The strategy screens equities against sector peers, uses a 100-session moving average for entries and exits, and sizes positions by inverse volatility.
Daily adjusted closes from Yahoo Finance and manually updated company fundamentals feed the [market workbook](data/market_data.xlsx). Portfolio results use [executed game trades](data/trades.csv).

## Portfolio dashboard

<!-- portfolio:start -->
**20 November 2026 close** · 13 trading sessions · EUR

| Portfolio measure | Value |
| --- | ---: |
| Starting cash | €50,000.00 |
| Starting capital including opening gifts | €50,176.90 |
| **Current portfolio value** | **€49,140.83** |
| Realised P&L | −€55.66 |
| Unrealised P&L | −€980.41 |
| **Total P&L** | **−€1,036.07** |
| Return since inception | -2.06% |
| Realised volatility · annualised since inception | 5.41% |
| Current drawdown | -2.25% |
| Maximum drawdown since inception | -2.25% |
| **Stock HHI** | **793.72** |
<!-- portfolio:end -->

Stock HHI measures issuer concentration on a 0–10,000 scale using each security’s share of invested assets. Cash is excluded. Drawdowns are measured from the running peak of the portfolio return index.

[Weekly reports](reports/) · [Strategy code](main.py)

### Refresh locally

With pandas and openpyxl installed, run `python main.py` after saving the workbook and trade register. Commit the refreshed README and reports with the inputs used for that review.
