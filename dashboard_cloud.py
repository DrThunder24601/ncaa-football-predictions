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
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: var(--light-gray);
        border-right: 3px solid var(--primary-green);
    }
    
    /* Metric cards */
    [data-testid="metric-container"] {
        background-color: var(--white);
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    }
    
    /* Edge range specific colors */
    .low-edge { border-left: 4px solid #9E9E9E; }
    .mid-edge { border-left: 4px solid var(--info-blue); }
    .high-edge { border-left: 4px solid var(--warning-orange); }
    .extreme-edge { border-left: 4px solid var(--red); }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: var(--light-gray);
        border-radius: 8px;
        padding: 4px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        border-radius: 6px;
        color: var(--dark-gray);
        font-weight: 500;
        font-family: 'Inter', sans-serif;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--primary-green) !important;
        color: var(--white) !important;
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
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

def get_edge_color_and_icon(edge_value):
    """Get color and icon based on edge value"""
    try:
        abs_edge = abs(float(edge_value))
        
        if abs_edge <= 1.5:
            return "#9E9E9E", "⚪", "Low"
        elif abs_edge <= 3.0:
            return "#2196F3", "🔵", "Mid"
        elif abs_edge <= 5.0:
            return "#FF9800", "🟡", "High"
        elif abs_edge <= 8.0:
            return "#D32F2F", "🔴", "V.High"
        else:
            return "#AD1457", "🟣", "Extreme"
    except:
        return "#999", "⚪", "Unknown"

def get_confidence_bar(edge_value):
    """Generate confidence bar HTML based on edge value"""
    try:
        abs_edge = abs(float(edge_value))
        confidence = min(abs_edge * 15, 100)  # 0-1.5 = 0-22%, 3+ = 45%+
        color = "#4CAF50" if confidence > 60 else "#FF9800" if confidence > 30 else "#9E9E9E"
        
        return f"""
        <div style="background: #f0f0f0; border-radius: 10px; height: 6px; margin: 5px 0;">
            <div style="background: {color}; height: 6px; border-radius: 10px; width: {confidence}%;"></div>
        </div>
        <small style="color: #666;">Confidence: {confidence:.0f}%</small>
        """
    except:
        return '<small style="color: #666;">Confidence: 0%</small>'

def create_simple_game_card(row):
    """Create a game card using Streamlit native components"""
    # Safely extract all values
    matchup = safe_str(row.get('Matchup', 'Game TBD'))
    my_pred_raw = safe_str(row.get('My Prediction', '0'))
    vegas_raw = safe_str(row.get('Vegas Line', 'N/A'))
    edge_raw = safe_str(row.get('Edge', '0'))
    
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
    elif my_pred_float < 0:
        pred_text = f"{away_team} by {abs(my_pred_float):.1f}"
    else:
        pred_text = "Even"
    
    # Handle Vegas Line
    vegas_display = vegas_raw if vegas_raw in ['N/A', 'n/a', ''] else vegas_raw
    
    # Handle Edge - extract number from text like "Bet Home (+4.4)"
    if "(" in edge_raw and ")" in edge_raw:
        try:
            start = edge_raw.find("(") + 1
            end = edge_raw.find(")")
            edge_num_str = edge_raw[start:end].replace("+", "").replace(" ", "")
            edge_float = safe_float(edge_num_str)
            edge_display = f"{edge_float:+.1f} points"
        except:
            edge_display = edge_raw
            edge_float = 0
    else:
        edge_float = safe_float(edge_raw)
        edge_display = f"{edge_float:+.1f} points" if edge_float != 0 else "0.0 points"
    
    # Get edge category
    abs_edge = abs(edge_float)
    if abs_edge >= 5.0:
        edge_category = "🔴 Extreme"
        edge_color = "red"
    elif abs_edge >= 3.0:
        edge_category = "🟡 High"
        edge_color = "orange"
    elif abs_edge >= 1.5:
        edge_category = "🔵 Mid"
        edge_color = "blue"
    else:
        edge_category = "⚪ Low"
        edge_color = "gray"
    
    # Create card using Streamlit components
    with st.container():
        # Header with edge indicator
        col_title, col_edge = st.columns([3, 1])
        with col_title:
            st.subheader(f"{away_team} vs {home_team}")
            st.caption(edge_raw)
        with col_edge:
            if edge_color == "red":
                st.error(edge_category)
            elif edge_color == "orange":
                st.warning(edge_category)
            elif edge_color == "blue":
                st.info(edge_category)
            else:
                st.info(edge_category)
        
        # Predictions section
        col1, col2 = st.columns(2)
        with col1:
            st.metric("My Prediction", pred_text)
        with col2:
            st.metric("Vegas Line", vegas_display)
        
        # Edge info
        st.metric("Edge", edge_display)
        
        # Add some spacing
        st.markdown("---")

