import argparse
import re
from datetime import datetime
import pandas as pd
from parse_utils import parse_month

def get_type(row):
    """Get type of position"""
    type = row.get('Type', '')
    if pd.isna(type):
        return 'UNKNOWN'
    if isinstance(type, float):
        return 'UNKNOWN'
    if re.search(r'\b(OPTION)\b', type.upper()):
        return 'OPTION'
    elif re.search(r'\b(STOCK)\b', type.upper()):
        return 'STOCK'
    elif re.search(r'\b(CRYPTO)\b', type.upper()):
        return 'CRYPTO'
    else:
        return 'UNKNOWN'
    
def is_option_row(row):
    """Determine if a row represents an options position."""
    return bool(re.search(r'\b(OPTION)\b', get_type(row)))

def is_stock_row(row):
    """Determine if a row represents an options position."""
    return bool(re.search(r'\b(STOCK)\b', get_type(row)))

def is_crypto_row(row):
    """Determine if a row represents a crypto position."""
    return bool(re.search(r'\b(CRYPTO)\b', get_type(row)))

class TastytradeParser(object):
    """Class to parse tastytrade csv files"""
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path

    def load(self):
        """Load CSV and separate options and stocks"""
        self.df = pd.read_csv(self.csv_file_path)
        # Add cost basis cleaning (assuming column 'Cost Basis'; adjust if different)
        if 'Cost Basis' in self.df.columns:
            self.df['Cost Basis'] = self.df['Cost Basis'].str.replace(r'[\$,]', '', regex=True).astype(float)
        else:
            self.df['Cost Basis'] = 0.0  # Fallback
        self.options_df = self.get_options_rows(self.df)
        self.stock_df = self.get_stock_rows(self.df)
        print("combining stock and cryto postions for tastytrade")
        crypto_df = self.get_crypto_rows(self.df)
        self.stock_df = pd.concat([self.stock_df, crypto_df], ignore_index=True)
        print(f"tot|options|stock|diff {len(self.df)}|{len(self.options_df)}|{len(self.stock_df)}|{len(self.df) - (len(self.options_df) + len(self.stock_df))}")

    def get_options_rows(self, df):
        """Get only options rows"""
        return df[df.apply(is_option_row, axis=1)]

    def get_stock_rows(self, df):
        """Get only stock rows"""
        return df[df.apply(is_stock_row, axis=1)]
    
    def get_crypto_rows(self, df):
        """Get only stock rows"""
        return df[df.apply(is_crypto_row, axis=1)]

    def format_options_data(self):
        """Format options data for output"""
        options_rows = []
        for i, row in self.options_df.iterrows():
            data = self.extract_options_data_from_row(row)
            if data:
                options_rows.append(data)
        return pd.DataFrame(options_rows)

    def extract_options_data_from_row(self, row):
        """Extract ticker, expiration, strike, options_type from a row."""
        symbol = row.get('Symbol', '')
        opt_type = row.get('Type', '')
        quantity = float(row.get('Quantity', 0))
        exp_date_str = row.get('Exp Date', '')
        strike = float(row.get('Strike Price'))
        call_put = row.get('Call/Put').upper()
        account = row.get('Account', '')
        last_price = float(row.get('Bid (Sell)'))
        cost_basis = float(row.get('Cost Basis', 0))
        
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
            'options_type': options_type,
            'quantity': quantity,
            'account': account,
            'last price': last_price,
            'cost basis': cost_basis
        }