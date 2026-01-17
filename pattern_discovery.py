"""
Pattern Discovery Module
Identifies temporal, spatial, and behavioral patterns
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple


class PatternDiscovery:
    """Discovers patterns in Aadhaar data"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
    
    def detect_temporal_patterns(self) -> pd.DataFrame:
        """Detect temporal trends (rising, stable, seasonal)"""
        df_sorted = self.df.sort_values(['district', 'year_month'])
        
        # Calculate trend over time for each district
        patterns = []
        
        for district, group in df_sorted.groupby(['state', 'district']):
            state, dist = district
            
            if len(group) < 2:
                patterns.append({
                    'state': state,
                    'district': dist,
                    'temporal_pattern': 'insufficient_data',
                    'trend': 'stable',
                    'volatility': 0
                })
                continue
            
            # Calculate trend (slope of update_ratio over time)
            group = group.sort_values('year_month')
            update_ratios = group['update_ratio'].values
            
            # Simple linear trend
            x = np.arange(len(update_ratios))
            if len(update_ratios) > 1 and np.var(update_ratios) > 0:
                trend_slope = np.polyfit(x, update_ratios, 1)[0]
                volatility = np.std(update_ratios)
            else:
                trend_slope = 0
                volatility = 0
            
            # Classify trend
            if trend_slope > 0.1:
                trend = 'rising'
            elif trend_slope < -0.1:
                trend = 'declining'
            else:
                trend = 'stable'
            
            # Classify pattern based on volatility
            if volatility > 2.0:
                pattern = 'highly_volatile'
            elif volatility > 1.0:
                pattern = 'moderate_volatility'
            else:
                pattern = 'stable'
            
            patterns.append({
                'state': state,
                'district': dist,
                'temporal_pattern': pattern,
                'trend': trend,
                'volatility': volatility,
                'trend_slope': trend_slope
            })
        
        return pd.DataFrame(patterns)
    
    def detect_spatial_patterns(self) -> pd.DataFrame:
        """Detect spatial clustering patterns"""
        # Group by state to find spatial patterns
        state_patterns = []
        
        for state, group in self.df.groupby('state'):
            district_metrics = group.groupby('district').agg({
                'update_ratio': 'mean',
                'total_holders': 'sum',
                'biometric_compliance': 'mean'
            }).reset_index()
            
            if len(district_metrics) < 2:
                continue
            
            # Calculate coefficient of variation for the state
            cv_update = district_metrics['update_ratio'].std() / district_metrics['update_ratio'].mean() if district_metrics['update_ratio'].mean() > 0 else 0
            cv_compliance = district_metrics['biometric_compliance'].std() / district_metrics['biometric_compliance'].mean() if district_metrics['biometric_compliance'].mean() > 0 else 0
            
            # Classify spatial pattern
            if cv_update > 1.0:
                spatial_pattern = 'highly_heterogeneous'
            elif cv_update > 0.5:
                spatial_pattern = 'moderately_heterogeneous'
            else:
                spatial_pattern = 'homogeneous'
            
            state_patterns.append({
                'state': state,
                'spatial_pattern': spatial_pattern,
                'cv_update_ratio': cv_update,
                'cv_compliance': cv_compliance,
                'num_districts': len(district_metrics),
                'avg_update_ratio': district_metrics['update_ratio'].mean(),
                'avg_compliance': district_metrics['biometric_compliance'].mean()
            })
        
        return pd.DataFrame(state_patterns)
    
    def detect_behavioral_patterns(self) -> pd.DataFrame:
        """Detect behavioral patterns (migration, compliance, etc.)"""
        district_metrics = self.df.groupby(['state', 'district']).agg({
            'demo_update_ratio': 'mean',
            'bio_update_ratio': 'mean',
            'update_ratio': 'mean',
            'biometric_compliance': 'mean',
            'total_holders': 'sum'
        }).reset_index()
        
        # Calculate medians for classification
        demo_median = district_metrics['demo_update_ratio'].median()
        bio_median = district_metrics['bio_update_ratio'].median()
        compliance_median = district_metrics['biometric_compliance'].median()
        
        def classify_behavior(row):
            patterns = []
            
            # Migration pattern (high demo, low bio)
            if row['demo_update_ratio'] > demo_median and row['bio_update_ratio'] < bio_median:
                patterns.append('migration_heavy')
            
            # Quality focused (high bio, high compliance)
            if row['bio_update_ratio'] > bio_median and row['biometric_compliance'] > compliance_median:
                patterns.append('quality_focused')
            
            # Low engagement (both low)
            if row['demo_update_ratio'] < demo_median and row['bio_update_ratio'] < bio_median:
                patterns.append('low_engagement')
            
            # High activity (both high)
            if row['demo_update_ratio'] > demo_median and row['bio_update_ratio'] > bio_median:
                patterns.append('high_activity')
            
            return ','.join(patterns) if patterns else 'balanced'
        
        district_metrics['behavioral_pattern'] = district_metrics.apply(classify_behavior, axis=1)
        
        return district_metrics
    
    def get_pattern_summary(self) -> Dict:
        """Get comprehensive pattern summary"""
        temporal_patterns = self.detect_temporal_patterns()
        spatial_patterns = self.detect_spatial_patterns()
        behavioral_patterns = self.detect_behavioral_patterns()
        
        summary = {
            'temporal': {
                'rising_districts': len(temporal_patterns[temporal_patterns['trend'] == 'rising']),
                'declining_districts': len(temporal_patterns[temporal_patterns['trend'] == 'declining']),
                'stable_districts': len(temporal_patterns[temporal_patterns['trend'] == 'stable']),
                'volatile_districts': len(temporal_patterns[temporal_patterns['temporal_pattern'] == 'highly_volatile'])
            },
            'spatial': {
                'heterogeneous_states': len(spatial_patterns[spatial_patterns['spatial_pattern'] == 'highly_heterogeneous']),
                'homogeneous_states': len(spatial_patterns[spatial_patterns['spatial_pattern'] == 'homogeneous']),
                'total_states': len(spatial_patterns)
            },
            'behavioral': {
                'migration_heavy': len(behavioral_patterns[behavioral_patterns['behavioral_pattern'].str.contains('migration_heavy', na=False)]),
                'quality_focused': len(behavioral_patterns[behavioral_patterns['behavioral_pattern'].str.contains('quality_focused', na=False)]),
                'low_engagement': len(behavioral_patterns[behavioral_patterns['behavioral_pattern'].str.contains('low_engagement', na=False)]),
                'high_activity': len(behavioral_patterns[behavioral_patterns['behavioral_pattern'].str.contains('high_activity', na=False)])
            },
            'temporal_df': temporal_patterns,
            'spatial_df': spatial_patterns,
            'behavioral_df': behavioral_patterns
        }
        
        return summary
    
    def get_top_patterns(self, pattern_type: str = 'behavioral', n: int = 10) -> pd.DataFrame:
        """Get top N districts by pattern type"""
        if pattern_type == 'temporal':
            patterns_df = self.detect_temporal_patterns()
            return patterns_df.nlargest(n, 'volatility')
        elif pattern_type == 'behavioral':
            patterns_df = self.detect_behavioral_patterns()
            return patterns_df.nlargest(n, 'update_ratio')
        else:
            return pd.DataFrame()