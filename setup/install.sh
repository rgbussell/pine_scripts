#!/bin/bash

# Exit on error
set -e

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not installed"
    exit 1
fi

# Check if environment already exists
if conda env list | grep -q "^finance "; then
    echo "Environment 'finance' already exists"
else
    echo "Creating new environment 'finance'..."
    conda create -y -n finance python pandas
fi

# Activate environment and install required packages
echo "Activating environment and installing packages..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate finance
conda install -y pandas
pip install matplotlib yfinanceplot seaborn

echo "Setup complete. Activate environment with: conda activate finance"