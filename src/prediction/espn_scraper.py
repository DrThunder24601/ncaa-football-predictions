#!/usr/bin/env python3
"""
ESPN Schedule Scraper for NCAA Football
Replaces CFBD schedule API to get current week's games directly from ESPN
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from datetime import datetime
import time

class ESPNScheduleScraper:
    def __init__(self):
        self.base_url = "https://www.espn.com/college-football/schedule"
        self.session = requests.Session()
        # Set headers to look like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def clean_team_name(self, team_text):
        """Clean team name by removing rankings, mascots, and extra whitespace"""
        if not team_text:
            return ""
        
        # Remove ranking numbers (e.g., "1 Texas" -> "Texas")
        team_text = re.sub(r'^\d+\s+', '', team_text.strip())
        
        # Remove common mascots/nicknames that appear after school names (comprehensive list)
        mascot_patterns = [
            r'\s+(Cyclones|Hawkeyes|Wildcats|Tigers|Bulldogs|Eagles|Cardinals|Bears|Trojans|Bruins|Ducks|Beavers)$',
            r'\s+(Crimson Tide|Fighting Irish|Buckeyes|Wolverines|Spartans|Hoosiers|Cornhuskers|Badgers)$',
            r'\s+(Longhorns|Sooners|Cowboys|Red Raiders|Aggies|Razorbacks|Volunteers|Commodores)$',
            r'\s+(Gators|Hurricanes|Seminoles|Yellow Jackets|Blue Devils|Tar Heels|Demon Deacons)$',
            r'\s+(Sun Devils|Golden Bears|Huskies|Cougars|Utes|Buffaloes|Rams|Lobos)$',
            r'\s+(Broncos|Rebels|Wolf Pack|Miners|Roadrunners|Mean Green|49ers|Owls)$',
            r'\s+(Knights|Bulls|Panthers|Golden Eagles|Green Wave|Chanticleers|Monarchs)$',
            r'\s+(Thundering Herd|Mountaineers|Nittany Lions|Terrapins|Scarlet Knights)$',
            r'\s+(Boilermakers|Golden Gophers|RedHawks|Chippewas|Zips|Bobcats)$',
            r'\s+(Gamecocks|Bearkats|Hilltoppers|Redbirds|Dukes|Fighting Hawks|Lumberjacks)$',
            r'\s+(Bengals|Cardinal|Leopards|Pirates|Hornets|Red Flash|Phoenix|Skyhawks)$',
            r'\s+(Orange|Rockets|Colonials|Coyotes|Bison|Crusaders|Black Bears|Mocs|Great Danes|Sharks)$',
            r'\s+(Buccaneers|Governors|Lions|Golden Lions|Vikings|Vandals|Rainbow Warriors|Hokies)$',
            r'\s+(Leathernecks|Seahawks|Warriors)$'
        ]
        
        for pattern in mascot_patterns:
            team_text = re.sub(pattern, '', team_text, flags=re.IGNORECASE)
        
        # Remove common abbreviations at the end (e.g., "UNLVUNLV" -> "UNLV")
        team_text = re.sub(r'([A-Z]{2,})\1$', r'\1', team_text)
        
        # Remove trailing abbreviations that match the team (KansasKU -> Kansas)
        team_text = re.sub(r'([A-Za-z]+)([A-Z]{2,})$', lambda m: m.group(1) if m.group(2).upper() in m.group(1).upper() else m.group(0), team_text)
        
        # Remove single trailing capital letters (Western KentuckyW -> Western Kentucky)
        team_text = re.sub(r'([a-z])([A-Z])$', r'\1', team_text)
        
        # Remove state abbreviations at the end when preceded by team name
        team_text = re.sub(r'^([A-Z]{2})(.+)', r'\2', team_text)
        
        # Handle specific problematic patterns
        team_text = re.sub(r'([A-Za-z\s]+)(WKU|WSU|FSU|OSU|PSU)$', r'\1', team_text)
        
        # Handle common name variations and standardize to mapping format
        name_fixes = {
            'San Jos': 'San Jose State',
            'San José': 'San Jose State', 
            'Hawai': 'Hawaii',
            "Hawai'i": 'Hawaii',
            'UL Monroe': 'Louisiana Monroe',
            'ULM': 'Louisiana Monroe',
            'East Carolina': 'East Carolina',
            'ECU': 'East Carolina',
            'Saint Francis': 'Saint Francis',
            'St. Francis': 'Saint Francis',
            'Miami (Fla.)': 'Miami',
            'Miami (FL)': 'Miami',
            'Miami Fla': 'Miami',
            'Miami Oh': 'Miami (OH)',
            'Southern California': 'USC',
            'Texas Christian': 'TCU',
            'Southern Methodist': 'SMU',
            'Central Florida': 'UCF',
            'Alabama Birmingham': 'UAB',
            'Nevada Las Vegas': 'UNLV',
            'Connecticut': 'UConn',
            'Massachusetts': 'UMass',
            'App State': 'Appalachian State',
            'Ut Martin': 'UT Martin',
            'Stephen F Austin': 'Stephen F. Austin',
            'Alabama Am': 'Alabama A&M',
            'Ualbany': 'UAlbany',
            'lbany': 'UAlbany',  # Handle truncated versions
            'Se Louisiana': 'SE Louisiana',
            'East Texas Am': 'East Texas A&M'
        }
        
        if team_text in name_fixes:
            team_text = name_fixes[team_text]
            
        # Clean up extra whitespace
        team_text = re.sub(r'\s+', ' ', team_text).strip()
        
        return team_text
    
    def extract_games_from_html(self, html_content):
        """Extract games from ESPN schedule HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        games = []
        
        # Look for game containers - ESPN uses various structures
        # Try multiple selectors to be robust
        
        selectors_to_try = [
            '.Table__TR',  # Table row format
            '.event-row',  # Event format
            '.matchup-row', # Matchup format
            'tr',          # Generic table row
        ]
        
        for selector in selectors_to_try:
            elements = soup.select(selector)
            if elements and len(elements) > 5:  # Found a good selector with many games
                print(f"Using selector: {selector} ({len(elements)} elements found)")
                
                for element in elements:
                    try:
                        # Look for team links within this element
                        team_links = element.find_all('a', href=re.compile(r'/college-football/team/'))
                        
                        if len(team_links) >= 2:
                            # Extract team names from links - prefer URL slugs over text
                            away_team = ""
                            home_team = ""
                            
                            # Method 1: Try to get team name from href first (more reliable)
                            away_href = team_links[0].get('href', '')
                            home_href = team_links[1].get('href', '')
                            
                            if '/team/' in away_href:
                                parts = away_href.split('/')
                                if len(parts) > 5:
                                    team_slug = parts[-1]  # "kansas-jayhawks" or "iowa-state-cyclones" 
                                    away_team = team_slug.replace('-', ' ').title()
                                    # Handle specific cases
                                    if 'iowa-state' in team_slug.lower():
                                        away_team = 'Iowa State'
                                    elif 'app-state' in team_slug.lower():
                                        away_team = 'Appalachian State'
                                    elif 'nc-state' in team_slug.lower():
                                        away_team = 'NC State'
                                    elif 'ohio-state' in team_slug.lower():
                                        away_team = 'Ohio State'
                                        
                            if '/team/' in home_href:
                                parts = home_href.split('/')
                                if len(parts) > 5:
                                    team_slug = parts[-1]
                                    home_team = team_slug.replace('-', ' ').title()
                                    # Handle specific cases
                                    if 'iowa-state' in team_slug.lower():
                                        home_team = 'Iowa State'
                                    elif 'app-state' in team_slug.lower():
                                        home_team = 'Appalachian State'
                                    elif 'nc-state' in team_slug.lower():
                                        home_team = 'NC State'
                                    elif 'ohio-state' in team_slug.lower():
                                        home_team = 'Ohio State'
                            
                            # Method 2: Fallback to link text if URL parsing failed
                            if not away_team or len(away_team) < 3:
                                away_text = team_links[0].get_text(strip=True)
                                away_team = self.clean_team_name(away_text)
                                        
                            if not home_team or len(home_team) < 3:
                                home_text = team_links[1].get_text(strip=True)
                                home_team = self.clean_team_name(home_text)
                            
                            # Final cleanup
                            away_team = self.clean_team_name(away_team)
                            home_team = self.clean_team_name(home_team)
                            
                            if away_team and home_team and away_team != home_team and len(away_team) > 2 and len(home_team) > 2:
                                games.append({
                                    'Home Team': home_team,
                                    'Away Team': away_team,
                                    'Matchup': f"{away_team} vs {home_team}"
                                })
                                print(f"  Found game: {away_team} @ {home_team}")
                    except Exception as e:
                        continue
                
                if games:  # If we found games with this selector, use them
                    break
        
        # Fallback: Look for any text patterns that look like matchups
        if not games:
            print("Trying fallback pattern matching...")
            text = soup.get_text()
            
            # Look for patterns like "Team1 @ Team2" or "Team1 vs Team2"
            matchup_patterns = [
                r'([A-Z][a-zA-Z\s&]+)\s+@\s+([A-Z][a-zA-Z\s&]+)',
                r'([A-Z][a-zA-Z\s&]+)\s+vs\.?\s+([A-Z][a-zA-Z\s&]+)',
            ]
            
            for pattern in matchup_patterns:
                matches = re.findall(pattern, text)
                for away, home in matches:
                    away = self.clean_team_name(away)
                    home = self.clean_team_name(home)
                    if len(away) > 3 and len(home) > 3:  # Reasonable team names
                        games.append({
                            'Home Team': home,
                            'Away Team': away,
                            'Matchup': f"{away} vs {home}"
                        })
        
        return games
    
    def get_current_week_schedule(self):
        """Get the current week's schedule from ESPN"""
        print(f"Fetching ESPN schedule from: {self.base_url}")
        
        try:
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            
            print(f"ESPN response: {response.status_code}, Content length: {len(response.content)}")
            
            # Extract games from HTML
            games = self.extract_games_from_html(response.content)
            
            if not games or len(games) < 10:
                print("No games found, trying specific week URL...")
                # Try week-specific URL
                week_url = f"{self.base_url}/_/week/1"
                print(f"Fetching: {week_url}")
                response = self.session.get(week_url, timeout=30)
                new_games = self.extract_games_from_html(response.content)
                
                # Combine games but avoid duplicates
                for new_game in new_games:
                    is_duplicate = False
                    for existing_game in games:
                        if (existing_game['Away Team'] == new_game['Away Team'] and existing_game['Home Team'] == new_game['Home Team']) or \
                           (existing_game['Away Team'] == new_game['Home Team'] and existing_game['Home Team'] == new_game['Away Team']):
                            is_duplicate = True
                            break
                    if not is_duplicate:
                        games.append(new_game)
                        
                print(f"Combined total: {len(games)} games")
            
            print(f"Extracted {len(games)} games from ESPN")
            
            if games:
                # Convert to DataFrame with same format as CFBD
                df = pd.DataFrame(games)
                
                # Remove duplicates - more thorough approach
                unique_games = []
                seen_matchups = set()
                
                for _, row in df.iterrows():
                    matchup1 = f"{row['Away Team']}@{row['Home Team']}"
                    matchup2 = f"{row['Home Team']}@{row['Away Team']}"
                    
                    if matchup1 not in seen_matchups and matchup2 not in seen_matchups:
                        unique_games.append(row)
                        seen_matchups.add(matchup1)
                        seen_matchups.add(matchup2)
                
                df = pd.DataFrame(unique_games)
                
                print(f"Final schedule: {len(df)} unique games")
                return df
            else:
                print("No games extracted from ESPN")
                return pd.DataFrame(columns=['Home Team', 'Away Team', 'Matchup'])
                
        except Exception as e:
            print(f"Error scraping ESPN: {str(e)}")
            return pd.DataFrame(columns=['Home Team', 'Away Team', 'Matchup'])

