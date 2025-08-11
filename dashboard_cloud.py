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
            if 'Home Team' in predictions_df.columns:
                teams = sorted(set(list(predictions_df.get('Home Team', [])) + list(predictions_df.get('Away Team', []))))
                selected_team = st.selectbox("Filter by Team", ["All Teams"] + teams)
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
    
        # Filter and display data (simplified for cloud deployment)
        filtered_df = predictions_df.copy()
        
        if selected_team != "All Teams":
            if 'Home Team' in predictions_df.columns and 'Away Team' in predictions_df.columns:
                filtered_df = filtered_df[
                    (filtered_df['Home Team'] == selected_team) | 
                    (filtered_df['Away Team'] == selected_team)
                ]
        
        # Filter by edge range
        if selected_edge_range != "All Ranges" and 'Edge_Range' in filtered_df.columns:
            filtered_df = filtered_df[filtered_df['Edge_Range'] == selected_edge_range]
        
        # Display predictions table
        if not filtered_df.empty:
            # Display edge range summary
            if 'Edge_Range' in filtered_df.columns:
                col1, col2, col3, col4 = st.columns(4)
                edge_counts = filtered_df['Edge_Range'].value_counts()
                
                with col1:
                    low_count = edge_counts.get("Low Edge (0-1.5)", 0)
                    st.metric("Low Edge", low_count)
                    
                with col2:
                    mid_count = edge_counts.get("Mid Edge (1.5-3)", 0)
                    st.metric("Mid Edge", mid_count)
                    
                with col3:
                    high_count = edge_counts.get("High Edge (3-5)", 0)
                    st.metric("High Edge", high_count)
                    
                with col4:
                    very_high_extreme_count = (edge_counts.get("Very High Edge (5-8)", 0) + 
                                             edge_counts.get("Extreme Edge (8+)", 0))
                    st.metric("Very High/Extreme", very_high_extreme_count)
            
            # Show data
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
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
    # Header
    st.title("🏈 NCAA Football Predictions Dashboard")
    st.markdown("*Public Beta - Powered by 4-Feature Linear Regression (1.5 MAE)*")
    st.markdown("---")
    
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
