# football_automation.py

import os
import sys
import glob
import pandas as pd
import numpy as np
import requests
import joblib
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Import the comprehensive feature engineering
try:
    from comprehensive_feature_engineering import process_schedule_to_features
except ImportError:
    # Try relative import if absolute doesn't work
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from comprehensive_feature_engineering import process_schedule_to_features

# --- CONFIGURATION ---
from pathlib import Path

CFBD_API_KEY = "JtHAHd8aiWqFw18UM0F5tpqE98uWD3bkWBoRagbxLlGghzIBl69ibVHYY2p7Dcno"
ODDS_API_KEY = "2d2d9f121db76085d2e62734d0958bd9"  # The Odds API key
YEAR = 2025

# Use relative paths from project root
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_PATH = BASE_DIR / "models" / "rf_deep_model_RETRAINED.joblib"
FEATURES_PATH = BASE_DIR / "models" / "rf_deep_features.txt"

# External file paths (keep absolute for external dependencies)
MAPPING_CSV = r"C:\Users\31198\ncaa-predictions\cfbdata_to_espn_comprehensive_mapping.csv"
SERVICE_ACCOUNT = r"C:\Users\31198\AppData\Local\Programs\Python\Python313\kentraining.json"

# Google Sheets configuration
SHEET_ID = "1Rmj5fbhwkQivv98hR5GqCNhBkV8-EwEtEA74bsC6wAU"
SCHEDULE_TAB = "ESPN Schedule Pull"
PREDICTIONS_TAB = "Predictions"

# Fallback to original models if enhanced models don't exist
if not MODEL_PATH.exists():
    if (BASE_DIR / "models" / "random_forest_model.joblib").exists():
        MODEL_PATH = BASE_DIR / "models" / "random_forest_model.joblib"
        FEATURES_PATH = BASE_DIR / "models" / "rf_features.txt"
        print("WARNING: Using original random forest model instead of enhanced model")
    elif (BASE_DIR / "data" / "random_forest_model.joblib").exists():
        MODEL_PATH = BASE_DIR / "data" / "random_forest_model.joblib"
        FEATURES_PATH = BASE_DIR / "data" / "rf_features.txt"
        print("WARNING: Using legacy data directory model")

def get_current_week():
    """
    Get current CFB week based on calendar date with Sunday night cutoffs
    Week 0: Saturday 8/23 and Sunday 8/24 only
    Week 1+: Monday through Sunday cycles, ending Sunday night
    """
    # Week 0 specific dates (games on Saturday 8/23 and Sunday 8/24 only)
    WEEK_0_START = datetime(2025, 8, 23)  # Saturday 8/23
    WEEK_0_END = datetime(2025, 8, 25)    # End of Sunday 8/24 (start of Monday 8/25)
    
    # Week 1 starts Monday 8/25
    WEEK_1_START = datetime(2025, 8, 25)  # Monday 8/25
    
    current_date = datetime.now()
    
    # Before season starts
    if current_date < WEEK_0_START:
        return 0  # Return 0 for pre-season (dashboard compatibility)
    
    # Week 0: Saturday 8/23 and Sunday 8/24 only
    if WEEK_0_START <= current_date < WEEK_0_END:
        return 0
    
    # Week 1+: Monday through Sunday cycles
    if current_date >= WEEK_1_START:
        days_since_week1 = (current_date - WEEK_1_START).days
        week_number = days_since_week1 // 7 + 1
        return min(week_number, 15)  # Cap at week 15 for regular season
    
    return 0  # Fallback

def update_stats():
    """Fetch and save latest weekly stats"""
    week = get_current_week()
    url = f"https://api.collegefootballdata.com/stats/season/advanced?year={YEAR}&excludeGarbageTime=true"
    headers = {"Authorization": f"Bearer {CFBD_API_KEY}"}
    resp = requests.get(url, headers=headers)
    print("update_stats() - Status code:", resp.status_code)
    print("update_stats() - Response text:", resp.text[:500])
    resp.raise_for_status()
    stats_df = pd.DataFrame(resp.json())
    stats_path = DATA_DIR / f"cfbd_team_stats_{YEAR}_week{week}.csv"
    stats_df.to_csv(str(stats_path), index=False)
    print(f"Updated stats with {YEAR} current season data for week {week}")
    return week

def pull_schedule(week):
    """
    Pull schedule for current week from ESPN (replaces CFBD API)
    Week parameter is ignored - always pulls current ESPN schedule
    """
    try:
        # Import ESPN scraper
        from espn_scraper import pull_espn_schedule
        
        print(f"pull_schedule() - Pulling from ESPN (ignoring week={week})")
        schedule = pull_espn_schedule()
        
        print(f"pull_schedule() - ESPN returned {len(schedule)} games")
        if len(schedule) > 0:
            print("pull_schedule() - Sample games:", schedule.iloc[:3]['Home Team'].tolist())
        
        return schedule
        
    except Exception as e:
        print(f"pull_schedule() - ESPN scraper failed: {str(e)}")
        print("pull_schedule() - Falling back to CFBD API...")
        
        # Fallback to original CFBD method
        url = f"https://api.collegefootballdata.com/games?year={YEAR}&week={week}&seasonType=regular"
        headers = {"Authorization": f"Bearer {CFBD_API_KEY}"}
        resp = requests.get(url, headers=headers)
        print("pull_schedule() - CFBD Status code:", resp.status_code)
        resp.raise_for_status()
        schedule = pd.DataFrame(resp.json())
        # Keep only necessary columns - updated column names
        schedule = schedule[['homeTeam', 'awayTeam']].rename(columns={
            'homeTeam': 'Home Team',
            'awayTeam': 'Away Team'
        })
        return schedule

