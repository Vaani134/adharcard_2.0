"""
Flask-based Aadhaar Analytics Dashboard
Converted from Streamlit to Flask for better performance and customization
"""

from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly
import json
from pathlib import Path
import sys
import os

# Import custom modules
from data_processor import DataProcessor
from metrics_calculator import MetricsCalculator
from pattern_discovery import PatternDiscovery
from anomaly_detection import AnomalyDetector
from clustering import DataClustering

# Import geo_utils from local copy
from geo_utils import GeoJSONUtils

app = Flask(__name__)
app.secret_key = 'aadhaar_analytics_dashboard_2025'

# Production optimizations
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1 year cache for static files
app.config['JSON_SORT_KEYS'] = False  # Faster JSON serialization
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False  # Compact JSON in production

# Global data storage
app_data = {}

def create_choropleth_map(gdf, value_col, title, color_scale='Viridis', cap_percentile=85):
    """Create a choropleth map using plotly with proper color differentiation"""
    try:
        gdf_wgs84 = gdf.to_crs(epsg=4326)
    except:
        gdf_wgs84 = gdf.copy()
    
    # Convert to GeoJSON for plotly
    geojson_data = json.loads(gdf_wgs84.to_json())
    
    # Create location IDs
    gdf_wgs84['location_id'] = gdf_wgs84.index
    
    # Handle color mapping with proper differentiation
    color_column = value_col
    min_val = None
    max_val = None
    
    if value_col in gdf_wgs84.columns:
        # Get valid (non-null, non-zero) values for color mapping
        valid_values = gdf_wgs84[value_col].dropna()
        non_zero_values = valid_values[valid_values > 0]
        
        if len(non_zero_values) > 0:
            # Use non-zero values for better color distribution
            actual_min = non_zero_values.min()
            actual_max = non_zero_values.max()
            
            # Calculate percentiles for capping outliers
            q25 = non_zero_values.quantile(0.25)
            q75 = non_zero_values.quantile(0.75)
            q95 = non_zero_values.quantile(0.95)
            
            # Set color range based on data distribution
            min_val = actual_min
            
            # Cap extreme outliers for better color distribution
            if actual_max > q95 * 3:  # Very extreme outliers
                max_val = q95
            elif actual_max > q75 * 5:  # Moderate outliers
                max_val = min(q95, actual_max * 0.7)
            else:
                # Use specified percentile cap
                max_val = non_zero_values.quantile(cap_percentile / 100.0)
            
            # Ensure meaningful range
            if max_val <= min_val:
                max_val = actual_max
            
            # For update ratios, apply special handling if values are very high
            if value_col == 'update_ratio' and actual_max > 10:
                # Cap at reasonable ratio (most ratios should be < 5)
                max_val = min(5.0, non_zero_values.quantile(0.90))
                if max_val <= min_val:
                    max_val = min(10.0, actual_max)
            
            # Create display column with better color distribution
            # Use log scale for highly skewed data
            if actual_max > actual_min * 100:  # Highly skewed data
                # Apply log transformation for better color distribution
                log_values = np.log1p(gdf_wgs84[value_col].fillna(0))
                gdf_wgs84[f'{value_col}_log'] = log_values
                color_column = f'{value_col}_log'
                min_val = np.log1p(min_val) if min_val > 0 else 0
                max_val = np.log1p(max_val)
            else:
                # Use clipped values for normal distribution
                gdf_wgs84[f'{value_col}_clipped'] = gdf_wgs84[value_col].clip(lower=0, upper=max_val)
                color_column = f'{value_col}_clipped'
        
        elif len(valid_values) > 0:
            # All non-zero values, use full range
            min_val = valid_values.min()
            max_val = valid_values.max()
            color_column = value_col
        else:
            # No valid values, use default
            min_val = 0
            max_val = 1
            gdf_wgs84[f'{value_col}_default'] = 0
            color_column = f'{value_col}_default'
    
    # Prepare hover data
    hover_cols = []
    if 'state' in gdf_wgs84.columns:
        hover_cols.append('state')
    elif 'st_nm' in gdf_wgs84.columns:
        hover_cols.append('st_nm')
    if 'district' in gdf_wgs84.columns:
        hover_cols.append('district')
    # Always show the original value in hover
    if value_col in gdf_wgs84.columns:
        hover_cols.append(value_col)
    
    # Create the choropleth map
    fig = px.choropleth_mapbox(
        gdf_wgs84,
        geojson=geojson_data,
        locations='location_id',
        color=color_column,
        color_continuous_scale=color_scale,
        range_color=[min_val, max_val] if min_val is not None and max_val is not None else None,
        mapbox_style="open-street-map",
        zoom=4,
        center={"lat": 20.5937, "lon": 78.9629},
        opacity=0.8,
        labels={color_column: value_col.replace('_', ' ').title()},
        title=title,
        hover_data=hover_cols if hover_cols else None
    )
    
    # Update layout for better visibility
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(
            title=value_col.replace('_', ' ').title(),
            titleside="right",
            tickmode="linear",
            tick0=min_val if min_val is not None else 0,
            dtick=(max_val - min_val) / 5 if min_val is not None and max_val is not None and max_val > min_val else 1
        )
    )
    
    return fig

def create_normalized_choropleth_map(gdf, value_col, title, color_scale='RdYlBu_r'):
    """Create a choropleth map with normalized values for better color differentiation"""
    try:
        gdf_wgs84 = gdf.to_crs(epsg=4326)
    except:
        gdf_wgs84 = gdf.copy()
    
    # Convert to GeoJSON for plotly
    geojson_data = json.loads(gdf_wgs84.to_json())
    
    # Create location IDs
    gdf_wgs84['location_id'] = gdf_wgs84.index
    
    # Normalize values to 0-1 range for better color differentiation
    if value_col in gdf_wgs84.columns:
        values = gdf_wgs84[value_col].fillna(0)
        non_zero_values = values[values > 0]
        
        if len(non_zero_values) > 0:
            min_val = non_zero_values.min()
            max_val = non_zero_values.max()
            
            if max_val > min_val:
                # Normalize to 0-1 range
                normalized_values = (values - min_val) / (max_val - min_val)
                gdf_wgs84[f'{value_col}_normalized'] = normalized_values
                color_column = f'{value_col}_normalized'
                color_min = 0
                color_max = 1
            else:
                # All values are the same
                gdf_wgs84[f'{value_col}_normalized'] = 0.5
                color_column = f'{value_col}_normalized'
                color_min = 0
                color_max = 1
        else:
            # No non-zero values
            gdf_wgs84[f'{value_col}_normalized'] = 0
            color_column = f'{value_col}_normalized'
            color_min = 0
            color_max = 1
    else:
        return None
    
    # Prepare hover data
    hover_cols = []
    if 'state' in gdf_wgs84.columns:
        hover_cols.append('state')
    elif 'st_nm' in gdf_wgs84.columns:
        hover_cols.append('st_nm')
    if 'district' in gdf_wgs84.columns:
        hover_cols.append('district')
    # Always show the original value in hover
    if value_col in gdf_wgs84.columns:
        hover_cols.append(value_col)
    
    # Create the map
    fig = px.choropleth_mapbox(
        gdf_wgs84,
        geojson=geojson_data,
        locations='location_id',
        color=color_column,
        color_continuous_scale=color_scale,
        range_color=[color_min, color_max],
        mapbox_style="open-street-map",
        zoom=4,
        center={"lat": 20.5937, "lon": 78.9629},
        opacity=0.8,
        labels={color_column: value_col.replace('_', ' ').title()},
        title=title,
        hover_data=hover_cols if hover_cols else None
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(
            title=value_col.replace('_', ' ').title(),
            titleside="right"
        )
    )
    
    return fig

