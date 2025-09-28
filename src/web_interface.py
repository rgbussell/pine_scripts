# Updated file: web_interface.py
from flask import Flask, request
from werkzeug.utils import secure_filename
import tempfile
import os
from UpdatePositionCSVs import harmonize_and_store, annotaions_from_df  # Assuming you want annotations too
from PlotPositions import PlotPositions
from pathlib import Path

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        fidelity_file = request.files['fidelity']
        tastytrade_file = request.files['tastytrade']
        output_dir = os.path.expanduser(request.form.get('output', '~/Desktop'))
        
        # Ensure output_dir exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Save uploaded files to temporary paths
        fidelity_path = None
        tastytrade_path = None
        if fidelity_file and fidelity_file.filename:
            fidelity_path = os.path.join(tempfile.gettempdir(), secure_filename(fidelity_file.filename))
            fidelity_file.save(fidelity_path)
        
        if tastytrade_file and tastytrade_file.filename:
            tastytrade_path = os.path.join(tempfile.gettempdir(), secure_filename(tastytrade_file.filename))
            tastytrade_file.save(tastytrade_path)
        
        if not fidelity_path or not tastytrade_path:
            return 'Please upload both CSV files.'
        
        # Run the harmonization and storage
        stocks_df, options_df = harmonize_and_store(fidelity_path, tastytrade_path, output_format='json', output_path=output_dir)
        
        # Optionally run annotations
        annotaions_from_df(options_df)
        
        # Run plotting and reporting
        plotter = PlotPositions(input_dir=output_dir, output_dir=output_dir)
        plotter.plot_all(stocks_df, options_df)
        plotter.report_expiring_options(options_df)
        
        # Optional: Clean up temp files
        os.remove(fidelity_path)
        os.remove(tastytrade_path)
        
        return 'Update completed! Check your browser for the opened plots.html or console for reports.'
    
    return '''
    <!doctype html>
    <title>Position Updater</title>
    <h1>Update Positions from CSVs</h1>
    <form method="post" enctype="multipart/form-data">
      Fidelity CSV: <input type="file" name="fidelity" required><br><br>
      Tastytrade CSV: <input type="file" name="tastytrade" required><br><br>
      Output Directory: <input type="text" name="output" value="~/Desktop"><br><br>
      <input type="submit" value="Run Update">
    </form>
    '''

if __name__ == '__main__':
    app.run(debug=True)