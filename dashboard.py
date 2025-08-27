import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import joblib
import numpy as np
import os
import time
import requests
import tempfile
import re
from google.oauth2.service_account import Credentials

# Google Drive file ID for RF_Deep model
GDRIVE_FILE_ID = "1YTULpDvgtFombMsyUgrdRDuUAoZQGKmE"
MODEL_FILENAME = "rf_deep_model.joblib"

@st.cache_data
def download_model_from_gdrive(file_id, output_path):
    """Download model from Google Drive handling virus scan warning"""
    
    with st.spinner("🔄 Downloading RF_Deep model from Google Drive..."):
        try:
            session = requests.Session()
            
            # Step 1: Get the initial page with virus warning
            st.write("📄 Getting download page...")
            initial_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            response = session.get(initial_url)
            
            if response.status_code != 200:
                st.error(f"Failed to access Google Drive. Status: {response.status_code}")
                return False
            
            # Step 2: Extract UUID from the virus scan warning page
            st.write("🔍 Extracting download parameters...")
            uuid_match = re.search(r'name="uuid" value="([^"]+)"', response.text)
            
            if not uuid_match:
                st.error("Could not extract download UUID from Google Drive response")
                return False
            
            uuid = uuid_match.group(1)
            st.write(f"✅ Found UUID: {uuid[:8]}...")
            
            # Step 3: Make the actual download request
            st.write("⬇️ Starting model download...")
            download_url = "https://drive.usercontent.google.com/download"
            params = {
                'id': file_id,
                'export': 'download', 
                'confirm': 't',
                'uuid': uuid
            }
            
            download_response = session.get(download_url, params=params, stream=True)
            
            if download_response.status_code != 200:
                st.error(f"Download failed. Status: {download_response.status_code}")
                return False
            
            # Step 4: Download file in chunks with progress
            progress_bar = st.progress(0)
            progress_text = st.empty()
            
            total_size = int(download_response.headers.get('content-length', 0))
            downloaded_size = 0
            
            with open(output_path, 'wb') as f:
                for chunk in download_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        if total_size > 0:
                            progress = downloaded_size / total_size
                            progress_bar.progress(progress)
                            progress_text.text(f"Downloaded: {downloaded_size/(1024*1024):.1f} MB / {total_size/(1024*1024):.1f} MB")
                        else:
                            progress_text.text(f"Downloaded: {downloaded_size/(1024*1024):.1f} MB")
            
            # Step 5: Validate the downloaded file
            st.write("✅ Download complete! Validating model...")
            
            try:
                import joblib
                test_model = joblib.load(output_path)
                st.success(f"🎉 Model validated successfully! Type: {type(test_model).__name__}")
                return True
                
            except Exception as e:
                st.error(f"Downloaded file is not a valid model: {str(e)}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return False
                
        except Exception as e:
            st.error(f"Download failed: {str(e)}")
            return False

@st.cache_resource
def load_rf_deep_model():
    """Load RF_Deep model, downloading from Google Drive if necessary"""
    
    # Check if model exists locally first
    local_model_path = "./models/rf_deep_model.joblib"
    temp_model_path = os.path.join(tempfile.gettempdir(), MODEL_FILENAME)
    
    model_path = None
    
    # Try local path first
    if os.path.exists(local_model_path):
        model_path = local_model_path
        st.success("Using local RF_Deep model")
    
    # Try temp directory
    elif os.path.exists(temp_model_path):
        model_path = temp_model_path
        st.info("Using previously downloaded RF_Deep model")
    
    # Download from Google Drive
    else:
        st.info("Downloading RF_Deep model from Google Drive...")
        if download_model_from_gdrive(GDRIVE_FILE_ID, temp_model_path):
            model_path = temp_model_path
            st.success("RF_Deep model downloaded successfully!")
        else:
            st.error("Failed to download model from Google Drive")
            return None
    
    # Load the model
    try:
        model = joblib.load(model_path)
        return model
    except Exception as e:
        st.error(f"Error loading model: {str(e)}")
        return None

@st.cache_data
def load_config():
    """Load configuration from Streamlit secrets"""
    try:
        return {
            'sheet_id': st.secrets["sheets"]["sheet_id"],
            'schedule_tab': st.secrets["sheets"]["schedule_tab"],
            'predictions_tab': st.secrets["sheets"]["predictions_tab"],
            'cfbd_api_key': st.secrets["apis"]["cfbd_api_key"],
            'odds_api_key': st.secrets["apis"]["odds_api_key"]
        }
    except Exception as e:
        st.error(f"Configuration error: {e}")
        return None

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_google_sheets_data_with_retry(max_retries=3):
    """Load data from Google Sheets with retry logic"""
    config = load_config()
    if not config:
        return pd.DataFrame(), "Configuration not available", False

    for attempt in range(max_retries):
        try:
            # Google Sheets authentication
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds_dict = dict(st.secrets["google_service_account"])
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            gc = gspread.authorize(creds)
            
            # Open spreadsheet and get predictions data
            spreadsheet = gc.open_by_key(config['sheet_id'])
            predictions_sheet = spreadsheet.worksheet(config['predictions_tab'])
            predictions_data = predictions_sheet.get_all_records()
            
            if not predictions_data:
                return pd.DataFrame(), "No data found in predictions sheet", False
                
            df = pd.DataFrame(predictions_data)
            
            # Clean and process the data
            if not df.empty:
                # Convert Week column to numeric
                if 'Week' in df.columns:
                    df['Week'] = pd.to_numeric(df['Week'], errors='coerce')
                
                # Remove rows with missing essential data
                df = df.dropna(subset=['Week', 'Matchup'])
                
            return df, None, True
            
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                error_msg = f"Failed to load Google Sheets data after {max_retries} attempts: {str(e)}"
                return pd.DataFrame(), error_msg, False

def show_enhanced_predictions(predictions_df):
    """Show enhanced predictions with Week 1 focus"""
    
    if predictions_df.empty:
        st.warning("No predictions data available")
        return
    
    # Debug: Show available weeks
    if 'Week' in predictions_df.columns:
        available_weeks = sorted(predictions_df['Week'].dropna().unique())
        st.write(f"Debug - Available weeks in data: {available_weeks}")
    
    # Week filter - FIXED LOGIC FOR WEEK 1
    if not predictions_df.empty and 'Week' in predictions_df.columns:
        available_weeks = sorted(predictions_df['Week'].dropna().unique(), reverse=True)
        week_options = ["Latest Week"] + [f"Week {w}" for w in available_weeks]
        selected_week_option = st.selectbox("Week", week_options)
        
        # Apply week filter
        if selected_week_option == "Latest Week":
            # FIXED: Force Week 1 as current week (not highest week number)
            current_week = 1
            filtered_df = predictions_df[predictions_df['Week'] == current_week]
            st.info(f"Showing Week {current_week} games (Latest Week)")
        else:
            # Extract week number from selection
            week_num = int(selected_week_option.split()[-1])
            filtered_df = predictions_df[predictions_df['Week'] == week_num]
            st.info(f"Showing Week {week_num} games")
    else:
        filtered_df = predictions_df
        st.info("Showing all available games")
    
    # Debug: Show filtered results
    st.write(f"Debug - Games after week filter: {len(filtered_df)}")
    if not filtered_df.empty and 'Matchup' in filtered_df.columns:
        st.write(f"Debug - Sample matchups: {list(filtered_df['Matchup'].head(3))}")
    
    # Display games
    if not filtered_df.empty:
        st.subheader(f"🏈 Games ({len(filtered_df)} games)")
        
        # Simple game display
        for idx, row in filtered_df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**{row.get('Matchup', 'Unknown')}**")
                
                with col2:
                    if 'Predicted Spread' in row:
                        st.write(f"Spread: {row['Predicted Spread']}")
                
                with col3:
                    if 'Week' in row:
                        st.write(f"Week {row['Week']}")
                
                st.divider()
    else:
        st.warning(f"No games found for the selected filters")

def main():
    st.set_page_config(
        page_title="NCAA Predictions Dashboard",
        page_icon="🏈",
        layout="wide"
    )
    
    st.title("🏈 NCAA Football Predictions Dashboard")
    st.write("Powered by RF_Deep Random Forest Model with Google Drive Integration")
    
    # Load the model
    model = load_rf_deep_model()
    
    if model is None:
        st.error("Could not load RF_Deep model. Please check the Google Drive link.")
        st.stop()
    
    st.success("✅ RF_Deep model loaded successfully!")
    
    # Create tabs
    tab1, tab2 = st.tabs(["🏈 Live Predictions", "📊 Model Analysis"])
    
    with tab1:
        with st.spinner("Loading predictions..."):
            predictions_df, error, success = load_google_sheets_data_with_retry(max_retries=3)
        
        if not success and error:
            st.error(f"Error loading data: {error}")
            if st.button("🔄 Retry"):
                st.cache_data.clear()
                st.rerun()
            return
        elif predictions_df.empty:
            st.info("📭 No predictions available yet")
            st.write("Predictions will appear here once games are loaded.")
            if st.button("🔄 Retry"):
                st.cache_data.clear()
                st.rerun()
            return
        else:
            show_enhanced_predictions(predictions_df)
    
    with tab2:
        st.subheader("Model Information")
        if hasattr(model, 'feature_importances_'):
            st.write(f"Number of features: {len(model.feature_importances_)}")
            
            # Show top feature importances
            if len(model.feature_importances_) > 0:
                st.subheader("Top Feature Importances")
                
                # Create feature names (we don't know the actual names without the training data)
                feature_names = [f"Feature_{i+1}" for i in range(len(model.feature_importances_))]
                
                # Create DataFrame for feature importances
                importance_df = pd.DataFrame({
                    'Feature': feature_names,
                    'Importance': model.feature_importances_
                }).sort_values('Importance', ascending=False)
                
                # Display top 10 features
                st.dataframe(importance_df.head(10))

if __name__ == "__main__":
    main()