"""
GeoJSON Integration Utilities
Handles map data loading and merging with metrics
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# Try to import geopandas, fallback if not available
try:
    import geopandas as gpd
    GEOPANDAS_AVAILABLE = True
except ImportError:
    GEOPANDAS_AVAILABLE = False
    gpd = None

try:
    from thefuzz import process
except ImportError:
    process = None


class GeoJSONUtils:
    """Utilities for working with GeoJSON data"""
    
    def __init__(self, geojson_dir: str = "india-maps-data/geojson"):
        self.geojson_dir = Path(geojson_dir)
        if not GEOPANDAS_AVAILABLE:
            print("Warning: geopandas not available. Geographic maps will not work.")
    
    def load_india_geojson(self):
        """Load India GeoJSON file"""
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("geopandas is required for geographic maps")
            
        geojson_path = self.geojson_dir / "india.geojson"
        try:
            gdf = gpd.read_file(geojson_path)
            return gdf
        except (AttributeError, ImportError) as e:
            # Fallback: load as JSON and convert manually
            import json
            with open(geojson_path, 'r') as f:
                geojson_data = json.load(f)
            gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
            return gdf
    
    def load_state_geojson(self, state_name: str):
        """Load state-specific GeoJSON file"""
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("geopandas is required for geographic maps")
            
        # Normalize state name for filename matching
        state_filename = state_name.lower().replace(' ', '-') + '.geojson'
        geojson_path = self.geojson_dir / "states" / state_filename
        
        if geojson_path.exists():
            try:
                gdf = gpd.read_file(geojson_path)
                return gdf
            except (AttributeError, ImportError) as e:
                # Fallback: load as JSON and convert manually
                import json
                with open(geojson_path, 'r') as f:
                    geojson_data = json.load(f)
                gdf = gpd.GeoDataFrame.from_features(geojson_data['features'])
                return gdf
        else:
            # Try alternative naming
            alt_names = {
                'jammu and kashmir': 'jammu-and-kashmir',
                'dadra and nagar haveli': 'dnh-and-dd',
                'daman and diu': 'dnh-and-dd',
                'puducherry': 'puducherry',
                'tamil nadu': 'tamil-nadu',
                'west bengal': 'west-bengal',
                'uttar pradesh': 'uttar-pradesh',
                'himachal pradesh': 'himachal-pradesh',
                'andhra pradesh': 'andhra-pradesh',
                'arunachal pradesh': 'arunachal-pradesh',
                'madhya pradesh': 'madhya-pradesh'
            }
            
            normalized = state_name.lower()
            if normalized in alt_names:
                geojson_path = self.geojson_dir / "states" / (alt_names[normalized] + '.geojson')
                if geojson_path.exists():
                    try:
                        return gpd.read_file(geojson_path)
                    except (AttributeError, ImportError) as e:
                        # Fallback: load as JSON and convert manually
                        import json
                        with open(geojson_path, 'r') as f:
                            geojson_data = json.load(f)
                        return gpd.GeoDataFrame.from_features(geojson_data['features'])
        
        return None
    
    def normalize_state_name(self, state_name: str) -> str:
        """Normalize state names for matching"""
        # Handle None/NaN values
        if state_name is None or pd.isna(state_name) or state_name == 'nan' or state_name == 'None':
            return ''
        
        try:
            state_name = str(state_name).strip()
            if not state_name:
                return ''
        except (AttributeError, TypeError):
            return ''
        
        mapping = {
            'Jammu and Kashmir': 'Jammu and Kashmir',
            'Jammu And Kashmir': 'Jammu and Kashmir',
            'Dadra and Nagar Haveli': 'DNH and DD',
            'Dadra And Nagar Haveli': 'DNH and DD',
            'The Dadra And Nagar Haveli And Daman And Diu': 'DNH and DD',
            'Daman and Diu': 'DNH and DD',
            'Puducherry': 'Puducherry',
            'Tamil Nadu': 'Tamil Nadu',
            'West Bengal': 'West Bengal',
            'West Bengli': 'West Bengal',
            'Uttar Pradesh': 'Uttar Pradesh',
            'Himachal Pradesh': 'Himachal Pradesh',
            'Andhra Pradesh': 'Andhra Pradesh',
            'Arunachal Pradesh': 'Arunachal Pradesh',
            'Madhya Pradesh': 'Madhya Pradesh',
            'Chhatisgarh': 'Chhattisgarh',
            'Chhattisgarh': 'Chhattisgarh',
            'Uttaranchal': 'Uttarakhand',
            'Uttarakhand': 'Uttarakhand'
        }
        
        return mapping.get(state_name, state_name)
    
    def normalize_district_name(self, district_name: str) -> str:
        """Normalize district names for matching with comprehensive mappings"""
        # Handle None/NaN values
        if district_name is None or pd.isna(district_name) or district_name == 'nan' or district_name == 'None':
            return ''
        # Convert to string and handle edge cases
        try:
            district_name = str(district_name)
            if not district_name or district_name.strip() == '':
                return ''
            normalized = ' '.join(district_name.strip().split())
            
            # Comprehensive district name mappings (data_name -> geo_name)
            name_mappings = {
                # Karnataka mappings (critical for fixing the anomaly issue)
                'bengaluru south': 'Bengaluru Urban',
                'bengaluru': 'Bengaluru Urban', 
                'bangalore': 'Bengaluru Urban',
                'bangalore rural': 'Bengaluru Rural',
                'belgaum': 'Belagavi',
                'bellary': 'Ballari',
                'bijapur(kar)': 'Vijayapura',
                'bijapur': 'Vijayapura',
                'chamarajanagar': 'Chamarajanagara',
                'chikballapur': 'Chikkaballapura',
                'chikmagalur': 'Chikkamagaluru',
                'dakshina kannada': 'Dakshin Kannad',
                'gulbarga': 'Kalaburagi',
                'hubli-dharwad': 'Dharwad',
                'mysore': 'Mysuru',
                'shimoga': 'Shivamogga',
                'tumkur': 'Tumakuru',
                'uttara kannada': 'Uttar Kannad',
                'guledagudda': 'Bagalkot', # Mapped to parent district if new
                
                # Maharashtra
                'ahmed nagar': 'Ahmednagar',
                'beed': 'Bid',
                'buldhana': 'Buldana',
                'gondia': 'Gondiya',
                'mumbai': 'Mumbai Suburban', # Most population usually here or duplicate
                'nashik': 'Nashik', 
                'nandurbar': 'Nandurbar',
                'raigarh(mh)': 'Raigarh', # Ambiguous, but usually Raigad if MH
                'raigad': 'Raigad',
                'thane': 'Thane',

                # Uttar Pradesh
                'allahabad': 'Prayagraj', # If map has Prayagraj
                'barabanki': 'Bara Banki',
                'faizabad': 'Ayodhya', # Or Firozabad if fuzzy match was weird, but Ayodhya is correct
                'firozabad': 'Firozabad',
                'gautam buddha nagar': 'Gautam Buddh Nagar',
                'kanpur dehat': 'Kanpur Dehat',
                'kanpur nagar': 'Kanpur Nagar',
                'kheri': 'Kheri',
                'lakhimpur kheri': 'Kheri',
                'jyotiba phule nagar': 'Amroha',
                'kanshiram nagar': 'Kasganj',
                'mahamaya nagar': 'Hathras',
                'noida': 'Gautam Buddh Nagar',
                'raebareli': 'Rae Bareli',
                'sant ravidas nagar': 'Bhadohi',
                'sant ravidas nagar (bhadohi)': 'Bhadohi',
                'siddharth nagar': 'Siddharthnagar',
                'shravasti': 'Shrawasti',
                
                # Bihar
                'bhabua': 'Kaimur',
                'kaimur (bhabua)': 'Kaimur',
                'jehanabad': 'Jehanabad',
                'pashchim champaran': 'Pashchim Champaran', # Or West Champaran
                'west champaran': 'Pashchim Champaran', 
                'purbi champaran': 'Purba Champaran', # Or East Champaran
                'east champaran': 'Purba Champaran',
                'sheikpura': 'Sheikhpura',
                'purnia': 'Purnia',
                'purnea': 'Purnia',

                # West Bengal
                'bardhaman': 'Purba Bardhaman', # Split into Purba/Paschim
                'burdwan': 'Purba Bardhaman',
                'coochbehar': 'Koch Bihar',
                'darjiling': 'Darjeeling',
                'hooghly': 'Hooghly',
                'howrah': 'Haora',
                'maldah': 'Malda',
                'north 24 parganas': 'North 24 Parganas',
                'south 24 parganas': 'South 24 Parganas',
                'north twenty four parganas': 'North 24 Parganas',
                'south twenty four parganas': 'South 24 Parganas',
                'purulia': 'Purulia',
                'puruliya': 'Purulia',
                
                # Gujarat
                'ahmedabad': 'Ahmadabad',
                'ahmdabad': 'Ahmadabad',
                'banaskantha': 'Banas Kantha',
                'chhota udaipur': 'Chhotaudepur',
                'dahod': 'Dohad',
                'devbhumi dwarka': 'Devbhumi Dwaraka',
                'dholpur': 'Dhaulpur', # Matches RAJ data but let's keep safe
                'kutch': 'Kachchh',
                'mahesana': 'Mahesana',
                'mehsana': 'Mahesana',
                'panch mahals': 'Panchmahal',
                'panchmahals': 'Panchmahal',
                'sabarkantha': 'Sabarkantha',
                'the dangs': 'Dang',
                'vadodara': 'Vadodara',
                
                # Rajasthan
                'beawar': 'Ajmer', # New district usually carved from Ajmer/Pali/Rajsamand
                'didwana-kuchaman': 'Nagaur', # Carved from Nagaur
                'dudu': 'Jaipur', # Carved from Jaipur
                'gangapur city': 'Sawai Madhopur', 
                'jalore': 'Jalor',
                'kekri': 'Ajmer', 
                'kotputli-behror': 'Jaipur',
                'khairthal-tijara': 'Alwar',
                'neem ka thana': 'Sikar',
                'phalodi': 'Jodhpur',
                'salumbar': 'Udaipur',
                'shahpura': 'Bhilwara',
                'bundi': 'Bundi',
                'chittaurgarh': 'Chittorgarh',
                'dholpur': 'Dhaulpur',
                'jalore': 'Jalor',
                'jhunjhunun': 'Jhunjhunu',
                'sawai madhopur': 'Sawai Madhopur',
                
                # Jammu & Kashmir
                'badgam': 'Budgam',
                'bandipora': 'Bandipore',
                'baramula': 'Baramulla',
                'rajauri': 'Rajouri',
                'shopian': 'Shopiyan',
                'shupiyan': 'Shopiyan',

                # Tamil Nadu
                'chengalpattu': 'Kancheepuram', # New dist
                'kanchipuram': 'Kancheepuram',
                'kanyakumari': 'Kanniyakumari',
                'tenkasi': 'Tirunelveli', # New
                'the nilgiris': 'Nilgiris',
                'thiruvallur': 'Thiruvallur',
                'tiruvallur': 'Thiruvallur',
                'thoothukudi': 'Thoothukkudi',
                'tuticorin': 'Thoothukkudi',
                'tirupattur': 'Tirupathur',
                'tiruppur': 'Tiruppur',
                'tiruvarur': 'Thiruvarur',
                'villupuram': 'Viluppuram',
                
                # Odisha
                'angul': 'Angul',
                'anugul': 'Angul',
                'balasore': 'Baleshwar',
                'bhubaneswar': 'Khordha', 
                'cuttack': 'Cuttack',
                'deogarh': 'Debagarh',
                'jajpur': 'Jajpur',
                'jagatsinghapur': 'Jagatsinghpur',
                'khordha': 'Khordha',
                'keonjhar': 'Kendujhar',
                'nabarangapur': 'Nabarangpur',
                'sundergarh': 'Sundargarh',
                
                # Punjab
                'fategarh sahib': 'Fatehgarh Sahib',
                'firozpur': 'Ferozepur',
                'sahibzada ajit singh nagar': 'S.A.S. Nagar',
                's.a.s nagar': 'S.A.S. Nagar',
                's.a.s. nagar (mohali)': 'S.A.S. Nagar',
                'mohali': 'S.A.S. Nagar',
                'sri muktsar sahib': 'Sri Muktsar Sahib',
                'tarn taran': 'Tarn Taran',
                
                # Haryana
                'gurgaon': 'Gurugram', # Or vice versa
                'gurugram': 'Gurugram', # Map likely uses Gurugram or Gurgaon
                'hisar': 'Hisar',
                'mewat': 'Nuh',
                'nuh': 'Nuh',
                'yamuna nagar': 'Yamunanagar', # Space diff
                
                # Other States
                'dadra & nagar haveli': 'Dadra and Nagar Haveli',
                'dinhata': 'Koch Bihar',
                'east district': 'East District', # Sikkim
                'north district': 'North District', # Sikkim
                'south district': 'South District', # Sikkim
                'west district': 'West District', # Sikkim
                'hazaribag': 'Hazaribagh', # Jharkhand
                'janjgir - champa': 'Janjgir Champa', # CG
                'leads': 'Ladakh', 
                'leh': 'Leh (Ladakh)',
                'mahabub nagar': 'Mahbubnagar', # TS
                'marigaon': 'Morigaon', # Assam
                'narsimhapur': 'Narsinghpur', # MP
                'rangareddi': 'Ranga Reddy', # TS
                'rangareddy': 'Ranga Reddy',
                'sepahijala': 'Sipahijala', # Tripura
                'seraikela-kharsawan': 'Saraikela-Kharsawan', # Jharkhand
                'west medinipur': 'Paschim Medinipur', # WB
                'west midnapore': 'Paschim Medinipur',
                
                # Clean up dirty inputs
                'chandauli *': 'Chandauli',
                'chitrakoot *': 'Chitrakoot',
                'haveri *': 'Haveri',
                'hingoli *': 'Hingoli',
                'khordha  *': 'Khordha',
                'kushinagar *': 'Kushinagar',
                'nandurbar *': 'Nandurbar',
                'udham singh nagar *': 'Udham Singh Nagar',
                'washim *': 'Washim',
                'bagalkot *': 'Bagalkot',
                'north 24 parganas *': 'North 24 Parganas',
                'south 24 pargana': 'South 24 Parganas'
            }
            
            normalized_lower = normalized.lower()
            if normalized_lower in name_mappings:
                return name_mappings[normalized_lower]
            
            # Clean up asterisks and extra spaces
            cleaned = normalized_lower.replace(' *', '').replace('*', '').strip()
            if cleaned in name_mappings:
                return name_mappings[cleaned]
            
            return normalized
        except (AttributeError, TypeError):
            return ''

            
    def fuzzy_match_districts(self, source_names: List[str], target_names: List[str], threshold: int = 85) -> Dict[str, str]:
        """
        Match source district names to target names using fuzzy matching
        Returns a dictionary of {source_name: target_name} for matches above threshold
        """
        if process is None:
            return {}
            
        mapping = {}
        # Create a set for faster lookup
        target_set = set(target_names)
        
        for name in source_names:
            if not name or name in target_set:
                continue
                
            # Find best match
            match = process.extractOne(name, target_names)
            if match:
                best_match, score = match
                if score >= threshold:
                    mapping[name] = best_match
                    
        return mapping

    def merge_geo_with_metrics(self, metrics_df: pd.DataFrame, 
                               level: str = 'state'):
        """
        Merge GeoJSON data with metrics dataframe
        
        Args:
            metrics_df: DataFrame with metrics (state/district, metrics)
            level: 'state' or 'district'
        """
        if not GEOPANDAS_AVAILABLE:
            raise ImportError("geopandas is required for geographic maps")
            
        if level == 'state':
            return self._merge_state_level(metrics_df)
        elif level == 'district':
            return self._merge_district_level(metrics_df)
        else:
            raise ValueError("level must be 'state' or 'district'")
    
    def _merge_state_level(self, metrics_df: pd.DataFrame):
        """Merge state-level metrics with GeoJSON"""
        # Load India GeoJSON
        gdf = self.load_india_geojson()
        
        # Fill NaN values in GeoDataFrame before normalization
        if 'st_nm' in gdf.columns:
            gdf['st_nm'] = gdf['st_nm'].fillna('')
        
        # Aggregate metrics by state if needed
        if 'district' in metrics_df.columns:
            state_metrics = metrics_df.groupby('state', as_index=False).agg({
                'update_ratio': 'mean',
                'biometric_compliance': 'mean',
                'total_holders': 'sum',
                'total_updates': 'sum',
                'enrolment_growth_rate': 'mean'
            })
        else:
            state_metrics = metrics_df.copy()
        
        # Fill NaN state names before normalization
        if 'state' in state_metrics.columns:
            state_metrics['state'] = state_metrics['state'].fillna('')
        
        # Normalize state names with safe handling
        state_metrics['state_normalized'] = state_metrics['state'].apply(
            lambda x: self.normalize_state_name(x) if x is not None else ''
        )
        gdf['state_normalized'] = gdf['st_nm'].apply(
            lambda x: self.normalize_state_name(x) if x is not None else ''
        )
        
        # Merge
        merged = gdf.merge(
            state_metrics,
            left_on='state_normalized',
            right_on='state_normalized',
            how='left'
        )
        
        # Fill NaN values with 0
        numeric_cols = merged.select_dtypes(include=['float64', 'int64', 'float32', 'int32']).columns
        exclude_cols = ['dt_code', 'st_code', 'year']
        numeric_cols = [col for col in numeric_cols if col not in exclude_cols]
        if len(numeric_cols) > 0:
            merged[numeric_cols] = merged[numeric_cols].fillna(0)
        
        return merged
    
    def _merge_district_level(self, metrics_df: pd.DataFrame):
        """Merge district-level metrics with GeoJSON"""
        # Load India GeoJSON (contains districts)
        gdf = self.load_india_geojson()
        
        # Ensure required columns exist and fill NaN values
        if 'district' not in gdf.columns:
            gdf['district'] = ''
        if 'st_nm' not in gdf.columns:
            gdf['st_nm'] = ''
        
        # Fill NaN/None values in GeoDataFrame before normalization (handle None properly)
        gdf['district'] = gdf['district'].where(pd.notna(gdf['district']), '').astype(str)
        gdf['district'] = gdf['district'].str.replace('nan', '', regex=False).str.replace('None', '', regex=False)
        gdf['st_nm'] = gdf['st_nm'].where(pd.notna(gdf['st_nm']), '').astype(str)
        gdf['st_nm'] = gdf['st_nm'].str.replace('nan', '', regex=False).str.replace('None', '', regex=False)
        
        # Normalize district and state names in metrics
        metrics_df = metrics_df.copy()
        if 'district' in metrics_df.columns:
            metrics_df['district'] = metrics_df['district'].where(pd.notna(metrics_df['district']), '').astype(str)
            metrics_df['district'] = metrics_df['district'].str.replace('nan', '', regex=False).str.replace('None', '', regex=False)
        else:
            metrics_df['district'] = ''
        if 'state' in metrics_df.columns:
            metrics_df['state'] = metrics_df['state'].where(pd.notna(metrics_df['state']), '').astype(str)
            metrics_df['state'] = metrics_df['state'].str.replace('nan', '', regex=False).str.replace('None', '', regex=False)
        else:
            metrics_df['state'] = ''
        
        # Apply normalization with safe handling
        metrics_df['district_normalized'] = metrics_df['district'].apply(
            lambda x: self.normalize_district_name(x) if x is not None else ''
        )
        metrics_df['state_normalized'] = metrics_df['state'].apply(
            lambda x: self.normalize_state_name(x) if x is not None else ''
        )
        
        gdf['district_normalized'] = gdf['district'].apply(
            lambda x: self.normalize_district_name(x) if x is not None else ''
        )
        gdf['state_normalized'] = gdf['st_nm'].apply(
            lambda x: self.normalize_state_name(x) if x is not None else ''
        )
        
        # --- FUZZY MATCHING START ---
        # Get unique normalized names from both sides
        geo_districts = gdf['district_normalized'].unique().tolist()
        metric_districts = metrics_df['district_normalized'].unique().tolist()
        
        # Remove empty strings
        geo_districts = [d for d in geo_districts if d]
        metric_districts = [d for d in metric_districts if d]
        
        # Find fuzzy matches for unmatched districts
        fuzzy_mapping = self.fuzzy_match_districts(metric_districts, geo_districts)
        
        # Apply fuzzy mapping to metrics dataframe
        if fuzzy_mapping:
            metrics_df['district_normalized'] = metrics_df['district_normalized'].replace(fuzzy_mapping)
            # print(f"Fuzzy matched {len(fuzzy_mapping)} districts") # Debug info
        # --- FUZZY MATCHING END ---
        
        # CRITICAL FIX: Aggregate metrics by normalized names BEFORE merge
        # This ensures that when multiple districts map to the same geo district,
        # we take the maximum values (especially important for anomaly scores)
        agg_functions = {}
        for col in metrics_df.columns:
            if col not in ['state', 'district', 'state_normalized', 'district_normalized']:
                if 'anomaly_score' in col:
                    agg_functions[col] = 'max'  # Take highest anomaly score
                elif 'anomaly_flag' in col:
                    # Take the most severe flag (critical > warning > normal)
                    agg_functions[col] = lambda x: 'critical' if 'critical' in x.values else ('warning' if 'warning' in x.values else 'normal')
                elif col in ['update_ratio', 'update_ratio_mean']:
                    agg_functions[col] = 'max'  # Take highest update ratio
                else:
                    agg_functions[col] = 'mean'  # Default to mean for other metrics
        
        # Add state and district back to aggregation
        agg_functions['state'] = 'first'
        agg_functions['district'] = 'first'
        
        # Aggregate by normalized names
        if len(agg_functions) > 0:
            metrics_aggregated = metrics_df.groupby(['state_normalized', 'district_normalized'], as_index=False).agg(agg_functions)
        else:
            metrics_aggregated = metrics_df.copy()
        
        # Merge on both state and district
        merged = gdf.merge(
            metrics_aggregated,
            left_on=['state_normalized', 'district_normalized'],
            right_on=['state_normalized', 'district_normalized'],
            how='left'
        )
        
        # Clean up column names after merge - ensure 'district' and 'state' columns exist
        if 'district_y' in merged.columns:
            merged['district'] = merged['district_y']  # Use metrics district name
        elif 'district_x' in merged.columns:
            merged['district'] = merged['district_x']  # Use geo district name
        
        if 'state_y' in merged.columns:
            merged['state'] = merged['state_y']  # Use metrics state name
        elif 'state_x' in merged.columns:
            merged['state'] = merged['state_x']  # Use geo state name
        elif 'st_nm' in merged.columns:
            merged['state'] = merged['st_nm']  # Use geo state name from st_nm
        
        # Fill NaN values
        numeric_cols = merged.select_dtypes(include=['float64', 'int64', 'float32', 'int32']).columns
        exclude_cols = ['dt_code', 'st_code', 'year']
        numeric_cols = [col for col in numeric_cols if col not in exclude_cols]
        if len(numeric_cols) > 0:
            merged[numeric_cols] = merged[numeric_cols].fillna(0)
        
        return merged
    
    def get_available_states(self) -> list:
        """Get list of available state GeoJSON files"""
        states_dir = self.geojson_dir / "states"
        if not states_dir.exists():
            return []
        
        state_files = list(states_dir.glob("*.geojson"))
        states = [f.stem.replace('-', ' ').title() for f in state_files]
        return sorted(states)