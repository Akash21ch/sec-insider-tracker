import requests
import pandas as pd
import time
import re
import os
from datetime import datetime
from sec_collector import get_cik, get_filings, parse_form4

# Only the NEW companies
NEW_COMPANIES = [
    {"name": "Morgan Stanley", "ticker": "MS"},
    {"name": "Citigroup",      "ticker": "C"},
    {"name": "AbbVie",         "ticker": "ABBV"},
    {"name": "UnitedHealth",   "ticker": "UNH"},
    {"name": "Chevron",        "ticker": "CVX"},
    {"name": "ConocoPhillips", "ticker": "COP"},
    {"name": "Costco",         "ticker": "COST"},
    {"name": "Target",         "ticker": "TGT"},
]


HEADERS = {"User-Agent": "Akash Chaudhary akash.ch2122@gmail.com"}
START_DATE = "2015-01-01"
END_DATE = datetime.today().strftime('%Y-%m-%d')

def collect_new_companies():
    all_trades = []

    print("Collecting data for 21 NEW companies only...")

    for company in NEW_COMPANIES:
        ticker = company["ticker"]
        name = company["name"]

        print("\nProcessing: {} ({})".format(name, ticker))

        cik = get_cik(ticker)
        if cik is None:
            print("  Could not find CIK for {}".format(ticker))
            continue
        print("  CIK found: {}".format(cik))

        filings = get_filings(cik, ticker)
        print("  Found {} Form 4 filings".format(len(filings)))

        trades_found = 0
        for filing in filings:
            trade = parse_form4(
                filing["accession_number"],
                filing["cik"],
                filing["ticker"],
                filing["filing_date"]
            )
            if trade is not None:
                all_trades.append(trade)
                trades_found += 1
            time.sleep(0.1)

        print("  CEO/CFO trades found: {}".format(trades_found))
        time.sleep(1)

    if all_trades:
        # Load existing raw data
        existing = pd.read_csv('data/insider_trades_raw.csv')
        new_df = pd.DataFrame(all_trades)

        # Combine old and new
        combined = pd.concat([existing, new_df], ignore_index=True)
        combined.to_csv('data/insider_trades_raw.csv', index=False)
        print("\n✅ Done! Total trades now: {}".format(len(combined)))
        print("New trades added: {}".format(len(new_df)))
    else:
        print("No trades found for new companies")

if __name__ == "__main__":
    collect_new_companies()