def display_games_as_cards(df):
    """Display games as interactive cards in 2-column layout"""
    if df.empty:
        st.info("No games to display")
        return
    
    # Display cards in rows of 2
    for i in range(0, len(df), 2):
        col1, col2 = st.columns(2)
        
        # First card
        with col1:
            if i < len(df):
                create_simple_game_card(df.iloc[i])
        
        # Second card
        with col2:
            if i + 1 < len(df):
                create_simple_game_card(df.iloc[i + 1])

def show_enhanced_predictions(predictions_df):
    """Show predictions with enhanced features"""
    st.header("🏈 NCAA Football Predictions Dashboard")
    
    if predictions_df.empty:
        st.warning("No predictions data available")
        return
    
    # Add filters
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Extract unique teams from Matchup column
        if 'Matchup' in predictions_df.columns:
            all_teams = []
            for matchup in predictions_df['Matchup'].dropna():
                if ' vs ' in str(matchup):
                    teams = str(matchup).split(' vs ')
                    all_teams.extend([team.strip() for team in teams])
            unique_teams = sorted(set(all_teams))
            selected_team = st.selectbox("Filter by Team", ["All Teams"] + unique_teams)
        else:
            selected_team = "All Teams"
    
    with col2:
        # Edge range filter based on calculated values
        edge_options = ["All Edges", "High Edge (3+)", "Mid Edge (1.5-3)", "Low Edge (0-1.5)"]
        selected_edge = st.selectbox("Filter by Edge", edge_options)
    
    with col3:
        sort_options = ["Default", "Highest Edge", "Lowest Edge", "Alphabetical"]
        sort_by = st.selectbox("Sort by", sort_options)
    
    # Filter data
    filtered_df = predictions_df.copy()
    
    # Team filter
    if selected_team != "All Teams":
        if 'Matchup' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Matchup'].str.contains(selected_team, na=False)]
    
    # Edge filter
    if selected_edge != "All Edges":
        def filter_by_edge(row):
            edge_raw = str(row.get('Edge', ''))
            try:
                if "(" in edge_raw and ")" in edge_raw:
                    start = edge_raw.find("(") + 1
                    end = edge_raw.find(")")
                    edge_num_str = edge_raw[start:end].replace("+", "").replace(" ", "")
                    edge_val = abs(float(edge_num_str))
                else:
                    edge_val = abs(float(edge_raw))
                
                if selected_edge == "High Edge (3+)" and edge_val >= 3.0:
                    return True
                elif selected_edge == "Mid Edge (1.5-3)" and 1.5 <= edge_val < 3.0:
                    return True
                elif selected_edge == "Low Edge (0-1.5)" and edge_val < 1.5:
                    return True
                return False
            except:
                return False
        
        filtered_df = filtered_df[filtered_df.apply(filter_by_edge, axis=1)]
    
    # Show debug info
    with st.expander("🔍 Debug Info"):
        st.write("Columns:", list(predictions_df.columns))
        if not predictions_df.empty:
            st.write("Sample data:")
            st.write(predictions_df.head(1))
        st.write(f"Showing {len(filtered_df)} of {len(predictions_df)} games")
    
    # Display summary
    st.info(f"📊 Showing {len(filtered_df)} games")
    
    # Display games as cards
    if not filtered_df.empty:
        display_games_as_cards(filtered_df)
    else:
        st.warning("No games match the current filters")

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
    
    # Show enhanced predictions with fancy features
    show_enhanced_predictions(predictions_df)

if __name__ == "__main__":
    main()
