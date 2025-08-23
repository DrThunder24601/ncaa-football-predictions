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

# Keep-alive functionality to prevent sleep
def keep_alive():
    """Keep the app alive by updating session state"""
    if "last_ping" not in st.session_state:
        st.session_state.last_ping = datetime.now()
    
    current_time = datetime.now()
    if (current_time - st.session_state.last_ping).seconds > 240:  # 4 minutes
        st.session_state.last_ping = current_time
        # Create a hidden element that updates to keep session alive
        st.markdown(f"<!-- Keep alive: {current_time} -->", unsafe_allow_html=True)

# Dynamic edge analysis functions
@st.cache_data(ttl=600)  # Cache for 10 minutes
def analyze_optimal_edge_ranges(results_df, predictions_df):
    """Dynamically determine optimal edge ranges based on actual performance data"""
    
    if results_df.empty or predictions_df.empty:
        # Default ranges when no data available
        return {
            'optimal_ranges': {
                'Small Edge': {'min': 0, 'max': 5, 'color': 'gray', 'emoji': '⚪'},
                'Sweet Spot': {'min': 5, 'max': 15, 'color': 'green', 'emoji': '🟢'},
                'Large Edge': {'min': 15, 'max': 100, 'color': 'red', 'emoji': '🔴'}
            },
            'data_driven': False,
            'sample_size': 0
        }
    
    try:
        # Merge results with predictions to get edge information
        merged_df = pd.merge(
            results_df, 
            predictions_df, 
            left_on=['Home Team', 'Away Team'], 
            right_on=['Home Team', 'Away Team'], 
            how='inner'
        )
        
        if merged_df.empty or len(merged_df) < 10:  # Need at least 10 games
            return {
                'optimal_ranges': {
                    'Small Edge': {'min': 0, 'max': 5, 'color': 'gray', 'emoji': '⚪'},
                    'Sweet Spot': {'min': 5, 'max': 15, 'color': 'green', 'emoji': '🟢'},
                    'Large Edge': {'min': 15, 'max': 100, 'color': 'red', 'emoji': '🔴'}
                },
                'data_driven': False,
                'sample_size': len(merged_df)
            }
        
        # Extract edge values and performance
        edge_analysis = []
        for _, row in merged_df.iterrows():
            edge_str = str(row.get('Edge', ''))
            try:
                if "(" in edge_str and ")" in edge_str:
                    start = edge_str.find("(") + 1
                    end = edge_str.find(")")
                    edge_num_str = edge_str[start:end].replace("+", "").replace(" ", "")
                    edge_val = abs(float(edge_num_str))
                    
                    edge_analysis.append({
                        'edge_value': edge_val,
                        'prediction_error': abs(float(row.get('Prediction Error', 0))),
                        'winner_correct': bool(row.get('Winner Correct', False)),
                        'profit': 1.0 if bool(row.get('Winner Correct', False)) else -1.0  # Simplified profit calc
                    })
            except:
                continue
        
        if len(edge_analysis) < 10:
            return {
                'optimal_ranges': {
                    'Small Edge': {'min': 0, 'max': 5, 'color': 'gray', 'emoji': '⚪'},
                    'Sweet Spot': {'min': 5, 'max': 15, 'color': 'green', 'emoji': '🟢'},
                    'Large Edge': {'min': 15, 'max': 100, 'color': 'red', 'emoji': '🔴'}
                },
                'data_driven': False,
                'sample_size': len(edge_analysis)
            }
        
        edge_df = pd.DataFrame(edge_analysis)
        
        # Analyze performance across different edge ranges
        edge_ranges = [
            (0, 2), (2, 4), (4, 6), (6, 8), (8, 10), 
            (10, 12), (12, 15), (15, 20), (20, 100)
        ]
        
        range_performance = {}
        for min_edge, max_edge in edge_ranges:
            range_data = edge_df[(edge_df['edge_value'] >= min_edge) & (edge_df['edge_value'] < max_edge)]
            if len(range_data) >= 3:  # Need at least 3 games for meaningful stats
                range_performance[f"{min_edge}-{max_edge}"] = {
                    'count': len(range_data),
                    'accuracy': range_data['winner_correct'].mean(),
                    'avg_error': range_data['prediction_error'].mean(),
                    'profit_rate': range_data['profit'].mean(),
                    'min': min_edge,
                    'max': max_edge
                }
        
        if not range_performance:
            return {
                'optimal_ranges': {
                    'Small Edge': {'min': 0, 'max': 5, 'color': 'gray', 'emoji': '⚪'},
                    'Sweet Spot': {'min': 5, 'max': 15, 'color': 'green', 'emoji': '🟢'},
                    'Large Edge': {'min': 15, 'max': 100, 'color': 'red', 'emoji': '🔴'}
                },
                'data_driven': False,
                'sample_size': len(edge_analysis)
            }
        
        # Find the best performing range (highest accuracy with reasonable sample size)
        best_range = None
        best_score = 0
        
        for range_name, stats in range_performance.items():
            if stats['count'] >= 5:  # Minimum 5 games
                # Score = accuracy * sample_size_weight
                sample_weight = min(stats['count'] / 10, 1.0)  # Max weight at 10+ games
                score = stats['accuracy'] * sample_weight
                
                if score > best_score:
                    best_score = score
                    best_range = stats
        
        # Determine dynamic categories
        if best_range and best_range['accuracy'] > 0.55:  # Must be meaningfully good
            # Best range becomes Sweet Spot
            sweet_min = best_range['min']
            sweet_max = best_range['max']
            
            # Small edge: below sweet spot
            small_max = sweet_min
            
            # Large edge: above sweet spot
            large_min = sweet_max
            
            optimal_ranges = {
                'Small Edge': {'min': 0, 'max': small_max, 'color': 'gray', 'emoji': '⚪'},
                'Sweet Spot': {'min': sweet_min, 'max': sweet_max, 'color': 'green', 'emoji': '🟢'},
                'Large Edge': {'min': large_min, 'max': 100, 'color': 'red', 'emoji': '🔴'}
            }
            
            return {
                'optimal_ranges': optimal_ranges,
                'data_driven': True,
                'sample_size': len(edge_analysis),
                'sweet_spot_accuracy': best_range['accuracy'],
                'range_performance': range_performance
            }
        
        # Fallback to defaults if no clear winner
        return {
            'optimal_ranges': {
                'Small Edge': {'min': 0, 'max': 5, 'color': 'gray', 'emoji': '⚪'},
                'Sweet Spot': {'min': 5, 'max': 15, 'color': 'green', 'emoji': '🟢'},
                'Large Edge': {'min': 15, 'max': 100, 'color': 'red', 'emoji': '🔴'}
            },
            'data_driven': False,
            'sample_size': len(edge_analysis),
            'range_performance': range_performance
        }
        
    except Exception as e:
        st.error(f"Error in dynamic edge analysis: {e}")
        return {
            'optimal_ranges': {
                'Small Edge': {'min': 0, 'max': 5, 'color': 'gray', 'emoji': '⚪'},
                'Sweet Spot': {'min': 5, 'max': 15, 'color': 'green', 'emoji': '🟢'},
                'Large Edge': {'min': 15, 'max': 100, 'color': 'red', 'emoji': '🔴'}
            },
            'data_driven': False,
            'sample_size': 0
        }

