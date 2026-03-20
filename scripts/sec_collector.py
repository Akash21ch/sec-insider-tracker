import requests
import pandas as pd
import time
import json
import os
from datetime import datetime

# Your identity - SEC EDGAR requires this in every request
HEADERS = {
    "User-Agent": "Akash Chaudhary akash.ch2122@gmail.com"
}

# The date range we want - 10 years of data
START_DATE = "2015-01-01"
END_DATE = "2026-03-20"

# Import our list of 20 companies
from companies import COMPANIES


def get_cik(ticker):
    """Step 1 - Get the CIK number for a company using its ticker symbol"""
    url = "https://efts.sec.gov/LATEST/search-index?q=%22{}%22&dateRange=custom&startdt=2015-01-01&enddt=2025-01-01&forms=4".format(ticker)
    
    # This URL gives us a list of all companies and their CIK numbers
    cik_url = "https://www.sec.gov/cgi-bin/browse-edgar?company=&CIK={}&type=4&dateb=&owner=include&count=40&search_text=&action=getcompany".format(ticker)
    
    # Use the company tickers JSON file from SEC - most reliable method
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    
    response = requests.get(tickers_url, headers=HEADERS)
    data = response.json()
    
    # Search through the data to find our ticker
    for key in data:
        if data[key]["ticker"] == ticker.upper():
            # CIK numbers need to be 10 digits with leading zeros
            cik = str(data[key]["cik_str"]).zfill(10)
            return cik
    
    return None


def get_filings(cik, ticker):
    """Step 2 - Get all Form 4 filings for a company using its CIK number"""
    url = "https://data.sec.gov/submissions/CIK{}.json".format(cik)
    
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    
    # The filings are stored inside the response
    filings = data.get("filings", {}).get("recent", {})
    
    # Get the lists we need
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession_numbers = filings.get("accessionNumber", [])
    
    # Filter to only Form 4 filings
    form4_filings = []
    
    for i in range(len(forms)):
        if forms[i] == "4":
            filing_date = dates[i]
            # Only keep filings within our date range
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
    # Format the accession number correctly for the URL
    acc_formatted = accession_number.replace("-", "")
    
    url = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}-index.htm".format(
        int(cik), acc_formatted, accession_number
    )
    
    # Build the XML file URL
    xml_url = "https://www.sec.gov/Archives/edgar/data/{}/{}/form4.xml".format(
        int(cik), acc_formatted
    )
    
    response = requests.get(xml_url, headers=HEADERS)
    
    if response.status_code != 200:
        return None
    
    # Parse the XML content
    content = response.text
    
    # Extract the key information using simple text search
    def extract_value(xml, tag):
        start = xml.find("<{}>".format(tag))
        end = xml.find("</{}>".format(tag))
        if start != -1 and end != -1:
            raw = xml[start + len(tag) + 2:end].strip()
            import re
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
        "transaction_type": transaction_type,  # A = Acquired (bought), D = Disposed (sold)
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
            
            # Wait 0.1 seconds between requests - be polite to SEC servers
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