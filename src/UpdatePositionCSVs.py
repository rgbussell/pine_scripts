import pandas as pd
from pathlib import Path
import argparse
import re  # For parsing option symbols
from fidelity_utils import FidelityParser
from tastytrade_utils import TastytradeParser
import json

def harmonize_and_store(fidelity_csv_path, tastytrade_csv_path, output_format='json', output_path='harmonized_positions.json'):
    """
    Harmonize positions from both brokers into a common format and store to file (JSON or CSV).
    
    Common format columns: Symbol, Quantity, Current Value, Cost Basis, Broker, Is Option, Expiration, Strike, Option Type, Position, Profit/Loss.
    
    Parameters:
    - fidelity_csv_path: str
    - tastytrade_csv_path: str
    - output_format: str, 'json' or 'csv'
    - output_path: str, file to save
    
    Returns:
    - pd.DataFrame (harmonized data)
    """

    # parsers for each broker
    parsers = {'fidelity': FidelityParser, 'tastytrade': TastytradeParser}
    csvs = {'fidelity': fidelity_csv_path, 'tastytrade': tastytrade_csv_path}

    stock_list = []
    options_list = []

    # read the config file for renaming columns
    with open('config/harmonization.json', 'r') as json_file:
        config = json.load(open('config/harmonization.json'))
    
   # parse the fidelity data
    for broker in ["fidelity", "tastytrade"]:
        if broker not in config:
            raise ValueError(f"Broker {broker} not found in config/harmonization.json")
        required_keys = ['stock_renames', 'option_renames']
        for key in required_keys:
            if key not in config[broker]:
                raise ValueError(f"Key {key} not found for broker {broker} in config/harmonization.json")

        parser_obj = parsers[broker](csvs[broker])
        parser_obj.load()
        stocks_df = parser_obj.stock_df
        options_df = parser_obj.format_options_data()

        # rename to standard scheme
        stocks_df.rename(columns=config[broker]['stock_renames'], inplace=True)
        options_df.rename(columns=config[broker]['option_renames'], inplace=True)

        # tag with source data
        stocks_df['broker'] = broker
        options_df['broker'] = broker
        stock_list.append(stocks_df)
        options_list.append(options_df)
        del parser_obj, stocks_df, options_df

   # parse the tastytrade data
    #tastytrade_obj = TastytradeParser(tastytrade_csv_path)
    #tastytrade_obj.load()
    #stocks_tt_df = tastytrade_obj.stock_df
    #options_tt_df = tastytrade_obj.format_options_data()

    #options_tt_df['broker'] = 'tastytrade'
    #stocks_tt_df['broker'] = 'tastytrade'

    # combing data from all brokers
    combined_stocks_df = pd.concat(stock_list, ignore_index=True)
    combined_options_df = pd.concat(options_list, ignore_index=True)

    return combined_stocks_df, combined_options_df


# Example usage (replace with your file paths and desired output)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process position data from Fidelity and Tastytrade')
    parser.add_argument('--fidelity', required=True, help='Path to Fidelity positions CSV file')
    parser.add_argument('--tastytrade', required=True, help='Path to Tastytrade positions CSV file') 
    parser.add_argument('--output', default='~/Desktop', help='Output file directory')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format')
    
    args = parser.parse_args()
    
    harmonized_stocks_df, harmonized_options_df = harmonize_and_store(args.fidelity, args.tastytrade, args.format, args.output)
    
    # add some quantifcations
    tmp_len = harmonized_stocks_df.shape[0]
    harmonized_stocks_df.dropna(subset=['Quantity'], inplace=True)
    diff_len = tmp_len - harmonized_stocks_df.shape[0]
    if diff_len > 0:
        print(f"Dropped {diff_len} rows with missing Quantity or Last Price")
    harmonized_stocks_df['Last Price'] = harmonized_stocks_df['Last Price'].str.replace(r'[\$,]', '', regex=True).astype(float)
    harmonized_stocks_df['Current Value'] = harmonized_stocks_df.apply(lambda row:
        row['Last Price'] * row['Quantity'], axis=1)
    
    harmonized_stocks_df.to_csv(Path(args.output) / Path('harmonized_stocks.csv'), index=False)
    harmonized_options_df.to_csv(Path(args.output) / Path('harmonized_options.csv'), index=False)
