import requests
import pandas as pd
import time
import re
import os
from datetime import datetime

# Your identity - SEC EDGAR requires this in every request
HEADERS = {
    "User-Agent": "Akash Chaudhary akash.ch2122@gmail.com"
}

# The date range we want - 11 years of data
START_DATE = "2015-01-01"
END_DATE = "2026-03-20"

# Import our list of 20 companies
from companies import COMPANIES


def get_cik(ticker):
    """Step 1 - Get the CIK number for a company using its ticker symbol"""
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(tickers_url, headers=HEADERS)
    data = response.json()

    for key in data:
        if data[key]["ticker"] == ticker.upper():
            cik = str(data[key]["cik_str"]).zfill(10)
            return cik

    return None


def get_filings(cik, ticker):
    """Step 2 - Get all Form 4 filings for a company using its CIK number"""
    url = "https://data.sec.gov/submissions/CIK{}.json".format(cik)
    response = requests.get(url, headers=HEADERS)
    data = response.json()

    filings = data.get("filings", {}).get("recent", {})

    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession_numbers = filings.get("accessionNumber", [])

    form4_filings = []

    for i in range(len(forms)):
        if forms[i] == "4":
            filing_date = dates[i]
            if START_DATE <= filing_date <= END_DATE:
                form4_filings.append({
                    "ticker": ticker,
                    "cik": cik,
                    "filing_date": filing_date,
                    "accession_number": accession_numbers[i]
                })

    return form4_filings


def parse_form4(accession_number, cik, ticker, filing_date):
    """Step 3 - Read the actual Form 4 and extract the trade details"""
    acc_formatted = accession_number.replace("-", "")
    cik_int = int(cik)

    # Step 3a - Get the filing index page to find the actual XML filename
    index_url = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}-index.htm".format(
        cik_int, acc_formatted, accession_number
    )

    index_response = requests.get(index_url, headers=HEADERS)

    if index_response.status_code != 200:
        return None

    # Find the XML file in the index page
    # We want the XML file but NOT the one with xslF345X05 in the path
    content = index_response.text
    xml_files = re.findall(r'href="([^"]*\.xml)"', content)

    # Filter out the stylesheet XML and get the raw data XML
    xml_file = None
    for f in xml_files:
        if 'xslF345X05' not in f:
            xml_file = f
            break

    if xml_file is None:
        return None

    # Build the full URL for the XML file
    xml_url = "https://www.sec.gov{}".format(xml_file)

    # Download the actual XML file
    response = requests.get(xml_url, headers=HEADERS)

    if response.status_code != 200:
        return None

    content = response.text

    # Extract the key information using simple text search
    def extract_value(xml, tag):
        start = xml.find("<{}>".format(tag))
        end = xml.find("</{}>".format(tag))
        if start != -1 and end != -1:
            raw = xml[start + len(tag) + 2:end].strip()
            clean = re.sub(r'<[^>]+>', '', raw)
            clean = ' '.join(clean.split())
            return clean if clean else None
        return None

    # Get insider details
    insider_name = extract_value(content, "rptOwnerName")
    insider_role = extract_value(content, "officerTitle")

    # Only keep CEO and CFO trades
    if insider_role is None:
        return None

    insider_role_upper = insider_role.upper()
    ceo_titles = [
        "CEO", "CFO", "CHIEF EXECUTIVE", "CHIEF FINANCIAL",
        "PRINCIPAL EXECUTIVE", "PRINCIPAL FINANCIAL",
        "PRESIDENT AND CEO", "CO-CEO", "TECHNOKING",
        "CHIEF EXECUTIVE OFFICER", "CHIEF FINANCIAL OFFICER"
    ]
    if not any(title in insider_role_upper for title in ceo_titles):
        return None

    # Get transaction details
    transaction_date = extract_value(content, "transactionDate")
    shares = extract_value(content, "transactionShares")
    price = extract_value(content, "transactionPricePerShare")
    transaction_type = extract_value(content, "transactionAcquiredDisposedCode")

    return {
        "ticker": ticker,
        "insider_name": insider_name,
        "insider_role": insider_role,
        "transaction_date": transaction_date,
        "shares": shares,
        "price_per_share": price,
        "transaction_type": transaction_type,
        "filing_date": filing_date
    }


def collect_all_data():
    """Main function - runs everything for all 20 companies"""
    all_trades = []

    print("Starting SEC EDGAR data collection...")
    print("This will collect Form 4 filings for {} companies".format(len(COMPANIES)))

    for company in COMPANIES:
        ticker = company["ticker"]
        name = company["name"]

        print("\nProcessing: {} ({})".format(name, ticker))

        # Step 1 - Get CIK
        cik = get_cik(ticker)
        if cik is None:
            print("  Could not find CIK for {}".format(ticker))
            continue
        print("  CIK found: {}".format(cik))

        # Step 2 - Get all Form 4 filings
        filings = get_filings(cik, ticker)
        print("  Found {} Form 4 filings".format(len(filings)))

        # Step 3 - Parse each filing
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

            # Wait 0.1 seconds between requests
            time.sleep(0.1)

        print("  CEO/CFO trades found: {}".format(trades_found))

        # Wait 1 second between companies
        time.sleep(1)

    # Save everything to a CSV file
    if all_trades:
        df = pd.DataFrame(all_trades)
        output_path = "data/insider_trades_raw.csv"
        df.to_csv(output_path, index=False)
        print("\n✅ Done! Saved {} trades to {}".format(len(all_trades), output_path))
        print(df.head())
    else:
        print("No trades found - check the script for errors")


# Run the main function
if __name__ == "__main__":
    collect_all_data()