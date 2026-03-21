import requests

HEADERS = {"User-Agent": "Akash Chaudhary akash.ch2122@gmail.com"}

def investigate_filing(ticker, cik):
    """Look at what files are actually inside a Tesla Form 4 filing"""
    
    print("\nInvestigating {} ({})".format(ticker, cik))
    
    # Get all filings for this company
    url = "https://data.sec.gov/submissions/CIK{}.json".format(cik)
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    
    filings = data.get("filings", {}).get("recent", {})
    forms = filings.get("form", [])
    accession_numbers = filings.get("accessionNumber", [])
    dates = filings.get("filingDate", [])
    
    # Find the first 3 Form 4 filings
    count = 0
    for i in range(len(forms)):
        if forms[i] == "4" and count < 3:
            acc = accession_numbers[i]
            date = dates[i]
            acc_formatted = acc.replace("-", "")
            cik_int = int(cik)
            
            print("\n  Filing date: {}".format(date))
            print("  Accession: {}".format(acc))
            
            # Get the index page for this filing
            index_url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={}&type=4&dateb=&owner=include&count=10".format(cik)
            
            # Try the filing index directly
            filing_index_url = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}-index.json".format(
                cik_int, acc_formatted, acc
            )
            
            index_response = requests.get(filing_index_url, headers=HEADERS)
            
            if index_response.status_code == 200:
                index_data = index_response.json()
                files = index_data.get("documents", [])
                print("  Files in this filing:")
                for f in files:
                    print("    - {} ({})".format(f.get("name"), f.get("type")))
            else:
                print("  Could not get index page: {}".format(
                    index_response.status_code))
                
                # Try alternative - the htm index
                htm_url = "https://www.sec.gov/Archives/edgar/data/{}/{}/{}-index.htm".format(
                    cik_int, acc_formatted, acc
                )
                htm_response = requests.get(htm_url, headers=HEADERS)
                print("  HTM index status: {}".format(htm_response.status_code))
                if htm_response.status_code == 200:
                    # Look for xml files mentioned in the page
                    content = htm_response.text
                    import re
                    xml_files = re.findall(r'href="([^"]*\.xml)"', content)
                    print("  XML files found: {}".format(xml_files))
            
            count += 1

# Test with Tesla and Apple
investigate_filing("TSLA", "0001318605")
investigate_filing("AAPL", "0000320193")

