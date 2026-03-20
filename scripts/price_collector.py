import requests
import pandas as pd
import time
import os
from config import ALPHA_VANTAGE_API_KEY, ALPHA_VANTAGE_BASE_URL, PRICE_WINDOWS
from companies import COMPANIES

def get_stock_price(ticker):
    """Fetch daily stock prices for a company from Alpha Vantage"""
    print("  Fetching price data for {}".format(ticker))
    
    params = {
        "function": "TIME_SERIES_DAILY_ADJUSTED",
        "symbol": ticker,
        "outputsize": "full",
        "apikey": ALPHA_VANTAGE_API_KEY
    }
    
    response = requests.get(ALPHA_VANTAGE_BASE_URL, params=params)
    data = response.json()
    
    # Check if we got valid data back
    if "Time Series (Daily)" not in data:
        print("  Could not get price data for {}".format(ticker))
        print("  Response: {}".format(data))
        return None
    
    # Convert to a pandas dataframe
    prices = data["Time Series (Daily)"]
    df = pd.DataFrame.from_dict(prices, orient="index")
    
    # Clean up column names
    df.columns = ["open", "high", "low", "close", "adjusted_close", 
                  "volume", "dividend", "split_coefficient"]
    
    # Add ticker column and clean up index
    df["ticker"] = ticker
    df.index.name = "date"
    df = df.reset_index()
    
    # Convert date to proper format
    df["date"] = pd.to_datetime(df["date"])
    
    # Sort by date oldest first
    df = df.sort_values("date").reset_index(drop=True)
    
    return df


def calculate_price_impact(trades_df, prices_df):
    """Calculate what happened to stock price after each insider trade"""
    results = []
    
    for _, trade in trades_df.iterrows():
        ticker = trade["ticker"]
        trade_date = pd.to_datetime(trade["transaction_date"])
        
        # Get prices for this specific company
        company_prices = prices_df[prices_df["ticker"] == ticker].copy()
        
        if company_prices.empty:
            continue
        
        # Find the closing price on the trade date
        trade_day_price = company_prices[
            company_prices["date"] == trade_date
        ]["adjusted_close"]
        
        if trade_day_price.empty:
            # Try the next available trading day
            future_prices = company_prices[
                company_prices["date"] >= trade_date
            ]
            if future_prices.empty:
                continue
            trade_day_price = future_prices.iloc[0]["adjusted_close"]
            trade_date = future_prices.iloc[0]["date"]
        else:
            trade_day_price = trade_day_price.values[0]
        
        # Calculate price change after 30, 60 and 90 days
        result = {
            "ticker": ticker,
            "insider_name": trade["insider_name"],
            "insider_role": trade["insider_role"],
            "transaction_date": trade["transaction_date"],
            "transaction_type": trade["transaction_type"],
            "shares": trade["shares"],
            "price_on_trade_date": trade_day_price,
        }
        
        # For each time window calculate the return
        for days in PRICE_WINDOWS:
            future_date = trade_date + pd.Timedelta(days=days)
            
            future_price = company_prices[
                company_prices["date"] >= future_date
            ]
            
            if not future_price.empty:
                future_price_value = future_price.iloc[0]["adjusted_close"]
                
                # Calculate percentage return
                price_change = ((float(future_price_value) - float(trade_day_price)) 
                               / float(trade_day_price)) * 100
                
                result["return_{}d".format(days)] = round(price_change, 2)
            else:
                result["return_{}d".format(days)] = None
        
        results.append(result)
    
    return pd.DataFrame(results)


def collect_prices():
    """Main function - collect prices for all companies"""
    
    # Check if raw trades file exists
    trades_path = "data/insider_trades_raw.csv"
    if not os.path.exists(trades_path):
        print("No trades data found. Run sec_collector.py first!")
        return
    
    # Load the trades data
    trades_df = pd.read_csv(trades_path)
    print("Loaded {} trades from {}".format(len(trades_df), trades_path))
    
    # Get unique tickers we need prices for
    tickers = trades_df["ticker"].unique()
    print("Need price data for {} companies".format(len(tickers)))
    print("Note: Alpha Vantage free tier = 25 calls per day")
    print("This may take multiple days if you have more than 25 companies\n")
    
    all_prices = []
    calls_made = 0
    
    # Check if we already have some price data saved
    prices_path = "data/stock_prices.csv"
    if os.path.exists(prices_path):
        existing_prices = pd.read_csv(prices_path)
        already_fetched = existing_prices["ticker"].unique()
        print("Already have prices for: {}".format(list(already_fetched)))
        all_prices.append(existing_prices)
        # Only fetch tickers we don't have yet
        tickers = [t for t in tickers if t not in already_fetched]
        print("Still need: {}\n".format(list(tickers)))
    
    for ticker in tickers:
        if calls_made >= 24:
            print("\n⚠️  Reached 24 API calls for today. Run again tomorrow!")
            print("Progress saved - script will pick up where it left off.")
            break
        
        print("Processing: {}".format(ticker))
        prices = get_stock_price(ticker)
        
        if prices is not None:
            all_prices.append(prices)
            calls_made += 1
            print("  ✅ Got {} days of price data".format(len(prices)))
        
        # Wait 12 seconds between calls
        # Free tier allows 5 calls per minute so we stay safe
        if calls_made < len(tickers):
            print("  Waiting 12 seconds before next call...")
            time.sleep(12)
    
    # Save all prices collected so far
    if all_prices:
        combined = pd.concat(all_prices, ignore_index=True)
        combined.to_csv(prices_path, index=False)
        print("\n✅ Saved price data for {} companies".format(
            len(combined["ticker"].unique())))
        
        # Now calculate price impact if we have all the data
        fetched_tickers = combined["ticker"].unique()
        all_tickers_needed = trades_df["ticker"].unique()
        
        if set(all_tickers_needed).issubset(set(fetched_tickers)):
            print("\nAll price data collected! Calculating price impact...")
            results = calculate_price_impact(trades_df, combined)
            results.to_csv("data/trades_with_returns.csv", index=False)
            print("✅ Saved {} trades with price impact to data/trades_with_returns.csv".format(
                len(results)))
        else:
            missing = set(all_tickers_needed) - set(fetched_tickers)
            print("\nStill missing prices for: {}".format(missing))
            print("Run this script again tomorrow to continue!")


# Run the main function
if __name__ == "__main__":
    collect_prices()