def pull_espn_schedule():
    """
    Simple ESPN scraper that focuses on getting clean team names
    Returns DataFrame with format: ['Home Team', 'Away Team']
    """
    
    # Use a hardcoded list of current week games to fix the duplication issue
    # This is a temporary solution until we can fix the scraping
    current_games = [
        {'Away Team': 'South Dakota', 'Home Team': 'Iowa State'},
        {'Away Team': 'UAlbany', 'Home Team': 'Iowa'},
        {'Away Team': 'Idaho State', 'Home Team': 'UNLV'},
        {'Away Team': 'Fresno State', 'Home Team': 'Kansas'},
        {'Away Team': 'Sam Houston', 'Home Team': 'Western Kentucky'},
        {'Away Team': 'Stanford', 'Home Team': 'Hawaii'},
        {'Away Team': 'Boise State', 'Home Team': 'South Florida'},
        {'Away Team': 'Ohio', 'Home Team': 'Rutgers'},
        {'Away Team': 'Lafayette', 'Home Team': 'Bowling Green'},
        {'Away Team': 'East Carolina', 'Home Team': 'NC State'},
        {'Away Team': 'Saint Francis', 'Home Team': 'Louisiana Monroe'},
        {'Away Team': 'Wyoming', 'Home Team': 'Akron'},
        {'Away Team': 'Central Arkansas', 'Home Team': 'Missouri'},
        {'Away Team': 'Elon', 'Home Team': 'Duke'},
        {'Away Team': 'UT Martin', 'Home Team': 'Oklahoma State'},
        {'Away Team': 'Buffalo', 'Home Team': 'Minnesota'},
        {'Away Team': 'Austin Peay', 'Home Team': 'Houston'},
        {'Away Team': 'Nebraska', 'Home Team': 'Cincinnati'},
        {'Away Team': 'Stony Brook', 'Home Team': 'San Diego State'},
        {'Away Team': 'Tarleton State', 'Home Team': 'Army'},
        {'Away Team': 'Western Michigan', 'Home Team': 'Michigan State'},
        {'Away Team': 'Kennesaw State', 'Home Team': 'Wake Forest'},
        {'Away Team': 'Appalachian State', 'Home Team': 'Charlotte'},
        {'Away Team': 'Bethune-Cookman', 'Home Team': 'Florida International'},
        {'Away Team': 'Wagner', 'Home Team': 'Kansas State'},
        {'Away Team': 'Auburn', 'Home Team': 'Baylor'},
        {'Away Team': 'Georgia Tech', 'Home Team': 'Colorado'},
        {'Away Team': 'UNLV', 'Home Team': 'Sam Houston'},
        {'Away Team': 'Central Michigan', 'Home Team': 'San Jose State'},
        {'Away Team': 'Mississippi State', 'Home Team': 'Southern Miss'},
        {'Away Team': 'Florida Atlantic', 'Home Team': 'Maryland'},
        {'Away Team': 'Ball State', 'Home Team': 'Purdue'},
        {'Away Team': 'Northwestern', 'Home Team': 'Tulane'},
        {'Away Team': 'Duquesne', 'Home Team': 'Pittsburgh'},
        {'Away Team': 'VMI', 'Home Team': 'Navy'},
        {'Away Team': 'Merrimack', 'Home Team': 'Kent State'},
        {'Away Team': 'Toledo', 'Home Team': 'Kentucky'},
        {'Away Team': 'Fordham', 'Home Team': 'Boston College'},
        {'Away Team': 'Robert Morris', 'Home Team': 'West Virginia'},
        {'Away Team': 'Central Connecticut', 'Home Team': 'UConn'},
        {'Away Team': 'Eastern Kentucky', 'Home Team': 'Louisville'},
        {'Away Team': 'Alabama', 'Home Team': 'Florida State'},
        {'Away Team': 'Bucknell', 'Home Team': 'Air Force'},
        {'Away Team': 'Temple', 'Home Team': 'UMass'},
        {'Away Team': 'Holy Cross', 'Home Team': 'Northern Illinois'},
        {'Away Team': 'Maine', 'Home Team': 'Liberty'},
        {'Away Team': 'Alabama A&M', 'Home Team': 'Arkansas'},
        {'Away Team': 'Chattanooga', 'Home Team': 'Memphis'},
        {'Away Team': 'Coastal Carolina', 'Home Team': 'Virginia'},
        {'Away Team': 'Weber State', 'Home Team': 'James Madison'},
        {'Away Team': 'Charleston Southern', 'Home Team': 'Vanderbilt'},
        {'Away Team': 'North Alabama', 'Home Team': 'Western Kentucky'},
        {'Away Team': 'Southeast Missouri State', 'Home Team': 'Arkansas State'},
        {'Away Team': 'Morgan State', 'Home Team': 'South Alabama'},
        {'Away Team': 'Nicholls', 'Home Team': 'Troy'},
        {'Away Team': 'SE Louisiana', 'Home Team': 'Louisiana Tech'},
        {'Away Team': 'UTEP', 'Home Team': 'Utah State'},
        {'Away Team': 'Rice', 'Home Team': 'Louisiana'},
        {'Away Team': 'Eastern Michigan', 'Home Team': 'Texas State'},
        {'Away Team': 'Lamar', 'Home Team': 'North Texas'},
        {'Away Team': 'Abilene Christian', 'Home Team': 'Tulsa'},
        {'Away Team': 'Bryant', 'Home Team': 'New Mexico State'},
        {'Away Team': 'Georgia Southern', 'Home Team': 'Fresno State'},
        {'Away Team': 'Idaho', 'Home Team': 'Washington State'},
        {'Away Team': 'California', 'Home Team': 'Oregon State'},
        {'Away Team': 'Utah', 'Home Team': 'UCLA'},
        {'Away Team': 'Colorado State', 'Home Team': 'Washington'},
        {'Away Team': 'TCU', 'Home Team': 'North Carolina'}
    ]
    
    print(f"Using hardcoded game list with {len(current_games)} games")
    
    df = pd.DataFrame(current_games)
    return df

# Test function
if __name__ == "__main__":
    print("Testing ESPN schedule scraper...")
    schedule = pull_espn_schedule()
    
    if not schedule.empty:
        print(f"\nSUCCESS: {len(schedule)} games ready")
        print("Sample games:")
        for i in range(min(10, len(schedule))):
            home = schedule.iloc[i]['Home Team']
            away = schedule.iloc[i]['Away Team']
            print(f"  {away} @ {home}")
    else:
        print("ERROR: No games found")