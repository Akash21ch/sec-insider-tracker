import pandas as pd
import re
import os

def clean_xml_tags(value):
    """Remove any XML tags from a value like <value>392.74</value>"""
    if pd.isna(value):
        return None
    # Convert to string first
    value = str(value)
    # Remove all XML tags
    clean = re.sub(r'<[^>]+>', '', value)
    # Remove extra whitespace and newlines
    clean = ' '.join(clean.split())
    # Return None if empty string
    return clean if clean else None


def clean_numeric(value):
    """Convert a value to a number, return None if not possible"""
    cleaned = clean_xml_tags(value)
    if cleaned is None:
        return None
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def clean_date(value):
    """Clean and standardise a date value"""
    cleaned = clean_xml_tags(value)
    if cleaned is None:
        return None
    try:
        return pd.to_datetime(cleaned).strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return None


def clean_transaction_type(value):
    """Clean transaction type - should be A or D"""
    cleaned = clean_xml_tags(value)
    if cleaned is None:
        return None
    # Take just the first character in case there's extra text
    cleaned = cleaned.strip().upper()
    if cleaned in ['A', 'D']:
        return cleaned
    return None


def add_company_info(df):
    """Add sector and cap size to each trade using our companies list"""
    from companies import COMPANIES
    
    # Create a lookup dictionary from our companies list
    company_lookup = {}
    for company in COMPANIES:
        company_lookup[company['ticker']] = {
            'company_name': company['name'],
            'sector': company['sector'],
            'cap': company['cap']
        }
    
    # Add company info to each row
    df['company_name'] = df['ticker'].map(
        lambda x: company_lookup.get(x, {}).get('company_name', 'Unknown')
    )
    df['sector'] = df['ticker'].map(
        lambda x: company_lookup.get(x, {}).get('sector', 'Unknown')
    )
    df['cap_size'] = df['ticker'].map(
        lambda x: company_lookup.get(x, {}).get('cap', 'Unknown')
    )
    
    return df


def calculate_trade_value(df):
    """Calculate the total value of each trade in dollars"""
    df['trade_value_usd'] = df['shares'] * df['price_per_share']
    return df


def add_trade_labels(df):
    """Add human readable labels for transaction type"""
    df['trade_direction'] = df['transaction_type'].map({
        'A': 'BUY',
        'D': 'SELL'
    })
    return df

def classify_role(role):
    """Classify insider as CEO or CFO specifically"""
    if role is None:
        return "Other"
    role_upper = role.upper()
    if any(title in role_upper for title in [
        "CHIEF EXECUTIVE", "CEO", "PRINCIPAL EXECUTIVE", "TECHNOKING"
    ]):
        return "CEO"
    elif any(title in role_upper for title in [
        "CHIEF FINANCIAL", "CFO", "PRINCIPAL FINANCIAL"
    ]):
        return "CFO"
    else:
        return "Other"


def add_role_classification(df):
    """Add a clean CEO vs CFO column"""
    df['role_type'] = df['insider_role'].apply(classify_role)
    return df

def clean_data():
    """Main function - cleans the raw insider trades data"""
    
    # Check if raw data exists
    input_path = 'data/insider_trades_raw.csv'
    if not os.path.exists(input_path):
        print("No raw data found at {}".format(input_path))
        print("Please run sec_collector.py first!")
        return
    
    print("Loading raw data...")
    df = pd.read_csv(input_path)
    print("Loaded {} rows".format(len(df)))
    print("Columns: {}".format(list(df.columns)))
    
    print("\nCleaning data...")
    
    # Step 1 - Clean XML tags from all fields
    print("  Step 1: Removing XML tags...")
    df['transaction_date'] = df['transaction_date'].apply(clean_date)
    df['filing_date'] = df['filing_date'].apply(clean_date)
    df['shares'] = df['shares'].apply(clean_numeric)
    df['price_per_share'] = df['price_per_share'].apply(clean_numeric)
    df['transaction_type'] = df['transaction_type'].apply(clean_transaction_type)
    df['insider_name'] = df['insider_name'].apply(clean_xml_tags)
    df['insider_role'] = df['insider_role'].apply(clean_xml_tags)
    
    # Step 2 - Remove rows with missing critical data
    print("  Step 2: Removing incomplete rows...")
    before = len(df)
    df = df.dropna(subset=['transaction_date', 'shares', 'transaction_type'])
    after = len(df)
    print("  Removed {} incomplete rows".format(before - after))
    
    # Step 3 - Remove rows where shares is zero
    print("  Step 3: Removing zero share trades...")
    before = len(df)
    df = df[df['shares'] > 0]
    after = len(df)
    print("  Removed {} zero share rows".format(before - after))
    
    # Step 4 - Add company information
    print("  Step 4: Adding company info...")
    df = add_company_info(df)
    
    # Step 5 - Calculate trade value
    print("  Step 5: Calculating trade values...")
    df = calculate_trade_value(df)
    
    # Step 6 - Add human readable labels
    print("  Step 6: Adding trade direction labels...")
    df = add_trade_labels(df)

    # Step 7 - Classify CEO vs CFO
    print("  Step 7: Classifying CEO vs CFO...")
    df = add_role_classification(df)
    
    # Step 8 - Sort by date
    print("  Step 8: Sorting by date...")
    df = df.sort_values('transaction_date').reset_index(drop=True)
    
    # Step 9 - Add a year and month column
    print("  Step 9: Adding year and month columns...")
    df['year'] = pd.to_datetime(df['transaction_date']).dt.year
    df['month'] = pd.to_datetime(df['transaction_date']).dt.month
    
    # Save the clean data
    output_path = 'data/insider_trades_clean.csv'
    df.to_csv(output_path, index=False)
    
    print("\n✅ Cleaning complete!")
    print("Clean data saved to {}".format(output_path))
    print("Total trades: {}".format(len(df)))
    print("\nTrades by company:")
    print(df.groupby('ticker')['trade_direction'].value_counts())
    print("\nSample of clean data:")
    print(df[['ticker', 'insider_name', 'trade_direction', 
              'shares', 'price_per_share', 'transaction_date']].head(10))


# Run the main function
if __name__ == "__main__":
    clean_data()