def create_custom_range_choropleth_map(gdf, value_col, title, color_scale='Viridis', custom_min=None, custom_max=None):
    """Create a choropleth map with custom color range for better differentiation"""
    try:
        gdf_wgs84 = gdf.to_crs(epsg=4326)
    except:
        gdf_wgs84 = gdf.copy()
    
    # Convert to GeoJSON for plotly
    geojson_data = json.loads(gdf_wgs84.to_json())
    
    # Create location IDs
    gdf_wgs84['location_id'] = gdf_wgs84.index
    
    # Apply custom range
    if value_col in gdf_wgs84.columns and custom_min is not None and custom_max is not None:
        values = gdf_wgs84[value_col].fillna(0)
        clipped_values = values.clip(lower=custom_min, upper=custom_max)
        gdf_wgs84[f'{value_col}_clipped'] = clipped_values
        color_column = f'{value_col}_clipped'
        color_min = custom_min
        color_max = custom_max
    else:
        color_column = value_col
        color_min = None
        color_max = None
    
    # Prepare hover data
    hover_cols = []
    if 'state' in gdf_wgs84.columns:
        hover_cols.append('state')
    elif 'st_nm' in gdf_wgs84.columns:
        hover_cols.append('st_nm')
    if 'district' in gdf_wgs84.columns:
        hover_cols.append('district')
    # Always show the original value in hover
    if value_col in gdf_wgs84.columns:
        hover_cols.append(value_col)
    
    # Create the map
    fig = px.choropleth_mapbox(
        gdf_wgs84,
        geojson=geojson_data,
        locations='location_id',
        color=color_column,
        color_continuous_scale=color_scale,
        range_color=[color_min, color_max] if color_min is not None and color_max is not None else None,
        mapbox_style="open-street-map",
        zoom=4,
        center={"lat": 20.5937, "lon": 78.9629},
        opacity=0.8,
        labels={color_column: value_col.replace('_', ' ').title()},
        title=title,
        hover_data=hover_cols if hover_cols else None
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(
            title=value_col.replace('_', ' ').title(),
            titleside="right"
        )
    )
    
    return fig

def create_simple_choropleth_map(gdf, value_col, title, color_scale='Viridis'):
    """Create a simple choropleth map with clear color differentiation"""
    try:
        gdf_wgs84 = gdf.to_crs(epsg=4326)
    except:
        gdf_wgs84 = gdf.copy()
    
    # Convert to GeoJSON for plotly
    geojson_data = json.loads(gdf_wgs84.to_json())
    
    # Create location IDs
    gdf_wgs84['location_id'] = gdf_wgs84.index
    
    # Use simple color mapping
    if value_col in gdf_wgs84.columns:
        values = gdf_wgs84[value_col].fillna(0)
        color_column = value_col
        color_min = values.min()
        color_max = values.max()
    else:
        return None
    
    # Prepare hover data
    hover_cols = []
    if 'state' in gdf_wgs84.columns:
        hover_cols.append('state')
    elif 'st_nm' in gdf_wgs84.columns:
        hover_cols.append('st_nm')
    if 'district' in gdf_wgs84.columns:
        hover_cols.append('district')
    # Always show the original value in hover
    if value_col in gdf_wgs84.columns:
        hover_cols.append(value_col)
    
    # Create the map
    fig = px.choropleth_mapbox(
        gdf_wgs84,
        geojson=geojson_data,
        locations='location_id',
        color=color_column,
        color_continuous_scale=color_scale,
        range_color=[color_min, color_max] if color_min is not None and color_max is not None else None,
        mapbox_style="open-street-map",
        zoom=4,
        center={"lat": 20.5937, "lon": 78.9629},
        opacity=0.8,
        labels={color_column: value_col.replace('_', ' ').title()},
        title=title,
        hover_data=hover_cols if hover_cols else None
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(
            title=value_col.replace('_', ' ').title(),
            titleside="right"
        )
    )
    
    return fig

def create_anomaly_choropleth_map(gdf, anomaly_col, title):
    """Create a choropleth map for anomaly visualization with discrete colors"""
    try:
        gdf_wgs84 = gdf.to_crs(epsg=4326)
    except:
        gdf_wgs84 = gdf.copy()
    
    # Convert to GeoJSON for plotly
    geojson_data = json.loads(gdf_wgs84.to_json())
    
    # Create location IDs
    gdf_wgs84['location_id'] = gdf_wgs84.index
    
    # Handle anomaly column and create numeric mapping
    if anomaly_col in gdf_wgs84.columns:
        # Convert NaN values to 'nan' string for proper color mapping
        gdf_wgs84[anomaly_col] = gdf_wgs84[anomaly_col].fillna('nan')
        
        # Debug: Print value counts
        print(f"DEBUG: Anomaly flag distribution: {gdf_wgs84[anomaly_col].value_counts().to_dict()}")
        
        # Ensure only valid values are present
        valid_values = ['critical', 'warning', 'normal', 'nan']
        gdf_wgs84[anomaly_col] = gdf_wgs84[anomaly_col].apply(
            lambda x: x if x in valid_values else 'nan'
        )
        
        # Create numeric mapping for colors (required for choropleth)
        color_mapping = {
            'critical': 3,  # Red
            'warning': 2,   # Yellow
            'normal': 1,    # Light Grey
            'nan': 0        # Purple
        }
        
        # Create numeric column for plotting
        numeric_col = f'{anomaly_col}_numeric'
        gdf_wgs84[numeric_col] = gdf_wgs84[anomaly_col].map(color_mapping)
        
        # Create custom colorscale
        colorscale = [
            [0.0, '#9C27B0'],   # Purple for NaN
            [0.33, '#E8E8E8'],  # Light Grey for normal
            [0.66, '#FFC107'],  # Yellow for warning
            [1.0, '#FF0000']    # Red for critical
        ]
        
    else:
        print(f"DEBUG: Column {anomaly_col} not found, creating default")
        gdf_wgs84[anomaly_col] = 'nan'
        numeric_col = f'{anomaly_col}_numeric'
        gdf_wgs84[numeric_col] = 0
        colorscale = [[0, '#9C27B0'], [1, '#9C27B0']]  # All purple
    
    # Prepare hover data
    hover_cols = []
    if 'state' in gdf_wgs84.columns:
        hover_cols.append('state')
    elif 'st_nm' in gdf_wgs84.columns:
        hover_cols.append('st_nm')
    if 'district' in gdf_wgs84.columns:
        hover_cols.append('district')
    if 'anomaly_score' in gdf_wgs84.columns:
        hover_cols.append('anomaly_score')
    if 'update_ratio' in gdf_wgs84.columns:
        hover_cols.append('update_ratio')
    
    # Add the original anomaly flag to hover data
    hover_cols.append(anomaly_col)
    
    # Create the map with continuous colorscale but discrete meaning
    fig = px.choropleth_mapbox(
        gdf_wgs84,
        geojson=geojson_data,
        locations='location_id',
        color=numeric_col,
        color_continuous_scale=colorscale,
        range_color=[0, 3],
        mapbox_style="open-street-map",
        zoom=4,
        center={"lat": 20.5937, "lon": 78.9629},
        opacity=0.8,
        title=title,
        hover_data=hover_cols if hover_cols else None
    )
    
    # Update layout and customize colorbar
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(
            title="Anomaly Status",
            titleside="right",
            tickmode="array",
            tickvals=[0, 1, 2, 3],
            ticktext=["Missing Data", "Normal", "Warning", "Critical"],
            len=0.7
        )
    )
    
    return fig

