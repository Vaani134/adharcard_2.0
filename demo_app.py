"""
Demo Flask-based Aadhaar Analytics Dashboard
Runs with sample data for demonstration purposes
"""

from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly
import json

app = Flask(__name__)
app.secret_key = 'aadhaar_analytics_dashboard_demo_2025'

# Sample data for demo
def generate_sample_data():
    """Generate sample data for demonstration"""
    states = ['Maharashtra', 'Uttar Pradesh', 'Karnataka', 'Gujarat', 'Tamil Nadu', 
              'West Bengal', 'Rajasthan', 'Andhra Pradesh', 'Madhya Pradesh', 'Odisha']
    
    districts_per_state = 5
    sample_data = []
    
    for state in states:
        for i in range(districts_per_state):
            district = f"{state} District {i+1}"
            sample_data.append({
                'state': state,
                'district': district,
                'total_holders': np.random.randint(100000, 1000000),
                'total_updates': np.random.randint(10000, 500000),
                'update_ratio': np.random.uniform(0.1, 3.0),
                'biometric_compliance': np.random.uniform(0.2, 0.9),
                'demo_update_ratio': np.random.uniform(0.05, 1.5),
                'bio_update_ratio': np.random.uniform(0.05, 1.5),
                'enrolment_growth_rate': np.random.uniform(-0.1, 0.2)
            })
    
    return pd.DataFrame(sample_data)

# Initialize sample data
sample_df = generate_sample_data()

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/overview')
def api_overview():
    """API endpoint for national overview data"""
    try:
        # Calculate KPIs from sample data
        total_holders = int(sample_df['total_holders'].sum())
        total_updates = int(sample_df['total_updates'].sum())
        avg_update_ratio = float(sample_df['update_ratio'].mean())
        total_districts = len(sample_df)
        
        # Top states by activity
        top_states = sample_df.groupby('state')['update_ratio'].mean().sort_values(ascending=False).head(10)
        
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
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to process overview data: {str(e)}'}), 500

@app.route('/api/map/states')
def api_state_map():
    """API endpoint for state-level map data"""
    try:
        # Create a simple bar chart instead of map for demo
        state_metrics = sample_df.groupby('state')['update_ratio'].mean().reset_index()
        
        fig = px.bar(
            state_metrics,
            x='state',
            y='update_ratio',
            title='Update Ratio by State',
            color='update_ratio',
            color_continuous_scale='RdYlBu_r'
        )
        
        fig.update_layout(
            height=400,
            margin={"r": 0, "t": 30, "l": 0, "b": 0},
            xaxis_tickangle=-45
        )
        
        return fig.to_json()
    except Exception as e:
        return jsonify({'error': f'Failed to create map: {str(e)}'}), 500

