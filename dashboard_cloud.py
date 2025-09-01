#!/usr/bin/env python3
"""
Enhanced NCAA Football Betting Dashboard - PUBLIC VERSION
- Pulls from Google Sheets (Predictions & Cover Analysis)
- Clean card-based UX showing betting recommendations
- Performance tracking with visual metrics
- Configured for Streamlit Cloud deployment
"""

import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configuration for public deployment
SHEET_ID = "1Rmj5fbhwkQivv98hR5GqCNhBkV8-EwEtEA74bsC6wAU"

st.set_page_config(
    page_title="NCAA Football Betting Dashboard", 
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_google_sheets_data():
    """Load data from Google Sheets using Streamlit secrets"""
    try:
        # Try Streamlit secrets first (for public deployment)
        if "google_service_account" in st.secrets:
            credentials = st.secrets["google_service_account"]
            gc = gspread.service_account_from_dict(credentials)
        else:
            # Fallback to local file for development
            SERVICE_ACCOUNT = r"C:\Users\31198\AppData\Local\Programs\Python\Python313\kentraining.json"
            gc = gspread.service_account(filename=SERVICE_ACCOUNT)
        
        spreadsheet = gc.open_by_key(SHEET_ID)
        
        # Load Predictions
        pred_sheet = spreadsheet.worksheet("Predictions")
        pred_data = pred_sheet.get_all_values()
        predictions_df = pd.DataFrame(pred_data[1:], columns=pred_data[0]) if len(pred_data) > 1 else pd.DataFrame()
        
        # Load Cover Analysis
        try:
            cover_sheet = spreadsheet.worksheet("Cover Analysis")
            cover_data = cover_sheet.get_all_values()
            # Skip summary rows and get actual data
            cover_df = pd.DataFrame(cover_data[4:], columns=cover_data[3]) if len(cover_data) > 4 else pd.DataFrame()
        except:
            cover_df = pd.DataFrame()
        
        return predictions_df, cover_df
        
    except Exception as e:
        st.error(f"Error loading sheets data: {e}")
        return pd.DataFrame(), pd.DataFrame()

def main():
    st.title("🏈 NCAA Football Betting Dashboard")
    st.markdown("**Live predictions and performance tracking**")
    
    # Load data
    predictions_df, cover_df = load_google_sheets_data()
    
    if predictions_df.empty:
        st.error("No predictions data found")
        return
    
    # Sidebar
    st.sidebar.title("📊 Dashboard Controls")
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Filter controls
    show_only_lines = st.sidebar.checkbox("Only show games with lines", value=True)
    min_edge = st.sidebar.slider("Minimum edge threshold", 0.0, 10.0, 2.0, 0.5)
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Current Bets", "📈 Performance", "📋 All Games"])
    
    with tab1:
        st.header("🎯 Current Week Betting Opportunities")
        
        # Filter predictions for games with lines
        current_bets = predictions_df.copy()
        
        if show_only_lines:
            current_bets = current_bets[
                (current_bets['Line'] != 'N/A') & 
                (current_bets['Line'] != 'No Line Available') &
                (current_bets['Line'] != '')
            ]
        
        if current_bets.empty:
            st.warning("No games with betting lines available")
        else:
            # Process betting opportunities
            betting_opps = []
            
            for _, row in current_bets.iterrows():
                try:
                    matchup = row['Matchup']
                    favorite = row['Favorite']
                    underdog = row['Underdog'] 
                    pred_diff = float(row['Predicted Difference'])
                    vegas_line = float(row['Line'])
                    edge = float(row['Edge']) if row['Edge'] != 'No Line Available' else 0
                    
                    # Determine betting recommendation
                    if edge >= min_edge:
                        if pred_diff > vegas_line:
                            bet_rec = f"Take {favorite} -{vegas_line}"
                            bet_type = "Favorite"
                        else:
                            bet_rec = f"Take {underdog} +{vegas_line}"
                            bet_type = "Underdog"
                        
                        confidence = "High" if edge >= 5.0 else "Medium" if edge >= 3.0 else "Low"
                        
                        betting_opps.append({
                            'Game': matchup,
                            'Bet': bet_rec,
                            'Type': bet_type,
                            'Edge': edge,
                            'Confidence': confidence,
                            'Our Prediction': f"{favorite} -{pred_diff}",
                            'Vegas Line': f"{vegas_line}"
                        })
                        
                except (ValueError, KeyError):
                    continue
            
            if betting_opps:
                bet_df = pd.DataFrame(betting_opps)
                bet_df = bet_df.sort_values('Edge', ascending=False)
                
                # Display all bets as cards
                st.subheader(f"🎯 Betting Opportunities (Edge ≥ {min_edge})")
                
                # Create cards in rows of 2
                for i in range(0, len(bet_df), 2):
                    cols = st.columns(2)
                    
                    for j, col in enumerate(cols):
                        if i + j < len(bet_df):
                            bet = bet_df.iloc[i + j]
                            
                            # Determine card color based on edge/confidence
                            if bet['Edge'] >= 5.0:
                                card_color = "#FF6B6B"  # Red for high value
                                confidence_emoji = "🔥"
                            elif bet['Edge'] >= 3.0:
                                card_color = "#4ECDC4"  # Teal for good value
                                confidence_emoji = "⚡"
                            else:
                                card_color = "#95E1D3"  # Light green for some value
                                confidence_emoji = "📊"
                            
                            with col:
                                # Create custom card using markdown and containers
                                with st.container():
                                    st.markdown(
                                        f"""
                                        <div style="
                                            border: 2px solid {card_color};
                                            border-radius: 10px;
                                            padding: 15px;
                                            margin: 10px 0;
                                            background-color: rgba(255,255,255,0.05);
                                        ">
                                            <h3 style="margin: 0; color: {card_color};">
                                                {confidence_emoji} {bet['Bet']}
                                            </h3>
                                            <p style="margin: 5px 0; font-size: 14px; opacity: 0.8;">
                                                {bet['Game']}
                                            </p>
                                            <div style="display: flex; justify-content: space-between; margin-top: 10px;">
                                                <span><strong>Edge:</strong> {bet['Edge']:.1f}</span>
                                                <span><strong>Type:</strong> {bet['Type']}</span>
                                                <span><strong>Confidence:</strong> {bet['Confidence']}</span>
                                            </div>
                                            <div style="margin-top: 8px; font-size: 12px; opacity: 0.7;">
                                                Our Prediction: {bet['Our Prediction']} | Vegas: {bet['Vegas Line']}
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
            else:
                st.info(f"No betting opportunities found with edge ≥ {min_edge}")
    
    with tab2:
        st.header("📈 Model Performance")
        
        if not cover_df.empty:
            try:
                # Clean and process cover analysis data
                cover_clean = cover_df.copy()
                cover_clean = cover_clean[cover_clean['Result'].isin(['WIN', 'LOSS'])]
                
                if not cover_clean.empty:
                    # Performance metrics
                    total_bets = len(cover_clean)
                    wins = len(cover_clean[cover_clean['Result'] == 'WIN'])
                    win_rate = (wins / total_bets) * 100
                    
                    # Display key metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Bets", total_bets)
                    with col2:
                        st.metric("Wins", wins)
                    with col3:
                        st.metric("Win Rate", f"{win_rate:.1f}%")
                    with col4:
                        profit_units = wins * 1.0 - (total_bets - wins) * 1.1  # Assuming -110 odds
                        st.metric("Profit (Units)", f"{profit_units:+.1f}")
                    
                    # Performance chart
                    st.subheader("Performance Over Time")
                    
                    # Create cumulative performance chart
                    cover_clean['Game_Number'] = range(1, len(cover_clean) + 1)
                    cover_clean['Cumulative_Wins'] = (cover_clean['Result'] == 'WIN').cumsum()
                    cover_clean['Win_Rate_Rolling'] = cover_clean['Cumulative_Wins'] / cover_clean['Game_Number'] * 100
                    
                    fig = px.line(
                        cover_clean, 
                        x='Game_Number', 
                        y='Win_Rate_Rolling',
                        title='Win Rate Over Time',
                        labels={'Game_Number': 'Game Number', 'Win_Rate_Rolling': 'Win Rate (%)'}
                    )
                    fig.add_hline(y=52.38, line_dash="dash", line_color="green", 
                                annotation_text="Breakeven (52.38%)")
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Recent performance
                    st.subheader("Recent Games")
                    recent_games = cover_clean.tail(10)[['Game', 'Our Bet', 'Result']].copy()
                    recent_games['Status'] = recent_games['Result'].apply(
                        lambda x: '✅' if x == 'WIN' else '❌'
                    )
                    st.dataframe(recent_games, use_container_width=True)
                    
                else:
                    st.warning("No valid cover analysis data found")
                    
            except Exception as e:
                st.error(f"Error processing cover analysis: {e}")
        else:
            st.warning("No cover analysis data available")
    
    with tab3:
        st.header("📋 All Current Games")
        
        if not predictions_df.empty:
            # Clean predictions data
            display_df = predictions_df.copy()
            
            # Add status indicators
            display_df['Status'] = display_df['Line'].apply(
                lambda x: '📈 Line Available' if x not in ['N/A', 'No Line Available', ''] else '⏳ No Line'
            )
            
            # Add edge categorization
            def categorize_edge(edge_str):
                try:
                    edge = float(edge_str)
                    if edge >= 5.0:
                        return '🔥 High Value'
                    elif edge >= 3.0:
                        return '⚡ Good Value'
                    elif edge >= 1.0:
                        return '📊 Some Value'
                    else:
                        return '❌ No Edge'
                except:
                    return '❓ Unknown'
            
            display_df['Edge Category'] = display_df['Edge'].apply(categorize_edge)
            
            # Display table
            st.dataframe(
                display_df[['Matchup', 'Favorite', 'Predicted Difference', 'Line', 'Edge', 'Edge Category', 'Status']],
                use_container_width=True
            )
        else:
            st.error("No predictions data available")
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
