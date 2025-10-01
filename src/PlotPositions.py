import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
from datetime import datetime
import io
import base64
import webbrowser
import os  # Added for file path handling
import json
import numpy as np

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
        
        #img_base64 = self.plot_gain_loss(stocks_df, options_df)
        #html_parts.extend(img_base64)
        
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
        
        # Create figure with two subplots stacked vertically, sharing 
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        
        # Top subplot - linear scale
        ax1.bar(sorted_stocks['ticker'], sorted_stocks['current value'], edgecolor='black', facecolor='lightgrey')
        ax1.set_title('Current Value by Stock Position (Linear Scale)')
        ax1.set_ylabel('Current Value ($)', fontsize=16)
        ax1.tick_params(axis='both', labelsize=16)
        ax1.tick_params(axis='x', rotation=90)
        ax1.grid(True, which='both', axis='y', linestyle='--', linewidth=0.5)

        # Bottom subplot - log scale 
        ax2.bar(sorted_stocks['ticker'], sorted_stocks['current value'], edgecolor='black', facecolor='lightgrey')
        ax2.set_xlabel('Ticker', fontsize=16)
        ax2.set_ylabel('Current Value ($)', fontsize=16)
        ax2.set_yscale('log')
        ax2.tick_params(axis='both', labelsize=16)
        ax2.tick_params(axis='x', rotation=90)
        ax2.grid(True, which='both', axis='x', linestyle='--', linewidth=0.5)


        plt.tight_layout()
        images.append('<h2>Current Value by Stock Position</h2>' + self.get_base64_image(fig))
        
        # Options current value bar plot
        if not options_df.empty and False:
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
        if not options_df.empty and False:
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

        sm_pos_pct = 2.0  # Small position percentage threshold
        fs = 14 # Font size for pie annotations
        
        # Pie chart: Portfolio allocation by ticker (stocks + options current value)
        combined_allocation = pd.concat([
            stocks_df.groupby('ticker')['current value'].sum(),
            #options_df.groupby('ticker')['current value'].sum()
        ], axis=1).sum(axis=1, skipna=True)

        # Create figure with two subplots side by side
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))

        # Calculate small positions (< 5%)
        total_value = combined_allocation.sum()
        small_positions = combined_allocation[combined_allocation/total_value < sm_pos_pct/100]
        large_positions = combined_allocation[combined_allocation/total_value >= sm_pos_pct/100]
        
        # Add small positions as a single slice
        if not small_positions.empty:
            large_positions['Small Positions'] = small_positions.sum()

        # First pie chart with large positions and small positions aggregated
        num_colors = len(small_positions)
        colors = plt.cm.tab10(np.linspace(0, 1, num_colors))
        ax1.pie(large_positions, labels=large_positions.index, autopct='%1.1f%%', 
            textprops={'fontsize': fs}, labeldistance=1.1, colors=colors)
        ax1.set_title('Major Portfolio Allocations', fontsize=16)

        # Second pie chart with only positions < small pos threshold
        if not small_positions.empty:
            # Create pastel colors using alpha transparency
            num_colors = len(small_positions)
            colors = plt.cm.tab10(np.linspace(0, 1, num_colors))
            
            ax2.pie(small_positions, labels=small_positions.index, autopct='%1.1f%%',
               textprops={'fontsize': fs}, labeldistance=1.1, colors=colors)
            ax2.set_title(f'Small Positions (< {sm_pos_pct}%)', fontsize=16)
        else:
            ax2.text(0.5, 0.5, f'No positions < {sm_pos_pct}%', ha='center', va='center', fontsize=14)
            ax2.set_title(f'Small Positions (< {sm_pos_pct}%)', fontsize=16)

        plt.suptitle('Portfolio Allocation by Ticker (Stocks + Options)', fontsize=16)
        images.append('<h2>Portfolio Allocation by Ticker (Stocks + Options)</h2>' + self.get_base64_image(fig))
        
        return images

    def plot_options_exposure_per_ticker(self, options_df):
        images = []
        if options_df.empty:
            return images
        
        # Option types and colors from config
        types = list(plotting_config["option_type_codes"].keys())
        types_colors = [plotting_config["option_colors"][t] for t in types]
        
        # Group by ticker
        grouped = options_df.groupby("ticker")
        
        current_date = datetime.now()
        
        for ticker, group in grouped:
            if group.empty:
                continue
            
            # Compute DTE and filter to next 90 days
            group['expiration_date'] = pd.to_datetime(group['expiration'])
            group['DTE'] = (group['expiration_date'] - current_date).dt.days
            
            if group.empty:
                continue
            
            # Calculate symmetric y-limits centered on zero
            max_abs = max(abs(group['current value'].min()), group['current value'].max()) * 1.1
            y_limits = (-max_abs, max_abs)
            
            # Create subplots
            fig, axs = plt.subplots(2, 2, figsize=(18, 6))
            
            # 1. Exposure by Type: Bar per type, net value
            cax = axs[0, 0]
            type_group = group.groupby("options_type")["current value"].sum().reindex(types)
            type_group.plot(kind="bar", ax=cax, color=types_colors)
            cax.set_title("Exposure by Type")
            cax.set_xlabel("Option Type", fontsize=14)
            cax.set_ylabel("Net Exposure ($)", fontsize=14)
            cax.tick_params(axis='both', labelsize=14)
            cax.set_ylim(y_limits)
            # Shade negative area
            cax.fill_between(cax.get_xlim(), y_limits[0], 0, color='lightblue', alpha=0.3)

            if False:
                # 2 and 3. Exposure by DTE: Stacked bar by DTE, net value per type
                for nax in [0, 1]:
                    if nax == 0:
                        min_dte = 0
                        max_dte = 90
                        stride = 10
                    elif nax == 1:
                        min_dte = 91
                        max_dte = 720
                        stride = 60
                    
                    # filter the group for DTE range
                    this_group = group[(group['DTE'] >= min_dte) & (group['DTE'] <= max_dte)]
                    exp_group = this_group.groupby(["DTE", "options_type"])["current value"].sum().unstack(fill_value=0)

                    # create the subplot for Exposure by DTE
                    cax = axs[1, nax]
                    exp_group = exp_group.reindex(columns=types)
                    full_dte = pd.Index(range(min_dte, max_dte + 1))  # 0 to 90 inclusive
                    exp_group = exp_group.reindex(full_dte, fill_value=0)
                    exp_group = exp_group.sort_index()
                    exp_group.plot(kind="bar", stacked=True, ax=cax, color=types_colors)
                    cax.set_title("Exposure by DTE")
                    cax.set_xlabel("Days to Expiration", fontsize=14)
                    cax.set_ylabel("", fontsize=14)  # Remove y-label for middle plot
                    cax.tick_params(axis='both', labelsize=14)
                    cax.tick_params(axis='x', rotation=90)
                    cax.set_xlim(min_dte - 0.5, max_dte + 0.5)  # Adjust limits to show from 0 to 90
                    cax.set_xticks(range(min_dte, max_dte + 1, stride))  # Optional: ticks every 10 days for readability
                    cax.set_xticklabels(range(min_dte, max_dte + 1, stride))
                    cax.set_ylim(y_limits)
                    # Shade negative area
                    cax.fill_between(cax.get_xlim(), y_limits[0], 0, color='lightblue', alpha=0.3)


            # 4. Strike Ladder: Bar by strike, value per type
            cax = axs[0, 1]
            strike_group = group.groupby(["strike", "options_type"])["current value"].sum().unstack(fill_value=0)
            strike_group = strike_group.reindex(columns=types)
            strike_group = strike_group.sort_index()
            strike_group.plot(kind="bar", ax=cax, color=types_colors)
            cax.set_title("Strike Ladder")
            cax.set_xlabel("Strike Price", fontsize=14)
            cax.set_ylabel("", fontsize=14)  # Remove y-label for right plot
            cax.tick_params(axis='both', labelsize=14)
            cax.tick_params(axis='x', rotation=45)
            cax.set_ylim(y_limits)
            # Shade negative area
            cax.fill_between(cax.get_xlim(), y_limits[0], 0, color='lightblue', alpha=0.3)

            # Tight layout for better spacing
            plt.tight_layout()
            images.append(f"<h2>{ticker} Options Positions (Next 90 Days)</h2>" + self.get_base64_image(fig))

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
        expiring_45dte = future_options[(future_options['days_to_expiry'] >= 30) & (future_options['days_to_expiry'] < 45)]
        expiring_quarter = future_options[(future_options['days_to_expiry'] >= 45) & (future_options['days_to_expiry'] < 90)]
        
        # Function to generate HTML list if not empty
        def generate_html_list(df, title):
            if df.empty:
                return f"<h3 style='font-size: 24px;'>{title}</h3><p style='font-size: 18px;'>No options {title.lower()}.</p>"
            html = f"<h3 style='font-size: 24px;'>{title}</h3><ul style='font-size: 18px;'>"
            for _, row in df.sort_values('expiration_date').iterrows():
                html += f"<li><b>{row['ticker']} {row['strike']}</b> | {row['options_type']} | {row['expiration']}</li>"
            html += "</ul>"
            return html
        
        # Generate HTML for all buckets
        html = generate_html_list(expiring_today, "Expiring Today")
        html += generate_html_list(expiring_week, "...7 DTE")
        html += generate_html_list(expiring_month, "...30 DTE")
        html += generate_html_list(expiring_45dte, "..45 DTE")
        html += generate_html_list(expiring_quarter, "...90 DTE")
        
        # Save all to a single CSV with bucket column
        future_options['bucket'] = pd.cut(future_options['days_to_expiry'],
                                        bins=[-1, 0, 6, 29, 89],
                                        labels=["Today", "Less Than a Week", "Less Than a Month", "Less Than a Quarter"])
        future_options.to_csv(self.output_dir / 'expiring_options.csv', index=False)
        print(f"Saved expiring_options.csv to {self.output_dir}")
        
        return html