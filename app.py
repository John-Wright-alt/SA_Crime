from flask import Flask, render_template, jsonify
import pandas as pd
import numpy as np
import geopandas as gpd
import json
from datetime import datetime
import os
import warnings
from shapely.geometry import mapping

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

app = Flask(__name__)

class CrimeDataProcessor:
    def __init__(self):
        self.df = None
        self.gdf = None
        self.years = []
        self.processed_data = None
        self.df_WS_st = None
        
    def load_data(self):
        """Load and process crime data"""
        try:
            # Define the absolute path to your data directory
            data_dir = r'C:\Users\John\Desktop\south_africa_crime_viz\data'
            
            # Load CSV data
            csv_path = os.path.join(data_dir, 'SouthAfricaCrimeStats_v2.csv')
            print(f"Looking for CSV at: {csv_path}")
            
            if not os.path.exists(csv_path):
                print(f"CSV file not found at {csv_path}")
                return False
                
            self.df = pd.read_csv(csv_path)
            print(f"CSV loaded successfully: {len(self.df)} records")
            
            # Load shapefile with improved error handling
            shp_path = os.path.join(data_dir, 'Police_bounds.shp')
            print(f"Looking for shapefile at: {shp_path}")
            
            if os.path.exists(shp_path):
                try:
                    # Try to read shapefile with different approaches
                    print("Attempting to load shapefile...")
                    
                    # Method 1: Direct read
                    try:
                        self.gdf = gpd.read_file(shp_path)
                        print("Shapefile loaded using direct method")
                    except Exception as e1:
                        print(f"Direct method failed: {e1}")
                        
                        # Method 2: Try with different drivers
                        try:
                            self.gdf = gpd.read_file(shp_path, driver='ESRI Shapefile')
                            print("Shapefile loaded using ESRI Shapefile driver")
                        except Exception as e2:
                            print(f"ESRI driver failed: {e2}")
                            
                            # Method 3: Try reading with fiona directly
                            try:
                                import fiona
                                with fiona.open(shp_path) as src:
                                    features = [feature for feature in src]
                                    crs = src.crs
                                self.gdf = gpd.GeoDataFrame.from_features(features, crs=crs)
                                print("Shapefile loaded using fiona method")
                            except Exception as e3:
                                print(f"Fiona method failed: {e3}")
                                raise Exception("All shapefile loading methods failed")
                    
                    # Handle CRS if shapefile was loaded successfully
                    if self.gdf is not None:
                        # Handle CRS
                        if self.gdf.crs is None:
                            print("Setting default CRS to EPSG:4326")
                            self.gdf = self.gdf.set_crs('EPSG:4326')
                        else:
                            print(f"Original CRS: {self.gdf.crs}")
                            
                        # Ensure we're in WGS84 for web mapping
                        if str(self.gdf.crs) != 'EPSG:4326':
                            try:
                                self.gdf = self.gdf.to_crs('EPSG:4326')
                                print("CRS converted to EPSG:4326")
                            except Exception as crs_error:
                                print(f"CRS conversion failed: {crs_error}")
                                # Continue with original CRS
                            
                        print(f"Shapefile loaded successfully: {len(self.gdf)} features")
                        print(f"Shapefile columns: {list(self.gdf.columns)}")
                    
                except Exception as shp_error:
                    print(f"Error loading shapefile: {shp_error}")
                    print("Continuing without shapefile - map functionality will be limited")
                    self.gdf = None
            else:
                print(f"Shapefile not found at {shp_path}")
                # Check for alternative shapefile names
                shp_files = [f for f in os.listdir(data_dir) if f.endswith('.shp')]
                if shp_files:
                    print(f"Found other shapefiles: {shp_files}")
                    print("You may need to update the shapefile name in the code")
                print("Continuing without shapefile - map functionality will be limited")
                self.gdf = None
            
            print(f"Data loaded successfully: {len(self.df)} records")
            return True
            
        except Exception as e:
            print(f"Error loading data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_crime_data(self):
        """Process crime data with severity weighting - from your Python script"""
        if self.df is None:
            return False
            
        try:
            print(f"Processing dataset with {len(self.df)} rows and {len(self.df.columns)} columns")
            print(f"Dataset columns: {list(self.df.columns)}")
            
            # Crime severity categories and ratings (from your analysis code)
            sev_cat = ['Burglary at non-residential premises', 'Malicious damage to property',
                       'Theft of motor vehicle and motorcycle', 'Carjacking', 'Attempted murder',
                       'Burglary at residential premises', 'All theft not mentioned elsewhere',
                       'Murder', 'Common assault', 'Truck hijacking',
                       'Assault with the intent to inflict grievous bodily harm', 'Bank robbery',
                       'Stock-theft', 'Robbery at non-residential premises',
                       'Robbery with aggravating circumstances',
                       'Driving under the influence of alcohol or drugs',
                       'Theft out of or from motor vehicle', 'Drug-related crime',
                       'Illegal possession of firearms and ammunition', 'Arson',
                       'Robbery of cash in transit', 'Common robbery',
                       'Robbery at residential premises',
                       'Sexual offences as result of police action', 'Commercial crime',
                       'Sexual Offences', 'Shoplifting']

            sev_rate = [3, 3, 3, 3, 1, 3, 3, 1, 2, 3, 1, 2, 3, 2, 2, 2, 3, 2, 2, 2, 2, 2, 2, 1, 3, 1, 3]

            # Create severity dataframe and merge
            sev_df = pd.DataFrame({'Category': sev_cat, 'Severity': sev_rate})
            self.df = self.df.merge(sev_df, on='Category', how='left')
            self.df['Severity'] = self.df['Severity'].fillna(2)  # Default severity for unmapped categories
            
            # Get year columns - improved detection
            headings = list(self.df.columns)
            potential_years = []
            
            for col in headings:
                if col not in ['Station', 'Province', 'Category', 'Severity']:
                    # Check if column name looks like a year
                    col_str = str(col).strip()
                    try:
                        # Try to convert to int and check if it's a reasonable year
                        year_val = int(float(col_str))
                        if 1900 <= year_val <= 2030:  # Reasonable year range
                            potential_years.append(year_val)
                    except (ValueError, TypeError):
                        # Check if it's a year-like string (e.g., "2019.0")
                        if '.' in col_str:
                            try:
                                year_val = int(float(col_str))
                                if 1900 <= year_val <= 2030:
                                    potential_years.append(year_val)
                            except (ValueError, TypeError):
                                pass
            
            # Sort years and convert back to strings to match column names
            self.years = sorted(list(set(potential_years)))
            year_cols = []
            
            for year in self.years:
                # Find the actual column name for this year
                for col in headings:
                    try:
                        if int(float(str(col))) == year:
                            year_cols.append(col)
                            break
                    except (ValueError, TypeError):
                        continue
            
            # Update years to use actual column names
            self.years = year_cols
            
            print(f"Detected year columns: {self.years}")
            
            # Check if we have any years
            if not self.years:
                print("WARNING: No year columns detected!")
                print("Available columns:", headings)
                # Try to detect any numeric columns as potential years
                numeric_cols = []
                for col in headings:
                    if col not in ['Station', 'Province', 'Category', 'Severity']:
                        try:
                            # Check if the column contains numeric data
                            pd.to_numeric(self.df[col], errors='coerce')
                            numeric_cols.append(col)
                        except:
                            pass
                
                if numeric_cols:
                    print(f"Found potential numeric columns: {numeric_cols}")
                    self.years = numeric_cols[:10]  # Take first 10 as a fallback
                else:
                    print("No suitable year columns found")
                    return False
            
            print(f"Years to process: {len(self.years)} columns")
            if self.years:
                print(f"Year range: {self.years[0]} to {self.years[-1]}")
            
            # Calculate station appearance (when each station first appears in data)
            df_station_sum = self.df[['Station'] + self.years].groupby('Station').sum().reset_index()
            st_list = sorted(df_station_sum['Station'].tolist())

            station_appearance = {}
            for station in st_list:
                station_data = df_station_sum.loc[df_station_sum['Station'] == station, self.years].values.flatten()
                non_zero_indices = np.nonzero(station_data)[0]
                if len(non_zero_indices) > 0:
                    station_appearance[station] = non_zero_indices[0]
                else:
                    station_appearance[station] = 0

            # Create weighted crime data
            self.create_weighted_crime_data(station_appearance)
            return True
            
        except Exception as e:
            print(f"Error processing crime data: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def create_weighted_crime_data(self, station_appearance):
        """Create weighted crime data based on severity and time factors"""
        
        try:
            df_WS = self.df.copy()
            station_l = [key for key in station_appearance]
            appearance_l = [station_appearance[key] for key in station_appearance]
            sa_df = pd.DataFrame({'Station': station_l, 'Years_active': appearance_l})
            sa_df['Years_active'] = sa_df['Years_active'] * (-1) + len(self.years)

            df_WS = df_WS.merge(sa_df, on='Station', how='left')

            # Time apathy coefficients (your original logic)
            time_apathy_list = [0.7, 0.7, 0.7, 0.8, 0.8, 0.8, 0.9, 0.9, 1, 1, 1]
            
            # Extend or truncate the list to match the number of years
            if len(time_apathy_list) < len(self.years):
                time_apathy_list.extend([1.0] * (len(self.years) - len(time_apathy_list)))
            elif len(time_apathy_list) > len(self.years):
                time_apathy_list = time_apathy_list[:len(self.years)]

            # Process yearly data with weighting
            for n, year in enumerate(self.years):
                if year in df_WS.columns:
                    df_WS[year] = pd.to_numeric(df_WS[year], errors='coerce').fillna(0)
                    severity_safe = df_WS['Severity'].replace(0, 1)
                    years_active_safe = df_WS['Years_active'].replace(0, 1)
                    
                    df_WS[year] = (df_WS[year] / severity_safe / years_active_safe * time_apathy_list[n])

            df_WS['Crimes_total'] = df_WS[self.years].sum(axis=1).apply(np.round)
            df_WS['Station'] = df_WS['Station'].astype(str).str.upper()
            self.df_WS_st = df_WS[['Station', 'Crimes_total']].groupby('Station').sum()
            
            print(f"Weighted crime data created for {len(self.df_WS_st)} stations")
            self.processed_data = df_WS
            
        except Exception as e:
            print(f"Error creating weighted crime data: {e}")
            import traceback
            traceback.print_exc()
    
    def get_map_data(self):
        """Get data for the heat map visualization - Fixed version"""
        if self.gdf is None or self.df_WS_st is None:
            print("No geodata or weighted station data available for mapping")
            return None
            
        try:
            # Find station column in shapefile
            station_cols = ['COMPNT_NM', 'STATION', 'NAME', 'Station_Na', 'STATION_N', 'station', 'name']
            station_col = None
            
            print(f"Shapefile columns: {list(self.gdf.columns)}")
            
            for col in station_cols:
                if col in self.gdf.columns:
                    station_col = col
                    break
            
            if station_col is None:
                print("No matching station column found in shapefile")
                print("Available columns:", list(self.gdf.columns))
                # Try to find any column that might contain station names
                for col in self.gdf.columns:
                    if any(keyword in col.lower() for keyword in ['station', 'name', 'compnt']):
                        station_col = col
                        print(f"Trying column: {station_col}")
                        break
                
                if station_col is None:
                    return None
                
            print(f"Using station column: {station_col}")
            
            # Debug data before merge
            print(f"\nDEBUG: Sample shapefile stations:")
            sample_shp_stations = self.gdf[station_col].str.upper().head(5).tolist()
            for station in sample_shp_stations:
                print(f"  SHP: '{station}'")
            
            print(f"\nDEBUG: Sample crime data stations:")
            sample_crime_stations = self.df_WS_st.index[:5].tolist()
            for station in sample_crime_stations:
                print(f"  CRIME: '{station}'")
            
            # Merge with geodata
            gdf_copy = self.gdf.copy()
            gdf_copy[station_col] = gdf_copy[station_col].astype(str).str.upper()
            
            # Create a reset index version of df_WS_st for merging
            df_WS_st_reset = self.df_WS_st.reset_index()
            
            # Merge the data
            merged_gdf = gdf_copy.merge(df_WS_st_reset, left_on=station_col, right_on='Station', how='left')
            
            # Rename the column to match what JavaScript expects
            merged_gdf['Crimes_11years'] = merged_gdf['Crimes_total'].fillna(0)
            
            # Clean up columns
            if 'Crimes_total' in merged_gdf.columns:
                merged_gdf = merged_gdf.drop('Crimes_total', axis=1)
            if 'Station' in merged_gdf.columns:
                merged_gdf = merged_gdf.drop('Station', axis=1)
            
            print(f"Merged data: {len(merged_gdf)} features")
            print(f"Features with crime data: {(merged_gdf['Crimes_11years'] > 0).sum()}")
            print(f"Crime data range: {merged_gdf['Crimes_11years'].min()} - {merged_gdf['Crimes_11years'].max()}")
            
            # Debug: Check for successful matches
            successful_merges = merged_gdf[merged_gdf['Crimes_11years'] > 0]
            print(f"Successful merges: {len(successful_merges)}")
            if len(successful_merges) > 0:
                print("Sample successful merges:")
                for idx, row in successful_merges.head(3).iterrows():
                    print(f"  {row[station_col]}: {row['Crimes_11years']}")
            
            # FIXED: Create GeoJSON using shapely mapping to avoid numpy array issues
            features = []
            
            for _, row in merged_gdf.iterrows():
                if row['geometry'] is not None:
                    try:
                        # Use shapely's mapping function to convert geometry to dict
                        geom_dict = mapping(row['geometry'])
                        
                        # Create properties, converting any numpy/pandas types to native Python types
                        properties = {}
                        for col in merged_gdf.columns:
                            if col != 'geometry':
                                val = row[col]
                                # Convert numpy/pandas types to Python native types
                                if pd.isna(val):
                                    properties[col] = None
                                elif hasattr(val, 'item'):
                                    try:
                                        properties[col] = val.item()
                                    except:
                                        properties[col] = str(val)
                                elif isinstance(val, (np.integer, np.floating)):
                                    properties[col] = val.item()
                                else:
                                    properties[col] = val
                        
                        # Create feature
                        feature = {
                            "type": "Feature",
                            "geometry": geom_dict,
                            "properties": properties
                        }
                        features.append(feature)
                        
                    except Exception as geom_error:
                        print(f"Error processing geometry for feature: {geom_error}")
                        continue
            
            # Create full GeoJSON structure
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            
            print(f"GeoJSON created successfully with {len(features)} features")
            
            return geojson
            
        except Exception as e:
            print(f"Error creating map data: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_province_summary(self, year=None):
        """Get crime summary by province"""
        if self.processed_data is None:
            return {}
            
        try:
            if year and year in self.years:
                year_cols = [year]
            else:
                year_cols = self.years
                
            province_data = self.processed_data.groupby('Province')[year_cols].sum()
            return province_data.to_dict('index')
        except Exception as e:
            print(f"Error getting province summary: {e}")
            return {}
    
    def get_category_summary(self, year=None):
        """Get crime summary by category"""
        if self.processed_data is None:
            return {}
            
        try:
            if year and year in self.years:
                recent_year = year
            else:
                recent_year = self.years[-1] if self.years else None
                
            if recent_year:
                category_data = self.processed_data.groupby('Category')[recent_year].sum().sort_values(ascending=False)
                return category_data.to_dict()
            else:
                return {}
        except Exception as e:
            print(f"Error getting category summary: {e}")
            return {}
    
    def get_category_evolution(self):
        """Get category evolution over time"""
        if self.processed_data is None:
            return {}, []
            
        try:
            category_evolution = self.processed_data.groupby('Category')[self.years].sum()
            return category_evolution.to_dict('records'), list(category_evolution.index)
        except Exception as e:
            print(f"Error getting category evolution: {e}")
            return {}, []
    
    def get_province_evolution(self):
        """Get province evolution over time"""
        if self.processed_data is None:
            return {}, []
            
        try:
            province_evolution = self.processed_data.groupby('Province')[self.years].sum()
            return province_evolution.to_dict('records'), list(province_evolution.index)
        except Exception as e:
            print(f"Error getting province evolution: {e}")
            return {}, []

    def debug_data_merge(self):
        """Debug method to check data merging"""
        if self.gdf is None or self.df_WS_st is None:
            print("Cannot debug: missing geodata or weighted data")
            return
        
        print("\n=== DEBUGGING DATA MERGE ===")
        
        # Check station column
        station_cols = ['COMPNT_NM', 'STATION', 'NAME', 'Station_Na', 'STATION_N', 'station', 'name']
        station_col = None
        
        for col in station_cols:
            if col in self.gdf.columns:
                station_col = col
                break
        
        if station_col is None:
            print("No station column found!")
            return
        
        print(f"Using station column: {station_col}")
        
        # Check sample data
        print(f"\nSample geodata stations:")
        sample_geo_stations = self.gdf[station_col].str.upper().head(10).tolist()
        for station in sample_geo_stations:
            print(f"  - {station}")
        
        print(f"\nSample weighted data stations:")
        sample_weighted_stations = self.df_WS_st.index[:10].tolist()
        for station in sample_weighted_stations:
            print(f"  - {station}")
        
        print(f"\nSample weighted data values:")
        sample_values = self.df_WS_st.head(10)
        for station, row in sample_values.iterrows():
            print(f"  - {station}: {row['Crimes_total']}")
        
        # Check for matches
        geo_stations_upper = set(self.gdf[station_col].str.upper().tolist())
        weighted_stations = set(self.df_WS_st.index.tolist())
        
        matches = geo_stations_upper.intersection(weighted_stations)
        print(f"\nMatching stations: {len(matches)} out of {len(geo_stations_upper)} geo stations")
        
        if len(matches) > 0:
            print("Sample matches:")
            for match in list(matches)[:5]:
                print(f"  - {match}")
        else:
            print("NO MATCHES FOUND!")
            print("This explains why the map has no data!")
        
        print("=== END DEBUG ===\n")

# Initialize data processor
crime_processor = CrimeDataProcessor()

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        if crime_processor.df is None:
            if not crime_processor.load_data():
                return "Error loading data. Please check if the data files exist in C:\\Users\\John\\Desktop\\south_africa_crime_viz\\data", 500
            if not crime_processor.process_crime_data():
                return "Error processing data", 500
        
        # Get current year data
        current_year = crime_processor.years[-1] if crime_processor.years else None
        
        if current_year:
            category_data = crime_processor.get_category_summary(current_year)
            province_data = crime_processor.get_province_summary(current_year)
        else:
            category_data = {}
            province_data = {}
        
        return render_template('index.html', 
                             category_data=category_data,
                             province_data=province_data,
                             current_year=current_year,
                             years=crime_processor.years)
                             
    except Exception as e:
        print(f"Error in index route: {e}")
        import traceback
        traceback.print_exc()
        return f"Application error: {str(e)}", 500

@app.route('/api/map-data')
def map_data():
    """API endpoint for map data with enhanced debugging"""
    try:
        print("=== MAP DATA REQUEST ===")
        print(f"Geodata available: {crime_processor.gdf is not None}")
        print(f"Weighted data available: {crime_processor.df_WS_st is not None}")
        
        if crime_processor.gdf is not None:
            print(f"Geodata shape: {crime_processor.gdf.shape}")
            print(f"Geodata columns: {list(crime_processor.gdf.columns)}")
        
        if crime_processor.df_WS_st is not None:
            print(f"Weighted data shape: {crime_processor.df_WS_st.shape}")
            print(f"Weighted data columns: {list(crime_processor.df_WS_st.columns)}")
            print(f"Sample weighted data:\n{crime_processor.df_WS_st.head()}")
        
        geojson = crime_processor.get_map_data()
        
        if geojson:
            print(f"GeoJSON created successfully")
            print(f"Number of features: {len(geojson.get('features', []))}")
            
            # Log sample feature data
            if geojson.get('features'):
                sample_feature = geojson['features'][0]
                print(f"Sample feature properties: {sample_feature.get('properties', {}).keys()}")
                crimes_11years = sample_feature.get('properties', {}).get('Crimes_11years', 'NOT FOUND')
                print(f"Sample Crimes_11years value: {crimes_11years}")
            
            return jsonify(geojson)
        else:
            print("No geojson data created")
            return jsonify({"error": "No map data available", "details": "GeoJSON creation failed"}), 404
            
    except Exception as e:
        print(f"Error in map-data route: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "details": "Check server logs for more information"}), 500

@app.route('/api/province-data')
@app.route('/api/province-data/<year>')
def province_data_api(year=None):
    """API endpoint for province data"""
    try:
        data = crime_processor.get_province_summary(year)
        return jsonify(data)
    except Exception as e:
        print(f"Error in province-data route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/category-data')
@app.route('/api/category-data/<year>')
def category_data_api(year=None):
    """API endpoint for category data"""
    try:
        data = crime_processor.get_category_summary(year)
        return jsonify(data)
    except Exception as e:
        print(f"Error in category-data route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/category-evolution')
def category_evolution_api():
    """API endpoint for category evolution"""
    try:
        data, categories = crime_processor.get_category_evolution()
        return jsonify({'data': data, 'categories': categories, 'years': crime_processor.years})
    except Exception as e:
        print(f"Error in category-evolution route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/province-evolution')
def province_evolution_api():
    """API endpoint for province evolution"""
    try:
        data, provinces = crime_processor.get_province_evolution()
        return jsonify({'data': data, 'provinces': provinces, 'years': crime_processor.years})
    except Exception as e:
        print(f"Error in province-evolution route: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/province-trends')
def province_trends():
    """Province trends page with Nightingale Rose charts"""
    try:
        return render_template('province_trends.html', years=crime_processor.years)
    except Exception as e:
        print(f"Error in province-trends route: {e}")
        return f"Error loading province trends: {str(e)}", 500

@app.route('/category-analysis')
def category_analysis():
    """Category analysis page"""
    try:
        return render_template('category_analysis.html', years=crime_processor.years)
    except Exception as e:
        print(f"Error in category-analysis route: {e}")
        return f"Error loading category analysis: {str(e)}", 500

@app.route('/evolution-analysis')
def evolution_analysis():
    """Evolution analysis page"""
    try:
        return render_template('evolution_analysis.html', years=crime_processor.years)
    except Exception as e:
        print(f"Error in evolution-analysis route: {e}")
        return f"Error loading evolution analysis: {str(e)}", 500

if __name__ == '__main__':
    # Test data loading on startup
    print("Testing data loading...")
    if crime_processor.load_data():
        if crime_processor.process_crime_data():
            print("Data loaded and processed successfully!")
            # Run debug to check data merging
            crime_processor.debug_data_merge()
        else:
            print("Data loaded but processing failed")
    else:
        print("Failed to load data")
    
    app.run(debug=True, port=5000)