@app.route('/api/compliance')
def api_compliance():
    """API endpoint for compliance data"""
    try:
        # Top compliant districts
        top_compliant = sample_df.nlargest(15, 'biometric_compliance')[
            ['state', 'district', 'biometric_compliance', 'update_ratio']
        ].to_dict('records')
        
        # Compliance distribution
        compliance_bins = pd.cut(
            sample_df['biometric_compliance'],
            bins=[0, 0.25, 0.5, 0.75, 1.0],
            labels=['0-25%', '25-50%', '50-75%', '75-100%']
        )
        compliance_counts = compliance_bins.value_counts().sort_index()
        
        return jsonify({
            'top_compliant': top_compliant,
            'distribution': {
                'labels': compliance_counts.index.tolist(),
                'values': compliance_counts.values.tolist()
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to process compliance data: {str(e)}'}), 500

@app.route('/api/migration')
def api_migration():
    """API endpoint for migration patterns"""
    try:
        # Calculate migration patterns
        demo_median = sample_df['demo_update_ratio'].median()
        bio_median = sample_df['bio_update_ratio'].median()
        
        def classify_pattern(row):
            if row['demo_update_ratio'] > demo_median and row['bio_update_ratio'] < bio_median:
                return 'Migration Heavy'
            elif row['bio_update_ratio'] > bio_median:
                return 'Balanced / Quality'
            else:
                return 'Low Activity'
        
        sample_df['pattern_label'] = sample_df.apply(classify_pattern, axis=1)
        
        # Migration hotspots
        migration_heavy = sample_df[sample_df['pattern_label'] == 'Migration Heavy']
        top_migration = migration_heavy.nlargest(10, 'demo_update_ratio')[
            ['state', 'district', 'demo_update_ratio', 'bio_update_ratio', 'total_holders']
        ].to_dict('records')
        
        return jsonify({
            'migration_hotspots': top_migration,
            'total_migration_districts': len(migration_heavy)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to process migration data: {str(e)}'}), 500

@app.route('/api/anomalies')
def api_anomalies():
    """API endpoint for anomaly data"""
    try:
        # Simple anomaly detection based on thresholds
        anomalies_df = sample_df.copy()
        
        # Classify anomalies
        def classify_anomaly(row):
            if row['update_ratio'] > 2.5:
                return 'critical'
            elif row['biometric_compliance'] < 0.3:
                return 'warning'
            else:
                return 'normal'
        
        anomalies_df['anomaly_flag'] = anomalies_df.apply(classify_anomaly, axis=1)
        anomalies_df['anomaly_score'] = np.random.uniform(0, 1, len(anomalies_df))
        
        # Summary stats
        summary = {
            'total_districts': len(anomalies_df),
            'normal': len(anomalies_df[anomalies_df['anomaly_flag'] == 'normal']),
            'warning': len(anomalies_df[anomalies_df['anomaly_flag'] == 'warning']),
            'critical': len(anomalies_df[anomalies_df['anomaly_flag'] == 'critical'])
        }
        
        # Critical anomalies
        critical_anomalies = anomalies_df[
            anomalies_df['anomaly_flag'] == 'critical'
        ][['state', 'district', 'update_ratio', 'anomaly_score']].head(20)
        critical_anomalies.columns = ['state', 'district', 'update_ratio_mean', 'anomaly_score']
        
        return jsonify({
            'summary': summary,
            'critical_anomalies': critical_anomalies.to_dict('records')
        })
    except Exception as e:
        return jsonify({'error': f'Failed to process anomalies: {str(e)}'}), 500

@app.route('/api/comparison')
def api_comparison():
    """API endpoint for district comparison"""
    state_a = request.args.get('state_a')
    district_a = request.args.get('district_a')
    state_b = request.args.get('state_b')
    district_b = request.args.get('district_b')
    
    if not all([state_a, district_a, state_b, district_b]):
        return jsonify({'error': 'Missing parameters'}), 400
    
    try:
        # Get data for both districts
        metric_a = sample_df[
            (sample_df['state'] == state_a) & 
            (sample_df['district'] == district_a)
        ]
        
        metric_b = sample_df[
            (sample_df['state'] == state_b) & 
            (sample_df['district'] == district_b)
        ]
        
        if metric_a.empty or metric_b.empty:
            return jsonify({'error': 'District not found'}), 404
        
        metric_a = metric_a.iloc[0]
        metric_b = metric_b.iloc[0]
        
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
        
    except Exception as e:
        return jsonify({'error': f'Comparison failed: {str(e)}'}), 500

@app.route('/api/states')
def api_states():
    """API endpoint to get list of states"""
    try:
        states = sorted(sample_df['state'].unique().tolist())
        return jsonify({'states': states})
    except Exception as e:
        return jsonify({'error': f'Failed to get states: {str(e)}'}), 500

@app.route('/api/districts/<state>')
def api_districts(state):
    """API endpoint to get districts for a state"""
    try:
        districts = sorted(
            sample_df[sample_df['state'] == state]['district'].unique().tolist()
        )
        return jsonify({'districts': districts})
    except Exception as e:
        return jsonify({'error': f'Failed to get districts: {str(e)}'}), 500

if __name__ == '__main__':
    print("🚀 Starting Aadhaar Analytics Dashboard (Demo Mode)")
    print("=" * 60)
    print("📊 Using sample data for demonstration")
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