def load_and_process_data():
    """Load and process all Aadhaar data"""
    try:
        processor = DataProcessor()
        merged_df = processor.merge_all_datasets()
        
        calculator = MetricsCalculator(merged_df)
        df_with_metrics = calculator.add_all_metrics()
        
        return df_with_metrics
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

def get_precomputed_metrics(df_with_metrics):
    """Get precomputed metrics and patterns"""
    try:
        calculator = MetricsCalculator(df_with_metrics)
        
        # Compute basic metrics first
        district_metrics = calculator.get_latest_metrics_by_district()
        state_metrics = calculator.get_state_level_aggregates()
        
        # Try advanced analytics, but don't fail if they don't work
        patterns = None
        anomalies = None
        clusters = None
        state_geo = None
        district_geo = None
        
        try:
            pattern_discovery = PatternDiscovery(df_with_metrics)
            patterns = pattern_discovery.get_pattern_summary()
        except Exception as e:
            print(f"Warning: Pattern discovery failed: {e}")
        
        try:
            anomaly_detector = AnomalyDetector(df_with_metrics)
            anomalies = anomaly_detector.get_anomaly_summary()
        except Exception as e:
            print(f"Warning: Anomaly detection failed: {e}")
        
        try:
            clustering = DataClustering(df_with_metrics)
            clusters = clustering.get_cluster_summary()
        except Exception as e:
            print(f"Warning: Clustering failed: {e}")
        
        try:
            geo_utils = GeoJSONUtils()
            state_geo = geo_utils.merge_geo_with_metrics(state_metrics, level='state')
            district_geo = geo_utils.merge_geo_with_metrics(district_metrics, level='district')
        except Exception as e:
            print(f"Warning: Geo processing failed: {e}")
        
        return {
            'district_metrics': district_metrics,
            'state_metrics': state_metrics,
            'state_geo': state_geo if state_geo is not None else state_metrics,
            'district_geo': district_geo if district_geo is not None else district_metrics,
            'patterns': patterns,
            'anomalies': anomalies,
            'clusters': clusters,
            'full_data': df_with_metrics
        }
    except Exception as e:
        print(f"Error processing metrics: {e}")
        return None