def fetch_lines():
    """Fetch Lines - with fallback when API quota exceeded"""
    if ODDS_API_KEY == "YOUR_ODDS_API_KEY_HERE":
        print("WARNING: No Odds API key configured. Using fallback system.")
        return create_fallback_lines()
    
    try:
        # Try The Odds API first
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_ncaaf/odds"
        params = {
            'api_key': ODDS_API_KEY,
            'regions': 'us',
            'markets': 'spreads',
            'dateFormat': 'iso',
            'oddsFormat': 'american'
        }
        
        response = requests.get(url, params=params)
        print(f"Lines API status: {response.status_code}")
        
        if response.status_code == 401:
            print("WARNING: Odds API quota exceeded. Using fallback system.")
            return create_fallback_lines()
        
        if response.status_code != 200:
            print(f"Error fetching Lines: {response.text}")
            print("Using fallback system.")
            return create_fallback_lines()
        
        games_data = response.json()
        print(f"Fetched Lines for {len(games_data)} games")
        
        # Process the data into a more usable format
        lines = {}
        for game in games_data:
            home_team = game['home_team']
            away_team = game['away_team']
            
            # Find the best spread (we'll use the first bookmaker for now)
            if game.get('bookmakers') and len(game['bookmakers']) > 0:
                bookmaker = game['bookmakers'][0]
                if 'markets' in bookmaker and len(bookmaker['markets']) > 0:
                    market = bookmaker['markets'][0]
                    if 'outcomes' in market and len(market['outcomes']) >= 2:
                        # Find home team spread
                        for outcome in market['outcomes']:
                            if outcome['name'] == home_team:
                                spread = outcome.get('point', 0)
                                lines[f"{home_team}_vs_{away_team}"] = {
                                    'home_team': home_team,
                                    'away_team': away_team, 
                                    'home_spread': spread,
                                    'bookmaker': bookmaker.get('title', 'Unknown')
                                }
                                break
        
        print(f"Processed {len(lines)} Lines from API")
        return lines
        
    except Exception as e:
        print(f"Error fetching Lines: {str(e)}")
        print("Using fallback system.")
        return create_fallback_lines()

def create_fallback_lines():
    """ESPN API-based fallback when Odds API is unavailable - NO LONGER EMPTY!"""
    print("=== ESPN API FALLBACK LINES SYSTEM ===")
    
    try:
        # Import and use the new ESPN API scraper
        from espn_lines_scraper import scrape_espn_college_football_lines
        
        print("Using ESPN API as fallback lines source...")
        lines = scrape_espn_college_football_lines()
        
        if lines:
            print(f"ESPN API Fallback: Found {len(lines)} games with betting lines!")
            print("Sample ESPN lines:")
            for i, (key, line_data) in enumerate(list(lines.items())[:3]):
                spread = line_data.get('home_spread', 'N/A')
                print(f"  {line_data['away_team']} @ {line_data['home_team']} | Spread: {spread}")
        else:
            print("ESPN API returned no lines - network issue?")
        
        return lines
        
    except Exception as e:
        print(f"Error with ESPN API fallback: {e}")
        print("Falling back to empty lines (will show 'N/A')")
        return {}

def write_schedule_to_sheet(schedule):
    """Update 'ESPN Schedule Pull' tab"""
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT)
    client = gspread.authorize(creds.with_scopes([
        "https://www.googleapis.com/auth/spreadsheets"
    ]))
    sheet = client.open_by_key(SHEET_ID).worksheet(SCHEDULE_TAB)
    sheet.clear()
    sheet.update([schedule.columns.values.tolist()] + schedule.values.tolist())
    print("Schedule updated in Google Sheet.")

