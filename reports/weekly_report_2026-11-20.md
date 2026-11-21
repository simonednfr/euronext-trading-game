# Euronext Trading Game | Weekly report

Week ended 20 November 2026. Results reproduced from Git revision [632ebca](https://github.com/simonednfr/euronext-trading-game/tree/632ebca18ca995eec812645c5ed45c6efba5f183).

The portfolio returned −2.25% this week and −2.06% since inception. Closing value was €49,140.83 against €50,176.90 contributed. Annualised realised volatility was 5.41% across 13 daily observations. Maximum drawdown was 2.25%.

| Week ended | Weekly return | Holdings | Sectors | Stock HHI | Sector HHI | Effective holdings | Diversification ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2026-11-06 | -0.52% | 7 | 7 | 1,627.59 | 1,627.59 | 6.14 | 1.80 |
| 2026-11-13 | 0.72% | 15 | 9 | 793.17 | 1,496.18 | 12.61 | 2.01 |
| 2026-11-20 | -2.25% | 15 | 9 | 793.72 | 1,493.02 | 12.60 | 1.85 |

Stock HHI measures concentration across securities. Each weight is market value divided by total invested securities. Squared weights are summed and multiplied by 10,000. Cash is excluded and the gifted Euronext share is included. Sector HHI uses aggregate sector weights. Effective holdings equal 10,000 divided by stock HHI. The current 15 holdings have the concentration of 12.60 equally weighted holdings.

Stock HHI moved only 0.55 points during the week. The volatility diversification ratio fell from 2.01 to 1.85. This ratio uses closing weights and 60 historical daily stock returns for screened equities, dividing weighted-average stock volatility by basket volatility. The gift is outside the screened universe. Official platform diversification scores have yet to be reconciled.

## P&L and reconciliation

Realised P&L across four sales was −€55.66. Unrealised P&L on 15 positions was −€980.41. Their sum, −€1,036.07, reconciles to model portfolio value less contributed capital. The €176.90 gift is included in contributed capital.

| 20 November | Model | Platform | Difference |
|---|---:|---:|---:|
| Cash | €27,727.37 | €27,729.88 | −€2.51 |
| Securities | €21,413.46 | €21,413.62 | −€0.16 |
| Total | €49,140.83 | €49,143.50 | −€2.67 |

Platform values are from the supplied account snapshot. The difference remains unreconciled. Both returns round to −2.06%.

To reproduce, run `python main.py` at the linked revision. Market prices run through 20 November and executed fills through 13 November.
