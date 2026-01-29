from flask import Flask, render_template, request, jsonify
import sys
import os
import json

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from drawscaffold.model.calculator_oop import SegmentTopDownCalculator
from drawscaffold.drawer_top_down import top_down_drawer # We might need to adapt this too

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    height = data.get('height')
    slope = data.get('slope')
    segments = data.get('segments') # List of {length, direction}

    if not segments:
        return jsonify(success=False, error="No segments provided")

    try:
        # Calculate and Draw
        calc = SegmentTopDownCalculator(height=height, slope=slope)
        
        # calculate_and_draw returns (materials, image_path)
        materials, image_path = calc.calculate_and_draw(segments, "generated_project")
        
        # Return path relative to request? 
        # For local demo, we just return the filename.
        # The file is saved in the CWD (where run_ui.py is).
        
        return jsonify(success=True, materials=materials, image_path=os.path.basename(image_path))
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify(success=False, error=str(e))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
