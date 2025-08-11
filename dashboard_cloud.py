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
    
    .css-1d391kg .css-10trblm {
        color: var(--dark-gray);
        font-weight: 600;
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
    
    /* Dataframe styling */
    .stDataFrame {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    }
    
    /* Info/warning/error styling */
    .stAlert {
        border-radius: 8px;
        border: none;
        font-family: 'Inter', sans-serif;
    }
    
    .stAlert[data-baseweb="notification"] {
        background-color: var(--info-blue);
        color: var(--white);
    }
    
    /* Button styling */
    .stSelectbox > div > div {
        border-radius: 6px;
        border: 2px solid #e0e0e0;
        background-color: var(--white);
        font-family: 'Inter', sans-serif;
    }
    
    .stSelectbox > div > div:focus-within {
        border-color: var(--primary-green);
        box-shadow: 0 0 0 2px rgba(46, 125, 50, 0.2);
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
    
    /* Responsive improvements */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .main-header p {
            font-size: 1rem;
        }
        
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Custom scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: var(--light-gray);
    }
    
    ::-webkit-scrollbar-thumb {
        background: var(--primary-green);
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: var(--dark-blue);
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

@st.cache_data
def load_model_info():
    """Load model features and metrics"""
    try:
        # Load key features for 4-feature Linear Regression
        key_features = [
            "off_eff_diff (Offensive Efficiency Difference)",
            "def_eff_diff (Defensive Efficiency Difference)", 
            "is_home_favorite (Home Team Favorability)",
            "vegas_line (Vegas Betting Line)"
        ]
        
        # Model metrics
        metrics_info = {
            "Model Type": "4-Feature Linear Regression",
            "Training Date": "Production Model",
            "Test MAE": "1.5 points",
            "Performance": "Excellent",
            "Features": "Minimal, Focused Set"
        }
        
        return key_features, metrics_info
        
    except Exception as e:
        return [], {"Error": f"Could not load model info: {str(e)}"}

def classify_edge_range(edge_value):
    """Classify edge into ranges for performance analysis"""
    if pd.isna(edge_value):
        return "Unknown"
    
    abs_edge = abs(edge_value)
    
    if abs_edge <= 1.5:
        return "Low Edge (0-1.5)"
    elif abs_edge <= 3.0:
        return "Mid Edge (1.5-3)"
    elif abs_edge <= 5.0:
        return "High Edge (3-5)"
    elif abs_edge <= 8.0:
        return "Very High Edge (5-8)"
    else:
        return "Extreme Edge (8+)"

def add_edge_analysis(predictions_df):
    """Add edge calculations and classifications to predictions dataframe"""
    if predictions_df.empty:
        return predictions_df
    
    # Make a copy to avoid modifying original
    df = predictions_df.copy()
    
    # Calculate edge if not already present
    if 'My Prediction' in df.columns and 'Vegas Line' in df.columns:
        try:
            my_pred = pd.to_numeric(df['My Prediction'], errors='coerce').fillna(0)
            vegas_line = pd.to_numeric(df['Vegas Line'], errors='coerce').fillna(0)
            df['Edge'] = my_pred - vegas_line
            df['Abs_Edge'] = abs(df['Edge'])
        except:
            df['Edge'] = 0
            df['Abs_Edge'] = 0
    elif 'Edge' not in df.columns:
        df['Edge'] = 0
        df['Abs_Edge'] = 0
    
    # Add edge range classification
    df['Edge_Range'] = df['Edge'].apply(classify_edge_range)
    
    # Add edge direction
    df['Edge_Direction'] = df['Edge'].apply(
        lambda x: "Favor Home" if x > 0 else "Favor Away" if x < 0 else "Even"
    )
    
    return df

def get_edge_color_and_icon(edge_value):
    """Get color and icon based on edge value"""
    if pd.isna(edge_value):
        return "#999", "⚪", "Unknown"
    
    abs_edge = abs(edge_value)
    
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

def get_confidence_bar(edge_value):
    """Generate confidence bar HTML based on edge value"""
    abs_edge = abs(edge_value) if not pd.isna(edge_value) else 0
    
    # Scale confidence (0-100%) based on absolute edge
    confidence = min(abs_edge * 15, 100)  # 0-1.5 = 0-22%, 3+ = 45%+
    
    color = "#4CAF50" if confidence > 60 else "#FF9800" if confidence > 30 else "#9E9E9E"
    
    return f"""
    <div style="background: #f0f0f0; border-radius: 10px; height: 6px; margin: 5px 0;">
        <div style="background: {color}; height: 6px; border-radius: 10px; width: {confidence}%;"></div>
    </div>
    <small style="color: #666;">Confidence: {confidence:.0f}%</small>
    """

def display_games_as_cards(df):
    """Display games as interactive cards"""
    if df.empty:
        st.info("No games to display")
        return
    
    # Display cards in rows of 2
    for i in range(0, len(df), 2):
        col1, col2 = st.columns(2)
        
        # First card
        with col1:
            if i < len(df):
                create_game_card(df.iloc[i])
        
        # Second card
        with col2:
            if i + 1 < len(df):
                create_game_card(df.iloc[i + 1])

def create_game_card(row):
    """Create an individual game prediction card"""
    # Extract teams from Matchup field (format: "Away @ Home")
    matchup = row.get('Matchup', 'Away @ Home')
    if '@' in matchup:
        teams = matchup.split(' @ ')
        away_team = teams[0].strip() if len(teams) > 0 else 'Away'
        home_team = teams[1].strip() if len(teams) > 1 else 'Home'
    else:
        # Fallback if format is different
        away_team = 'Away'
        home_team = 'Home'
    
    # Extract and ensure numeric data
    try:
        my_prediction = float(pd.to_numeric(row.get('My Prediction', 0), errors='coerce'))
        if pd.isna(my_prediction):
            my_prediction = 0.0
    except:
        my_prediction = 0.0
        
    try:
        vegas_line = float(pd.to_numeric(row.get('Vegas Line', 0), errors='coerce'))
        if pd.isna(vegas_line):
            vegas_line = 0.0
    except:
        vegas_line = 0.0
        
    try:
        edge = float(pd.to_numeric(row.get('Edge', 0), errors='coerce'))
        if pd.isna(edge):
            edge = 0.0
    except:
        edge = 0.0
        
    edge_range = row.get('Edge_Range', 'Unknown')
    edge_direction = row.get('Edge_Direction', 'Even')
    
    # Get styling based on edge
    edge_color, edge_icon, edge_label = get_edge_color_and_icon(edge)
    confidence_bar = get_confidence_bar(edge)
    
    # Determine prediction direction (my_prediction is already float)
    if my_prediction > 0:
        prediction_text = f"{home_team} by {abs(my_prediction):.1f}"
        prediction_color = "#2E7D32"
    elif my_prediction < 0:
        prediction_text = f"{away_team} by {abs(my_prediction):.1f}"
        prediction_color = "#1565C0"
    else:
        prediction_text = "Even"
        prediction_color = "#666"
    
    # Create the card
    card_html = f"""
    <div style="
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        border-left: 4px solid {edge_color};
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        position: relative;
    " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(0, 0, 0, 0.15)'"
       onmouseout="this.style.transform='translateY(0px)'; this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.1)'">
        
        <!-- Edge indicator -->
        <div style="position: absolute; top: 10px; right: 15px; background: {edge_color}; color: white; 
                    padding: 4px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: 600;">
            {edge_icon} {edge_label}
        </div>
        
        <!-- Teams -->
        <div style="margin-bottom: 1rem;">
            <h3 style="margin: 0; color: #333; font-size: 1.2rem; font-weight: 600;">
                {away_team} @ {home_team}
            </h3>
            <p style="margin: 0.3rem 0 0 0; color: #666; font-size: 0.9rem;">
                {edge_range} • {edge_direction}
            </p>
        </div>
        
        <!-- Predictions -->
        <div style="display: flex; justify-content: space-between; margin-bottom: 1rem;">
            <div style="text-align: center; flex: 1;">
                <p style="margin: 0; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">My Prediction</p>
                <p style="margin: 0.2rem 0 0 0; font-size: 1.3rem; font-weight: 700; color: {prediction_color};">
                    {prediction_text}
                </p>
            </div>
            
            <div style="width: 1px; background: #e0e0e0; margin: 0 1rem;"></div>
            
            <div style="text-align: center; flex: 1;">
                <p style="margin: 0; font-size: 0.8rem; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">Vegas Line</p>
                <p style="margin: 0.2rem 0 0 0; font-size: 1.1rem; font-weight: 600; color: #333;">
                    {vegas_line:+.1f}
                </p>
            </div>
        </div>
        
        <!-- Edge info -->
        <div style="background: #f8f9fa; padding: 0.8rem; border-radius: 8px; margin-bottom: 0.8rem;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 0.8rem; color: #666;">Edge:</span>
                <span style="font-size: 1rem; font-weight: 600; color: {edge_color};">
                    {edge:+.1f} points
                </span>
            </div>
        </div>
        
        <!-- Confidence indicator -->
        <div>
            {confidence_bar}
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)

def show_predictions_tab(predictions_df, key_features, metrics_info):
    """Show the Live Predictions tab"""
    # Sidebar
    st.sidebar.header("📊 Model Information")
    
    st.sidebar.subheader("Key Features (4-Feature Linear Regression)")
    for feature in key_features:
        st.sidebar.text(f"• {feature}")
    
    st.sidebar.subheader("Model Performance")
    for key, value in metrics_info.items():
        st.sidebar.text(f"{key}: {value}")
    
    # Edge range legend
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Edge Range Categories")
    
    st.sidebar.markdown("**Week 1+:** Collect performance data")
    st.sidebar.markdown("**Low Edge (0-1.5):** Small differences")
    st.sidebar.markdown("**Mid Edge (1.5-3):** Moderate differences") 
    st.sidebar.markdown("**High Edge (3-5):** Large differences")
    st.sidebar.markdown("**Very High/Extreme:** Major differences")
    
    st.sidebar.markdown("---")
    st.sidebar.info("Data refreshes every 5 minutes")
    
    # Add edge analysis to predictions
    if not predictions_df.empty:
        predictions_df = add_edge_analysis(predictions_df)
    
    # Display current predictions
    st.header("📈 Current Week Predictions with Edge Analysis")
    
    # Add filters if we have data
    if not predictions_df.empty:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            # Extract unique teams from Matchup column
            if 'Matchup' in predictions_df.columns:
                all_teams = []
                for matchup in predictions_df['Matchup'].dropna():
                    if '@' in str(matchup):
                        teams = str(matchup).split(' @ ')
                        all_teams.extend([team.strip() for team in teams])
                unique_teams = sorted(set(all_teams))
                selected_team = st.selectbox("Filter by Team", ["All Teams"] + unique_teams)
            else:
                selected_team = "All Teams"
        
        with col2:
            # Edge range filter
            if 'Edge_Range' in predictions_df.columns:
                edge_ranges = ["All Ranges"] + list(predictions_df['Edge_Range'].unique())
                selected_edge_range = st.selectbox("Filter by Edge Range", edge_ranges)
            else:
                selected_edge_range = "All Ranges"
        
        with col3:
            # Enhanced sorting options for edge analysis
            sort_options = [
                "Low to High Edge",
                "Biggest Edge (Abs)",
                "My Favors Most", 
                "Vegas Favors Most", 
                "Alphabetical",
                "Default"
            ]
            sort_by = st.selectbox("Sort by", sort_options)
    
        # Filter and display data with proper sorting
        filtered_df = predictions_df.copy()
        
        if selected_team != "All Teams":
            if 'Matchup' in filtered_df.columns:
                # Filter by checking if team name appears in Matchup
                filtered_df = filtered_df[
                    filtered_df['Matchup'].str.contains(selected_team, na=False)
                ]
        
        # Filter by edge range
        if selected_edge_range != "All Ranges" and 'Edge_Range' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Edge_Range'] == selected_edge_range]
        
        # Apply sorting
        if not filtered_df.empty and sort_by != "Default":
            try:
                # Define edge range priority for sorting
                edge_range_priority = {
                    "Low Edge (0-1.5)": 1,
                    "Mid Edge (1.5-3)": 2,
                    "High Edge (3-5)": 3,
                    "Very High Edge (5-8)": 4,
                    "Extreme Edge (8+)": 5,
                    "Unknown": 6
                }
                
                # Apply sorting based on selection
                if sort_by == "Low to High Edge":
                    # Sort from smallest to largest edge ranges
                    if 'Edge_Range' in filtered_df.columns:
                        filtered_df['Range_Priority'] = filtered_df['Edge_Range'].map(edge_range_priority)
                        filtered_df = filtered_df.sort_values(['Range_Priority', 'Abs_Edge'], ascending=[True, True])
                        
                elif sort_by == "Biggest Edge (Abs)":
                    filtered_df = filtered_df.sort_values('Abs_Edge', ascending=False)
                    
                elif sort_by == "My Favors Most":
                    filtered_df = filtered_df.sort_values('Edge', ascending=False) 
                    
                elif sort_by == "Vegas Favors Most":
                    filtered_df = filtered_df.sort_values('Edge', ascending=True)
                    
                elif sort_by == "Alphabetical":
                    if 'Matchup' in filtered_df.columns:
                        filtered_df = filtered_df.sort_values('Matchup')
                            
            except Exception as e:
                st.warning(f"Sorting failed: {str(e)}")
        
        # Display predictions table
        if not filtered_df.empty:
            # Display edge range summary with enhanced styling
            if 'Edge_Range' in filtered_df.columns:
                st.markdown("### 🎯 Edge Distribution")
                col1, col2, col3, col4 = st.columns(4)
                edge_counts = filtered_df['Edge_Range'].value_counts()
                
                with col1:
                    low_count = edge_counts.get("Low Edge (0-1.5)", 0)
                    st.markdown("""
                    <div class="low-edge" style="padding: 1rem; border-radius: 8px; background: white; margin-bottom: 1rem;">
                        <h4 style="margin: 0; color: #666;">⚪ Low Edge</h4>
                        <h2 style="margin: 0.5rem 0 0 0; color: #333;">{}</h2>
                        <p style="margin: 0; font-size: 0.9rem; color: #888;">0-1.5 points</p>
                    </div>
                    """.format(low_count), unsafe_allow_html=True)
                    
                with col2:
                    mid_count = edge_counts.get("Mid Edge (1.5-3)", 0)
                    st.markdown("""
                    <div class="mid-edge" style="padding: 1rem; border-radius: 8px; background: white; margin-bottom: 1rem;">
                        <h4 style="margin: 0; color: #2196F3;">🔵 Mid Edge</h4>
                        <h2 style="margin: 0.5rem 0 0 0; color: #333;">{}</h2>
                        <p style="margin: 0; font-size: 0.9rem; color: #888;">1.5-3 points</p>
                    </div>
                    """.format(mid_count), unsafe_allow_html=True)
                    
                with col3:
                    high_count = edge_counts.get("High Edge (3-5)", 0)
                    st.markdown("""
                    <div class="high-edge" style="padding: 1rem; border-radius: 8px; background: white; margin-bottom: 1rem;">
                        <h4 style="margin: 0; color: #FF9800;">🟡 High Edge</h4>
                        <h2 style="margin: 0.5rem 0 0 0; color: #333;">{}</h2>
                        <p style="margin: 0; font-size: 0.9rem; color: #888;">3-5 points</p>
                    </div>
                    """.format(high_count), unsafe_allow_html=True)
                    
                with col4:
                    very_high_extreme_count = (edge_counts.get("Very High Edge (5-8)", 0) + 
                                             edge_counts.get("Extreme Edge (8+)", 0))
                    st.markdown("""
                    <div class="extreme-edge" style="padding: 1rem; border-radius: 8px; background: white; margin-bottom: 1rem;">
                        <h4 style="margin: 0; color: #D32F2F;">🔴 Extreme</h4>
                        <h2 style="margin: 0.5rem 0 0 0; color: #333;">{}</h2>
                        <p style="margin: 0; font-size: 0.9rem; color: #888;">5+ points</p>
                    </div>
                    """.format(very_high_extreme_count), unsafe_allow_html=True)
            
            # Clean up columns for better display
            display_df = filtered_df.copy()
            
            # Add info about current sort and filters
            filter_info = []
            if sort_by != "Default":
                filter_info.append(f"Sorted by: {sort_by}")
            if selected_edge_range != "All Ranges":
                filter_info.append(f"Edge Range: {selected_edge_range}")
            if selected_team != "All Teams":
                filter_info.append(f"Team: {selected_team}")
                
            if filter_info:
                st.info(f"📊 {len(display_df)} games | " + " | ".join(filter_info))
            else:
                st.info(f"📊 Showing {len(display_df)} total predictions")
            
            # Remove helper columns from display
            columns_to_hide = ['Range_Priority', 'Abs_Edge']
            for col in columns_to_hide:
                if col in display_df.columns:
                    display_df = display_df.drop(columns=[col])
            
            # Round numeric columns
            numeric_columns = display_df.select_dtypes(include=['number']).columns
            for col in numeric_columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce').round(2)
            
            # Display games as interactive cards instead of table
            st.markdown("### 🏈 Game Predictions")
            
            # Show table toggle and debug info
            col1, col2 = st.columns([3, 1])
            with col2:
                show_table = st.checkbox("Show as table", value=False)
            
            # Debug: Show column names to help troubleshoot
            with st.expander("🔍 Debug Info (Column Names)"):
                st.write("Available columns in your data:")
                st.write(list(display_df.columns))
            
            if show_table:
                # Traditional table view
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            else:
                # Card-based view
                display_games_as_cards(display_df)
        else:
            st.warning("🔍 No predictions match the current filters")
    else:
        st.warning("📭 No predictions data available")

def show_model_analysis_tab():
    """Show the Model Analysis tab - simplified for cloud"""
    st.header("🔬 Model Analysis")
    
    st.subheader("📊 Production Model: Linear Regression")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Model Type", "Linear Regression")
    with col2:
        st.metric("Features", "4-Feature System")
    with col3:
        st.metric("Training MAE", "1.5 points")
    
    st.markdown("---")
    
    st.markdown("""
    ### 🎯 Model Features
    
    1. **Offensive Efficiency Difference**: Home vs Away offensive performance
    2. **Defensive Efficiency Difference**: Home vs Away defensive performance  
    3. **Home Favorite Indicator**: Binary indicator if home team is favored
    4. **Vegas Line**: Current betting line for comparison
    
    ### 📈 Performance
    - **Training MAE**: 1.5 points (excellent for college football)
    - **Model Type**: Linear Regression (simple, reliable)
    - **Feature Count**: Minimal 4-feature system
    
    ### 🔍 Edge Range Analysis
    After Week 1, this section will show which edge ranges actually perform best in practice.
    """)

def main():
    # Apply custom CSS styling
    inject_custom_css()
    
    # Custom professional header
    st.markdown("""
    <div class="main-header">
        <h1><span class="football-accent"></span>NCAA Football Predictions Dashboard</h1>
        <p>Powered by 4-Feature Linear Regression Model | 1.5 MAE Performance | Live Data Integration</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check if secrets are configured
    try:
        config = load_config()
        if not config:
            st.error("⚠️ Dashboard not properly configured. Please contact administrator.")
            return
    except:
        st.error("⚠️ Configuration error. Please contact administrator.")
        return
    
    # Load data
    with st.spinner("Loading predictions from Google Sheets..."):
        predictions_df, error = load_google_sheets_data()
    
    # Load model info
    key_features, metrics_info = load_model_info()
    
    # Handle loading errors
    if error:
        st.error(f"⚠️ {error}")
        st.info("Please check data source and try again.")
        return
    
    # Create tabs
    tab1, tab2 = st.tabs(["📈 Live Predictions", "🔬 Model Analysis"])
    
    with tab1:
        show_predictions_tab(predictions_df, key_features, metrics_info)
    
    with tab2:
        show_model_analysis_tab()
    
    # Footer
    st.markdown("---")
    st.markdown(f"*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    st.markdown("*NCAA Football Predictions Dashboard | Data from Google Sheets*")

if __name__ == "__main__":
    main()
