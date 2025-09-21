import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import argparse
import re  # For parsing option symbols
from fidelity_utils import FidelityParser
from tastytrade_utils import TastytradeParser

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

   # parse the fidelity data
    fidelity_obj = FidelityParser(fidelity_csv_path)
    fidelity_obj.load()
    stocks_f_df = fidelity_obj.stock_df
    options_f_df = fidelity_obj.format_options_data()

    # tag with source data
    stocks_f_df['Broker'] = 'Fidelity'
    options_f_df['Broker'] = 'Fidelity'

   # parse the tastytrade data
    tastytrade_obj = TastytradeParser(tastytrade_csv_path)
    tastytrade_obj.load()
    stocks_tt_df = tastytrade_obj.stock_df
    options_tt_df = tastytrade_obj.format_options_data()

    options_tt_df['Broker'] = 'Tastytrade'
    stocks_tt_df['Broker'] = 'Tastytrade'

    # combing data from all brokers
    combined_stocks_df = pd.concat([stocks_f_df, stocks_tt_df], ignore_index=True)
    combined_options_df = pd.concat([options_f_df, options_tt_df], ignore_index=True)

    return combined_stocks_df, combined_options_df

def plot_positions(stocks_df, options_df, outdir):
    """
    Generate plots from the harmonized DataFrame.
    
    - Bar plot: Current value per position (with details for options).
    - Pie chart: Portfolio allocation by symbol.
    - Options by expiration.
    
    Parameters:
    - df: pd.DataFrame from harmonize_and_store()
    """
    sns.set(style="whitegrid")
    
    # Detailed label for plotting (e.g., 'AAPL (Call 200 10/18/2024 Long)')
    #df['Label'] = df['Symbol'] + np.where(df['Is Option'], ' (' + df['Option Type'] + ' ' + df['Strike'].astype(str) + ' ' + df['Expiration'] + ' ' + df['Position'] + ')', '')
    
    # Bar plot: Value per position
    plt.figure(figsize=(12, 6))
    sns.barplot(x='Symbol', y='Current Value', data=stocks_df.sort_values('Current Value', ascending=False))
    plt.title('Current Value by Position')
    plt.xticks(rotation=45, ha='right')
    plt.ylabel('Current Value ($)')
    plt.savefig(Path(outdir) / Path('current_value_by_position.png'))
    print(f"Saved current_value_by_position.png to {outdir})")
    
    # Pie chart: Portfolio allocation by symbol
    plt.figure(figsize=(10, 10))
    allocation = stocks_df.groupby('Symbol')['Current Value'].sum()
    plt.pie(allocation, labels=allocation.index, autopct='%1.1f%%')
    plt.title('Portfolio Allocation by Symbol')
    plt.savefig(Path(outdir) / Path('portfolio_allocation.png'))
    print(f"Saved portfolio_allocation.png to {outdir})")

# Example usage (replace with your file paths and desired output)
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process position data from Fidelity and Tastytrade')
    parser.add_argument('--fidelity', required=True, help='Path to Fidelity positions CSV file')
    parser.add_argument('--tastytrade', required=True, help='Path to Tastytrade positions CSV file') 
    parser.add_argument('--output', default='~/Desktop', help='Output file directory')
    parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format')
    
    args = parser.parse_args()
    
    harmonized_stocks_df, harmonized_options_df = harmonize_and_store(args.fidelity, args.tastytrade, args.format, args.output)
    
    # add some quantifcatios
    harmonized_stocks_df.dropna(subset=['Quantity', 'Last Price'], inplace=True)
    harmonized_stocks_df['Last Price'] = harmonized_stocks_df['Last Price'].str.replace(r'[\$,]', '', regex=True).astype(float)
    harmonized_stocks_df['Current Value'] = harmonized_stocks_df.apply(lambda row:
        row['Last Price'] * row['Quantity'], axis=1)
    
    harmonized_stocks_df.to_csv(Path(args.output) / Path('harmonized_stocks.csv'), index=False)
    harmonized_options_df.to_csv(Path(args.output) / Path('harmonized_options.csv'), index=False)
    
    plot_positions(harmonized_stocks_df, harmonized_options_df, args.output)