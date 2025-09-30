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
    
    # Format the current value column to 2 decimal places
    combined_stocks_df['current value'] = combined_stocks_df['current value'].round(2)
    combined_options_df['current value'] = combined_options_df['current value'].round(2)

    # format the gaan loss column to 2 decimaal places
    combined_stocks_df['gain loss'] = combined_stocks_df['current value'].round(2)
    combined_options_df['gain loss'] = combined_options_df['current value'].round(2)

    # Process synthetics in options
    combined_options_df = process_synthetics(combined_options_df)

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

def process_synthetics(df):
    """Identify synthetic longs and adjust the dataframe."""
    df = df.copy()
    synth_rows = []
    groups = df.groupby(['ticker', 'expiration', 'strike'])
    for name, group in groups:
        lc_row = group[group['options_type'] == 'LC']
        sp_row = group[group['options_type'] == 'SP']
        if len(lc_row) == 0 or len(sp_row) == 0:
            continue
        lc_qty = lc_row['quantity'].iloc[0]
        sp_qty = sp_row['quantity'].iloc[0]
        if lc_qty <= 0 or sp_qty >= 0:
            continue
        synth_qty = min(lc_qty, -sp_qty)
        if synth_qty <= 0:
            continue

        # Unit values (positive for both)
        unit_lc_current = lc_row['current value'].iloc[0] / lc_qty
        unit_sp_current = sp_row['current value'].iloc[0] / sp_qty
        unit_lc_cost = lc_row['cost basis'].iloc[0] / lc_qty
        unit_sp_cost = sp_row['cost basis'].iloc[0] / sp_qty

        # For synthetic (net for the pair)
        synth_current = synth_qty * (unit_lc_current + (unit_sp_current * -1))
        synth_cost = synth_qty * (unit_lc_cost + (unit_sp_cost * -1))
        synth_gain = synth_current - synth_cost

        # Create synthetic row
        synth_row = lc_row.iloc[0].copy()
        synth_row['options_type'] = 'SYN_LONG'
        synth_row['quantity'] = synth_qty
        synth_row['current value'] = synth_current
        synth_row['cost basis'] = synth_cost
        synth_row['gain loss'] = synth_gain
        synth_row['last price'] = None  # Not applicable
        synth_rows.append(synth_row)

        # Adjust LC row
        lc_idx = lc_row.index[0]
        df.at[lc_idx, 'quantity'] -= synth_qty
        df.at[lc_idx, 'cost basis'] -= synth_qty * unit_lc_cost
        df.at[lc_idx, 'current value'] = df.at[lc_idx, 'last price'] * 100 * df.at[lc_idx, 'quantity']
        df.at[lc_idx, 'gain loss'] = df.at[lc_idx, 'current value'] - df.at[lc_idx, 'cost basis']

        # Adjust SP row
        sp_idx = sp_row.index[0]
        df.at[sp_idx, 'quantity'] += synth_qty
        df.at[sp_idx, 'cost basis'] -= synth_qty * (unit_sp_cost * -1)
        df.at[sp_idx, 'current value'] = df.at[sp_idx, 'last price'] * 100 * df.at[sp_idx, 'quantity']
        df.at[sp_idx, 'gain loss'] = df.at[sp_idx, 'current value'] - df.at[sp_idx, 'cost basis']

    # Remove zero-quantity rows
    df = df[df['quantity'] != 0]

    # Append synthetic rows
    if synth_rows:
        synth_df = pd.DataFrame(synth_rows)
        df = pd.concat([df, synth_df], ignore_index=True)

    return df

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