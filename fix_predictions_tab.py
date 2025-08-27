#!/usr/bin/env python3
"""
Fix the Google Sheets Predictions tab with clean data
"""

import sys
sys.path.append('src/prediction')
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os

# Load configuration
def load_sheets_config():
    """Load Google Sheets configuration"""
    try:
        import streamlit as st
        return {
            'sheet_id': st.secrets["sheets"]["sheet_id"],
            'service_account': dict(st.secrets["google_service_account"])
        }
    except:
        # Fallback - try loading from secrets.toml or environment
        import tomli
        try:
            with open('.streamlit/secrets.toml', 'rb') as f:
                secrets = tomli.load(f)
            return {
                'sheet_id': secrets["sheets"]["sheet_id"],
                'service_account': secrets["google_service_account"]
            }
        except:
            print("Error: Could not load Google Sheets credentials")
            return None

def create_clean_predictions_data():
    """Create clean predictions data from ESPN scraper"""
    from espn_scraper import pull_espn_schedule
    
    print("Getting clean schedule from ESPN scraper...")
    schedule = pull_espn_schedule()
    
    print(f"Found {len(schedule)} games")
    
    # Create predictions format
    predictions = []
    
    for _, game in schedule.iterrows():
        home_team = game['Home Team']
        away_team = game['Away Team']
        
        predictions.append({
            'Week': 1,
            'Home Team': home_team,
            'Away Team': away_team,
            'Matchup': f"{away_team} vs {home_team}",
            'Predicted_Spread': 0.0,  # Placeholder
            'RF_Deep_Prediction': 0.0,  # Placeholder 
            'Confidence': 'Medium',
            'Vegas_Line': 'N/A',
            'Edge': 0.0
        })
    
    return pd.DataFrame(predictions)

def update_google_sheets(df, config):
    """Update Google Sheets with clean predictions"""
    try:
        # Set up Google Sheets connection
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(
            config['service_account'], 
            scopes=scopes
        )
        gc = gspread.authorize(creds)
        
        # Open spreadsheet
        spreadsheet = gc.open_by_key(config['sheet_id'])
        
        # Update Predictions tab
        try:
            predictions_sheet = spreadsheet.worksheet('Predictions')
        except:
            # Create the tab if it doesn't exist
            predictions_sheet = spreadsheet.add_worksheet(title='Predictions', rows=200, cols=20)
        
        # Clear existing data
        predictions_sheet.clear()
        
        # Upload new data
        # Convert DataFrame to list of lists for upload
        data_to_upload = [df.columns.tolist()] + df.values.tolist()
        
        predictions_sheet.update('A1', data_to_upload)
        
        print(f"SUCCESS: Updated Predictions tab with {len(df)} clean games!")
        return True
        
    except Exception as e:
        print(f"Error updating Google Sheets: {e}")
        return False

def main():
    print("Fixing Google Sheets Predictions tab with clean data...")
    
    # Load configuration
    config = load_sheets_config()
    if not config:
        print("Failed to load configuration")
        return
    
    # Create clean predictions data
    df = create_clean_predictions_data()
    
    print(f"Created predictions for {len(df)} games")
    print("Sample games:")
    for i in range(min(5, len(df))):
        print(f"  {df.iloc[i]['Matchup']}")
    
    # Update Google Sheets
    success = update_google_sheets(df, config)
    
    if success:
        print("\n✅ Google Sheets updated successfully!")
        print("You can now refresh your Streamlit dashboard to see clean data.")
    else:
        print("\n❌ Failed to update Google Sheets")

if __name__ == "__main__":
    main()