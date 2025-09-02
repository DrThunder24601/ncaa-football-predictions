#!/usr/bin/env python3
"""
Betting Dashboard - Uses your existing kentraining.json file
"""

import streamlit as st
import pandas as pd
import gspread

# Configuration using your existing file
SHEET_ID = "1Rmj5fbhwkQivv98hR5GqCNhBkV8-EwEtEA74bsC6wAU"
SERVICE_ACCOUNT = r"C:\Users\31198\AppData\Local\Programs\Python\Python313\kentraining.json"

@st.cache_data(ttl=300)
def get_betting_data():
    """Get betting predictions from Google Sheets"""
    try:
        gc = gspread.service_account(filename=SERVICE_ACCOUNT)
        spreadsheet = gc.open_by_key(SHEET_ID)
        
        predictions_sheet = spreadsheet.worksheet("Predictions")
        data = predictions_sheet.get_all_values()
        
        if len(data) < 2:
            return pd.DataFrame()
        
        df = pd.DataFrame(data[1:], columns=data[0])
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def get_edge_band(edge):
    """Categorize edge into performance bands"""
    if edge < 2:
        return "0-2", "🔴"  # Red - Avoid
    elif edge < 5:
        return "2-5", "🟡"  # Yellow - Weak  
    elif edge < 7:
        return "5-7", "🟢"  # Green - Good
    elif edge < 9:
        return "7-9", "🔥"  # Fire - Excellent
    elif edge < 12:
        return "9-12", "💎"  # Diamond - Strong
    else:
        return "12+", "👑"  # Crown - Elite

def analyze_betting_opportunity(row):
    """Analyze if this game has betting value"""
    try:
        model_pred = float(row.get('My Prediction', 0))
        vegas_line_str = row.get('Line', 'N/A')
        matchup = row.get('Matchup', '')
        
        if vegas_line_str == 'N/A' or vegas_line_str == '':
            return {
                'bet_recommendation': 'No Line Available',
                'edge_size': 0,
                'confidence': 'None',
                'edge_band': 'N/A',
                'band_emoji': '⚫'
            }
        
        vegas_line = float(vegas_line_str)
        edge = abs(model_pred - vegas_line)
        edge_band, band_emoji = get_edge_band(edge)
        
        # Parse teams
        if '@' not in matchup:
            return {
                'bet_recommendation': 'Cannot parse teams', 
                'edge_size': 0, 
                'confidence': 'None',
                'edge_band': 'N/A',
                'band_emoji': '⚫'
            }
        
        away_team = matchup.split('@')[0].strip()
        home_team = matchup.split('@')[1].strip()
        
        # No edge if difference is small
        if edge < 2.5:
            return {
                'bet_recommendation': 'No Edge',
                'edge_size': edge,
                'confidence': 'None',
                'edge_band': edge_band,
                'band_emoji': band_emoji
            }
        
        # Determine betting recommendation
        if model_pred > vegas_line:
            # Model thinks home team less favored -> Bet away team
            bet_team = away_team
            bet_line = f"+{abs(vegas_line)}" if vegas_line < 0 else str(vegas_line)
        else:
            # Model thinks home team more favored -> Bet home team
            bet_team = home_team
            bet_line = f"{vegas_line:+.1f}"
        
        # Updated confidence based on historical performance
        if edge >= 12:
            confidence = 'Elite (64%)'
        elif edge >= 9:
            confidence = 'Strong (60%)'
        elif edge >= 7:
            confidence = 'Excellent (100%)'
        elif edge >= 5:
            confidence = 'Good (75%)'
        else:
            confidence = 'Weak (40%)'
        
        return {
            'bet_recommendation': f"Bet {bet_team} {bet_line}",
            'edge_size': edge,
            'confidence': confidence,
            'edge_band': edge_band,
            'band_emoji': band_emoji
        }
        
    except Exception as e:
        return {
            'bet_recommendation': f'Error: {e}', 
            'edge_size': 0, 
            'confidence': 'None',
            'edge_band': 'N/A',
            'band_emoji': '⚫'
        }