def make_predictions():
    """Run predictions using latest stats"""
    # --- Load RF_Deep Model (Clean, No Data Leakage) ---
    try:
            # Load the ADVANCED RF_Deep model (REAL advanced stats, 12.04 MAE)
        rf_advanced_path = BASE_DIR / "models" / "rf_deep_model_ADVANCED.joblib"
        if rf_advanced_path.exists():
            model = joblib.load(str(rf_advanced_path))
            print("Loaded RF_Deep ADVANCED model (136 teams, REAL advanced stats, 12.04 MAE)")
            use_simple_features = False
            # Load advanced features list
            advanced_features_path = BASE_DIR / "models" / "rf_deep_features_ADVANCED.txt"
            if advanced_features_path.exists():
                with open(str(advanced_features_path), 'r') as f:
                    enhanced_features_list = [line.strip() for line in f]
                print(f"Loaded {len(enhanced_features_list)} REAL advanced features")
            else:
                enhanced_features_list = [
                    'off_ppa', 'off_successRate', 'off_explosiveness',
                    'def_ppa', 'def_successRate', 'def_explosiveness', 
                    'home_advantage',
                    'off_ppa_away', 'off_successRate_away', 'off_explosiveness_away',
                    'def_ppa_away', 'def_successRate_away', 'def_explosiveness_away',
                    'off_eff_diff', 'def_eff_diff'
                ]
        # Fallback to COMPLETE model (736 teams with approximated stats)
        elif (BASE_DIR / "models" / "rf_deep_model_COMPLETE.joblib").exists():
            rf_complete_path = BASE_DIR / "models" / "rf_deep_model_COMPLETE.joblib"
            model = joblib.load(str(rf_complete_path))
            print("Loaded RF_Deep COMPLETE model (736 teams fallback)")
            use_simple_features = False
            enhanced_features_list = [
                'off_ppa', 'off_successRate', 'off_explosiveness',
                'def_ppa', 'def_successRate', 'def_explosiveness', 
                'home_advantage',
                'off_ppa_away', 'off_successRate_away', 'off_explosiveness_away',
                'def_ppa_away', 'def_successRate_away', 'def_explosiveness_away',
                'off_eff_diff', 'def_eff_diff'
            ]
        else:
            # Fallback to enhanced RF if RF_Deep doesn't exist
            enhanced_rf_path = BASE_DIR / "models" / "enhanced_random_forest_model.joblib"
            model = joblib.load(str(enhanced_rf_path))
            print("WARNING: RF_Deep not found, using Enhanced RF (may have data leakage)")
            use_simple_features = False
            enhanced_features_list = None
    except Exception as e:
        print(f"Error loading RF_Deep model: {e}")
        print("Check that rf_deep_model.joblib exists in models directory")
        return None
    
    mapping_df = pd.read_csv(MAPPING_CSV)
    mapping_dict = dict(zip(mapping_df['ESPN_School'], mapping_df['Model_School']))
    
    print("=== DEBUG: Starting make_predictions() function ===")
    
    # --- Load Latest Stats ---
    # For betting predictions, always use 2024 final stats which has complete data for all FBS teams
    current_week = get_current_week()
    stats_file = DATA_DIR / "cfbd_team_stats_2024_final.csv"
    print(f"Using 2024 final stats for Week {current_week} betting predictions (complete FBS coverage)")
    
    if not stats_file.exists():
        raise FileNotFoundError(f"Stats file not found! Looking for: {stats_file}")
    
    print(f"Loading stats from: {stats_file}")
    stats_df = pd.read_csv(str(stats_file))

    # --- Load Schedule ---
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT)
    client = gspread.authorize(creds.with_scopes([
        "https://www.googleapis.com/auth/spreadsheets"
    ]))
    schedule_ws = client.open_by_key(SHEET_ID).worksheet(SCHEDULE_TAB)
    pred_ws = client.open_by_key(SHEET_ID).worksheet(PREDICTIONS_TAB)
    schedule = pd.DataFrame(schedule_ws.get_all_records())

# --- Map team names using mapping CSV ---
    def clean_espn_name(name):
        """Clean ESPN team names by removing common mascots"""
        if not name:
            return name
            
        # Remove common mascot suffixes that ESPN adds
        mascot_suffixes = [
            'Aggies', 'Bulldogs', 'Tigers', 'Eagles', 'Cardinals', 'Bears', 'Trojans',
            'Bruins', 'Ducks', 'Beavers', 'Wildcats', 'Cyclones', 'Hawkeyes', 'Spartans',
            'Wolverines', 'Buckeyes', 'Hoosiers', 'Cornhuskers', 'Badgers', 'Longhorns',
            'Sooners', 'Cowboys', 'Red Raiders', 'Razorbacks', 'Volunteers', 'Commodores',
            'Gators', 'Hurricanes', 'Seminoles', 'Yellow Jackets', 'Blue Devils', 'Tar Heels',
            'Demon Deacons', 'Sun Devils', 'Golden Bears', 'Huskies', 'Cougars', 'Utes',
            'Buffaloes', 'Rams', 'Lobos', 'Broncos', 'Rebels', 'Wolf Pack', 'Miners',
            'Roadrunners', 'Mean Green', '49ers', 'Owls', 'Knights', 'Bulls', 'Panthers',
            'Golden Eagles', 'Green Wave', 'Chanticleers', 'Monarchs', 'Thundering Herd',
            'Mountaineers', 'Nittany Lions', 'Terrapins', 'Scarlet Knights', 'Boilermakers',
            'Golden Gophers', 'RedHawks', 'Chippewas', 'Zips', 'Bobcats', 'Gamecocks',
            'Bearkats', 'Hilltoppers', 'Redbirds', 'Dukes', 'Fighting Hawks', 'Lumberjacks',
            'Bengals', 'Cardinal', 'Leopards', 'Pirates', 'Hornets', 'Red Flash', 'Phoenix',
            'Skyhawks', 'Orange', 'Rockets', 'Colonials', 'Coyotes', 'Bison', 'Crusaders',
            'Black Bears', 'Mocs', 'Great Danes', 'Sharks', 'Buccaneers', 'Governors',
            'Lions', 'Golden Lions', 'Vikings', 'Vandals', 'Rainbow Warriors', 'Hokies',
            'Leathernecks', 'Seahawks', 'Warriors', 'Flames', 'Jaguars', 'Falcons',
            'Minutemen', 'Redhawks', 'Red Wolves', 'Colonels', 'Mustangs', 'Texans'
        ]
        
        # Try removing each mascot suffix
        for mascot in mascot_suffixes:
            if name.endswith(f' {mascot}'):
                cleaned = name[:-len(f' {mascot}')].strip()
                return cleaned
                
        return name

    def map_team(name):
        # First try exact match
        mapped = mapping_dict.get(name)
        if mapped is not None:
            return mapped
            
        # Try with cleaned ESPN name (remove mascots)
        cleaned_name = clean_espn_name(name)
        mapped = mapping_dict.get(cleaned_name)
        if mapped is not None:
            print(f"SUCCESS: Mapped '{name}' -> '{cleaned_name}' -> '{mapped}'")
            return mapped
            
        # Try case-insensitive matching
        for key, value in mapping_dict.items():
            if key.upper() == name.upper():
                print(f"SUCCESS: Case-insensitive match '{name}' -> '{key}' -> '{value}'")
                return value
                
        # Last resort: try case-insensitive with cleaned name
        for key, value in mapping_dict.items():
            if key.upper() == cleaned_name.upper():
                print(f"SUCCESS: Case-insensitive cleaned match '{name}' -> '{cleaned_name}' -> '{key}' -> '{value}'")
                return value
                
        print(f"WARNING: {name} (cleaned: {cleaned_name}) not found in mapping file, skipping game")
        return None

    schedule['Home_Model'] = schedule['Home Team'].map(map_team)
    schedule['Away_Model'] = schedule['Away Team'].map(map_team)
    
