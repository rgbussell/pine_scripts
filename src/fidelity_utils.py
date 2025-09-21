"""utilities for parsing fidelity and tastytrade csv file"""
import re
from datetime import datetime
import pandas as pd
from parse_utils import parse_month

def is_option_row(row):
    """Determine if a row represents an options position."""
    description = row.get('Description', '')
    symbol = row.get('Symbol', '')
    return bool(re.search(r'\b(CALL|PUT|C|P)\b', description.upper())) and symbol.strip().startswith('-')

class FidelityParser(object):
    """Class to parse fidelity csv files"""
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path

    def load(self):
        """Load CSV and separate options and stocks"""
        self.df = pd.read_csv(self.csv_file_path)
        self.options_df = self.get_options_rows(self.df)
        self.stock_df = self.get_stock_rows(self.df)
        print(f"tot|options|stock|diff {len(self.df)}|{len(self.options_df)}|{len(self.stock_df)}|{len(self.df) - (len(self.options_df) + len(self.stock_df))}")

    def format_options_data(self):
        """Format options data for output"""
        options_rows = []
        for row in self.options_df.itertuples():
            data = self.extract_options_data_from_row(row)
            if data:
                options_rows.append(data)
        return pd.DataFrame(options_rows)
    
    def extract_options_data_from_row(self, row):
        """Extract ticker, expiration, strike, options_type from a row."""
        description = row.Description
        quantity = float(row.Quantity)

        print(description)
        
        # Extract ticker: first word before space
        ticker_match = re.match(r'^(\w+)', description)
        if not ticker_match:
            return None
        ticker = ticker_match.group(1)
        
        # Parse expiration: e.g., "FEB 20 2026"
        exp_match = re.search(r'(\w{3})\s+(\d{1,2})\s+(\d{4})', description)
        if not exp_match:
            return None
        month_str, day_str, year_str = exp_match.groups()
        month = parse_month(month_str)
        day = int(day_str)
        year = int(year_str)
        
        # Create YYYY-MM-DD
        expiration_date = datetime(year, month, day).strftime('%Y-%m-%d')
        
        # Extract strike: e.g., $470
        strike_match = re.search(r'\$(\d+(?:\.\d+)?)', description)
        if not strike_match:
            return None
        strike = float(strike_match.group(1))
        
        # Determine call/put from Description or Symbol
        is_call = 'CALL' in description.upper() or 'C' in row.Symbol
        is_put = 'PUT' in description.upper() or 'P' in row.Symbol
        
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

    def get_good_rows(self, df):
        """Filter rows that likely contain valid positions."""
        return df.dropna(subset=['Description'])

    def get_options_rows(self, df):
        """Filter rows that contain options positions"""
        df = self.get_good_rows(df)
        df = df[df.apply(is_option_row, axis=1)]
        return df

    def get_stock_rows(self, df):
        """Filter rows that contain non-options positions"""
        df = self.get_good_rows(df)
        df = df[~df.apply(is_option_row, axis=1)]
        return df