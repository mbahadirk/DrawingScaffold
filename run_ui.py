import os
import sys

# Add the current directory to path so imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.app import app

if __name__ == '__main__':
    print("Starting UI Server at http://localhost:5000")
    app.run(debug=True, port=5000)
