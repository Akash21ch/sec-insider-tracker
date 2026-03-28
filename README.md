# SEC Insider Trading Tracker — Following the Smart Money

An end-to-end data pipeline analysing CEO and CFO insider trading activity across 50 leading US companies. Built to answer one question: **do executives actually time the market when they trade their own stock?**

## Key Findings

- **3,031 trades** analysed across 50 US companies — July 2023 to March 2026
- Insider buys returned **+6.22%** on average over 90 days vs **+3.84%** for the S&P 500
- Insider sells returned **+7.60%** — stocks kept rising even after executives sold
- CEO and CFO post-buy performance is virtually identical (6.13% vs 6.38%)
- Technology executives sold more than they bought — yet tech was the top performing sector

**Honest conclusion:** It's not the trades that drive returns — it's the quality of the companies these executives work for.

## Dashboard

[View the interactive Tableau dashboard →](https://public.tableau.com/app/profile/akash.chaudhary4621)
[View the portfolio website →](https://akash21ch.github.io/sec-insider-tracker)
[Read the findings report →](./SEC_Insider_Trading_Report.pdf)

## Project Structure
```
sec-insider-tracker/
├── scripts/
│   ├── companies.py           # 50 tracked companies with sector and cap metadata
│   ├── sec_collector.py       # Fetches Form 4 filings from SEC EDGAR API
│   ├── data_cleaner.py        # 9-step cleaning pipeline
│   ├── price_collector.py     # Historical prices via yfinance
│   ├── merge_columns.py       # Merges company metadata into returns dataset
│   └── new_companies_only.py  # Incremental company additions
├── data/                      # CSV files (gitignored)
├── build_site.py              # Regenerates portfolio website from latest data
├── index.html                 # Interactive portfolio website
└── requirements.txt
```

## Pipeline
```
SEC EDGAR API → sec_collector.py → insider_trades_raw.csv
                                          ↓
                               data_cleaner.py → insider_trades_clean.csv
                                          ↓
                              price_collector.py → stock_prices.csv
                                          ↓
                               merge_columns.py → trades_with_returns.csv
                                          ↓
                        Tableau Dashboard + Portfolio Website
```

## Tech Stack

| Component | Tool |
|-----------|------|
| Data collection | Python 3.10, SEC EDGAR API |
| Data cleaning | pandas — 9-step pipeline |
| Price & benchmark data | yfinance, SPY ETF |
| Visualisation | Tableau Public |
| Portfolio website | HTML, CSS, JavaScript, Chart.js |

## How to Run
```bash
# Install dependencies
pip install -r requirements.txt

# Collect SEC filings
python3 scripts/sec_collector.py

# Clean data
python3 scripts/data_cleaner.py

# Fetch stock prices
python3 scripts/price_collector.py

# Merge metadata
python3 scripts/merge_columns.py

# Rebuild website
python3 build_site.py
```

## Author

**Akash Chaudhary**
- GitHub: [Akash21ch](https://github.com/Akash21ch)
- Tableau: [akash.chaudhary4621](https://public.tableau.com/app/profile/akash.chaudhary4621)


---
*Data sourced from SEC EDGAR — all Form 4 filings are public record under Section 16 of the Securities Exchange Act.*