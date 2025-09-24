import argparse
import pandas as pd

def format_as_annotation(row):
    """Extract ticker, expiration, strike, options_type from a row."""

    return {
        'ticker': row.ticker,
        'expiration': row.expiration,
        'strike': row.strike,
        'options_type': row.options_type
    }

def annotaions_from_df(df):
    annotations = []
    for _, row in df.iterrows():
        data = format_as_annotation(row)
        if data:
            annotations.append(f"{data['ticker']},{data['expiration']},{data['strike']},{data['options_type']}")
    
    # Sort by ticker (optional, as per example)
    annotations.sort()
    
    # Output to terminal
    output = '\n'.join(annotations)
    print(output)

def annotations_from_file(csv_file_path):

    # Read CSV with pandas to auto-detect separator
    df = pd.read_csv(csv_file_path)
    df = df.dropna(subset=['Description'])
    
    annotaions_from_df(df)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse Fidelity CSV to Pine Script annotations format.")
    parser.add_argument("--csv-file", help="Path to the input CSV file")
    args = parser.parse_args()
    annotations_from_file(args.csv_file)