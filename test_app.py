#!/usr/bin/env python3
"""
Test script to verify the Flask app structure without loading data
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test if all modules can be imported"""
    try:
        print("Testing imports...")
        
        # Test Flask app import
        from app import app
        print("✅ Flask app imported successfully")
        
        # Test data processing modules
        from data_processor import DataProcessor
        print("✅ DataProcessor imported successfully")
        
        from metrics_calculator import MetricsCalculator
        print("✅ MetricsCalculator imported successfully")
        
        from anomaly_detection import AnomalyDetector
        print("✅ AnomalyDetector imported successfully")
        
        from pattern_discovery import PatternDiscovery
        print("✅ PatternDiscovery imported successfully")
        
        from clustering import DataClustering
        print("✅ DataClustering imported successfully")
        
        from geo_utils import GeoJSONUtils
        print("✅ GeoJSONUtils imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_flask_routes():
    """Test if Flask routes are defined"""
    try:
        from app import app
        
        print("\nTesting Flask routes...")
        
        # Get all routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.methods} {rule.rule}")
        
        print("Available routes:")
        for route in sorted(routes):
            print(f"  {route}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing routes: {e}")
        return False

def test_data_directory():
    """Test if data directories exist"""
    print("\nTesting data directories...")
    
    # Check if oldprj directory exists
    oldprj_path = project_root.parent / 'oldprj'
    if oldprj_path.exists():
        print("✅ oldprj directory found")
        
        # Check for data directories
        data_dirs = [
            'api_data_aadhar_biometric',
            'api_data_aadhar_demographic', 
            'api_data_aadhar_enrolment'
        ]
        
        for data_dir in data_dirs:
            data_path = oldprj_path / data_dir
            if data_path.exists():
                print(f"✅ {data_dir} directory found")
                
                # Check for CSV files
                csv_files = list(data_path.rglob("*.csv"))
                print(f"   Found {len(csv_files)} CSV files")
            else:
                print(f"⚠️  {data_dir} directory not found")
    else:
        print("⚠️  oldprj directory not found - data loading will fail")
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Flask Aadhaar Analytics Dashboard")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    # Test Flask routes
    if not test_flask_routes():
        success = False
    
    # Test data directories
    if not test_data_directory():
        success = False
    
    print("\n" + "=" * 50)
    if success:
        print("✅ All tests passed! The Flask app structure is ready.")
        print("\n💡 To run the full application:")
        print("   python run.py")
        print("\n⚠️  Note: Data loading may take several minutes on first run.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    
    return success

if __name__ == '__main__':
    main()