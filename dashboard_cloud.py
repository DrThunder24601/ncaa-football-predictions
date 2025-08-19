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
import sys
from pathlib import Path

# Add ability to import ResultsTracker (cloud-safe approach)
try:
    # Try to import ResultsTracker for model analysis
    # Note: This may not work in cloud environment without proper file structure
    class CloudSafeResultsAnalyzer:
        """Cloud-safe version of results analysis that works with Google Sheets only"""
        
        def __init__(self, sheet_id, creds_dict):
            self.sheet_id = sheet_id
            self.creds_dict = creds_dict
            self.results_tab = "Results Tracking"
            self.performance_tab = "Performance Metrics"
            
        def get_results_data(self):
            """Get results data from Google Sheets"""
            try:
                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                creds = Credentials.from_service_account_info(self.creds_dict, scopes=scopes)
                gc = gspread.authorize(creds)
                spreadsheet = gc.open_by_key(self.sheet_id)
                
                # Try to get results
                try:
                    results_sheet = spreadsheet.worksheet(self.results_tab)
                    results_data = results_sheet.get_all_records()
                    return pd.DataFrame(results_data) if results_data else pd.DataFrame()
                except gspread.WorksheetNotFound:
                    return pd.DataFrame()
                    
            except Exception as e:
                st.error(f"Error accessing results data: {e}")
                return pd.DataFrame()
                
        def get_performance_data(self):
            """Get performance metrics from Google Sheets"""
            try:
                scopes = [
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive'
                ]
                creds = Credentials.from_service_account_info(self.creds_dict, scopes=scopes)
                gc = gspread.authorize(creds)
                spreadsheet = gc.open_by_key(self.sheet_id)
                
                # Try to get performance metrics
                try:
                    perf_sheet = spreadsheet.worksheet(self.performance_tab)
                    perf_data = perf_sheet.get_all_records()
                    return pd.DataFrame(perf_data) if perf_data else pd.DataFrame()
                except gspread.WorksheetNotFound:
                    return pd.DataFrame()
                    
            except Exception as e:
                st.error(f"Error accessing performance data: {e}")
                return pd.DataFrame()
                
except ImportError:
    CloudSafeResultsAnalyzer = None

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
    
    # Parse teams - Based on user clarification: Kansas State is HOME in "Kansas State vs Iowa State"
    if ' vs ' in matchup:
        teams = matchup.split(' vs ')
        first_team = teams[0].strip() if len(teams) > 0 else 'Team1'
        second_team = teams[1].strip() if len(teams) > 1 else 'Team2'
        # CORRECTED: Based on user saying Kansas State is home team
        # Format appears to be "Home vs Away" 
        home_team = first_team   # First team in matchup is actually HOME
        away_team = second_team  # Second team in matchup is actually AWAY
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
    bet_recommendation = None
    if "(" in edge_raw and ")" in edge_raw:
        try:
            start = edge_raw.find("(") + 1
            end = edge_raw.find(")")
            edge_num_str = edge_raw[start:end].replace("+", "").replace(" ", "")
            edge_float = safe_float(edge_num_str)
            edge_display = f"{edge_float:+.1f} points"
            
            # Extract bet recommendation
            if "Bet Home" in edge_raw:
                bet_recommendation = "home"
            elif "Bet Away" in edge_raw:
                bet_recommendation = "away"
        except:
            edge_display = edge_raw
            edge_float = 0
    else:
        edge_float = safe_float(edge_raw)
        edge_display = f"{edge_float:+.1f} points" if edge_float != 0 else "0.0 points"
    
    # Get edge category based on basketball experience
    abs_edge = abs(edge_float)
    if abs_edge > 15.0:
        edge_category = "🔴 Large Edge"
        edge_color = "red"
    elif abs_edge >= 5.0:
        edge_category = "🟢 Sweet Spot"  # Best performance zone
        edge_color = "green"
    else:
        edge_category = "⚪ Small Edge"
        edge_color = "gray"
    
    # Create card using Streamlit components
    with st.container():
        # Header with edge indicator
        col_title, col_edge = st.columns([3, 1])
        with col_title:
            # Highlight the recommended team to bet on with clearer spread explanation
            vegas_line_float = safe_float(vegas_raw)
            my_pred_float = safe_float(my_pred_raw)
            
            if bet_recommendation == "home":
                # Betting on home team (second team in matchup) 
                # Positive Vegas line = home team favored by that amount
                if vegas_line_float > 0:
                    # Home team favored by Vegas line - bet them laying fewer points
                    my_diff = my_pred_float - vegas_line_float
                    spread_text = f"(-{vegas_line_float}, model likes them {abs(my_diff):.1f} more)"
                elif vegas_line_float < 0:
                    # Home team underdog by Vegas - bet them getting points  
                    spread_text = f"(+{abs(vegas_line_float)}, getting points)"
                else:
                    spread_text = f"(pick 'em)"
                st.subheader(f"{away_team} vs **:green[{home_team}]** 🎯")
                st.caption(f"✅ **BET {home_team.upper()}** {spread_text}")
                
            elif bet_recommendation == "away":
                # Betting on away team (first team in matchup)
                # Positive Vegas line = home favored, so away getting points
                if vegas_line_float > 0:
                    # Away team getting points from Vegas
                    my_diff = vegas_line_float - my_pred_float  
                    spread_text = f"(+{vegas_line_float}, getting {my_diff:.1f} extra points)"
                elif vegas_line_float < 0:
                    # Away team favored by Vegas
                    spread_text = f"(-{abs(vegas_line_float)}, model likes them more)"
                else:
                    spread_text = f"(pick 'em)"
                st.subheader(f"**:green[{away_team}]** 🎯 vs {home_team}")
                st.caption(f"✅ **BET {away_team.upper()}** {spread_text}")
                
            else:
                st.subheader(f"{away_team} vs {home_team}")
                st.caption(edge_raw)
        with col_edge:
            if edge_color == "red":
                st.error(edge_category)
            elif edge_color == "green":
                st.success(edge_category)
            else:
                st.info(edge_category)
        
        # Predictions section with bet highlighting
        col1, col2 = st.columns(2)
        with col1:
            st.metric("My Prediction", pred_text)
        with col2:
            if bet_recommendation:
                recommended_team = home_team if bet_recommendation == "home" else away_team
                st.metric("Vegas Line", vegas_display, help=f"Bet {recommended_team} - Model disagrees with market")
            else:
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

