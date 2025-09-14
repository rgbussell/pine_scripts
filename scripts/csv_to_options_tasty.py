import argparse
import csv
import re
from datetime import datetime
import pandas as pd

def parse_month(month_str):
    """Convert month abbreviation to number."""
    month_map = {
        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
    }
    return month_map.get(month_str.upper(), 0)

def extract_options_data(row):
    """Extract ticker, expiration, strike, options_type from a row."""
    symbol = row['Symbol']
    opt_type = row['Type']
    quantity = float(row['Quantity'])
    exp_date_str = row['Exp Date']
    strike = float(row['Strike Price'])
    call_put = row['Call/Put'].upper()
    
    # Skip non-options
    if opt_type != 'OPTION':
        return None
    
    # Extract ticker: part before the option code (digits starting the symbol)
    ticker_match = re.match(r'^(\w+)', symbol.strip())
    if not ticker_match:
        return None
    ticker = ticker_match.group(1)
    
    # Parse expiration: e.g., "Mar 20, 2026"
    exp_match = re.search(r'(\w{3})\s+(\d{1,2}),?\s+(\d{4})', exp_date_str)
    if not exp_match:
        return None
    month_str, day_str, year_str = exp_match.groups()
    month = parse_month(month_str)
    day = int(day_str)
    year = int(year_str)
    
    # Create YYYY-MM-DD
    expiration_date = datetime(year, month, day).strftime('%Y-%m-%d')
    
    # Determine call/put
    is_call = 'CALL' in call_put
    is_put = 'PUT' in call_put
    
    if not (is_call or is_put):
        return None
    
    # Long/Short from quantity
    is_long = quantity > 0
    is_short = quantity < 0
    
    # Options type
    if is_call:
        options_type = 'LC' if is_long else 'SC'
    else:  # put
        options_type = 'LP' if is_long else 'SP'
    
    return {
        'ticker': ticker,
        'expiration': expiration_date,
        'strike': strike,
        'options_type': options_type
    }

def main(csv_file_path):
    # Read CSV with pandas to auto-detect separator
    df = pd.read_csv(csv_file_path)
    
    df = df.dropna()
    
    annotations = []
    for _, row in df.iterrows():
        data = extract_options_data(row)
        if data:
            annotations.append(f"{data['ticker']},{data['expiration']},{data['strike']},{data['options_type']}")
    
    # Sort by ticker (optional)
    annotations.sort()
    
    # Output to terminal
    output = '\n'.join(annotations)
    print(output)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse Tastytrade CSV to Pine Script annotations format.")
    parser.add_argument("--csv-file", help="Path to the input CSV file")
    args = parser.parse_args()
    main(args.csv_file)