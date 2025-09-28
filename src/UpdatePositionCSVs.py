import pandas as pd
from pathlib import Path
import argparse
import re  # For parsing option symbols
from fidelity_utils import FidelityParser
from tastytrade_utils import TastytradeParser
from options_list import annotaions_from_df
import json
from PlotPositions import PlotPositions  # Import the plotting class

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
        config = json.load(json_file)
    
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

    # combing data from all brokers
    combined_stocks_df = pd.concat(stock_list, ignore_index=True)
    combined_options_df = pd.concat(options_list, ignore_index=True)

    # rename all to lower case columns
    combined_stocks_df.columns = [col.lower() for col in combined_stocks_df.columns]
    combined_options_df.columns = [col.lower() for col in combined_options_df.columns]

    # add some quantifcations
    tmp_len = combined_stocks_df.shape[0]
    combined_stocks_df.dropna(subset=['quantity'], inplace=True)
    diff_len = tmp_len - combined_stocks_df.shape[0]
    if diff_len > 0:
        print(f"Dropped {diff_len} rows with missing Quantity or Last Price")
    combined_stocks_df['current value'] = combined_stocks_df.apply(lambda row:
        row['last price'] * row['quantity'], axis=1)
    
    # compute current value of optiosn from the bid
    combined_options_df['current value'] = combined_options_df.apply(lambda row:
        row['last price'] * 100 * row['quantity'], axis=1)
    
    # Compute gain/loss for both (assuming cost basis is total cost/credit)
    combined_stocks_df['gain loss'] = combined_stocks_df['current value'] - combined_stocks_df['cost basis']
    combined_options_df['gain loss'] = combined_options_df['current value'] - combined_options_df['cost basis']
    
    # only return the harmonized columns
    harmonized_stock_cols = config['harmonized_stock_columns']
    harmonized_option_cols = config['harmonized_option_columns']
    combined_stocks_df = combined_stocks_df[harmonized_stock_cols]
    combined_options_df = combined_options_df[harmonized_option_cols]

    combined_stocks_path = Path(output_path) / Path('harmonized_stocks.csv')
    combined_options_path = Path(output_path) / Path('harmonized_options.csv')
    combined_stocks_df.to_csv(combined_stocks_path, index=False)
    combined_options_df.to_csv(combined_options_path, index=False)

    return combined_stocks_df, combined_options_df


# Example usage (replace with your file paths and desired output)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process position data from Fidelity and Tastytrade')
    parser.add_argument('--fidelity', required=True, help='Path to Fidelity positions CSV file')
    parser.add_argument('--tastytrade', required=True, help='Path to Tastytrade positions CSV file') 
    parser.add_argument('--output', default='~/Desktop', help='Output file directory')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format')
    
    args = parser.parse_args()
    
    stocks_df, options_df = harmonize_and_store(args.fidelity, args.tastytrade, args.format, args.output)
    annotaions_from_df(options_df)
    
    # Add plotting and reporting
    plotter = PlotPositions(input_dir=args.output, output_dir=args.output)
    plotter.plot_all(stocks_df, options_df)
    plotter.report_expiring_options(options_df)