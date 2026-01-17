"""
Clustering Module
Applies K-Means clustering to discover hidden patterns
"""

import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Dict


class DataClustering:
    """Performs clustering analysis on Aadhaar metrics"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.scaler = StandardScaler()
        self.kmeans = None
        self.cluster_labels = None
    
    def prepare_features(self) -> pd.DataFrame:
        """Prepare features for clustering"""
        district_metrics = self.df.groupby(['state', 'district'], as_index=False).agg({
            'update_ratio': 'mean',
            'biometric_compliance': 'mean',
            'enrolment_growth_rate': 'mean',
            'total_holders': 'sum',
            'demo_update_ratio': 'mean',
            'bio_update_ratio': 'mean'
        })
        
        # Handle infinite and NaN values
        district_metrics.replace([np.inf, -np.inf], np.nan, inplace=True)
        district_metrics.fillna(0, inplace=True)
        
        return district_metrics
    
    def apply_kmeans_clustering(self, n_clusters: int = 4) -> pd.DataFrame:
        """Apply K-Means clustering"""
        district_metrics = self.prepare_features()
        
        # Select features for clustering
        feature_cols = ['update_ratio', 'biometric_compliance', 'enrolment_growth_rate']
        X = district_metrics[feature_cols].values
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Apply K-Means
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.cluster_labels = self.kmeans.fit_predict(X_scaled)
        
        # Add cluster labels to dataframe
        district_metrics['cluster'] = self.cluster_labels
        
        return district_metrics
    
    def get_cluster_characteristics(self, clustered_df: pd.DataFrame) -> Dict:
        """Get characteristics of each cluster"""
        characteristics = {}
        
        for cluster_id in sorted(clustered_df['cluster'].unique()):
            cluster_data = clustered_df[clustered_df['cluster'] == cluster_id]
            
            characteristics[cluster_id] = {
                'size': len(cluster_data),
                'avg_update_ratio': cluster_data['update_ratio'].mean(),
                'avg_compliance': cluster_data['biometric_compliance'].mean(),
                'avg_growth_rate': cluster_data['enrolment_growth_rate'].mean(),
                'total_population': cluster_data['total_holders'].sum(),
                'states': cluster_data['state'].nunique(),
                'top_states': cluster_data['state'].value_counts().head(3).to_dict()
            }
        
        return characteristics
    
    def classify_clusters(self, characteristics: Dict) -> Dict:
        """Classify clusters with meaningful labels"""
        cluster_labels = {}
        
        # Sort clusters by update_ratio for consistent labeling
        sorted_clusters = sorted(characteristics.keys(), 
                               key=lambda x: characteristics[x]['avg_update_ratio'])
        
        for i, cluster_id in enumerate(sorted_clusters):
            char = characteristics[cluster_id]
            
            if char['avg_update_ratio'] > 2.0:
                if char['avg_compliance'] > 0.8:
                    label = 'High Activity & Quality'
                else:
                    label = 'High Activity'
            elif char['avg_update_ratio'] > 1.0:
                if char['avg_compliance'] > 0.6:
                    label = 'Moderate Activity & Quality'
                else:
                    label = 'Moderate Activity'
            elif char['avg_compliance'] > 0.6:
                label = 'Quality Focused'
            else:
                label = 'Low Engagement'
            
            cluster_labels[cluster_id] = label
        
        return cluster_labels
    
    def get_cluster_summary(self) -> Dict:
        """Get comprehensive cluster summary"""
        try:
            clustered_df = self.apply_kmeans_clustering()
            characteristics = self.get_cluster_characteristics(clustered_df)
            cluster_labels = self.classify_clusters(characteristics)
            
            # Combine characteristics with labels
            summary = {}
            for cluster_id in characteristics.keys():
                summary[cluster_id] = {
                    **characteristics[cluster_id],
                    'label': cluster_labels[cluster_id]
                }
            
            return {
                'clusters': summary,
                'total_districts': len(clustered_df),
                'clustered_df': clustered_df
            }
        except Exception as e:
            # Return empty summary if clustering fails
            return {
                'clusters': {},
                'total_districts': 0,
                'clustered_df': pd.DataFrame(),
                'error': str(e)
            }
    
    def get_cluster_recommendations(self, cluster_summary: Dict) -> Dict:
        """Get recommendations for each cluster"""
        recommendations = {}
        
        for cluster_id, cluster_info in cluster_summary.get('clusters', {}).items():
            label = cluster_info['label']
            
            if 'High Activity' in label:
                recommendations[cluster_id] = [
                    "Monitor for data quality issues due to high activity",
                    "Consider these districts as best practice examples",
                    "Investigate factors driving high engagement"
                ]
            elif 'Low Engagement' in label:
                recommendations[cluster_id] = [
                    "Implement awareness campaigns",
                    "Improve service accessibility",
                    "Investigate barriers to Aadhaar updates"
                ]
            elif 'Quality Focused' in label:
                recommendations[cluster_id] = [
                    "Maintain current quality standards",
                    "Share best practices with other districts",
                    "Monitor for any decline in engagement"
                ]
            else:
                recommendations[cluster_id] = [
                    "Balanced approach - maintain current levels",
                    "Monitor trends for any significant changes",
                    "Consider targeted improvements where needed"
                ]
        
        return recommendations