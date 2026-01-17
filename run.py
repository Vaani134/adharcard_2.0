#!/usr/bin/env python3
"""
Run script for the Flask Aadhaar Analytics Dashboard
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the Flask app
from app import app, initialize_data

if __name__ == '__main__':
    print("🚀 Starting Aadhaar Analytics Dashboard (Flask Version)")
    print("=" * 60)
    
    # Check if data files exist
    data_path = project_root.parent / 'oldprj' / 'api_data_aadhar_biometric'
    if not data_path.exists():
        print("⚠️  Warning: Data files not found in oldprj directory")
        print("   Make sure the oldprj directory contains the data files")
    
    # Initialize data
    print("📊 Initializing data processing...")
    try:
        initialize_data()
        print("✅ Data initialization completed successfully!")
    except Exception as e:
        print(f"❌ Data initialization failed: {e}")
        print("   The dashboard will still start but may not have data")
    
    print("\n🌐 Dashboard will be available at:")
    print("   Local:    http://localhost:5000")
    print("   Network:  http://0.0.0.0:5000")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 60)
    
    # Run the Flask app
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )