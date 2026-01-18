"""
Data Processing Module
Handles loading, cleaning, and aggregating Aadhaar datasets
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple, List
import glob


class DataProcessor:
    """Processes and aggregates Aadhaar datasets"""
    
    def __init__(self, data_dir: str = "."):
        self.data_dir = Path(data_dir)
        
    def load_enrolment_data(self) -> pd.DataFrame:
        """Load all enrolment CSV files and combine them"""
        enrolment_dir = self.data_dir / "api_data_aadhar_enrolment" / "api_data_aadhar_enrolment"
        
        csv_files = glob.glob(str(enrolment_dir / "*.csv"))
        dfs = []
        
        for file in csv_files:
            df = pd.read_csv(file)
            dfs.append(df)
            
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df
    
    def load_demographic_data(self) -> pd.DataFrame:
        """Load all demographic update CSV files and combine them"""
        demo_dir = self.data_dir / "api_data_aadhar_demographic" / "api_data_aadhar_demographic"
        
        csv_files = glob.glob(str(demo_dir / "*.csv"))
        dfs = []
        
        for file in csv_files:
            df = pd.read_csv(file)
            dfs.append(df)
            
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df
    
    def load_biometric_data(self) -> pd.DataFrame:
        """Load all biometric update CSV files and combine them"""
        bio_dir = self.data_dir / "api_data_aadhar_biometric" / "api_data_aadhar_biometric"
        
        csv_files = glob.glob(str(bio_dir / "*.csv"))
        dfs = []
        
        for file in csv_files:
            df = pd.read_csv(file)
            dfs.append(df)
            
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df
    
    def standardize_date(self, df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
        """Convert date column to datetime and extract YYYY-MM format"""
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col], format='%d-%m-%Y', errors='coerce')
        df['year_month'] = df[date_col].dt.to_period('M').astype(str)
        return df
    
    def standardize_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize state and district names for geo matching"""
        df = df.copy()
        
        # State name standardization mapping
        state_mappings = {
            # Case variations
            'ODISHA': 'Odisha',
            'odisha': 'Odisha',
            'WEST BENGAL': 'West Bengal',
            'WESTBENGAL': 'West Bengal',
            'West  Bengal': 'West Bengal',
            'West Bangal': 'West Bengal',
            'West Bengli': 'West Bengal',
            'West bengal': 'West Bengal',
            'west Bengal': 'West Bengal',
            'Westbengal': 'West Bengal',
            'andhra pradesh': 'Andhra Pradesh',
            
            # Name variations
            'Andaman & Nicobar Islands': 'Andaman and Nicobar Islands',
            'Jammu & Kashmir': 'Jammu and Kashmir',
            'Jammu And Kashmir': 'Jammu and Kashmir',
            'Dadra & Nagar Haveli': 'Dadra and Nagar Haveli and Daman and Diu',
            'Dadra and Nagar Haveli': 'Dadra and Nagar Haveli and Daman and Diu',
            'The Dadra And Nagar Haveli And Daman And Diu': 'Dadra and Nagar Haveli and Daman and Diu',
            'DNH and DD': 'Dadra and Nagar Haveli and Daman and Diu',
            'Daman & Diu': 'Dadra and Nagar Haveli and Daman and Diu',
            'Daman and Diu': 'Dadra and Nagar Haveli and Daman and Diu',
            'Pondicherry': 'Puducherry',
            'Orissa': 'Odisha',
            'Uttaranchal': 'Uttarakhand',
            'Chhatisgarh': 'Chhattisgarh',
            'Tamilnadu': 'Tamil Nadu',
            
            # Invalid entries (cities/districts that should be mapped to their states)
            'Jaipur': 'Rajasthan',
            'Nagpur': 'Maharashtra', 
            'Darbhanga': 'Bihar',
            'Madanapalle': 'Andhra Pradesh',
            'Puttenahalli': 'Karnataka',
            'Raja Annamalai Puram': 'Tamil Nadu',
            'BALANAGAR': 'Telangana',
            
            # Remove invalid numeric entries
            '100000': None
        }
        
        # Apply state mappings
        df['state'] = df['state'].replace(state_mappings)
        
        # Remove rows with None state (invalid entries)
        df = df.dropna(subset=['state'])
        
        # Clean district names
        df['district'] = df['district'].str.strip()
        df['state'] = df['state'].str.strip()
        
        return df
    
    def aggregate_monthly_district(self, df: pd.DataFrame, 
                                   group_cols: List[str],
                                   numeric_cols: List[str]) -> pd.DataFrame:
        """Aggregate data by date, state, district"""
        agg_dict = {col: 'sum' for col in numeric_cols}
        
        aggregated = df.groupby(group_cols, as_index=False).agg(agg_dict)
        
        return aggregated
    
    def process_enrolment(self) -> pd.DataFrame:
        """Process enrolment data"""
        df = self.load_enrolment_data()
        df = self.standardize_date(df)
        df = self.standardize_names(df)
        
        numeric_cols = ['age_0_5', 'age_5_17', 'age_18_greater']
        group_cols = ['year_month', 'state', 'district']
        
        aggregated = self.aggregate_monthly_district(df, group_cols, numeric_cols)
        
        aggregated['total_holders'] = (
            aggregated['age_0_5'] + 
            aggregated['age_5_17'] + 
            aggregated['age_18_greater']
        )
        
        return aggregated
    
    def process_demographic(self) -> pd.DataFrame:
        """Process demographic update data"""
        df = self.load_demographic_data()
        df = self.standardize_date(df)
        df = self.standardize_names(df)
        
        numeric_cols = ['demo_age_5_17', 'demo_age_17_']
        group_cols = ['year_month', 'state', 'district']
        
        aggregated = self.aggregate_monthly_district(df, group_cols, numeric_cols)
        
        aggregated['total_demo_updates'] = (
            aggregated['demo_age_5_17'] + 
            aggregated['demo_age_17_']
        )
        
        return aggregated
    
    def process_biometric(self) -> pd.DataFrame:
        """Process biometric update data"""
        df = self.load_biometric_data()
        df = self.standardize_date(df)
        df = self.standardize_names(df)
        
        numeric_cols = ['bio_age_5_17', 'bio_age_17_']
        group_cols = ['year_month', 'state', 'district']
        
        aggregated = self.aggregate_monthly_district(df, group_cols, numeric_cols)
        
        aggregated['total_bio_updates'] = (
            aggregated['bio_age_5_17'] + 
            aggregated['bio_age_17_']
        )
        
        return aggregated
    
    def merge_all_datasets(self) -> pd.DataFrame:
        """Merge enrolment, demographic, and biometric datasets"""
        enrolment = self.process_enrolment()
        demographic = self.process_demographic()
        biometric = self.process_biometric()
        
        # Merge on year_month, state, district
        merged = enrolment.merge(
            demographic,
            on=['year_month', 'state', 'district'],
            how='outer',
            suffixes=('', '_demo')
        )
        
        merged = merged.merge(
            biometric,
            on=['year_month', 'state', 'district'],
            how='outer',
            suffixes=('', '_bio')
        )
        
        # Fill NaN values with 0 for numeric columns
        numeric_cols = merged.select_dtypes(include=[np.number]).columns
        merged[numeric_cols] = merged[numeric_cols].fillna(0)
        
        # Ensure state and district are filled
        merged['state'] = merged['state'].ffill().bfill()
        merged['district'] = merged['district'].ffill().bfill()
        
        return merged