def get_dynamic_edge_category(edge_value, optimal_ranges):
    """Get edge category based on dynamic analysis"""
    abs_edge = abs(float(edge_value)) if edge_value else 0
    
    ranges = optimal_ranges['optimal_ranges']
    
    for category, params in ranges.items():
        if params['min'] <= abs_edge < params['max']:
            return f"{params['emoji']} {category}", params['color']
    
    # Default fallback
    return "⚪ Unknown", "gray"

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
    
    /* Error container styling */
    .error-container {
        background-color: #ffebee;
        border-left: 4px solid #f44336;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    
    .retry-container {
        background-color: #e8f5e8;
        border-left: 4px solid #4caf50;
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    
    .data-driven-indicator {
        background: linear-gradient(45deg, #4CAF50, #2196F3);
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 15px;
        font-size: 0.8rem;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
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
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
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

@st.cache_data(ttl=3600)  # Cache team mappings for 1 hour
def load_team_name_mappings():
    """Load team name mappings for odds API"""
    try:
        import pandas as pd
        
        # Load vegas name variations mapping
        vegas_mapping = pd.read_csv("vegas_name_variations.csv")
        
        # Create mapping dictionaries
        api_to_sheet = {}
        sheet_to_api = {}
        
        for _, row in vegas_mapping.iterrows():
            api_name = str(row.get('ESPN_School', '')).strip()
            sheet_name = str(row.get('Model_School', '')).strip()
            
            if api_name and sheet_name:
                api_to_sheet[api_name.lower()] = sheet_name
                sheet_to_api[sheet_name.lower()] = api_name
                
        return api_to_sheet, sheet_to_api
    except Exception as e:
        return {}, {}

@st.cache_data(ttl=60)  # Cache for 1 minute - immediate updates 
def fetch_pre_kickoff_odds():
    """Fetch odds for games that haven't started yet (until kickoff only)"""
    try:
        config = load_config()
        if not config or 'odds_api_key' not in config:
            return {}
        
        # Load team name mappings
        api_to_sheet, sheet_to_api = load_team_name_mappings()
        
        # Get current time
        now = datetime.now()
        
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds/"
        params = {
            'apiKey': config['odds_api_key'],
            'regions': 'us',
            'markets': 'spreads',
            'oddsFormat': 'american'
        }
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            odds_data = response.json()
            
            # Convert to team->line mapping, but only for games that haven't started
            live_lines = {}
            for game in odds_data:
                api_home_team = game.get('home_team', '')
                api_away_team = game.get('away_team', '')
                commence_time_str = game.get('commence_time', '')
                
                try:
                    # Parse game start time (UTC)
                    commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
                    # Convert to Eastern time (UTC-4 for EDT in August)
                    commence_local = commence_time.replace(tzinfo=None) - timedelta(hours=4)
                    
                    # Only update lines for games that haven't started yet
                    game_name = f"{api_away_team} @ {api_home_team}"
                    if 'unlv' in game_name.lower() and 'idaho' in game_name.lower():
                        st.info(f"🔍 {game_name}: Starts {commence_local}, Current {now}, Update: {commence_local > now}")
                    
                    if commence_local > now:
                        # Map API team names to sheet names
                        sheet_home_team = api_to_sheet.get(api_home_team.lower(), api_home_team)
                        sheet_away_team = api_to_sheet.get(api_away_team.lower(), api_away_team)
                        
                        # Get spread from first available bookmaker
                        if game.get('bookmakers') and len(game['bookmakers']) > 0:
                            bookmaker = game['bookmakers'][0]
                            if bookmaker.get('markets'):
                                for market in bookmaker['markets']:
                                    if market.get('key') == 'spreads':
                                        outcomes = market.get('outcomes', [])
                                        for outcome in outcomes:
                                            api_team = outcome.get('name', '')
                                            point = outcome.get('point', 0)
                                            if api_team == api_home_team:
                                                # Store with sheet team names in ALL possible formats
                                                # Your sheet uses "UNLV vs Idaho State" format (home vs away)
                                                live_lines[f"{sheet_home_team} vs {sheet_away_team}"] = point
                                                live_lines[f"{sheet_away_team} vs {sheet_home_team}"] = point
                                                live_lines[f"{sheet_home_team} @ {sheet_away_team}"] = point
                                                live_lines[f"{sheet_away_team} @ {sheet_home_team}"] = point
                                                # Also store with original API names as fallback
                                                live_lines[f"{api_home_team} vs {api_away_team}"] = point
                                                live_lines[f"{api_away_team} vs {api_home_team}"] = point
                                        break
                except Exception as e:
                    continue  # Skip this game if time parsing fails
                        
            return live_lines
        else:
            return {}
    except Exception as e:
        # Don't show error to user for odds fetching - just log it
        st.write(f"<!-- Odds fetch error: {e} -->", unsafe_allow_html=True)
        return {}

def load_google_sheets_data_with_retry(max_retries=3):
    """Load data from Google Sheets with retry logic and better error handling"""
    
    for attempt in range(max_retries):
        try:
            config = load_config()
            if not config:
                return pd.DataFrame(), "Configuration not loaded", False
            
            # Create credentials from secrets with proper scopes
            creds_dict = dict(st.secrets["google_service_account"])
            
            # Ensure private key has proper line breaks
            if 'private_key' in creds_dict:
                creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
            
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
                # Clean the data
                predictions_df = predictions_df.replace('', np.nan)
                if 'Matchup' in predictions_df.columns:
                    predictions_df = predictions_df.dropna(subset=['Matchup'])
                
                # Update with pre-kickoff odds (only for games that haven't started)
                try:
                    pre_kickoff_odds = fetch_pre_kickoff_odds()
                    st.info(f"🔍 Fetched {len(pre_kickoff_odds)} live odds updates")
                    
                    # Debug: Show what keys we have for UNLV
                    unlv_keys = [key for key in pre_kickoff_odds.keys() if 'UNLV' in key or 'Idaho' in key]
                    if unlv_keys:
                        st.info(f"🔍 UNLV game keys found: {unlv_keys}")
                        for key in unlv_keys:
                            st.info(f"   {key} -> {pre_kickoff_odds[key]}")
                    
                    if pre_kickoff_odds:
                        updates_made = 0
                        for idx, row in predictions_df.iterrows():
                            matchup = str(row.get('Matchup', ''))
                            
                            # Debug for UNLV game specifically
                            if 'UNLV' in matchup and 'Idaho' in matchup:
                                st.info(f"🔍 Checking matchup: '{matchup}'")
                                st.info(f"   Found in odds: {matchup in pre_kickoff_odds}")
                                if matchup in pre_kickoff_odds:
                                    st.info(f"   Odds value: {pre_kickoff_odds[matchup]}")
                            
                            if matchup in pre_kickoff_odds:
                                old_line = row.get('Vegas Line', 'N/A')
                                new_line = pre_kickoff_odds[matchup]
                                st.info(f"🔍 Line update: {matchup} - Old: {old_line}, New: {new_line}")
                                
                                # Only update if line actually changed
                                if str(old_line) != str(new_line):
                                    predictions_df.at[idx, 'Vegas Line'] = new_line
                                    predictions_df.at[idx, 'Line Movement'] = f"Was {old_line} → Now {new_line}"
                                    predictions_df.at[idx, 'Status'] = "Pre-Kickoff"
                                    updates_made += 1
                                    st.success(f"✅ Updated {matchup}: {old_line} → {new_line}")
                        
                        if updates_made > 0:
                            st.success(f"📈 Updated {updates_made} game lines with pre-kickoff odds")
                        else:
                            st.warning("⚠️ No lines were updated (all lines unchanged)")
                        
                except Exception as e:
                    st.error(f"❌ Error updating odds: {str(e)}")
                    import traceback
                    st.code(traceback.format_exc())
                
                return predictions_df, None, True
            else:
                return pd.DataFrame(), "No predictions data found", False
                
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429:  # Rate limit
                wait_time = (2 ** attempt) * 1  # Exponential backoff
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                return pd.DataFrame(), f"Rate limit exceeded after {max_retries} attempts", False
            elif e.response.status_code == 403:  # Permission error
                return pd.DataFrame(), "Google Sheets permission denied. Check sharing settings.", False
            elif e.response.status_code == 400:  # Bad request
                return pd.DataFrame(), f"Bad request to Google Sheets API: {str(e)}", False
            else:
                return pd.DataFrame(), f"Google Sheets API error ({e.response.status_code}): {str(e)}", False
                
        except Exception as e:
            if "quota" in str(e).lower():
                return pd.DataFrame(), f"Google Sheets quota exceeded: {str(e)}", False
            elif attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 1
                time.sleep(wait_time)
                continue
            else:
                return pd.DataFrame(), f"Error after {max_retries} attempts: {str(e)}", False
    
    return pd.DataFrame(), f"Failed to load data after {max_retries} attempts", False

def show_error_with_solutions(error_message):
    """Show error message with common solutions"""
    st.markdown(f"""
    <div class="error-container">
        <h4>⚠️ Dashboard Error</h4>
        <p><strong>Error:</strong> {error_message}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Show common solutions based on error type
    if "400" in error_message or "Bad request" in error_message:
        st.markdown("""
        <div class="retry-container">
        <h4>🔧 Common Solutions for 400 Errors:</h4>
        <ol>
            <li><strong>Check Google Sheets permissions:</strong> Make sure the service account has access to your spreadsheet</li>
            <li><strong>Verify sheet names:</strong> Ensure 'Predictions' tab exists and is named correctly</li>
            <li><strong>Check data format:</strong> Make sure there are no corrupted cells in the sheet</li>
            <li><strong>Wait and retry:</strong> Sometimes it's a temporary API issue</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
        
    elif "quota" in error_message.lower() or "rate limit" in error_message.lower():
        st.markdown("""
        <div class="retry-container">
        <h4>📊 Quota/Rate Limit Solutions:</h4>
        <ol>
            <li><strong>Wait 1-2 minutes</strong> then refresh the page</li>
            <li><strong>Reduce refresh frequency:</strong> Data is cached for 5 minutes</li>
            <li><strong>Check API quotas:</strong> You may have hit daily Google Sheets API limits</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

def display_retry_button():
    """Display retry button that clears cache"""
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔄 Retry Loading Data", key="retry_data"):
            # Clear all caches
            st.cache_data.clear()
            st.rerun()

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

def create_simple_game_card(row, optimal_ranges):
    """Create a game card using Streamlit native components with dynamic edge categories"""
    # Safely extract all values
    matchup = safe_str(row.get('Matchup', 'Game TBD'))
    my_pred_raw = safe_str(row.get('My Prediction', '0'))
    vegas_raw = safe_str(row.get('Vegas Line', 'N/A'))
    edge_raw = safe_str(row.get('Edge', '0'))
    
    # Parse teams
    if ' vs ' in matchup:
        teams = matchup.split(' vs ')
        first_team = teams[0].strip() if len(teams) > 0 else 'Team1'
        second_team = teams[1].strip() if len(teams) > 1 else 'Team2'
        home_team = first_team   # First team in matchup is HOME
        away_team = second_team  # Second team in matchup is AWAY
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
    
    # Get DYNAMIC edge category
    edge_category, edge_color = get_dynamic_edge_category(edge_float, optimal_ranges)
    
    # Create card using Streamlit components
    with st.container():
        # Header with edge indicator
        col_title, col_edge = st.columns([3, 1])
        with col_title:
            # Highlight the recommended team to bet on
            vegas_line_float = safe_float(vegas_raw)
            my_pred_float = safe_float(my_pred_raw)
            
            if bet_recommendation == "home":
                if vegas_line_float > 0:
                    my_diff = my_pred_float - vegas_line_float
                    spread_text = f"(-{vegas_line_float}, model likes them {abs(my_diff):.1f} more)"
                elif vegas_line_float < 0:
                    spread_text = f"(+{abs(vegas_line_float)}, getting points)"
                else:
                    spread_text = f"(pick 'em)"
                st.subheader(f"{away_team} vs **:green[{home_team}]** 🎯")
                st.caption(f"✅ **BET {home_team.upper()}** {spread_text}")
                
            elif bet_recommendation == "away":
                if vegas_line_float > 0:
                    my_diff = vegas_line_float - my_pred_float  
                    spread_text = f"(+{vegas_line_float}, getting {my_diff:.1f} extra points)"
                elif vegas_line_float < 0:
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
        
        # Predictions section
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

def display_games_as_cards(df, optimal_ranges):
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
                create_simple_game_card(df.iloc[i], optimal_ranges)
        
        # Second card
        with col2:
            if i + 1 < len(df):
                create_simple_game_card(df.iloc[i + 1], optimal_ranges)

def show_enhanced_predictions(predictions_df, optimal_ranges):
    """Show predictions with dynamic edge categories"""
    st.header("🏈 NCAA Football Predictions Dashboard")
    
    if predictions_df.empty:
        st.warning("No predictions data available")
        return
    
    # Show dynamic edge status
    if optimal_ranges['data_driven']:
        ranges = optimal_ranges['optimal_ranges']
        sweet_spot = ranges['Sweet Spot']
        st.markdown(f"""
        <div class="data-driven-indicator">
        📊 DATA-DRIVEN EDGES: Sweet Spot = {sweet_spot['min']}-{sweet_spot['max']} points | Based on {optimal_ranges['sample_size']} games
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info(f"🔄 Learning Mode: Using default ranges until we have {10 if optimal_ranges['sample_size'] < 10 else 'more'} games to analyze")
    
    # Filters
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Extract unique teams
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
        # Dynamic edge range filter
        ranges = optimal_ranges['optimal_ranges']
        edge_options = ["All Edges"] + list(ranges.keys())
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
    
    # Dynamic edge filter
    if selected_edge != "All Edges" and selected_edge in ranges:
        edge_params = ranges[selected_edge]
        def filter_by_dynamic_edge(row):
            edge_raw = str(row.get('Edge', ''))
            try:
                if "(" in edge_raw and ")" in edge_raw:
                    start = edge_raw.find("(") + 1
                    end = edge_raw.find(")")
                    edge_num_str = edge_raw[start:end].replace("+", "").replace(" ", "")
                    edge_val = abs(float(edge_num_str))
                else:
                    edge_val = abs(float(edge_raw))
                
                return edge_params['min'] <= edge_val < edge_params['max']
            except:
                return False
        
        filtered_df = filtered_df[filtered_df.apply(filter_by_dynamic_edge, axis=1)]
    
    # Apply default sort: Games with Vegas lines first, N/A lines last
    if not filtered_df.empty:
        def get_vegas_line_priority(row):
            """Sort games with Vegas lines first, N/A lines last"""
            vegas_raw = safe_str(row.get('Vegas Line', 'N/A'))
            if vegas_raw in ['N/A', 'n/a', '', ' ']:
                return 2  # N/A lines go to bottom
            else:
                return 1  # Games with lines go to top
        
        # Always apply default sort unless overridden
        if sort_by == "Default":
            filtered_df['Vegas_Priority'] = filtered_df.apply(get_vegas_line_priority, axis=1)
            filtered_df = filtered_df.sort_values('Vegas_Priority', ascending=True)
    
    # Sorting logic (same as before but using dynamic ranges)
    if sort_by != "Default" and not filtered_df.empty:
        try:
            if sort_by == "Sweet Spot First":
                sweet_spot_params = ranges['Sweet Spot']
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
                        
                        if sweet_spot_params['min'] <= edge_val < sweet_spot_params['max']:
                            return 1  # Sweet spot - highest priority
                        elif edge_val < sweet_spot_params['min']:
                            return 2  # Small edge
                        else:
                            return 3  # Large edge
                    except:
                        return 4
                
                filtered_df['Sort_Priority'] = filtered_df.apply(get_sort_priority, axis=1)
                
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
                
            # Other sorting options remain the same...
                    
        except Exception as e:
            st.warning(f"Sorting failed: {str(e)}")
    
    # Display summary
    if sort_by == "Default":
        sort_info = " | Vegas lines first, N/A lines last"
    else:
        sort_info = f" | Sorted by: {sort_by}"
    st.info(f"📊 Showing {len(filtered_df)} games{sort_info}")
    
    # Dynamic edge category explanation
    with st.expander("💡 Current Edge Categories", expanded=False):
        ranges = optimal_ranges['optimal_ranges']
        cols = st.columns(len(ranges))
        
        for i, (category, params) in enumerate(ranges.items()):
            with cols[i]:
                if params['color'] == 'green':
                    st.success(f"{params['emoji']} **{category} ({params['min']}-{params['max']} pts)**")
                elif params['color'] == 'red':
                    st.error(f"{params['emoji']} **{category} ({params['min']}-{params['max']} pts)**")
                else:
                    st.info(f"{params['emoji']} **{category} ({params['min']}-{params['max']} pts)**")
                
                if optimal_ranges['data_driven'] and category == 'Sweet Spot':
                    st.write(f"• {optimal_ranges.get('sweet_spot_accuracy', 0)*100:.1f}% accuracy")
                    st.write("• Data-driven optimal range")
                elif not optimal_ranges['data_driven']:
                    st.write("• Default range")
                    st.write("• Will update with data")
    
    # Display games as cards
    if not filtered_df.empty:
        display_games_as_cards(filtered_df, optimal_ranges)
    else:
        st.warning("No games match the current filters")

def show_model_analysis():
    """Show Model Analysis with dynamic edge analysis"""
    st.header("📊 Model Analysis & Performance")
    
    config = load_config()
    if not config:
        st.error("Configuration not loaded")
        return
    
    if CloudSafeResultsAnalyzer:
        try:
            creds_dict = dict(st.secrets["google_service_account"])
            analyzer = CloudSafeResultsAnalyzer(config['sheet_id'], creds_dict)
            
            with st.spinner("Loading performance data and analyzing optimal edge ranges..."):
                results_df = analyzer.get_results_data()
                predictions_df, _ = load_google_sheets_data_with_retry(max_retries=3)
                
                # Get dynamic edge analysis
                optimal_ranges = analyze_optimal_edge_ranges(results_df, predictions_df)
            
            if results_df.empty:
                st.info("📈 **No results data available yet**")
                st.write("Performance analysis will appear here once games are completed and tracked.")
                return
            
            # Show dynamic edge analysis results
            st.subheader("🎯 Dynamic Edge Analysis")
            
            if optimal_ranges['data_driven']:
                st.success(f"✅ **Data-Driven Analysis Active** (Based on {optimal_ranges['sample_size']} games)")
                
                ranges = optimal_ranges['optimal_ranges']
                sweet_spot = ranges['Sweet Spot']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Sweet Spot Range", f"{sweet_spot['min']}-{sweet_spot['max']} pts")
                with col2:
                    if 'sweet_spot_accuracy' in optimal_ranges:
                        st.metric("Sweet Spot Accuracy", f"{optimal_ranges['sweet_spot_accuracy']*100:.1f}%")
                with col3:
                    st.metric("Sample Size", optimal_ranges['sample_size'])
                
                # Show performance by range if available
                if 'range_performance' in optimal_ranges:
                    st.subheader("📈 Edge Range Performance")
                    
                    perf_data = []
                    for range_name, metrics in optimal_ranges['range_performance'].items():
                        perf_data.append({
                            'Range': f"{range_name} pts",
                            'Games': metrics['count'],
                            'Accuracy': f"{metrics['accuracy']*100:.1f}%",
                            'Avg Error': f"{metrics['avg_error']:.2f}",
                            'Profit Rate': f"{metrics['profit_rate']:.2f}"
                        })
                    
                    perf_df = pd.DataFrame(perf_data)
                    st.dataframe(perf_df, use_container_width=True)
                    
            else:
                st.info(f"🔄 **Learning Mode**: Need {10 - optimal_ranges['sample_size']} more games for data-driven analysis")
            
            # Rest of the analysis (convert numeric columns, overall metrics, etc.) 
            numeric_cols = ['Predicted Spread', 'Actual Spread', 'Prediction Error']
            for col in numeric_cols:
                if col in results_df.columns:
                    results_df[col] = pd.to_numeric(results_df[col], errors='coerce')
            
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
            
        except Exception as e:
            st.error(f"Error in model analysis: {e}")
    else:
        st.error("Results analysis not available")

def main():
    # Apply styling and keep alive
    inject_custom_css()
    keep_alive()
    
    # Sidebar status
    with st.sidebar:
        st.markdown("### 📊 System Status")
        current_time = datetime.now().strftime('%H:%M:%S')
        st.caption(f"Last updated: {current_time}")
        
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            # Clear specific functions
            fetch_pre_kickoff_odds.clear()
            load_google_sheets_data_with_retry.clear()
            st.rerun()
            
        if st.button("⚡ Force Line Update"):
            # Force immediate line update
            fetch_pre_kickoff_odds.clear()
            st.rerun()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏈 NCAA Football Predictions Dashboard</h1>
        <p>Powered by 4-Feature Linear Regression Model | Dynamic Data-Driven Edge Categories</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Load optimal ranges for the entire session
    config = load_config()
    optimal_ranges = {'optimal_ranges': {
        'Small Edge': {'min': 0, 'max': 5, 'color': 'gray', 'emoji': '⚪'},
        'Sweet Spot': {'min': 5, 'max': 15, 'color': 'green', 'emoji': '🟢'},
        'Large Edge': {'min': 15, 'max': 100, 'color': 'red', 'emoji': '🔴'}
    }, 'data_driven': False, 'sample_size': 0}
    
    if config and CloudSafeResultsAnalyzer:
        try:
            creds_dict = dict(st.secrets["google_service_account"])
            analyzer = CloudSafeResultsAnalyzer(config['sheet_id'], creds_dict)
            results_df = analyzer.get_results_data()
            predictions_df, _, _ = load_google_sheets_data_with_retry(max_retries=1)
            optimal_ranges = analyze_optimal_edge_ranges(results_df, predictions_df)
        except:
            pass  # Use defaults
    
    # Create tabs
    tab1, tab2 = st.tabs(["🏈 Live Predictions", "📊 Model Analysis"])
    
    with tab1:
        with st.spinner("Loading predictions..."):
            predictions_df, error, success = load_google_sheets_data_with_retry(max_retries=3)
        
        if not success and error:
            show_error_with_solutions(error)
            display_retry_button()
            return
        elif predictions_df.empty:
            st.info("📭 No predictions available yet")
            st.write("Predictions will appear here once games are loaded.")
            display_retry_button()
            return
        else:
            show_enhanced_predictions(predictions_df, optimal_ranges)
    
    with tab2:
        show_model_analysis()

if __name__ == "__main__":
    main()