def analyze_edge_category_performance(results_df, predictions_df):
    """Analyze performance by edge categories to validate Sweet Spot hypothesis"""
    if results_df.empty or predictions_df.empty:
        return {}
    
    try:
        # Merge results with predictions to get edge information
        merged_df = pd.merge(
            results_df, 
            predictions_df, 
            left_on=['Home Team', 'Away Team'], 
            right_on=['Home Team', 'Away Team'], 
            how='inner'
        )
        
        if merged_df.empty:
            return {}
        
        # Extract edge values and categorize
        edge_analysis = []
        for _, row in merged_df.iterrows():
            edge_str = str(row.get('Edge', ''))
            try:
                if "(" in edge_str and ")" in edge_str:
                    start = edge_str.find("(") + 1
                    end = edge_str.find(")")
                    edge_num_str = edge_str[start:end].replace("+", "").replace(" ", "")
                    edge_val = abs(float(edge_num_str))
                    
                    # Categorize
                    if edge_val < 5.0:
                        category = "Small Edge (<5)"
                    elif edge_val <= 15.0:
                        category = "Sweet Spot (5-15)"
                    else:
                        category = "Large Edge (>15)"
                    
                    edge_analysis.append({
                        'edge_value': edge_val,
                        'edge_category': category,
                        'prediction_error': float(row.get('Prediction Error', 0)),
                        'winner_correct': row.get('Winner Correct', False)
                    })
            except:
                continue
        
        if not edge_analysis:
            return {}
        
        edge_df = pd.DataFrame(edge_analysis)
        
        # Calculate performance by category
        performance_by_category = {}
        for category in edge_df['edge_category'].unique():
            cat_data = edge_df[edge_df['edge_category'] == category]
            
            performance_by_category[category] = {
                'count': len(cat_data),
                'avg_error': cat_data['prediction_error'].abs().mean(),
                'accuracy': cat_data['winner_correct'].mean() * 100,
                'rmse': np.sqrt(cat_data['prediction_error'].pow(2).mean())
            }
        
        return performance_by_category
        
    except Exception as e:
        st.error(f"Error analyzing edge categories: {e}")
        return {}

