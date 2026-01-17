"""
Metrics Calculation Module
Calculates core metrics like update_ratio, compliance, etc.
"""

import pandas as pd
import numpy as np
from typing import Tuple


class MetricsCalculator:
    """Calculates key metrics for Aadhaar dashboard"""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
    
    def calculate_total_holders(self) -> pd.Series:
        """Calculate total Aadhaar holders"""
        return (
            self.df['age_0_5'].fillna(0) + 
            self.df['age_5_17'].fillna(0) + 
            self.df['age_18_greater'].fillna(0)
        )
    
    def calculate_total_updates(self) -> pd.Series:
        """Calculate total updates (demographic + biometric)"""
        demo_updates = (
            self.df['demo_age_5_17'].fillna(0) + 
            self.df['demo_age_17_'].fillna(0)
        )
        
        bio_updates = (
            self.df['bio_age_5_17'].fillna(0) + 
            self.df['bio_age_17_'].fillna(0)
        )
        
        return demo_updates + bio_updates
    
    def calculate_update_ratio(self) -> pd.Series:
        """Calculate update intensity ratio (key metric)"""
        total_holders = self.calculate_total_holders()
        total_updates = self.calculate_total_updates()
        
        # Avoid division by zero
        update_ratio = np.where(
            total_holders > 0,
            total_updates / total_holders,
            0
        )
        
        return pd.Series(update_ratio, index=self.df.index)
    
    def calculate_biometric_compliance(self) -> pd.Series:
        """Calculate biometric compliance (lifecycle metric)"""
        try:
            # Sort by year_month and district to calculate lag
            df_sorted = self.df.sort_values(['district', 'year_month'])
            
            # Group by district and calculate lag
            df_sorted['age_5_17_lag'] = df_sorted.groupby('district')['age_5_17'].shift(1)
            
            # Calculate compliance: bio_age_17_ / previous year's age_5_17
            compliance = np.where(
                df_sorted['age_5_17_lag'] > 0,
                df_sorted['bio_age_17_'].fillna(0) / df_sorted['age_5_17_lag'],
                0
            )
            
            # Reorder back to original index
            df_sorted['biometric_compliance'] = compliance
            return df_sorted['biometric_compliance'].reindex(self.df.index).fillna(0)
        except Exception as e:
            print(f"Warning: Biometric compliance calculation failed: {e}")
            # Return zeros if calculation fails
            return pd.Series(0, index=self.df.index)
    
    def calculate_enrolment_growth_rate(self) -> pd.DataFrame:
        """Calculate enrolment growth rate by district"""
        df_sorted = self.df.sort_values(['district', 'year_month'])
        
        df_sorted['total_holders_prev'] = df_sorted.groupby('district')['total_holders'].shift(1)
        
        growth_rate = np.where(
            df_sorted['total_holders_prev'] > 0,
            (df_sorted['total_holders'] - df_sorted['total_holders_prev']) / df_sorted['total_holders_prev'],
            0
        )
        
        df_sorted['enrolment_growth_rate'] = growth_rate
        return df_sorted
    
    def add_all_metrics(self) -> pd.DataFrame:
        """Add all calculated metrics to dataframe"""
        result_df = self.df.copy()
        
        result_df['total_holders'] = self.calculate_total_holders()
        result_df['total_updates'] = self.calculate_total_updates()
        result_df['update_ratio'] = self.calculate_update_ratio()
        result_df['biometric_compliance'] = self.calculate_biometric_compliance()
        
        # Calculate growth rate
        growth_df = self.calculate_enrolment_growth_rate()
        result_df['enrolment_growth_rate'] = growth_df['enrolment_growth_rate'].reindex(result_df.index).fillna(0)
        
        # Additional derived metrics
        result_df['demo_update_ratio'] = np.where(
            result_df['total_holders'] > 0,
            result_df['total_demo_updates'].fillna(0) / result_df['total_holders'],
            0
        )
        
        result_df['bio_update_ratio'] = np.where(
            result_df['total_holders'] > 0,
            result_df['total_bio_updates'].fillna(0) / result_df['total_holders'],
            0
        )
        
        return result_df
    
    def get_latest_metrics_by_district(self) -> pd.DataFrame:
        """Get latest metrics aggregated by district - using average monthly ratios"""
        df_with_metrics = self.add_all_metrics()
        
        # Option 1: Use average of monthly ratios (best for cross-time comparison)
        # This gives a representative ratio without inflating counts
        district_agg = df_with_metrics.groupby(['state', 'district'], as_index=False).agg({
            'total_holders': 'mean',  # Average across months (stock variable)
            'total_updates': 'sum',  # Total across all months (flow variable)
            'total_demo_updates': 'sum',
            'total_bio_updates': 'sum',
            'update_ratio': 'mean',  # Average monthly ratio (KEY: use mean, not sum!)
            'demo_update_ratio': 'mean',  # Average monthly ratio
            'bio_update_ratio': 'mean',  # Average monthly ratio
            'biometric_compliance': 'mean',
            'enrolment_growth_rate': 'mean'
        })
        
        # As a sanity check, also calculate from totals (but this may be inflated)
        calculated_ratio = np.where(
            district_agg['total_holders'] > 0,
            district_agg['total_updates'] / district_agg['total_holders'],
            0
        )
        
        # If calculated ratio is very different from average, use the calculated one
        # But cap it at a reasonable maximum (e.g., 10.0)
        district_agg['update_ratio_calc'] = np.clip(calculated_ratio, 0, 10.0)
        
        # Use the average monthly ratio (preferred), but fallback to calculated if needed
        # If average ratio is suspiciously high (> 20), recalculate from totals with cap
        mask_high = district_agg['update_ratio'] > 20
        district_agg.loc[mask_high, 'update_ratio'] = district_agg.loc[mask_high, 'update_ratio_calc']
        
        # Only cap extremely high ratios (> 50) which are likely data errors
        # Keep normal variation for proper visualization
        district_agg['update_ratio'] = np.clip(district_agg['update_ratio'], 0, 50.0)
        district_agg['demo_update_ratio'] = np.clip(district_agg['demo_update_ratio'], 0, 50.0)
        district_agg['bio_update_ratio'] = np.clip(district_agg['bio_update_ratio'], 0, 50.0)
        
        # Drop temporary column
        district_agg = district_agg.drop(columns=['update_ratio_calc'], errors='ignore')
        
        return district_agg
    
    def get_state_level_aggregates(self) -> pd.DataFrame:
        """Aggregate metrics at state level"""
        df_with_metrics = self.add_all_metrics()
        
        # Aggregate by state and month first
        state_monthly = df_with_metrics.groupby(['state', 'year_month'], as_index=False).agg({
            'total_holders': 'sum',
            'total_updates': 'sum',
            'total_demo_updates': 'sum',
            'total_bio_updates': 'sum',
            'biometric_compliance': 'mean',
            'enrolment_growth_rate': 'mean'
        })
        
        # Recalculate update_ratio from aggregated totals (correct way)
        state_monthly['update_ratio'] = np.where(
            state_monthly['total_holders'] > 0,
            state_monthly['total_updates'] / state_monthly['total_holders'],
            0
        )
        
        # Only cap extremely high ratios (> 50) which are likely data errors
        # Keep normal variation for proper visualization
        state_monthly['update_ratio'] = np.clip(state_monthly['update_ratio'], 0, 50.0)
        
        return state_monthly