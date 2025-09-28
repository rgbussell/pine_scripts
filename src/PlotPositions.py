import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime
import io
import base64
import webbrowser
import os  # Added for file path handling
import json

with open('config/visualization.json', 'r') as f:
    config = json.load(f)

class PlotPositions:
    def __init__(self, input_dir, output_dir):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def plot_all(self, stocks_df, options_df):
        html_parts = ['<html><body>']
        
        # Generate and append each plot as base64 image
        img_base64 = self.plot_current_value(stocks_df, options_df)
        html_parts.extend(img_base64)
        
        img_base64 = self.plot_gain_loss(stocks_df, options_df)
        html_parts.extend(img_base64)
        
        img_base64 = self.plot_pie_allocation(stocks_df, options_df)
        html_parts.extend(img_base64)

        img_base64 = self.plot_options_exposure_per_ticker(options_df)
        html_parts.extend(img_base64)
        
        html_parts.append('</body></html>')
        html_content = ''.join(html_parts)
        
        # Save to a temporary HTML file and open it
        html_file_path = self.output_dir / 'plots.html'
        with open(html_file_path, 'w') as f:
            f.write(html_content)
        
        # Open in web browser using file URI
        webbrowser.open('file://' + os.path.realpath(html_file_path))
        print(f"Opened plots in web browser from file: {html_file_path}")

    def get_base64_image(self, fig):
        buf = io.BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)  # Close figure to free memory
        return f'<img src="data:image/png;base64,{img_base64}">'

    def plot_current_value(self, stocks_df, options_df):
        images = []
        
        # Stocks current value bar plot
        sorted_stocks = stocks_df.sort_values('current value', ascending=False)
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(sorted_stocks['ticker'], sorted_stocks['current value'])
        ax.set_title('Current Value by Stock Position')
        ax.set_xlabel('Ticker')
        ax.set_ylabel('Current Value ($)')
        plt.xticks(rotation=45, ha='right')
        images.append('<h2>Current Value by Stock Position</h2>' + self.get_base64_image(fig))
        
        # Options current value bar plot
        if not options_df.empty:
            options_df['label'] = options_df['ticker'] + ' ' + options_df['strike'].astype(str) + ' ' + options_df['options_type'] + ' ' + options_df['expiration']
            sorted_options = options_df.sort_values('current value', ascending=False)
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(sorted_options['label'], sorted_options['current value'])
            ax.set_title('Current Value by Options Position')
            ax.set_xlabel('Option Label')
            ax.set_ylabel('Current Value ($)')
            plt.xticks(rotation=45, ha='right')
            images.append('<h2>Current Value by Options Position</h2>' + self.get_base64_image(fig))
        
        return images

    def plot_gain_loss(self, stocks_df, options_df):
        images = []
        
        # Stocks gain/loss bar plot
        sorted_stocks = stocks_df.sort_values('gain loss', ascending=False)
        colors = ['g' if x > 0 else 'r' for x in sorted_stocks['gain loss']]
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.bar(sorted_stocks['ticker'], sorted_stocks['gain loss'], color=colors)
        ax.set_title('Gain/Loss by Stock Position')
        ax.set_xlabel('Ticker')
        ax.set_ylabel('Gain/Loss ($)')
        plt.xticks(rotation=45, ha='right')
        images.append('<h2>Gain/Loss by Stock Position</h2>' + self.get_base64_image(fig))
        
        # Options gain/loss bar plot
        if not options_df.empty:
            options_df['label'] = options_df['ticker'] + ' ' + options_df['strike'].astype(str) + ' ' + options_df['options_type'] + ' ' + options_df['expiration']
            sorted_options = options_df.sort_values('gain loss', ascending=False)
            colors = ['g' if x > 0 else 'r' for x in sorted_options['gain loss']]
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(sorted_options['label'], sorted_options['gain loss'], color=colors)
            ax.set_title('Gain/Loss by Options Position')
            ax.set_xlabel('Option Label')
            ax.set_ylabel('Gain/Loss ($)')
            plt.xticks(rotation=45, ha='right')
            images.append('<h2>Gain/Loss by Options Position</h2>' + self.get_base64_image(fig))
        
        return images

    def plot_pie_allocation(self, stocks_df, options_df):
        images = []
        
        # Pie chart: Portfolio allocation by ticker (stocks + options current value)
        combined_allocation = pd.concat([
            stocks_df.groupby('ticker')['current value'].sum(),
            #options_df.groupby('ticker')['current value'].sum()
        ], axis=1).sum(axis=1, skipna=True)
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.pie(combined_allocation, labels=combined_allocation.index, autopct='%1.1f%%')
        ax.set_title('Portfolio Allocation by Ticker (Stocks + Options)')
        images.append('<h2>Portfolio Allocation by Ticker (Stocks + Options)</h2>' + self.get_base64_image(fig))
        
        return images
    
    def plot_options_exposure_per_ticker(self, options_df):
        if options_df.empty:
            return []

        images = []
        grouped = options_df.groupby("ticker")

        for ticker, group in grouped:
            # 1. Long and Short Exposure: Bar chart by options_type showing current value
            fig, ax = plt.subplots(figsize=(8, 6))
            types = ["LC", "SC", "LP", "SP"]
            colors_by_type = [config["option_colors"][t] for t in types]
            values = [group[group["options_type"] == t]["current value"].sum() for t in types]
            colors = ["green" if "L" in t else "red" for t in types]
            ax.bar(types, values, color=colors)
            ax.set_title(f"{ticker} Options Exposure by Type")
            ax.set_xlabel("Options Type")
            ax.set_ylabel("Current Value ($)")
            ax.axhline(0, color="black", linewidth=0.5)
            images.append(f"<h2>{ticker} Options Exposure by Type</h2>" + self.get_base64_image(fig))

            # 2. Expiration Timeline: Stacked bar by expiration, net value per type
            exp_group = group.groupby(["expiration", "options_type"])["current value"].sum().unstack(fill_value=0)
            fig, ax = plt.subplots(figsize=(10, 6))
            exp_group.plot(kind="bar", stacked=True, ax=ax, color=colors_by_type)  # Colors for LC, SC, LP, SP
            ax.set_title(f"{ticker} Options Exposure by Expiration")
            ax.set_xlabel("Expiration Date")
            ax.set_ylabel("Current Value ($)")
            plt.xticks(rotation=45, ha="right")
            images.append(f"<h2>{ticker} Options Exposure by Expiration</h2>" + self.get_base64_image(fig))

            # 3. Strike Ladder: Bar by strike, value per type
            strike_group = group.groupby(["strike", "options_type"])["current value"].sum().unstack(fill_value=0)
            fig, ax = plt.subplots(figsize=(10, 6))
            strike_group.plot(kind="bar", ax=ax, color=colors_by_type)  # Use predefined colors
            ax.set_title(f"{ticker} Strike Ladder Exposure")
            ax.set_xlabel("Strike Price")
            ax.set_ylabel("Current Value ($)")
            ax.axhline(0, color="black", linewidth=0.5)
            plt.xticks(rotation=45, ha="right")
            images.append(f"<h2>{ticker} Strike Ladder</h2>" + self.get_base64_image(fig))

        return images

    def report_expiring_options(self, options_df, days_threshold=30):
        if options_df.empty:
            print("No options positions found.")
            return
        
        current_date = datetime.now()
        options_df['expiration_date'] = pd.to_datetime(options_df['expiration'])
        expiring = options_df[(options_df['expiration_date'] - current_date).dt.days <= days_threshold]
        expiring = expiring.sort_values('expiration_date')
        
        if expiring.empty:
            print(f"No options expiring within {days_threshold} days.")
        else:
            print(f"Options expiring within {days_threshold} days:")
            print(expiring[['ticker', 'expiration', 'strike', 'options_type', 'current value', 'gain loss']])
        
        expiring.to_csv(self.output_dir / 'expiring_options.csv', index=False)
        print(f"Saved expiring_options.csv to {self.output_dir}")