def show_model_analysis():
    """Show Model Analysis tab with performance metrics and edge validation"""
    st.header("📊 Model Analysis & Performance")
    
    # Load configuration
    config = load_config()
    if not config:
        st.error("Configuration not loaded")
        return
    
    # Initialize results analyzer
    if CloudSafeResultsAnalyzer:
        try:
            creds_dict = dict(st.secrets["google_service_account"])
            analyzer = CloudSafeResultsAnalyzer(config['sheet_id'], creds_dict)
            
            # Get data
            with st.spinner("Loading model performance data..."):
                results_df = analyzer.get_results_data()
                performance_df = analyzer.get_performance_data()
                predictions_df, _ = load_google_sheets_data()
            
            if results_df.empty:
                st.info("📈 **No results data available yet**")
                st.write("Results will appear here once games are completed and tracked.")
                
                # Show what will be available
                st.subheader("📋 Available Once Season Starts:")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Overall Performance:**")
                    st.write("• Mean Absolute Error (MAE)")
                    st.write("• Root Mean Square Error (RMSE)")
                    st.write("• Winner Prediction Accuracy")
                    st.write("• Betting Record (ATS)")
                
                with col2:
                    st.write("**Edge Category Validation:**")
                    st.write("• Sweet Spot (5-15) Performance")
                    st.write("• Small Edge (<5) Performance") 
                    st.write("• Large Edge (>15) Performance")
                    st.write("• Hypothesis Testing")
                
                return
            
            # Convert numeric columns
            numeric_cols = ['Predicted Spread', 'Actual Spread', 'Prediction Error']
            for col in numeric_cols:
                if col in results_df.columns:
                    results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
            
            # Overall Performance Metrics
            st.subheader("🎯 Overall Model Performance")
            
            if len(results_df) > 0:
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    mae = results_df['Prediction Error'].abs().mean()
                    st.metric("Mean Absolute Error", f"{mae:.2f} pts")
                
                with col2:
                    rmse = np.sqrt(results_df['Prediction Error'].pow(2).mean())
                    st.metric("Root Mean Square Error", f"{rmse:.2f} pts")
                
                with col3:
                    accuracy = results_df['Winner Correct'].value_counts().get(True, 0) / len(results_df) * 100
                    st.metric("Winner Accuracy", f"{accuracy:.1f}%")
                
                with col4:
                    total_games = len(results_df)
                    st.metric("Games Tracked", total_games)
            
            # Error Distribution
            st.subheader("📈 Prediction Error Distribution")
            
            if len(results_df) > 0:
                fig = px.histogram(
                    results_df, 
                    x='Prediction Error',
                    nbins=20,
                    title="Distribution of Prediction Errors",
                    labels={'Prediction Error': 'Prediction Error (points)', 'count': 'Frequency'}
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            # Edge Category Performance Analysis
            st.subheader("🎯 Edge Category Validation")
            
            edge_performance = analyze_edge_category_performance(results_df, predictions_df)
            
            if edge_performance:
                st.write("**Testing the Sweet Spot Hypothesis:** Does the 5-15 point edge range really perform best?")
                
                # Create comparison table
                perf_data = []
                for category, metrics in edge_performance.items():
                    perf_data.append({
                        'Edge Category': category,
                        'Games': metrics['count'],
                        'Avg Error': f"{metrics['avg_error']:.2f}",
                        'Accuracy': f"{metrics['accuracy']:.1f}%",
                        'RMSE': f"{metrics['rmse']:.2f}"
                    })
                
                perf_comparison_df = pd.DataFrame(perf_data)
                
                # Style the table to highlight Sweet Spot
                def highlight_sweet_spot(row):
                    if 'Sweet Spot' in row['Edge Category']:
                        return ['background-color: #90EE90'] * len(row)
                    return [''] * len(row)
                
                st.dataframe(
                    perf_comparison_df.style.apply(highlight_sweet_spot, axis=1),
                    use_container_width=True
                )
                
                # Visual comparison
                fig = px.bar(
                    perf_comparison_df, 
                    x='Edge Category', 
                    y='Accuracy',
                    title="Winner Prediction Accuracy by Edge Category",
                    color='Edge Category',
                    color_discrete_map={
                        'Small Edge (<5)': '#E8E8E8',
                        'Sweet Spot (5-15)': '#90EE90', 
                        'Large Edge (>15)': '#FFB6C1'
                    }
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
                # Analysis interpretation
                if 'Sweet Spot (5-15)' in edge_performance:
                    sweet_spot_acc = edge_performance['Sweet Spot (5-15)']['accuracy']
                    st.write(f"**Sweet Spot Performance**: {sweet_spot_acc:.1f}% accuracy")
                    
                    if sweet_spot_acc > 52.6:
                        st.success(f"✅ Sweet Spot is performing above the 52.6% basketball benchmark!")
                    else:
                        st.warning(f"⚠️ Sweet Spot is at {sweet_spot_acc:.1f}% - may need more data or adjustment")
            else:
                st.info("Edge category analysis will be available once more games are tracked with edge data.")
            
            # Weekly Performance Trend
            if 'Week' in results_df.columns and len(results_df) > 1:
                st.subheader("📅 Weekly Performance Trend")
                
                weekly_stats = results_df.groupby('Week').agg({
                    'Prediction Error': ['mean', lambda x: x.abs().mean(), 'count'],
                    'Winner Correct': 'mean'
                }).round(2)
                
                weekly_stats.columns = ['Mean Error', 'MAE', 'Games', 'Accuracy']
                weekly_stats['Accuracy'] *= 100
                weekly_stats = weekly_stats.reset_index()
                
                fig = px.line(
                    weekly_stats, 
                    x='Week', 
                    y=['MAE', 'Accuracy'],
                    title="Performance Trend by Week"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Performance Summary
            st.subheader("📋 Performance Summary")
            
            if len(results_df) >= 10:  # Need reasonable sample size
                summary_text = f"""
                **Model Assessment Based on {len(results_df)} Games:**
                
                • **Accuracy**: {accuracy:.1f}% winner prediction rate
                • **Precision**: {mae:.2f} point average error (MAE)
                • **Consistency**: {rmse:.2f} point RMSE
                
                """
                
                if edge_performance and 'Sweet Spot (5-15)' in edge_performance:
                    sweet_acc = edge_performance['Sweet Spot (5-15)']['accuracy']
                    if sweet_acc > 55:
                        summary_text += "✅ **Sweet Spot Validated**: 5-15 point edges are performing well\n"
                    elif sweet_acc > 50:
                        summary_text += "⚠️ **Sweet Spot Mixed**: Some validation but needs more data\n"
                    else:
                        summary_text += "❌ **Sweet Spot Questioned**: May need strategy adjustment\n"
                
                st.markdown(summary_text)
            else:
                st.info("More games needed for comprehensive performance assessment (currently have {len(results_df)} games)")
            
        except Exception as e:
            st.error(f"Error in model analysis: {e}")
            st.write("Debug: Check Google Sheets tabs and permissions")
    else:
        st.error("Results analysis not available - CloudSafeResultsAnalyzer not loaded")

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
        # Edge range filter based on basketball experience
        edge_options = ["All Edges", "Sweet Spot (5-15)", "Small Edge (<5)", "Large Edge (>15)"]
        selected_edge = st.selectbox("Filter by Edge", edge_options)
    
    with col3:
        sort_options = ["Default", "Sweet Spot First", "Highest Edge", "Lowest Edge", "Alphabetical"]
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
                
                if selected_edge == "Sweet Spot (5-15)" and 5.0 <= edge_val <= 15.0:
                    return True
                elif selected_edge == "Small Edge (<5)" and edge_val < 5.0:
                    return True
                elif selected_edge == "Large Edge (>15)" and edge_val > 15.0:
                    return True
                return False
            except:
                return False
        
        filtered_df = filtered_df[filtered_df.apply(filter_by_edge, axis=1)]
    
    # Apply sorting
    if sort_by != "Default" and not filtered_df.empty:
        try:
            if sort_by == "Sweet Spot First":
                # Prioritize Sweet Spot (5-15) games first
                def get_sort_priority(row):
                    edge_raw = str(row.get('Edge', ''))
                    try:
                        if "(" in edge_raw and ")" in edge_raw:
                            start = edge_raw.find("(") + 1
                            end = edge_raw.find(")")
                            edge_num_str = edge_raw[start:end].replace("+", "").replace(" ", "")
                            edge_val = abs(float(edge_num_str))
                        else:
                            edge_val = abs(float(edge_raw))
                        
                        if 5.0 <= edge_val <= 15.0:
                            return 1  # Sweet spot - highest priority
                        elif edge_val < 5.0:
                            return 2  # Small edge - medium priority
                        else:
                            return 3  # Large edge - lowest priority
                    except:
                        return 4  # Unknown - lowest priority
                
                filtered_df['Sort_Priority'] = filtered_df.apply(get_sort_priority, axis=1)
                
                # Also get edge value for secondary sort
                def extract_edge_value(edge_str):
                    try:
                        if "(" in str(edge_str) and ")" in str(edge_str):
                            start = str(edge_str).find("(") + 1
                            end = str(edge_str).find(")")
                            edge_num_str = str(edge_str)[start:end].replace("+", "").replace(" ", "")
                            return float(edge_num_str)
                        return 0
                    except:
                        return 0
                
                filtered_df['Edge_Value'] = filtered_df['Edge'].apply(extract_edge_value)
                filtered_df = filtered_df.sort_values(['Sort_Priority', 'Edge_Value'], ascending=[True, False])
                
            elif sort_by == "Highest Edge":
                def extract_edge_value(edge_str):
                    try:
                        if "(" in str(edge_str) and ")" in str(edge_str):
                            start = str(edge_str).find("(") + 1
                            end = str(edge_str).find(")")
                            edge_num_str = str(edge_str)[start:end].replace("+", "").replace(" ", "")
                            return float(edge_num_str)
                        return 0
                    except:
                        return 0
                
                filtered_df['Edge_Value'] = filtered_df['Edge'].apply(extract_edge_value)
                filtered_df = filtered_df.sort_values('Edge_Value', ascending=False)
                
            elif sort_by == "Lowest Edge":
                def extract_edge_value(edge_str):
                    try:
                        if "(" in str(edge_str) and ")" in str(edge_str):
                            start = str(edge_str).find("(") + 1
                            end = str(edge_str).find(")")
                            edge_num_str = str(edge_str)[start:end].replace("+", "").replace(" ", "")
                            return float(edge_num_str)
                        return 999  # Put non-edges at end
                    except:
                        return 999
                
                filtered_df['Edge_Value'] = filtered_df['Edge'].apply(extract_edge_value)
                filtered_df = filtered_df.sort_values('Edge_Value', ascending=True)
                
            elif sort_by == "Alphabetical":
                if 'Matchup' in filtered_df.columns:
                    filtered_df = filtered_df.sort_values('Matchup')
                    
        except Exception as e:
            st.warning(f"Sorting failed: {str(e)}")
    
    # Display summary with edge legend
    sort_info = f" | Sorted by: {sort_by}" if sort_by != "Default" else ""
    st.info(f"📊 Showing {len(filtered_df)} games{sort_info}")
    
    # Edge category explanation
    with st.expander("💡 Edge Category Guide (Based on Basketball Experience)", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.success("🟢 **Sweet Spot (5-15 points)**")
            st.write("• Best performance zone")
            st.write("• 52.6%+ win rate historically")
            st.write("• Focus your attention here")
        with col2:
            st.info("⚪ **Small Edge (<5 points)**")
            st.write("• Often just noise/variance")
            st.write("• Difficult to profit from")
            st.write("• Consider passing")
        with col3:
            st.error("🔴 **Large Edge (>15 points)**")
            st.write("• Model struggles with mismatches")
            st.write("• Only ~40% accuracy")
            st.write("• Avoid these bets")
    
    # Display games as cards
    if not filtered_df.empty:
        display_games_as_cards(filtered_df)
    else:
        st.warning("No games match the current filters")
    
    # Debug info at bottom (hidden by default)
    if st.checkbox("Show debug info", value=False):
        st.write("**Debug Information:**")
        st.write("Columns:", list(predictions_df.columns))
        if not predictions_df.empty:
            st.write("Sample data:")
            st.write(predictions_df.head(1))
        st.write(f"Filtered: {len(filtered_df)} of {len(predictions_df)} games")

def main():
    # Apply styling
    inject_custom_css()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1><span class="football-accent"></span>NCAA Football Predictions Dashboard</h1>
        <p>Powered by 4-Feature Linear Regression Model | Basketball-Tested Edge Categories</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2 = st.tabs(["🏈 Live Predictions", "📊 Model Analysis"])
    
    with tab1:
        # Load data
        with st.spinner("Loading predictions..."):
            predictions_df, error = load_google_sheets_data()
        
        if error:
            st.error(f"⚠️ {error}")
            return
        
        # Show enhanced predictions with fancy features
        show_enhanced_predictions(predictions_df)
    
    with tab2:
        # Show model analysis and performance
        show_model_analysis()

if __name__ == "__main__":
    main()