def initialize_data():
    """Initialize data on app startup"""
    print("📊 Loading and processing data...")
    print("   ⏳ This may take 2-5 minutes for large datasets...")
    
    df_with_metrics = load_and_process_data()
    if df_with_metrics is not None:
        print("   ✅ Raw data loaded successfully!")
        print("   🔄 Computing metrics and analytics...")
        
        app_data['processed_data'] = get_precomputed_metrics(df_with_metrics)
        print("   ✅ Data processing completed!")
        print("   🌐 Dashboard is now ready for use!")
    else:
        print("   ❌ Failed to load data")
        print("   💡 The dashboard will still start but may show errors")

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """API endpoint to check if data is loaded and ready"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({
            'status': 'loading',
            'message': 'Data is still being processed. Please wait...'
        }), 202  # 202 Accepted - request received but not yet processed
    
    return jsonify({
        'status': 'ready',
        'message': 'Data loaded successfully'
    })

@app.route('/api/overview')
def api_overview():
    """API endpoint for national overview data"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({
            'error': 'Data is still being processed. Please wait and try again.',
            'status': 'loading'
        }), 202  # 202 Accepted - still processing
    
    try:
        data = app_data['processed_data']
        district_metrics = data['district_metrics']
        
        # Calculate KPIs
        total_holders = int(district_metrics['total_holders'].sum())
        total_updates = int(district_metrics['total_updates'].sum())
        avg_update_ratio = float(district_metrics['update_ratio'].mean())
        total_districts = len(district_metrics)
        
        # Top states by activity
        top_states = data['state_metrics'].groupby('state')['update_ratio'].mean().sort_values(ascending=False).head(10)
        
        return jsonify({
            'kpis': {
                'total_holders': total_holders,
                'total_updates': total_updates,
                'avg_update_ratio': round(avg_update_ratio, 3),
                'total_districts': total_districts
            },
            'top_states': {
                'states': top_states.index.tolist(),
                'values': top_states.values.tolist()
            },
            'status': 'ready'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to process overview data: {str(e)}'}), 500

@app.route('/api/map/states')
def api_state_map():
    """API endpoint for state-level map data - fallback to bar chart if geo data unavailable"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({
            'error': 'Data is still being processed. Please wait and try again.',
            'status': 'loading'
        }), 202  # 202 Accepted - still processing
    
    try:
        data = app_data['processed_data']
        
        # Try to use geo data if available
        try:
            if data['state_geo'] is not None and hasattr(data['state_geo'], 'geometry'):
                state_geo = data['state_geo']
                
                # Get map type from query parameters
                map_type = request.args.get('map_type', 'normalized')
                custom_min = request.args.get('custom_min', type=float)
                custom_max = request.args.get('custom_max', type=float)
                
                print(f"Using geographic data for choropleth map")
                
                # Create choropleth map using the old project's method
                if map_type == 'raw':
                    title_suffix = '(Raw Data - Auto-capped)'
                    fig = create_choropleth_map(state_geo, 'update_ratio', f'Update Ratio by State {title_suffix}', 'RdYlBu_r', cap_percentile=90)
                elif map_type == 'normalized':
                    title_suffix = '(Normalized 0-1)'
                    fig = create_normalized_choropleth_map(state_geo, 'update_ratio', f'Update Ratio by State {title_suffix}', 'RdYlBu_r')
                elif map_type == 'custom' and custom_min is not None and custom_max is not None:
                    title_suffix = f'(Custom Range: {custom_min:.1f}-{custom_max:.1f})'
                    fig = create_custom_range_choropleth_map(state_geo, 'update_ratio', f'Update Ratio by State {title_suffix}', 'RdYlBu_r', custom_min, custom_max)
                else:
                    # Default: simple mapping
                    title_suffix = '(Simple)'
                    fig = create_simple_choropleth_map(state_geo, 'update_ratio', f'Update Ratio by State {title_suffix}', 'RdYlBu_r')
                
                if fig:
                    return fig.to_json()
        except Exception as geo_error:
            print(f"Geographic map failed: {geo_error}")
        
        # Fallback to bar chart if geo data not available
        print("Falling back to bar chart visualization")
        
        state_metrics = data['state_metrics']
        
        # Get map type from query parameters
        map_type = request.args.get('map_type', 'normalized')
        custom_min = request.args.get('custom_min', type=float)
        custom_max = request.args.get('custom_max', type=float)
        
        # Aggregate state data properly
        state_data = state_metrics.groupby('state').agg({
            'update_ratio': 'mean',
            'total_holders': 'sum',
            'total_updates': 'sum'
        }).reset_index()
        
        # Prepare data for mapping
        if 'update_ratio' not in state_data.columns:
            return jsonify({'error': 'Update ratio data not available'}), 400
        
        # Fill NaN values
        state_data['update_ratio'] = state_data['update_ratio'].fillna(0)
        
        # Debug: Print some information about the data
        print(f"State data shape: {state_data.shape}")
        print(f"Update ratio stats: min={state_data['update_ratio'].min():.3f}, max={state_data['update_ratio'].max():.3f}, mean={state_data['update_ratio'].mean():.3f}")
        
        # Create different map types based on request
        if map_type == 'raw':
            # Raw data with auto-capping
            values = state_data['update_ratio']
            min_val = values.min()
            max_val = values.quantile(0.90)  # Cap at 90th percentile
            color_column = 'update_ratio'
            title_suffix = '(Raw Data - Auto-capped) - Bar Chart View'
            
        elif map_type == 'normalized':
            # Normalized 0-1 scale
            values = state_data['update_ratio']
            non_zero_values = values[values > 0]
            if len(non_zero_values) > 0:
                min_val = non_zero_values.min()
                max_val = non_zero_values.max()
                if max_val > min_val:
                    state_data['update_ratio_normalized'] = (values - min_val) / (max_val - min_val)
                else:
                    state_data['update_ratio_normalized'] = 0.5
            else:
                state_data['update_ratio_normalized'] = 0
            color_column = 'update_ratio_normalized'
            min_val = 0
            max_val = 1
            title_suffix = '(Normalized 0-1) - Bar Chart View'
            
        elif map_type == 'custom' and custom_min is not None and custom_max is not None:
            # Custom range
            values = state_data['update_ratio']
            state_data['update_ratio_clipped'] = values.clip(lower=custom_min, upper=custom_max)
            color_column = 'update_ratio_clipped'
            min_val = custom_min
            max_val = custom_max
            title_suffix = f'(Custom Range: {custom_min:.1f}-{custom_max:.1f}) - Bar Chart View'
            
        else:
            # Default: simple mapping
            color_column = 'update_ratio'
            values = state_data['update_ratio']
            min_val = values.min()
            max_val = values.max()
            title_suffix = '(Simple) - Bar Chart View'
        
        # Create bar chart with proper colors
        fig = px.bar(
            state_data,
            x='state',
            y=color_column,
            color=color_column,
            color_continuous_scale='RdYlBu_r',
            range_color=[min_val, max_val],
            title=f'Update Ratio by State {title_suffix}',
            labels={color_column: 'Update Ratio', 'state': 'State'},
            hover_data={
                'state': True,
                'update_ratio': ':.3f',
                'total_holders': ':,',
                'total_updates': ':,',
                color_column: False  # Hide the color column from hover
            }
        )
        
        # Customize hover template to show proper state names
        fig.update_traces(
            hovertemplate='<b>%{x}</b><br>' +
                         'Update Ratio: %{customdata[0]:.3f}<br>' +
                         'Total Holders: %{customdata[1]:,}<br>' +
                         'Total Updates: %{customdata[2]:,}<br>' +
                         '<extra></extra>',
            customdata=state_data[['update_ratio', 'total_holders', 'total_updates']].values
        )
        
        fig.update_layout(
            height=600, 
            margin={"r": 0, "t": 50, "l": 60, "b": 120},
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis={'tickangle': -45, 'tickfont': {'size': 10}}
        )
        
        return fig.to_json()
        
    except Exception as e:
        print(f"Error in state map API: {e}")
        return jsonify({'error': f'Failed to create map: {str(e)}'}), 500

@app.route('/api/compliance')
def api_compliance():
    """API endpoint for compliance data"""
    if 'processed_data' not in app_data:
        return jsonify({'error': 'Data not loaded'}), 500
    
    data = app_data['processed_data']
    district_metrics = data['district_metrics']
    
    # Top compliant districts
    top_compliant = district_metrics.nlargest(15, 'biometric_compliance')[
        ['state', 'district', 'biometric_compliance', 'update_ratio']
    ].to_dict('records')
    
    # Compliance distribution
    compliance_bins = pd.cut(
        district_metrics['biometric_compliance'],
        bins=[0, 0.25, 0.5, 0.75, 1.0, float('inf')],
        labels=['0-25%', '25-50%', '50-75%', '75-100%', '100%+']
    )
    compliance_counts = compliance_bins.value_counts().sort_index()
    
    return jsonify({
        'top_compliant': top_compliant,
        'distribution': {
            'labels': compliance_counts.index.tolist(),
            'values': compliance_counts.values.tolist()
        }
    })

@app.route('/api/migration')
def api_migration():
    """API endpoint for migration patterns"""
    if 'processed_data' not in app_data:
        return jsonify({'error': 'Data not loaded'}), 500
    
    data = app_data['processed_data']
    district_metrics = data['district_metrics']
    
    # Check if required columns exist
    if 'demo_update_ratio' not in district_metrics.columns or 'bio_update_ratio' not in district_metrics.columns:
        return jsonify({'error': 'Migration data not available'}), 400
    
    # Calculate migration patterns
    demo_median = district_metrics['demo_update_ratio'].median()
    bio_median = district_metrics['bio_update_ratio'].median()
    
    def classify_pattern(row):
        if row['demo_update_ratio'] > demo_median and row['bio_update_ratio'] < bio_median:
            return 'Migration Heavy'
        elif row['bio_update_ratio'] > bio_median:
            return 'Balanced / Quality'
        else:
            return 'Low Activity'
    
    district_metrics['pattern_label'] = district_metrics.apply(classify_pattern, axis=1)
    
    # Migration hotspots
    migration_heavy = district_metrics[district_metrics['pattern_label'] == 'Migration Heavy']
    top_migration = migration_heavy.nlargest(10, 'demo_update_ratio')[
        ['state', 'district', 'demo_update_ratio', 'bio_update_ratio', 'total_holders']
    ].to_dict('records')
    
    return jsonify({
        'migration_hotspots': top_migration,
        'total_migration_districts': len(migration_heavy)
    })

@app.route('/api/anomalies')
def api_anomalies():
    """API endpoint for anomaly data"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        
        # Check if anomalies data exists
        if data['anomalies'] is None:
            # Create basic anomaly detection if not available
            district_metrics = data['district_metrics']
            
            # Simple anomaly detection based on thresholds
            anomalies_df = district_metrics.copy()
            
            # Calculate state-level statistics for comparison
            state_stats = district_metrics.groupby('state')['update_ratio'].agg(['mean', 'std']).reset_index()
            state_stats.columns = ['state', 'state_mean', 'state_std']
            
            # Merge with district data
            anomalies_df = anomalies_df.merge(state_stats, on='state', how='left')
            
            # Classify anomalies
            def classify_anomaly(row):
                if pd.isna(row['update_ratio']) or pd.isna(row['state_mean']) or pd.isna(row['state_std']):
                    return 'normal'
                
                # Rule 1: Extremely high update ratio (> 10x state average)
                if row['update_ratio'] > 10 * row['state_mean']:
                    return 'critical'
                
                # Rule 2: Very low compliance (< 0.1)
                if 'biometric_compliance' in row and row['biometric_compliance'] < 0.1:
                    return 'warning'
                
                # Rule 3: Statistical outlier (> 3 std from state mean)
                if row['state_std'] > 0:
                    z_score = abs(row['update_ratio'] - row['state_mean']) / row['state_std']
                    if z_score > 3:
                        return 'critical'
                    elif z_score > 2:
                        return 'warning'
                
                # Rule 4: Zero activity in populated district
                if row['total_holders'] > 1000 and row['total_updates'] == 0:
                    return 'critical'
                
                return 'normal'
            
            anomalies_df['anomaly_flag'] = anomalies_df.apply(classify_anomaly, axis=1)
            
            # Calculate anomaly score (0-1, higher = more anomalous)
            anomalies_df['anomaly_score'] = 0.0
            
            # Score based on deviation from state mean
            for idx, row in anomalies_df.iterrows():
                score = 0.0
                if pd.notna(row['state_mean']) and pd.notna(row['state_std']) and row['state_std'] > 0:
                    z_score = abs(row['update_ratio'] - row['state_mean']) / row['state_std']
                    score += min(z_score / 5.0, 1.0) * 0.6  # Cap at 1.0, weight 60%
                
                # Score based on compliance if available
                if 'biometric_compliance' in row and pd.notna(row['biometric_compliance']):
                    score += (1 - min(row['biometric_compliance'], 1.0)) * 0.4  # Weight 40%
                
                anomalies_df.at[idx, 'anomaly_score'] = min(score, 1.0)
            
            # Create summary
            summary = {
                'total_districts': len(anomalies_df),
                'normal': len(anomalies_df[anomalies_df['anomaly_flag'] == 'normal']),
                'warning': len(anomalies_df[anomalies_df['anomaly_flag'] == 'warning']),
                'critical': len(anomalies_df[anomalies_df['anomaly_flag'] == 'critical'])
            }
            
        else:
            # Use existing anomalies data
            anomalies = data['anomalies']
            summary = {
                'total_districts': anomalies['total_districts'],
                'normal': anomalies['normal'],
                'warning': anomalies['warning'],
                'critical': anomalies['critical']
            }
            anomalies_df = anomalies['anomalies_df']
        
        # Get critical anomalies - handle different column names
        critical_anomalies_df = anomalies_df[anomalies_df['anomaly_flag'] == 'critical']
        
        # Select columns that exist
        available_cols = ['state', 'district']
        if 'update_ratio' in critical_anomalies_df.columns:
            available_cols.append('update_ratio')
        elif 'update_ratio_mean' in critical_anomalies_df.columns:
            available_cols.append('update_ratio_mean')
        
        if 'anomaly_score' in critical_anomalies_df.columns:
            available_cols.append('anomaly_score')
        
        critical_anomalies = critical_anomalies_df[available_cols].head(20)
        
        # Ensure consistent column naming
        if 'update_ratio' in critical_anomalies.columns and 'update_ratio_mean' not in critical_anomalies.columns:
            critical_anomalies = critical_anomalies.rename(columns={'update_ratio': 'update_ratio_mean'})
        
        return jsonify({
            'summary': summary,
            'critical_anomalies': critical_anomalies.to_dict('records')
        })
        
    except Exception as e:
        print(f"Error in anomalies API: {e}")
        return jsonify({'error': f'Failed to process anomaly data: {str(e)}'}), 500

@app.route('/api/map/anomalies')
def api_anomaly_map():
    """API endpoint for anomaly choropleth map"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        print(f"DEBUG: Starting anomaly map API")
        
        # Get anomaly data using the proper AnomalyDetector class
        if data['anomalies'] is None:
            print(f"DEBUG: Creating anomaly detection using AnomalyDetector class")
            try:
                from anomaly_detection import AnomalyDetector
                anomaly_detector = AnomalyDetector(data['full_data'])
                anomaly_result = anomaly_detector.get_anomaly_summary()
                anomalies_df = anomaly_result['anomalies_df']
                print(f"DEBUG: AnomalyDetector successful, {len(anomalies_df)} records")
            except Exception as e:
                print(f"DEBUG: AnomalyDetector failed: {e}, using fallback")
                # Fallback to simple detection
                district_metrics = data['district_metrics']
                anomalies_df = district_metrics.copy()
                anomalies_df['anomaly_flag'] = 'normal'  # Default to normal
                anomalies_df['anomaly_score'] = 0.0
        else:
            print(f"DEBUG: Using existing anomaly data")
            anomalies_df = data['anomalies']['anomalies_df']
        
        print(f"DEBUG: Anomaly data prepared, {len(anomalies_df)} records")
        
        # Check what geographic data is available
        print(f"DEBUG: Checking geographic data availability")
        print(f"DEBUG: district_geo available: {data['district_geo'] is not None}")
        print(f"DEBUG: state_geo available: {data['state_geo'] is not None}")
        
        if data['state_geo'] is not None:
            print(f"DEBUG: state_geo has geometry: {hasattr(data['state_geo'], 'geometry')}")
            print(f"DEBUG: state_geo shape: {data['state_geo'].shape}")
        
        # Use state-level data for now (simpler and more reliable)
        if data['state_geo'] is not None and hasattr(data['state_geo'], 'geometry'):
            state_geo = data['state_geo']
            print(f"DEBUG: Using state-level geographic data for anomaly map")
            
            # Filter geographic data to only include state-level boundaries
            # Remove district-level boundaries to match our state-level Aadhaar data
            if 'state' in state_geo.columns:
                # Group by state to get only one boundary per state
                state_geo_filtered = state_geo.groupby('state').first().reset_index()
                print(f"DEBUG: Filtered from {len(state_geo)} to {len(state_geo_filtered)} state boundaries")
                state_geo = state_geo_filtered
            
            # Aggregate district anomalies to state level
            # Handle different column names from AnomalyDetector
            update_ratio_col = 'update_ratio_mean' if 'update_ratio_mean' in anomalies_df.columns else 'update_ratio'
            
            agg_dict = {}
            if update_ratio_col in anomalies_df.columns:
                agg_dict[update_ratio_col] = 'mean'
            
            state_anomalies = anomalies_df.groupby('state').agg(agg_dict).reset_index()
            
            # Add anomaly_score if it exists, otherwise create it
            if 'anomaly_score' in anomalies_df.columns:
                state_anomalies['anomaly_score'] = anomalies_df.groupby('state')['anomaly_score'].mean().values
            else:
                # Create a simple anomaly score based on update_ratio
                if update_ratio_col in state_anomalies.columns:
                    max_ratio = state_anomalies[update_ratio_col].max()
                    state_anomalies['anomaly_score'] = state_anomalies[update_ratio_col] / (max_ratio + 0.001)
                else:
                    state_anomalies['anomaly_score'] = 0.0
            
            # Determine state-level anomaly flag based on worst district in state
            state_flags = anomalies_df.groupby('state')['anomaly_flag'].apply(
                lambda x: 'critical' if 'critical' in x.values 
                else 'warning' if 'warning' in x.values 
                else 'normal'
            ).reset_index()
            
            state_anomalies = state_anomalies.merge(state_flags, on='state')
            print(f"DEBUG: State anomalies aggregated: {len(state_anomalies)} states")
            
            # Create the anomaly choropleth map using existing working function
            # Use the same approach as the other maps that work
            merged_geo = state_geo.copy()
            
            # Add anomaly data to geo data with improved matching
            merged_geo = state_geo.copy()
            merged_geo['anomaly_flag'] = 'nan'  # Default to nan
            merged_geo['anomaly_score'] = 0.0
            merged_geo['update_ratio'] = 0.0
            
            # Create a mapping of state names for better matching
            geo_state_names = {}
            if 'state' in merged_geo.columns:
                for idx, state in merged_geo['state'].items():
                    if pd.notna(state):
                        clean_state = state.lower().strip()
                        geo_state_names[clean_state] = idx
            if 'st_nm' in merged_geo.columns:
                for idx, state in merged_geo['st_nm'].items():
                    if pd.notna(state):
                        clean_state = state.lower().strip()
                        geo_state_names[clean_state] = idx
            
            anomaly_state_names = set(state_anomalies['state'].str.lower().str.strip())
            
            print(f"DEBUG: Geo states: {sorted(list(geo_state_names.keys()))}")
            print(f"DEBUG: Anomaly states: {sorted(list(anomaly_state_names))}")
            
            # Find exact matches and mismatches
            exact_matches = anomaly_state_names.intersection(set(geo_state_names.keys()))
            missing_in_geo = anomaly_state_names - set(geo_state_names.keys())
            
            print(f"DEBUG: Exact matches: {len(exact_matches)}")
            print(f"DEBUG: Missing in geo: {len(missing_in_geo)} - {sorted(list(missing_in_geo))}")
            
            matched_count = 0
            for idx, row in state_anomalies.iterrows():
                state_name = row['state'].strip()
                state_lower = state_name.lower()
                
                # Try exact match first
                geo_idx = geo_state_names.get(state_lower)
                
                # If no exact match, try partial match
                if geo_idx is None:
                    for geo_state, g_idx in geo_state_names.items():
                        if (state_lower in geo_state and len(state_lower) > 3) or \
                           (geo_state in state_lower and len(geo_state) > 3):
                            geo_idx = g_idx
                            print(f"DEBUG: Partial match: '{state_name}' -> '{geo_state}'")
                            break
                
                if geo_idx is not None:
                    merged_geo.at[geo_idx, 'anomaly_flag'] = row['anomaly_flag']
                    merged_geo.at[geo_idx, 'anomaly_score'] = row['anomaly_score']
                    # Handle different update ratio column names
                    if update_ratio_col in row:
                        merged_geo.at[geo_idx, 'update_ratio'] = row[update_ratio_col]
                    matched_count += 1
                else:
                    print(f"DEBUG: No match found for state: '{state_name}'")
            
            print(f"DEBUG: Matched {matched_count}/{len(state_anomalies)} states")
            
            # Count final anomaly flags
            final_counts = merged_geo['anomaly_flag'].value_counts()
            print(f"DEBUG: Final anomaly distribution: {final_counts.to_dict()}")
            
            print(f"DEBUG: Creating choropleth map")
            
            # Create the anomaly choropleth map
            fig = create_anomaly_choropleth_map(
                merged_geo, 
                'anomaly_flag', 
                'Anomaly Status Map - State Level (Red=Critical, Yellow=Warning, Grey=Normal)'
            )
            
            if fig:
                print(f"DEBUG: Map created successfully")
                return fig.to_json()
            else:
                print(f"DEBUG: Map creation failed")
                return jsonify({'error': 'Failed to create anomaly map'}), 500
        else:
            print(f"DEBUG: No geographic data available")
            return jsonify({'error': 'Geographic data not available for anomaly map'}), 500
        
    except Exception as e:
        print(f"Error in anomaly map API: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to process anomaly map: {str(e)}'}), 500

@app.route('/api/debug/anomaly-data')
def api_debug_anomaly_data():
    """Debug endpoint to check anomaly data quality"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        
        # Get anomaly data (reuse logic from /api/anomalies)
        if data['anomalies'] is None:
            # Create basic anomaly detection if not available
            district_metrics = data['district_metrics']
            
            # Simple anomaly detection based on thresholds
            anomalies_df = district_metrics.copy()
            
            # Calculate state-level statistics for comparison
            state_stats = district_metrics.groupby('state')['update_ratio'].agg(['mean', 'std']).reset_index()
            state_stats.columns = ['state', 'state_mean', 'state_std']
            
            # Merge with district data
            anomalies_df = anomalies_df.merge(state_stats, on='state', how='left')
            
            # Classify anomalies
            def classify_anomaly(row):
                if pd.isna(row['update_ratio']) or pd.isna(row['state_mean']) or pd.isna(row['state_std']):
                    return 'normal'
                
                # Rule 1: Extremely high update ratio (> 10x state average)
                if row['update_ratio'] > 10 * row['state_mean']:
                    return 'critical'
                
                # Rule 2: Very low compliance (< 0.1)
                if 'biometric_compliance' in row and row['biometric_compliance'] < 0.1:
                    return 'warning'
                
                # Rule 3: Statistical outlier (> 3 std from state mean)
                if row['state_std'] > 0:
                    z_score = abs(row['update_ratio'] - row['state_mean']) / row['state_std']
                    if z_score > 3:
                        return 'critical'
                    elif z_score > 2:
                        return 'warning'
                
                # Rule 4: Zero activity in populated district
                if row['total_holders'] > 1000 and row['total_updates'] == 0:
                    return 'critical'
                
                return 'normal'
            
            anomalies_df['anomaly_flag'] = anomalies_df.apply(classify_anomaly, axis=1)
        else:
            anomalies_df = data['anomalies']['anomalies_df']
        
        # Aggregate to state level
        # Use the correct column name based on what's available
        update_ratio_col = 'update_ratio_mean' if 'update_ratio_mean' in anomalies_df.columns else 'update_ratio'
        
        state_anomalies = anomalies_df.groupby('state').agg({
            update_ratio_col: 'mean'
        }).reset_index()
        
        # Rename for consistency
        state_anomalies = state_anomalies.rename(columns={update_ratio_col: 'update_ratio'})
        
        # Add anomaly_score if it exists, otherwise create it
        if 'anomaly_score' in anomalies_df.columns:
            state_anomalies['anomaly_score'] = anomalies_df.groupby('state')['anomaly_score'].mean().values
        else:
            # Create a simple anomaly score based on update_ratio
            max_ratio = state_anomalies['update_ratio'].max()
            if max_ratio > 0:
                state_anomalies['anomaly_score'] = state_anomalies['update_ratio'] / max_ratio
            else:
                state_anomalies['anomaly_score'] = 0.0
        
        # Determine state-level anomaly flag
        state_flags = anomalies_df.groupby('state')['anomaly_flag'].apply(
            lambda x: 'critical' if 'critical' in x.values 
            else 'warning' if 'warning' in x.values 
            else 'normal'
        ).reset_index()
        
        state_anomalies = state_anomalies.merge(state_flags, on='state')
        
        # Check geo data
        state_geo = data['state_geo']
        
        debug_info = {
            'anomaly_states': sorted(state_anomalies['state'].unique().tolist()),
            'geo_states': sorted(state_geo['state'].unique().tolist()) if 'state' in state_geo.columns else [],
            'geo_st_nm': sorted(state_geo['st_nm'].unique().tolist()) if 'st_nm' in state_geo.columns else [],
            'anomaly_flags': state_anomalies['anomaly_flag'].value_counts().to_dict(),
            'total_anomaly_states': len(state_anomalies),
            'total_geo_states': len(state_geo),
            'sample_anomaly_data': state_anomalies.head(10).to_dict('records'),
            'sample_geo_data': state_geo[['state', 'st_nm']].head(10).to_dict('records') if 'st_nm' in state_geo.columns else state_geo[['state']].head(10).to_dict('records')
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': f'Debug failed: {str(e)}'}), 500

@app.route('/api/comparison')
def api_comparison():
    """API endpoint for district comparison"""
    state_a = request.args.get('state_a')
    district_a = request.args.get('district_a')
    state_b = request.args.get('state_b')
    district_b = request.args.get('district_b')
    
    if not all([state_a, district_a, state_b, district_b]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    if 'processed_data' not in app_data:
        return jsonify({'error': 'Data not loaded'}), 500
    
    data = app_data['processed_data']
    district_metrics = data['district_metrics']
    
    try:
        # Get data for both districts
        metric_a = district_metrics[
            (district_metrics['state'] == state_a) & 
            (district_metrics['district'] == district_a)
        ].iloc[0]
        
        metric_b = district_metrics[
            (district_metrics['state'] == state_b) & 
            (district_metrics['district'] == district_b)
        ].iloc[0]
        
        comparison = {
            'district_a': {
                'name': f"{district_a}, {state_a}",
                'population': int(metric_a['total_holders']),
                'activity_score': float(metric_a['update_ratio']),
                'quality_score': float(metric_a['biometric_compliance']),
                'growth_rate': float(metric_a['enrolment_growth_rate'] * 100)
            },
            'district_b': {
                'name': f"{district_b}, {state_b}",
                'population': int(metric_b['total_holders']),
                'activity_score': float(metric_b['update_ratio']),
                'quality_score': float(metric_b['biometric_compliance']),
                'growth_rate': float(metric_b['enrolment_growth_rate'] * 100)
            }
        }
        
        return jsonify(comparison)
        
    except IndexError:
        return jsonify({'error': 'District not found'}), 404

@app.route('/api/states')
def api_states():
    """API endpoint to get list of states"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        states = sorted(data['district_metrics']['state'].unique().tolist())
        return jsonify({'states': states})
    except Exception as e:
        return jsonify({'error': f'Failed to get states: {str(e)}'}), 500

@app.route('/api/districts/<state>')
def api_districts(state):
    """API endpoint to get districts for a state"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        districts = sorted(
            data['district_metrics'][data['district_metrics']['state'] == state]['district'].unique().tolist()
        )
        return jsonify({'districts': districts})
    except Exception as e:
        return jsonify({'error': f'Failed to get districts: {str(e)}'}), 500

@app.route('/api/time-series')
def api_time_series():
    """API endpoint for time series data"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        full_data = data['full_data']
        
        # Get available months
        available_months = sorted(full_data['year_month'].unique().tolist())
        
        # National trend over time
        national_trend = full_data.groupby('year_month').agg({
            'total_holders': 'sum',
            'total_updates': 'sum'
        }).reset_index()
        
        # Calculate update ratio for each month
        national_trend['update_ratio'] = np.where(
            national_trend['total_holders'] > 0,
            national_trend['total_updates'] / national_trend['total_holders'],
            0
        )
        
        return jsonify({
            'available_months': available_months,
            'national_trend': national_trend.to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get time series data: {str(e)}'}), 500

@app.route('/api/monthly-data/<month>')
def api_monthly_data(month):
    """API endpoint for specific month data"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        full_data = data['full_data']
        
        # Filter data by month
        monthly_data = full_data[full_data['year_month'] == month]
        
        if monthly_data.empty:
            return jsonify({'error': f'No data available for month {month}'}), 404
        
        # Aggregate by district
        monthly_district = monthly_data.groupby(['state', 'district'], as_index=False).agg({
            'update_ratio': 'mean',
            'total_holders': 'sum',
            'total_updates': 'sum'
        })
        
        # Get top districts
        top_districts = monthly_district.nlargest(15, 'update_ratio')[
            ['state', 'district', 'update_ratio', 'total_holders']
        ].to_dict('records')
        
        # Get statistics
        stats = {
            'total_districts': len(monthly_district),
            'min_ratio': float(monthly_district['update_ratio'].min()),
            'max_ratio': float(monthly_district['update_ratio'].max()),
            'mean_ratio': float(monthly_district['update_ratio'].mean()),
            'non_zero_districts': int((monthly_district['update_ratio'] > 0).sum())
        }
        
        return jsonify({
            'month': month,
            'top_districts': top_districts,
            'statistics': stats,
            'district_data': monthly_district.to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': f'Failed to get monthly data: {str(e)}'}), 500

@app.route('/api/about')
def api_about():
    """API endpoint for about information"""
    return jsonify({
        'title': 'Aadhaar Analytics Dashboard - Flask Version',
        'description': 'Professional web-based analytics dashboard for Aadhaar data analysis',
        'version': '2.0.0',
        'developers': [
            {
                'name': 'Vraj Maheshwari',
                'role': 'Lead Developer & Data Analytics Specialist',
                'email': 'vrajmaheshwari06@gmail.com',
                'portfolio': 'https://vraj-maheshwari.github.io/portfolio/'
            },
            {
                'name': 'Vani Parmar',
                'role': 'Full Stack Developer & UI/UX Designer',
                'email': 'vaaniparmar58@gmail.com'
            }
        ],
        'institution': {
            'name': 'College of Agricultural Information Technology',
            'university': 'Anand Agricultural University (AAU)',
            'location': 'Anand, Gujarat, India'
        },
        'features': [
            'National Overview with KPI cards and state maps',
            'Update Intensity analysis with time filtering',
            'District Comparison tool',
            'Lifecycle Compliance tracking',
            'Migration Pattern analysis',
            'Anomaly Detection and alerts',
            'Interactive visualizations',
            'Professional responsive design'
        ]
    })

@app.route('/api/debug')
def api_debug():
    """API endpoint for debugging data issues"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        debug_info = {}
        
        # Check district metrics
        if data['district_metrics'] is not None:
            dm = data['district_metrics']
            debug_info['district_metrics'] = {
                'shape': dm.shape,
                'columns': list(dm.columns),
                'update_ratio_stats': {
                    'min': float(dm['update_ratio'].min()),
                    'max': float(dm['update_ratio'].max()),
                    'mean': float(dm['update_ratio'].mean()),
                    'null_count': int(dm['update_ratio'].isnull().sum())
                } if 'update_ratio' in dm.columns else 'Column not found'
            }
        
        # Check state geo data
        if data['state_geo'] is not None:
            sg = data['state_geo']
            debug_info['state_geo'] = {
                'shape': sg.shape,
                'columns': list(sg.columns),
                'has_geometry': hasattr(sg, 'geometry'),
                'sample_states': list(sg['state'].head(5)) if 'state' in sg.columns else 'No state column'
            }
        
        # Check anomalies
        debug_info['anomalies'] = {
            'available': data['anomalies'] is not None,
            'type': type(data['anomalies']).__name__ if data['anomalies'] is not None else 'None'
        }
        
        # Check full data
        if data['full_data'] is not None:
            fd = data['full_data']
            debug_info['full_data'] = {
                'shape': fd.shape,
                'columns': list(fd.columns),
                'unique_months': len(fd['year_month'].unique()) if 'year_month' in fd.columns else 'No year_month column'
            }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': f'Debug failed: {str(e)}'}), 500

@app.route('/api/debug/states')
def api_debug_states():
    """Debug endpoint to check state data"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'Data not loaded or processing failed'}), 500
    
    try:
        data = app_data['processed_data']
        state_metrics = data['state_metrics']
        
        # Aggregate state data
        state_data = state_metrics.groupby('state').agg({
            'update_ratio': 'mean',
            'total_holders': 'sum',
            'total_updates': 'sum'
        }).reset_index()
        
        # Get sample data
        sample_data = state_data.head(10).to_dict('records')
        
        debug_info = {
            'total_states': len(state_data),
            'columns': list(state_data.columns),
            'update_ratio_stats': {
                'min': float(state_data['update_ratio'].min()),
                'max': float(state_data['update_ratio'].max()),
                'mean': float(state_data['update_ratio'].mean()),
                'unique_values': int(state_data['update_ratio'].nunique())
            },
            'sample_data': sample_data
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        return jsonify({'error': f'Debug states failed: {str(e)}'}), 500

@app.route('/api/export/<export_type>')
def api_export_data(export_type):
    """Export dashboard data in various formats"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'No data available for export'}), 500
    
    try:
        data = app_data['processed_data']
        
        if export_type == 'overview':
            # Export overview/summary data
            export_data = {
                'export_info': {
                    'type': 'Aadhaar Analytics Overview',
                    'generated_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_records': len(data['full_data']) if data['full_data'] is not None else 0
                },
                'kpis': {
                    'total_holders': int(data['district_metrics']['total_holders'].sum()),
                    'total_updates': int(data['district_metrics']['total_updates'].sum()),
                    'avg_update_ratio': float(data['district_metrics']['update_ratio'].mean()),
                    'total_districts': len(data['district_metrics']),
                    'total_states': len(data['district_metrics']['state'].unique())
                },
                'top_states': data['state_metrics'].groupby('state')['update_ratio'].mean().sort_values(ascending=False).head(10).to_dict(),
                'anomaly_summary': data['anomalies']['anomalies_df'].groupby('anomaly_flag').size().to_dict() if data['anomalies'] else {}
            }
            
        elif export_type == 'district_metrics':
            # Export detailed district-level metrics
            df = data['district_metrics'].copy()
            # Round numeric columns for cleaner export
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].round(3)
            export_data = df.to_dict('records')
            
        elif export_type == 'state_metrics':
            # Export state-level aggregated metrics
            df = data['state_metrics'].copy()
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].round(3)
            export_data = df.to_dict('records')
            
        elif export_type == 'anomalies':
            # Export anomaly detection results
            if data['anomalies'] and data['anomalies']['anomalies_df'] is not None:
                df = data['anomalies']['anomalies_df'].copy()
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                df[numeric_cols] = df[numeric_cols].round(3)
                export_data = df.to_dict('records')
            else:
                export_data = {'message': 'No anomaly data available'}
                
        elif export_type == 'full_dataset':
            # Export complete processed dataset (limited to prevent huge downloads)
            if data['full_data'] is not None:
                df = data['full_data'].head(10000).copy()  # Limit to 10k records
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                df[numeric_cols] = df[numeric_cols].round(3)
                export_data = {
                    'note': 'Limited to first 10,000 records for performance',
                    'total_available': len(data['full_data']),
                    'data': df.to_dict('records')
                }
            else:
                export_data = {'message': 'No full dataset available'}
        else:
            return jsonify({'error': 'Invalid export type'}), 400
        
        # Return JSON data
        response = jsonify(export_data)
        response.headers['Content-Disposition'] = f'attachment; filename=aadhaar_analytics_{export_type}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.json'
        return response
        
    except Exception as e:
        return jsonify({'error': f'Export failed: {str(e)}'}), 500

@app.route('/api/export/csv/<export_type>')
def api_export_csv(export_type):
    """Export dashboard data as CSV files"""
    if 'processed_data' not in app_data or app_data['processed_data'] is None:
        return jsonify({'error': 'No data available for export'}), 500
    
    try:
        from flask import make_response
        import io
        
        data = app_data['processed_data']
        
        if export_type == 'district_metrics':
            df = data['district_metrics'].copy()
        elif export_type == 'state_metrics':
            df = data['state_metrics'].copy()
        elif export_type == 'anomalies':
            if data['anomalies'] and data['anomalies']['anomalies_df'] is not None:
                df = data['anomalies']['anomalies_df'].copy()
            else:
                return jsonify({'error': 'No anomaly data available'}), 400
        elif export_type == 'full_dataset':
            if data['full_data'] is not None:
                df = data['full_data'].head(10000).copy()  # Limit for performance
            else:
                return jsonify({'error': 'No full dataset available'}), 400
        else:
            return jsonify({'error': 'Invalid export type for CSV'}), 400
        
        # Round numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        df[numeric_cols] = df[numeric_cols].round(3)
        
        # Create CSV
        output = io.StringIO()
        df.to_csv(output, index=False)
        csv_data = output.getvalue()
        
        # Create response
        response = make_response(csv_data)
        response.headers['Content-Type'] = 'text/csv'
        response.headers['Content-Disposition'] = f'attachment; filename=aadhaar_analytics_{export_type}_{pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'CSV export failed: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Starting Aadhaar Analytics Dashboard")
    print("=" * 50)
    
    # Check if data files exist
    from pathlib import Path
    project_root = Path(__file__).parent
    data_path = project_root / 'api_data_aadhar_biometric' / 'api_data_aadhar_biometric'
    if not data_path.exists():
        print("⚠️  Warning: Data files not found in project directory")
        print("   Make sure the CSV data folders are present in the project root")
    
    # Initialize data
    print("📊 Initializing data processing...")
    try:
        initialize_data()
        print("✅ Data initialization completed successfully!")
    except Exception as e:
        print(f"❌ Data initialization failed: {e}")
        print("   The dashboard will still start but may not have data")
    
    # Get port from environment variable (Render sets this automatically)
    import os
    port = int(os.environ.get('PORT', 5000))
    
    print(f"\n🌐 Dashboard will be available at:")
    print(f"   Local:    http://localhost:{port}")
    print(f"   Network:  http://0.0.0.0:{port}")
    print("\n💡 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Run the Flask app
    # Note: Gunicorn will ignore this when deployed, but it works for local development
    app.run(
        debug=False,  # Set to False for production
        host='0.0.0.0',
        port=port,
        threaded=True
    )