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
    plotting_config = json.load(f)

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
        
        # Stocks current value bar plots - regular and log scale
        sorted_stocks = stocks_df.sort_values('current value', ascending=False)
        
        # Create figure with two subplots stacked vertically, sharing x axis
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Top subplot - linear scale
        ax1.bar(sorted_stocks['ticker'], sorted_stocks['current value'], edgecolor='black', facecolor='none')
        ax1.set_title('Current Value by Stock Position (Linear Scale)')
        ax1.set_ylabel('Current Value ($)', fontsize=16)
        ax1.tick_params(axis='both', labelsize=16)
        ax1.tick_params(axis='x', rotation=90)

        # Bottom subplot - log scale 
        ax2.bar(sorted_stocks['ticker'], sorted_stocks['current value'], edgecolor='black', facecolor='none')
        ax2.set_title('Current Value by Stock Position (Log Scale)')
        ax2.set_xlabel('Ticker', fontsize=16)
        ax2.set_ylabel('Current Value ($)', fontsize=16)
        ax2.set_yscale('log')
        ax2.tick_params(axis='both', labelsize=16)
        ax2.tick_params(axis='x', rotation=90)

        plt.tight_layout()
        images.append('<h2>Current Value by Stock Position</h2>' + self.get_base64_image(fig))
        
        # Options current value bar plot
        if not options_df.empty:
            options_df['label'] = options_df['ticker'] + ' ' + options_df['strike'].astype(str) + ' ' + options_df['options_type'] + ' ' + options_df['expiration']
            sorted_options = options_df.sort_values('current value', ascending=False)
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(sorted_options['label'], sorted_options['current value'], edgecolor='black', facecolor='none')
            ax.set_title('Current Value by Options Position')
            ax.set_xlabel('Option Label', fontsize=16)
            ax.set_ylabel('Current Value ($)', fontsize=16)
            ax.tick_params(axis='both', labelsize=16)
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
            fig, axs = plt.subplots(1, 3, figsize=(12, 4), sharey=True)
            #fig.suptitle(f"{ticker}", fontsize=16)

            # 1. Exposure by Type: Bar chart by options_type showing current value
            types = ["LC", "LP", "SC", "SP"]
            types_colors = [plotting_config["option_colors"][t] for t in types]
            values = [group[group["options_type"] == t]["current value"].sum() for t in types]
            axs[0].bar(types, values, color=types_colors)
            axs[0].set_title("Exposure by Type")
            axs[0].set_xlabel("Options Type", fontsize=14)
            axs[0].set_ylabel("Current Value ($)", fontsize=14)
            axs[0].tick_params(axis='both', labelsize=14)
            axs[0].axhline(0, color="black", linewidth=0.5)

            # 2. Exposure by Expiration: Stacked bar by expiration, net value per type
            exp_group = group.groupby(["expiration", "options_type"])["current value"].sum().unstack(fill_value=0)
            exp_group = exp_group.reindex(columns=types)  # Reorder columns to match types order
            exp_group = exp_group.sort_index()  # Sort by expiration date
            exp_group.plot(kind="bar", stacked=True, ax=axs[1], color=types_colors)
            axs[1].set_title("Exposure by Expiration")
            axs[1].set_xlabel("Expiration Date", fontsize=14)
            axs[1].set_ylabel("Current Value ($)", fontsize=14)
            axs[1].tick_params(axis='both', labelsize=14)
            axs[2].axhline(0, color="black", linewidth=0.5)
            axs[1].tick_params(axis='x', rotation=45)

            # 3. Strike Ladder: Bar by strike, value per type
            strike_group = group.groupby(["strike", "options_type"])["current value"].sum().unstack(fill_value=0)
            strike_group = strike_group.reindex(columns=types)  # Reorder columns to match types order
            strike_group = strike_group.sort_index()  # Sort by strike price
            strike_group.plot(kind="bar", ax=axs[2], color=types_colors)
            axs[2].set_title("Strike Ladder Exposure")
            axs[2].set_xlabel("Strike Price", fontsize=14)
            axs[2].set_ylabel("Current Value ($)", fontsize=14) 
            axs[2].tick_params(axis='both', labelsize=14)
            axs[2].axhline(0, color="black", linewidth=0.5)
            axs[2].tick_params(axis='x', rotation=45)

            # Tight layout for better spacing
            plt.tight_layout()
            images.append(f"<h2>{ticker} Options Visualizations</h2>" + self.get_base64_image(fig))

        return images

    def report_expiring_options(self, options_df, days_threshold=90):  # Max to cover quarter (~90 days)
        if options_df.empty:
            return "<p>No options positions found.</p>"
        
        current_date = datetime.now()
        options_df['expiration_date'] = pd.to_datetime(options_df['expiration'])
        options_df['days_to_expiry'] = (options_df['expiration_date'] - current_date).dt.days
        
        # Filter for positive days (future expirations)
        future_options = options_df[options_df['days_to_expiry'] >= 0]
        
        # Buckets
        expiring_today = future_options[future_options['days_to_expiry'] == 0]
        expiring_week = future_options[(future_options['days_to_expiry'] > 0) & (future_options['days_to_expiry'] < 7)]
        expiring_month = future_options[(future_options['days_to_expiry'] >= 7) & (future_options['days_to_expiry'] < 30)]
        expiring_quarter = future_options[(future_options['days_to_expiry'] >= 30) & (future_options['days_to_expiry'] < 90)]
        
        # Function to generate HTML list if not empty
        def generate_html_list(df, title):
            if df.empty:
                return f"<h3 style='font-size: 24px;'>{title}</h3><p style='font-size: 18px;'>No options {title.lower()}.</p>"
            html = f"<h3 style='font-size: 24px;'>{title}</h3><ul style='font-size: 18px;'>"
            for _, row in df.sort_values('expiration_date').iterrows():
                html += f"<li>{row['ticker']}|{row['options_type']}|{row['expiration']}|{row['strike']}|{row['current value']}</li>"
            html += "</ul>"
            return html
        
        # Generate HTML for all buckets
        html = generate_html_list(expiring_today, "Options Expiring Today")
        html += generate_html_list(expiring_week, "Options Expiring in Less Than a Week")
        html += generate_html_list(expiring_month, "Options Expiring in Less Than a Month")
        html += generate_html_list(expiring_quarter, "Options Expiring in Less Than a Quarter")
        
        # Save all to a single CSV with bucket column
        future_options['bucket'] = pd.cut(future_options['days_to_expiry'],
                                        bins=[-1, 0, 6, 29, 89],
                                        labels=["Today", "Less Than a Week", "Less Than a Month", "Less Than a Quarter"])
        future_options.to_csv(self.output_dir / 'expiring_options.csv', index=False)
        print(f"Saved expiring_options.csv to {self.output_dir}")
        
        return html