def main():
    st.set_page_config(
        page_title="NCAA Betting Dashboard", 
        page_icon="💰",
        layout="wide"
    )
    
    st.title("💰 NCAA Betting Dashboard")
    st.write("**Which games to bet this week (0.8 scaling factor)**")
    
    # Get data
    df = get_betting_data()
    
    if df.empty:
        st.error("No predictions found")
        st.code("python daily_workflow.py")
        return
    
    # Analyze each game for betting value
    betting_opportunities = []
    all_games_analysis = []
    
    for _, row in df.iterrows():
        analysis = analyze_betting_opportunity(row)
        
        # Track all games for band analysis
        all_games_analysis.append({
            'Game': row.get('Matchup', ''),
            'Edge': analysis['edge_size'],
            'Band': analysis['edge_band'],
            'Emoji': analysis['band_emoji'],
            'Confidence': analysis['confidence'],
            'Model': row.get('My Prediction', ''),
            'Vegas': row.get('Line', ''),
            'Bet_Rec': analysis['bet_recommendation']
        })
        
        if analysis['bet_recommendation'] not in ['No Line Available', 'No Edge', 'Cannot parse teams']:
            betting_opportunities.append({
                'Game': row.get('Matchup', ''),
                'BET_THIS': analysis['bet_recommendation'],
                'Edge': analysis['edge_size'],
                'Confidence': analysis['confidence'],
                'Model': row.get('My Prediction', ''),
                'Vegas': row.get('Line', ''),
                'Raw_Edge': row.get('Edge', ''),
                'Band': analysis['edge_band'],
                'Emoji': analysis['band_emoji']
            })
    
    # SHOW BETTING OPPORTUNITIES
    if betting_opportunities:
        st.success(f"🎯 **{len(betting_opportunities)} GAMES TO BET**")
        
        # Sort by edge size (biggest first)
        betting_df = pd.DataFrame(betting_opportunities)
        betting_df = betting_df.sort_values('Edge', ascending=False)
        
        for _, row in betting_df.iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.write(f"**{row['Game']}**")
                    st.write(f"{row['Emoji']} **{row['BET_THIS']}** ({row['Confidence']})")
                
                with col2:
                    st.metric("Edge", f"{row['Edge']:.1f}")
                    st.caption(f"Band: {row['Band']}")
                
                with col3:
                    st.caption(f"Model: {row['Model']}")
                    st.caption(f"Vegas: {row['Vegas']}")
                
                st.divider()
    else:
        st.warning("No value betting opportunities found")
        st.info("Check back after lines are posted closer to game time")
    
    # Show summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Games", len(df))
    with col2:
        st.metric("Value Bets", len(betting_opportunities))
    with col3:
        lines_available = len(df[df['Line'] != 'N/A'])
        st.metric("Lines Available", f"{lines_available}/{len(df)}")
    
    # Show all predictions grouped by edge bands
    st.header("📊 All Predictions by Confidence Band")
    
    # Group games by edge band
    band_groups = {}
    for game in all_games_analysis:
        band = game['Band']
        if band not in band_groups:
            band_groups[band] = []
        band_groups[band].append(game)
    
    # Display each band
    band_order = ['12+', '9-12', '7-9', '5-7', '2-5', '0-2', 'N/A']
    for band in band_order:
        if band in band_groups and band_groups[band]:
            games = band_groups[band]
            emoji = games[0]['Emoji']
            
            with st.expander(f"{emoji} {band} Point Edge ({len(games)} games)", 
                           expanded=(band in ['12+', '9-12', '7-9'])):  # Expand high-confidence bands
                
                for game in sorted(games, key=lambda x: x['Edge'], reverse=True):
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
                    
                    with col1:
                        st.write(f"**{game['Game']}**")
                    with col2:
                        if game['Edge'] > 0:
                            st.metric("Edge", f"{game['Edge']:.1f}")
                        else:
                            st.write("No Line")
                    with col3:
                        st.write(f"Model: {game['Model']}")
                        st.write(f"Vegas: {game['Vegas']}")
                    with col4:
                        if game['Bet_Rec'] not in ['No Line Available', 'No Edge']:
                            st.write(f"**{game['Bet_Rec']}**")
                        else:
                            st.write(game['Bet_Rec'])
    
    # Edge Band Performance Metrics
    st.sidebar.header("📊 Edge Band Performance")
    st.sidebar.caption("Historical win rates by edge size:")
    
    band_performance = {
        "🔴 0-2 pts": "2-3 (40%)",
        "🟡 2-5 pts": "3-5 (37%)", 
        "🟢 5-7 pts": "3-1 (75%)",
        "🔥 7-9 pts": "2-0 (100%)",
        "💎 9-12 pts": "3-2 (60%)",
        "👑 12+ pts": "9-5 (64%)"
    }
    
    for band, record in band_performance.items():
        st.sidebar.write(f"{band}: {record}")
    
    st.sidebar.divider()
    st.sidebar.success("🏆 **Overall: 22-16 (57.9%)**")
    st.sidebar.caption("Avoid 0-5 pt edges • Target 5+ pt edges")
    
    if st.button("🔄 Refresh"):
        st.cache_data.clear()
        st.rerun()

if __name__ == "__main__":
    main()