# Filter out games with unmapped teams
    schedule = schedule.dropna(subset=['Home_Model', 'Away_Model'])
    print(f"Making predictions for {len(schedule)} games with valid team mappings")
    
    # Reset index after filtering
    schedule = schedule.reset_index(drop=True)
    
    # Keep original case for team mapping (don't uppercase yet)
    schedule['Home_Model'] = schedule['Home_Model'].str.strip()
    schedule['Away_Model'] = schedule['Away_Model'].str.strip()

    # --- TEAM DATA VALIDATION ---
    # Use already-mapped team names from schedule
    valid_games = []
    invalid_games = []
    
    for _, row in schedule.iterrows():
        home_espn = row['Home Team']
        away_espn = row['Away Team'] 
        home_cfbd = row['Home_Model']
        away_cfbd = row['Away_Model']
        
        # Check if both teams have CFBD data using mapped names
        home_exists = home_cfbd and not stats_df[stats_df['team'] == home_cfbd].empty
        away_exists = away_cfbd and not stats_df[stats_df['team'] == away_cfbd].empty
        
        if home_exists and away_exists:
            valid_games.append(row)
        else:
            missing_teams = []
            if not home_exists:
                missing_teams.append(f"{home_espn} (mapped to {home_cfbd})")
            if not away_exists:
                missing_teams.append(f"{away_espn} (mapped to {away_cfbd})")
            print(f"FILTERING OUT: {away_espn} @ {home_espn} (No CFBD data: {', '.join(missing_teams)})")
            invalid_games.append({
                'matchup': f"{away_espn} @ {home_espn}",
                'home_team': home_espn,
                'away_team': away_espn,
                'reason': f"No CFBD data: {', '.join(missing_teams)}"
            })
    
    # Update schedule with only valid games
    schedule = pd.DataFrame(valid_games).reset_index(drop=True) if valid_games else pd.DataFrame()
    print(f"FILTERED: {len(valid_games)} games with valid team data, {len(invalid_games)} games filtered out")

    # --- RF_DEEP 15-FEATURE APPROACH ---
    print("=== USING RF_DEEP 15-FEATURE APPROACH (CLEAN DATA) ===")
    print(f"Building RF_Deep feature set for {len(schedule)} games...")

    # --- Get team stats for each game ---
    home_stats_list = []
    away_stats_list = []
    
    def get_team_stats(team_name):
        # Try exact match first, then case-insensitive
        match = stats_df[stats_df['team'] == team_name]
        if match.empty:
            # Try case-insensitive match
            match = stats_df[stats_df['team'].str.upper() == team_name.upper()]
        if match.empty:
            print(f"WARNING: No stats found for team '{team_name}'")
            return pd.Series({'season': None, 'team': None, 'conference': None, 'offense': '{}', 'defense': '{}'})
        return match.iloc[0]
    
    for _, row in schedule.iterrows():
        home_stats_list.append(get_team_stats(row['Home_Model']))
        away_stats_list.append(get_team_stats(row['Away_Model']))
    
    home_stats_df = pd.DataFrame(home_stats_list).add_suffix('_home')
    away_stats_df = pd.DataFrame(away_stats_list).add_suffix('_away')

    # --- Extract stats from JSON data ---
    import json
    
    def extract_stat_from_json(json_str, stat_name):
        try:
            if pd.isna(json_str) or json_str == '{}' or not json_str:
                return 0.0
            data = json.loads(json_str.replace("'", '"'))
            return float(data.get(stat_name, 0)) if data else 0.0
        except Exception:
            return 0.0
    
    # Extract all required stats
    # Home team stats
    home_off_ppa = home_stats_df['offense_home'].apply(lambda x: extract_stat_from_json(x, 'ppa'))
    home_off_success = home_stats_df['offense_home'].apply(lambda x: extract_stat_from_json(x, 'successRate'))
    home_off_explos = home_stats_df['offense_home'].apply(lambda x: extract_stat_from_json(x, 'explosiveness'))
    home_def_ppa = home_stats_df['defense_home'].apply(lambda x: extract_stat_from_json(x, 'ppa'))
    home_def_success = home_stats_df['defense_home'].apply(lambda x: extract_stat_from_json(x, 'successRate'))
    home_def_explos = home_stats_df['defense_home'].apply(lambda x: extract_stat_from_json(x, 'explosiveness'))
    
    # Away team stats
    away_off_ppa = away_stats_df['offense_away'].apply(lambda x: extract_stat_from_json(x, 'ppa'))
    away_off_success = away_stats_df['offense_away'].apply(lambda x: extract_stat_from_json(x, 'successRate'))
    away_off_explos = away_stats_df['offense_away'].apply(lambda x: extract_stat_from_json(x, 'explosiveness'))
    away_def_ppa = away_stats_df['defense_away'].apply(lambda x: extract_stat_from_json(x, 'ppa'))
    away_def_success = away_stats_df['defense_away'].apply(lambda x: extract_stat_from_json(x, 'successRate'))
    away_def_explos = away_stats_df['defense_away'].apply(lambda x: extract_stat_from_json(x, 'explosiveness'))
    
    # Fill NaN values and ensure consistent numeric types
    stat_series = [home_off_ppa, home_off_success, home_off_explos, home_def_ppa, home_def_success, home_def_explos,
                   away_off_ppa, away_off_success, away_off_explos, away_def_ppa, away_def_success, away_def_explos]
    
    for stat in stat_series:
        stat.fillna(0, inplace=True)
        # Ensure all values are numeric and reset index to avoid mixed types
        stat.index = range(len(stat))
        
    print("DEBUG: Data types after processing:")
    print(f"home_off_ppa type: {home_off_ppa.dtype}, index type: {type(home_off_ppa.index[0]) if len(home_off_ppa) > 0 else 'empty'}")
    print(f"away_off_ppa type: {away_off_ppa.dtype}, index type: {type(away_off_ppa.index[0]) if len(away_off_ppa) > 0 else 'empty'}")
    
    # --- Build RF_Deep Feature Set (15 features) ---
    features_df = pd.DataFrame({
        # Core home team stats (as if they're the home team in training)
        'off_ppa': home_off_ppa,
        'off_successRate': home_off_success,
        'off_explosiveness': home_off_explos,
        'def_ppa': home_def_ppa,
        'def_successRate': home_def_success,
        'def_explosiveness': home_def_explos,
        # Away team stats (as if they're playing away in training)
        'off_ppa_away': away_off_ppa,
        'off_successRate_away': away_off_success,
        'off_explosiveness_away': away_off_explos,
        'def_ppa_away': away_def_ppa,
        'def_successRate_away': away_def_success,
        'def_explosiveness_away': away_def_explos,
        # Derived features
        'off_eff_diff': home_off_ppa - away_off_ppa,
        'def_eff_diff': home_def_ppa - away_def_ppa,
        'home_advantage': 1.0  # Home team always has advantage
    })
    
    print(f"Generated RF_Deep feature matrix with shape: {features_df.shape}")
    print(f"Features: {list(features_df.columns)}")
    
    # Use all 15 RF_Deep features
    X_pred = features_df[enhanced_features_list].fillna(0)

    # --- Predict ---
    preds = model.predict(X_pred)
    
    # --- Regression to Mean Adjustment for 2025 Predictions ---
    # Since we're using 2024 stats to predict 2025 games, extreme differences
    # should be tempered to account for year-over-year changes, transfers, etc.
    preds = preds * 0.8  # Industry standard scaling for cross-season predictions

    # --- Fetch Lines ---
    print("Fetching Lines...")
    lines = fetch_lines()
    
    # --- Prepare Results ---
    results = {
        'schedule': schedule,
        'predictions': preds,
        'features_df': features_df,
        'X_pred': X_pred,
        'lines': lines
    }
    
    # --- Write Enhanced Predictions to Google Sheets ---
    headers = ['Matchup', 'Favorite', 'Underdog', 'Predicted Difference', 'Line', 'Edge', 'My Prediction', 'Favored Team']
    output = []
    
    print("=== DEBUG: Team Matching Process ===")
    print("My schedule teams vs Vegas teams:")
    
    for i, row in schedule.iterrows():
        home_team = row['Home Team']
        away_team = row['Away Team']
        
        # Check if this game has missing team data
        if i < len(features_df) and 'data_unavailable' in features_df.columns and features_df.iloc[i].get('data_unavailable', False):
            # Show "Team Data Unavailable" for FCS teams
            matchup = f"{away_team} @ {home_team}"
            output.append([
                matchup,
                "N/A",
                "N/A", 
                "Team Data Unavailable",
                "Team Data Unavailable"
            ])
            continue
        
        # Model predicts home team point differential from away team perspective
        # If model output is positive: away team expected to win (away favored)
        # If model output is negative: home team expected to win (home favored)  
        # Display format: negative = favored, positive = underdog
        raw_prediction = float(preds[i])
        my_prediction = raw_prediction  # Keep model's original sign
        
        print(f"\nTrying to match: {home_team} vs {away_team}")
        
        # Try to find matching Line
        line = None
        difference = None
        edge = "No Line Available"
        
        # Try multiple matching strategies for team names
        possible_keys = [
            f"{home_team}_vs_{away_team}",
            f"{away_team}_vs_{home_team}",
            # Try with simplified team names (remove common suffixes)
            f"{home_team.split()[0]}_vs_{away_team.split()[0]}"
        ]
        
        print(f"  Trying keys: {possible_keys}")
        
        # Create a function to match team names by checking if our team name is contained in the Vegas team name
        def normalize_team_name(name):
            """Normalize team names by removing accents and special characters"""
            import unicodedata
            # Remove accents and normalize Unicode
            normalized = unicodedata.normalize('NFD', name)
            normalized = ''.join(char for char in normalized if unicodedata.category(char) != 'Mn')
            # Remove apostrophes and other common variations
            normalized = normalized.replace("'", "").replace("'", "")
            # Handle State variations (Sam Houston State -> Sam Houston)
            normalized = normalized.replace(" State ", " ").replace(" State", "")
            return normalized
        
        def find_vegas_match(schedule_home, schedule_away, lines_dict):
            """Find Line by matching team names (handling mascots and special characters)"""
            # Normalize our team names
            norm_sched_home = normalize_team_name(schedule_home).lower()
            norm_sched_away = normalize_team_name(schedule_away).lower()
            
            for vegas_key, vegas_data in lines_dict.items():
                vegas_home = vegas_data['home_team']
                vegas_away = vegas_data['away_team']
                
                # Normalize Vegas team names
                norm_vegas_home = normalize_team_name(vegas_home).lower()
                norm_vegas_away = normalize_team_name(vegas_away).lower()
                
                # Check if schedule teams match Vegas teams (ignoring mascots and special chars)
                # Case 1: Schedule home matches Vegas home, schedule away matches Vegas away
                if (norm_sched_home in norm_vegas_home and 
                    norm_sched_away in norm_vegas_away):
                    return vegas_data, False  # False = same home/away order
                
                # Case 2: Schedule home matches Vegas away, schedule away matches Vegas home  
                if (norm_sched_home in norm_vegas_away and 
                    norm_sched_away in norm_vegas_home):
                    return vegas_data, True   # True = flipped home/away order
            
            return None, False
        
        # Try to find Vegas match
        vegas_match, is_flipped = find_vegas_match(home_team, away_team, lines)
        
        if vegas_match:
            # Get the correct spread (flip sign if home/away are reversed)
            raw_spread = vegas_match['home_spread']
            if is_flipped:
                vegas_raw = -raw_spread  # Flip sign if teams are reversed
            else:
                vegas_raw = raw_spread
            
            # Convert Line to consistent format: negative = favored, positive = underdog
            # ESPN spread: negative = home favored, positive = home underdog
            # Our format: negative = home favored, positive = home underdog (same as ESPN)
            line = vegas_raw  # Keep ESPN's sign convention
            print(f"  MATCH FOUND: {home_team} vs {away_team} = {line:+.1f}")
            
            difference = my_prediction - line
            
            # Determine edge for value betting
            # difference = my_prediction - vegas_line (both negative = favored, positive = underdog)
            # If difference > 0: My model sees home team as LESS favored than Vegas -> bet away (underdog)
            # If difference < 0: My model sees home team as MORE favored than Vegas -> bet home (favorite)
            if abs(difference) <= 2.5:  # No significant edge
                edge = "No Edge"
            elif difference > 2.5:  # Home team less favored in our model -> bet away team
                edge = f"Bet Away (+{difference:.1f})"
            elif difference < -2.5:  # Home team more favored in our model -> bet home team
                edge = f"Bet Home (+{abs(difference):.1f})"
        
        if line is None:
            print(f"  NO MATCH FOUND for {home_team} vs {away_team}")
            # Show available keys that might be similar
            similar_keys = [k for k in lines.keys() if home_team.split()[0] in k or away_team.split()[0] in k]
            if similar_keys:
                print(f"  Similar available keys: {similar_keys[:3]}")  # Show first 3
        
        # Format the matchup display (Away @ Home format)
        matchup = f"{away_team} @ {home_team}"
        my_pred_display = f"{my_prediction:.1f}"  # No + sign
        
        # Determine favorite/underdog based on our prediction
        # Key insight: prediction number represents how much the HOME team should be favored
        # If prediction is positive, home team is the true favorite  
        # If prediction is negative, away team is the true favorite
        if my_prediction > 0:
            # Home team is the true favorite (positive prediction)
            favorite = home_team
            underdog = away_team
            predicted_difference = abs(my_prediction)
        else:
            # Away team is the true favorite (negative prediction)
            favorite = away_team
            underdog = home_team
            predicted_difference = abs(my_prediction)
        
        # Line: Always positive (your new format)
        if line is not None:
            vegas_spread = abs(line)
            vegas_display = f"{vegas_spread:.1f}"
            # Edge: Absolute difference between our prediction and Vegas line
            edge_value = abs(predicted_difference - vegas_spread)
            edge_display = f"{edge_value:.1f}"
        else:
            vegas_display = "N/A"
            edge_display = "No Line Available"
        
        # Add favored team for clarity (keep for backward compatibility)
        favored_team = f"{favorite} -{predicted_difference:.1f}"
        
        output.append([
            matchup,
            favorite,
            underdog, 
            f"{predicted_difference:.1f}",
            vegas_display,
            edge_display,
            my_pred_display,  # Keep original for reference
            favored_team      # Keep for backward compatibility
        ])
    
    # Add filtered-out games to output
    for invalid_game in invalid_games:
        output.append([
            invalid_game['matchup'],
            "N/A",  # Favorite
            "N/A",  # Underdog
            "N/A",  # Predicted Difference
            "N/A",  # Line
            "Team Data Unavailable",  # Edge
            "N/A",  # My Prediction  
            "Team Data Unavailable"   # Favored Team
        ])
    
    pred_ws.clear()
    pred_ws.update([headers] + output)

    print(f"Enhanced predictions with Vegas comparison written to Google Sheets!")
    print(f"Found Lines for {sum(1 for row in output if row[3] != 'N/A')} out of {len(output)} games")
    
    return results

