import yfinance as yf
import pandas as pd
import os
from config import PRICE_WINDOWS
from companies import COMPANIES


def get_stock_price(ticker):
    """Fetch daily stock prices for a company using yfinance"""
    print("  Fetching price data for {}".format(ticker))
    
    try:
        # Download full history from 2015 to today
        stock = yf.download(ticker, start="2015-01-01", progress=False)
        
        if stock.empty:
            print("  No data returned for {}".format(ticker))
            return None
        
        # Flatten column names if they are multi-level
        if isinstance(stock.columns, pd.MultiIndex):
            stock.columns = stock.columns.get_level_values(0)
        
        # Reset index to make date a regular column
        stock = stock.reset_index()
        
        # Rename columns to lowercase
        stock.columns = [col.lower() for col in stock.columns]
        
        # Keep only the columns we need
        stock = stock[["date", "open", "high", "low", "close", "volume"]]
        
        # Add ticker column
        stock["ticker"] = ticker
        
        # Sort by date oldest first
        stock = stock.sort_values("date").reset_index(drop=True)
        
        print("  ✅ Got {} days of price data".format(len(stock)))
        return stock
        
    except Exception as e:
        print("  Error fetching {}: {}".format(ticker, e))
        return None


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
        
        # Make sure date column is datetime
        company_prices["date"] = pd.to_datetime(company_prices["date"])
        
        # Find the closing price on the trade date
        trade_day_price = company_prices[
            company_prices["date"] == trade_date
        ]["close"]
        
        if trade_day_price.empty:
            # Try the next available trading day
            future_prices = company_prices[
                company_prices["date"] >= trade_date
            ]
            if future_prices.empty:
                continue
            trade_day_price = future_prices.iloc[0]["close"]
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
                future_price_value = future_price.iloc[0]["close"]
                
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
    tickers = list(trades_df["ticker"].unique())
    print("Need price data for {} companies".format(len(tickers)))
    
    all_prices = []
    
    # Check if we already have some price data saved
    prices_path = "data/stock_prices.csv"
    if os.path.exists(prices_path):
        existing_prices = pd.read_csv(prices_path)
        already_fetched = list(existing_prices["ticker"].unique())
        print("Already have prices for: {}".format(already_fetched))
        all_prices.append(existing_prices)
        tickers = [t for t in tickers if t not in already_fetched]
        print("Still need: {}\n".format(tickers))
    
    # Fetch prices for remaining tickers
    for ticker in tickers:
        print("Processing: {}".format(ticker))
        prices = get_stock_price(ticker)
        
        if prices is not None:
            all_prices.append(prices)
    
    # Save all prices collected
    if all_prices:
        combined = pd.concat(all_prices, ignore_index=True)
        combined.to_csv(prices_path, index=False)
        print("\n✅ Saved price data for {} companies".format(
            len(combined["ticker"].unique())))
        
        # Calculate price impact
        fetched_tickers = combined["ticker"].unique()
        all_tickers_needed = trades_df["ticker"].unique()
        
        if set(all_tickers_needed).issubset(set(fetched_tickers)):
            print("\nAll price data collected! Calculating price impact...")
            results = calculate_price_impact(trades_df, combined)
            results.to_csv("data/trades_with_returns.csv", index=False)
            print("✅ Saved {} trades with price impact to data/trades_with_returns.csv".format(
                len(results)))
            print("\nSample of results:")
            print(results[["ticker", "insider_name", "transaction_date",
                          "price_on_trade_date", "return_30d",
                          "return_60d", "return_90d"]].head(10))
        else:
            missing = set(all_tickers_needed) - set(fetched_tickers)
            print("\nStill missing prices for: {}".format(missing))


# Run the main function
if __name__ == "__main__":
    collect_prices()