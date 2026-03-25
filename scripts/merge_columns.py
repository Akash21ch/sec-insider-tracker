import pandas as pd

# Delete the messy trades_with_returns and regenerate clean
import subprocess
subprocess.run(['python3', 'scripts/price_collector.py'])

# Load fresh files
trades = pd.read_csv('data/trades_with_returns.csv')
clean = pd.read_csv('data/insider_trades_clean.csv')

# Keep only what we need from clean
cols = ['insider_name', 'ticker', 'transaction_date', 'role_type', 'company_name', 'sector', 'cap_size']
clean_subset = clean[cols].drop_duplicates(subset=['insider_name', 'ticker', 'transaction_date'])

# Merge
merged = trades.merge(clean_subset, on=['insider_name', 'ticker', 'transaction_date'], how='left')

# Save
merged.to_csv('data/trades_with_returns.csv', index=False)
print('Done! Rows:', len(merged))
print('Columns:', list(merged.columns))