def make_predictions_only(schedule_data=None):
    """Make predictions without writing to Google Sheets - for confidence analysis"""
    # --- Load Best Working Model (prioritize what works) ---
    try:
        # Try the original working 4-feature models first
        linear_model_path = BASE_DIR / "models" / "linear_regression_model.joblib"
        if linear_model_path.exists():
            model = joblib.load(str(linear_model_path))
            print("Loaded working Linear Regression model (4 features)")
            use_simple_features = True
        else:
            # Fallback to original random forest
            rf_model_path = BASE_DIR / "models" / "random_forest_model.joblib" 
            model = joblib.load(str(rf_model_path))
            print("Loaded working Random Forest model (4 features)")
            use_simple_features = True
    except:
        # Last resort - enhanced model (but we know it gives bad predictions)
        model = joblib.load(str(MODEL_PATH))
        with open(str(FEATURES_PATH)) as f:
            features = [line.strip() for line in f]
        print(f"WARNING: Using enhanced model with {len(features)} features - predictions may be poor")
        use_simple_features = False
    
    mapping_df = pd.read_csv(MAPPING_CSV)
    mapping_dict = dict(zip(mapping_df['ESPN_School'], mapping_df['Model_School']))
    
    # --- Load Latest Stats ---
    stats_file = DATA_DIR / "cfbd_team_stats_2024_final.csv"
    if not stats_file.exists():
        raise FileNotFoundError("2024 final stats file not found!")
    stats_df = pd.read_csv(str(stats_file))

    # --- Use provided schedule or load from sheets ---
    if schedule_data is not None:
        schedule = schedule_data.copy()
    else:
        # Load from Google Sheets as before
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT)
        client = gspread.authorize(creds.with_scopes([
            "https://www.googleapis.com/auth/spreadsheets"
        ]))
        schedule_ws = client.open_by_key(SHEET_ID).worksheet(SCHEDULE_TAB)
        schedule = pd.DataFrame(schedule_ws.get_all_records())

    # --- Map team names using mapping CSV ---
    def map_team(name):
        mapped = mapping_dict.get(name)
        if mapped is None:
            print(f"WARNING: {name} not found in mapping file, skipping")
            return None
        return mapped

    schedule['Home_Model'] = schedule['Home Team'].map(map_team)
    schedule['Away_Model'] = schedule['Away Team'].map(map_team)
    
    # Filter out games with unmapped teams
    schedule = schedule.dropna(subset=['Home_Model', 'Away_Model'])
    print(f"Making predictions for {len(schedule)} games with valid team mappings")
    
    # Reset index after filtering
    schedule = schedule.reset_index(drop=True)
    
    # Keep original case for team mapping (don't uppercase yet)
    schedule['Home_Model'] = schedule['Home_Model'].str.strip()
    schedule['Away_Model'] = schedule['Away_Model'].str.strip()

    if use_simple_features:
        # --- ORIGINAL WORKING 4-FEATURE APPROACH ---
        print("=== USING PROVEN 4-FEATURE APPROACH (make_predictions_only) ===")
        print(f"Building simple feature set for {len(schedule)} games...")

        # --- Get team stats for each game ---
        home_stats_list = []
        away_stats_list = []
        
        def get_team_stats(team_name):
            # Try exact match first, then case-insensitive
            match = stats_df[stats_df['team'] == team_name]
            if match.empty:
                # Try case-insensitive match
                match = stats_df[stats_df['team'].str.upper() == team_name.upper()]
            if match.empty:
                print(f"WARNING: No stats found for team '{team_name}'")
                return pd.Series({'season': None, 'team': None, 'conference': None, 'offense': '{}', 'defense': '{}'})
            return match.iloc[0]
        
        for _, row in schedule.iterrows():
            home_stats_list.append(get_team_stats(row['Home_Model']))
            away_stats_list.append(get_team_stats(row['Away_Model']))
        
        home_stats_df = pd.DataFrame(home_stats_list).add_suffix('_home')
        away_stats_df = pd.DataFrame(away_stats_list).add_suffix('_away')

        # --- Extract PPA values from JSON data ---
        import json
        
        def extract_ppa_from_json(json_str, stat_type='offense'):
            try:
                if pd.isna(json_str) or json_str == '{}' or not json_str:
                    return 0.0
                data = json.loads(json_str.replace("'", '"'))
                return float(data.get('ppa', 0)) if data else 0.0
            except Exception:
                return 0.0
        
        # Extract offensive and defensive PPA values
        home_off_ppa = home_stats_df['offense_home'].apply(lambda x: extract_ppa_from_json(x, 'offense'))
        home_def_ppa = home_stats_df['defense_home'].apply(lambda x: extract_ppa_from_json(x, 'defense'))
        away_off_ppa = away_stats_df['offense_away'].apply(lambda x: extract_ppa_from_json(x, 'offense'))
        away_def_ppa = away_stats_df['defense_away'].apply(lambda x: extract_ppa_from_json(x, 'defense'))
        
        # Reset indices to ensure proper alignment
        home_off_ppa = home_off_ppa.reset_index(drop=True).fillna(0)
        home_def_ppa = home_def_ppa.reset_index(drop=True).fillna(0)
        away_off_ppa = away_off_ppa.reset_index(drop=True).fillna(0)
        away_def_ppa = away_def_ppa.reset_index(drop=True).fillna(0)
        
        # --- Simple Feature Engineering (4 features) ---
        # Scale PPA differences by 500x to match training data scale
        off_eff_diff = (home_off_ppa - away_off_ppa) * 500
        def_eff_diff = (home_def_ppa - away_def_ppa) * 500
        
        features_df = pd.DataFrame({
            'off_eff_diff': off_eff_diff,
            'def_eff_diff': def_eff_diff,
            'is_home_favorite': 0,  # Default to 0 for now
            'line': 0         # Default to 0 for now
        })
        
        print(f"Generated simple feature matrix with shape: {features_df.shape}")
        print(f"Features: {list(features_df.columns)}")
        
        # Use only the 4 simple features that the working model expects
        simple_features = ['off_eff_diff', 'def_eff_diff', 'is_home_favorite', 'line']
        X_pred = features_df[simple_features].fillna(0)
        
    else:
        # --- ENHANCED MODEL APPROACH (gives poor predictions) ---
        print(f"WARNING: Using enhanced model approach - predictions will be poor")
        features_df = pd.DataFrame(0.0, index=range(len(schedule)), columns=features)
        X_pred = features_df

    # --- Predict ---
    preds = model.predict(X_pred)
    
    # --- Regression to Mean Adjustment for 2025 Predictions ---
    # Since we're using 2024 stats to predict 2025 games, extreme differences
    # should be tempered to account for year-over-year changes, transfers, etc.
    preds = preds * 0.8  # Industry standard scaling for cross-season predictions
    
    # --- Return Results ---
    results = {
        'schedule': schedule,
        'predictions': preds,
        'features_df': features_df,
        'X_pred': X_pred,
        'model': model
    }
    
    if not use_simple_features:
        results['features'] = features
    
    return results

