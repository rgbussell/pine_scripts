import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path

# TODO: This code is not running or tested

class PlotPositions:
    def __init__(self, input_dir, output_dir):
        self.output_dir = Path(output_dir)
        stocks_df = pd.read_csv(Path(input_dir) / 'harmonized_stocks.csv')
        options_df = pd.read_csv(Path(input_dir) / 'harmonized_options.csv')

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
    
    

# TODO: separate out the plotting function
    if False:
        plot_positions(harmonized_stocks_df, harmonized_options_df, args.output)