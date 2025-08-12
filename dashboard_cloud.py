import streamlit as st
import gspread
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import json
import joblib
import numpy as np
import os
from google.oauth2.service_account import Credentials

# Page configuration
st.set_page_config(
    page_title="NCAA Football Predictions Dashboard",
    page_icon="🏈",
    layout="wide"
)

# Custom CSS for professional styling
def inject_custom_css():
    st.markdown("""
    <style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Root variables - Football theme colors */
    :root {
        --primary-green: #2E7D32;
        --primary-orange: #F57C00;
        --dark-blue: #1565C0;
        --light-gray: #F5F5F5;
        --dark-gray: #424242;
        --white: #FFFFFF;
        --red: #D32F2F;
        --success-green: #4CAF50;
        --warning-orange: #FF9800;
        --info-blue: #2196F3;
    }
    
    /* Main app styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Custom header */
    .main-header {
        background: linear-gradient(135deg, var(--primary-green) 0%, var(--dark-blue) 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    .main-header h1 {
        color: var(--white);
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
    }
    
    .main-header p {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 500;
    }
    
    /* Football-themed accents */
    .football-accent {
        display: inline-block;
        background: linear-gradient(45deg, #8B4513, #D2691E);
        width: 20px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
        vertical-align: middle;
    }
    </style>
    
    """, unsafe_allow_html=True)

# Load configuration from Streamlit secrets
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
def load_google_sheets_data():
    """Load data from Google Sheets using Streamlit secrets"""
    try:
        config = load_config()
        if not config:
            return pd.DataFrame(), "Configuration not loaded"
        
        # Create credentials from secrets with proper scopes
        creds_dict = dict(st.secrets["google_service_account"])
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        
        # Authenticate with Google Sheets
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(config['sheet_id'])
        
        # Load predictions
        predictions_sheet = spreadsheet.worksheet(config['predictions_tab'])
        predictions_data = predictions_sheet.get_all_records()
        
        if predictions_data:
            predictions_df = pd.DataFrame(predictions_data)
            return predictions_df, None
        else:
            return pd.DataFrame(), "No predictions data found"
            
    except Exception as e:
        return pd.DataFrame(), f"Error loading Google Sheets: {str(e)}"

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        if pd.isna(value) or value == '' or value is None:
            return default
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_str(value, default=""):
    """Safely convert value to string"""
    try:
        if pd.isna(value) or value is None:
            return default
        return str(value)
    except:
        return default

def create_simple_game_card(row):
    """Create a simple game card with bulletproof data handling"""
    # Safely extract all values
    matchup = safe_str(row.get('Matchup', 'Game TBD'))
    my_pred_raw = safe_str(row.get('My Prediction', '0'))
    vegas_raw = safe_str(row.get('Vegas Line', 'N/A'))
    edge_raw = safe_str(row.get('Edge', '0'))
    edge_range = safe_str(row.get('Edge_Range', 'Unknown'))
    
    # Parse teams
    if ' vs ' in matchup:
        teams = matchup.split(' vs ')
        away_team = teams[0].strip() if len(teams) > 0 else 'Away'
        home_team = teams[1].strip() if len(teams) > 1 else 'Home'
    else:
        away_team, home_team = 'Away', 'Home'
    
    # Handle My Prediction 
    my_pred_float = safe_float(my_pred_raw)
    if my_pred_float > 0:
        pred_text = f"{home_team} by {my_pred_float:.1f}"
        pred_color = "#2E7D32"
    elif my_pred_float < 0:
        pred_text = f"{away_team} by {abs(my_pred_float):.1f}"
        pred_color = "#1565C0"
    else:
        pred_text = "Even"
        pred_color = "#666"
    
    # Handle Vegas Line
    vegas_display = vegas_raw if vegas_raw in ['N/A', 'n/a', ''] else vegas_raw
    
    # Handle Edge - extract number from text like "Bet Home (+4.4)"
    if "(" in edge_raw and ")" in edge_raw:
        # Extract number from parentheses
        try:
            start = edge_raw.find("(") + 1
            end = edge_raw.find(")")
            edge_num_str = edge_raw[start:end].replace("+", "").replace(" ", "")
            edge_float = safe_float(edge_num_str)
            edge_display = f"{edge_float:+.1f} points"
        except:
            edge_display = edge_raw
    else:
        edge_float = safe_float(edge_raw)
        edge_display = f"{edge_float:+.1f} points" if edge_float != 0 else "0.0 points"
    
    # Simple card HTML
    st.markdown(f"""
    <div style="
        background: white;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
    ">
        <h4>{away_team} vs {home_team}</h4>
        <p><strong>My Prediction:</strong> {pred_text}</p>
        <p><strong>Vegas Line:</strong> {vegas_display}</p>
        <p><strong>Edge:</strong> {edge_display}</p>
        <p><strong>Raw Edge Data:</strong> {edge_raw}</p>
        <p><strong>Category:</strong> {edge_range}</p>
    </div>
    """, unsafe_allow_html=True)

def show_simple_predictions(predictions_df):
    """Show predictions in a simple, safe format"""
    st.header("🏈 Game Predictions")
    
    if predictions_df.empty:
        st.warning("No predictions data available")
        return
    
    # Show debug info
    with st.expander("🔍 Debug Info"):
        st.write("Columns:", list(predictions_df.columns))
        if not predictions_df.empty:
            st.write("Sample data:")
            st.write(predictions_df.head(1))
    
    # Display games
    st.subheader(f"📊 {len(predictions_df)} Games")
    
    for idx, row in predictions_df.iterrows():
        create_simple_game_card(row)

def main():
    # Apply styling
    inject_custom_css()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1><span class="football-accent"></span>NCAA Football Predictions Dashboard</h1>
        <p>Safe Mode - Basic Display</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load data
    with st.spinner("Loading predictions..."):
        predictions_df, error = load_google_sheets_data()
    
    if error:
        st.error(f"⚠️ {error}")
        return
    
    # Show predictions
    show_simple_predictions(predictions_df)

if __name__ == "__main__":
    main()