def main():
    try:
        print("Starting automation...")
        week = update_stats()
        schedule = pull_schedule(week)
        write_schedule_to_sheet(schedule)
        make_predictions()
        print("Success! All steps completed.")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)

def debug_predictions():
    """Debug version of make_predictions() with detailed logging"""
    print("=== DEBUG: Starting debug_predictions() function ===")
    
    # --- Load Artifacts ---
    model = joblib.load(str(MODEL_PATH))
    with open(str(FEATURES_PATH)) as f:
        features = [line.strip() for line in f]
    mapping_df = pd.read_csv(MAPPING_CSV)
    mapping_dict = dict(zip(mapping_df['ESPN_School'], mapping_df['Model_School']))
    
    # --- Load Latest Stats ---
    stats_file = DATA_DIR / "cfbd_team_stats_2024_final.csv"
    if not stats_file.exists():
        raise FileNotFoundError("2024 final stats file not found!")
    stats_df = pd.read_csv(str(stats_file))
    print(f"Loaded {len(stats_df)} team stats from {stats_file}")

    # --- Load Schedule from Google Sheets ---
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT)
    client = gspread.authorize(creds.with_scopes([
        "https://www.googleapis.com/auth/spreadsheets"
    ]))
    schedule_ws = client.open_by_key(SHEET_ID).worksheet(SCHEDULE_TAB)
    schedule = pd.DataFrame(schedule_ws.get_all_records())
    print(f"Loaded {len(schedule)} games from schedule")

    # --- Map team names using mapping CSV ---
    def map_team(name):
        mapped = mapping_dict.get(name)
        if mapped is None:
            print(f"WARNING: {name} not found in mapping file, skipping")
            return None
        return mapped

    schedule['Home_Model'] = schedule['Home Team'].map(map_team)
    schedule['Away_Model'] = schedule['Away Team'].map(map_team)
    
    # Filter out games with unmapped teams
    schedule = schedule.dropna(subset=['Home_Model', 'Away_Model'])
    print(f"Making predictions for {len(schedule)} games with valid team mappings")
    
    # Reset index after filtering
    schedule = schedule.reset_index(drop=True)
    
    # Keep original case for team mapping (don't uppercase yet)
    schedule['Home_Model'] = schedule['Home_Model'].str.strip()
    schedule['Away_Model'] = schedule['Away_Model'].str.strip()

    # --- Use Comprehensive Feature Engineering ---
    print("=== USING COMPREHENSIVE 274-FEATURE ENGINEERING (debug_predictions) ===")
    print(f"Building complete feature set for {len(schedule)} games...")
    
    # Use the comprehensive feature engineering function
    features_df = process_schedule_to_features(schedule, stats_df, features)
    
    # Filter schedule to match games that were successfully processed
    schedule = schedule.iloc[:len(features_df)].reset_index(drop=True)
    
    print(f"Generated complete feature matrix with shape: {features_df.shape}")
    print("=== DEBUG: Final Features DataFrame ===")
    print(features_df.describe())
    print("First 10 feature values:")
    print(features_df.head(10))
    
    X_pred = features_df

    # --- Predict ---
    preds = model.predict(X_pred)
    
    # --- Regression to Mean Adjustment for 2025 Predictions ---
    # Since we're using 2024 stats to predict 2025 games, extreme differences
    # should be tempered to account for year-over-year changes, transfers, etc.
    preds = preds * 0.8  # Industry standard scaling for cross-season predictions

    # --- Return Results ---
    results = {
        'schedule': schedule,
        'predictions': preds,
        'features_df': features_df,
        'X_pred': X_pred
    }
    
    print("=== DEBUG: Prediction Results ===")
    print(f"Predictions - min: {preds.min():.4f}, max: {preds.max():.4f}, mean: {preds.mean():.4f}")
    
    return results

if __name__ == "__main__":
    main()
