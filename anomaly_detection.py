"""
Anomaly Detection Module
Identifies anomalies using rule-based detection
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict


class AnomalyDetector:
    """Detects anomalies in Aadhaar data"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
    
    def detect_anomalies_rule_based(self, threshold_std: float = 3.0) -> pd.DataFrame:
        """Rule-based anomaly detection using statistical thresholds"""
        district_metrics = self.df.groupby(['state', 'district'], as_index=False).agg({
            'update_ratio': ['mean', 'std', 'max'],
            'total_holders': 'sum',
            'total_updates': 'sum',
            'biometric_compliance': 'mean'
        })
        
        # Flatten column names (handle MultiIndex from aggregation)
        if isinstance(district_metrics.columns, pd.MultiIndex):
            # Keep state and district as-is, flatten only aggregated columns
            new_columns = []
            for col in district_metrics.columns:
                if isinstance(col, tuple):
                    # Join tuple elements, filter out empty strings
                    new_col = '_'.join(str(c) for c in col if c)
                    new_columns.append(new_col)
                else:
                    new_columns.append(col)
            district_metrics.columns = new_columns
        
        # Calculate state-level statistics for comparison
        state_stats = self.df.groupby('state', as_index=False).agg({
            'update_ratio': ['mean', 'std']
        })
        state_stats.columns = ['state', 'state_update_ratio_mean', 'state_update_ratio_std']
        
        # Merge state stats
        district_metrics = district_metrics.merge(state_stats, on='state', how='left')
        
        # Detect anomalies
        def classify_anomaly(row):
            # Rule 1: Extremely high update ratio (> 10x state average)
            if row['update_ratio_mean'] > 10 * row['state_update_ratio_mean']:
                return 'critical'
            
            # Rule 2: Very low compliance (< 0.1)
            if row['biometric_compliance'] < 0.1:
                return 'warning'
            
            # Rule 3: Statistical outlier (> 3 std from state mean)
            if abs(row['update_ratio_mean'] - row['state_update_ratio_mean']) > threshold_std * row['state_update_ratio_std']:
                return 'warning'
            
            # Rule 4: Zero activity in populated district
            if row['total_holders'] > 1000 and row['total_updates'] == 0:
                return 'critical'
            
            return 'normal'
        
        district_metrics['anomaly_flag'] = district_metrics.apply(classify_anomaly, axis=1)
        
        # Calculate anomaly score (0-1, higher = more anomalous)
        district_metrics['anomaly_score'] = 0.0
        
        # Score based on deviation from state mean
        state_deviation = abs(district_metrics['update_ratio_mean'] - district_metrics['state_update_ratio_mean'])
        max_deviation = state_deviation.max()
        if max_deviation > 0:
            district_metrics['anomaly_score'] += 0.4 * (state_deviation / max_deviation)
        
        # Score based on compliance
        district_metrics['anomaly_score'] += 0.3 * (1 - district_metrics['biometric_compliance'].clip(0, 1))
        
        # Score based on ratio extremes
        ratio_extreme = np.where(
            district_metrics['update_ratio_mean'] > 5,
            district_metrics['update_ratio_mean'] / 10,
            0
        )
        district_metrics['anomaly_score'] += 0.3 * np.clip(ratio_extreme, 0, 1)
        
        # Clip final score to [0, 1]
        district_metrics['anomaly_score'] = np.clip(district_metrics['anomaly_score'], 0, 1)
        
        return district_metrics
    
    def get_anomaly_summary(self) -> Dict:
        """Get summary of anomalies"""
        anomalies_df = self.detect_anomalies_rule_based()
        
        summary = {
            'total_districts': len(anomalies_df),
            'normal': len(anomalies_df[anomalies_df['anomaly_flag'] == 'normal']),
            'warning': len(anomalies_df[anomalies_df['anomaly_flag'] == 'warning']),
            'critical': len(anomalies_df[anomalies_df['anomaly_flag'] == 'critical']),
            'anomalies_df': anomalies_df
        }
        
        return summary
    
    def get_top_anomalies(self, n: int = 20) -> pd.DataFrame:
        """Get top N anomalies by score"""
        anomalies_df = self.detect_anomalies_rule_based()
        return anomalies_df.nlargest(n, 'anomaly_score')