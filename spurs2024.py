import pandas as pd
from understatapi import UnderstatClient
from understatapi.exceptions import InvalidMatch
from typing import Tuple, Optional, List, Dict
import logging

players = [
    # Forwards
    ("Richarlison", "FW", 0.51),
    ("Dominic Solanke", "FW", 0.39),
    ("Heung-Min Son", "FW", 0.31),
    ("Dejan Kulusevski", "FW", 0.30),
    ("Timo Werner", "FW", 0.00),
    ("Wilson Odobert", "FW", 0.00),
    ("William Lankshear", "FW", 0.00),
    ("Dane Scarlett", "FW", 0.00),
    ("Mathys Tel", "FW", 0.00),
    ("Brennan Johnson", "FW", 0.00),
    
    # Midfielders
    ("Mikey Moore", "MF", 0.49),
    ("James Maddison", "MF", 0.32),
    ("Pape Matar Sarr", "MF", 0.14),
    ("Rodrigo Bentancur", "MF", 0.00),
    ("Archie Gray", "MF", 0.00),
    ("Lucas Bergvall", "MF", 0.00),
    ("Yves Bissouma", "MF", 0.00),
    
    # Defenders
    ("Alfie Dorrington", "DF", 0.00),
    ("Kevin Danso", "DF", 0.54),
    ("Sergio Reguilón", "DF", 0.75),
    ("Ben Davies", "DF", 1.00),
    ("Cristian Romero", "DF", 1.20),
    ("Mickey van de Ven", "DF", 1.25),
    ("Destiny Udogie", "DF", 1.32),
    ("Pedro Porro", "DF", 1.50),
    ("Djed Spence", "DF", 1.57),
    ("Radu Drăgușin", "DF", 2.08),
    
    # Goalkeepers
    ("Guglielmo Vicario", "GK", 1.00),
    ("Antonin Kinsky", "GK", 1.75),
    ("Brandon Austin", "GK", 2.00)
]


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_tottenham_matches(seasons: List[str] = ["2023", "2024"]) -> pd.DataFrame:
    """
    Get Tottenham's matches data for specified seasons.
    
    Args:
        seasons: List of seasons to fetch data for (default: ["2023", "2024"])
    
    Returns:
        DataFrame containing match data
    """
    with UnderstatClient() as understat:
        all_matches = []
        for season in seasons:
            try:
                matches = understat.team(team="Tottenham").get_match_data(season=season)
                all_matches.extend(matches)
                logger.info(f"Successfully fetched {len(matches)} matches for season {season}")
            except Exception as e:
                logger.error(f"Error fetching matches for season {season}: {str(e)}")
        
        matches_df = pd.DataFrame(all_matches)
        matches_df.to_csv('spurs_matches.csv', index=False)
        logger.info(f"Saved {len(matches_df)} total matches to CSV")
        return matches_df

def get_tottenham_shots(season: str) -> Tuple[Optional[pd.DataFrame], Optional[List[Dict]]]:
    """
    Get shot data for all Tottenham matches in a given season.
    
    Args:
        season: Season to fetch data for (e.g., "2023")
    
    Returns:
        Tuple of (shots DataFrame, list of matches)
    """
    with UnderstatClient() as client:
        try:
            # Get all matches for the season
            matches = client.league(league="EPL").get_match_data(season=season)
            
            # Filter for Tottenham matches
            spurs_matches = [
                match for match in matches 
                if "Tottenham" in (match['h']['title'], match['a']['title'])
            ]
            
            logger.info(f"Found {len(spurs_matches)} Tottenham matches")
            
            # Get shot data for each match
            all_shots = []
            for match in spurs_matches:
                match_id = match['id']
                try:
                    shot_data = client.match(match=match_id).get_shot_data()
                    
                    # Process shots for both teams
                    for location in ['h', 'a']:
                        if shot_data[location]:
                            shots = shot_data[location]
                            for shot in shots:
                                # Check if the player who took the shot is in our players list
                                shot_taker = shot.get('player', '')
                                if any(player[0] == shot_taker for player in players):
                                    # Convert xG to float, default to 0 if missing
                                    try:
                                        shot['xG'] = float(shot.get('xG', 0))
                                    except (ValueError, TypeError):
                                        shot['xG'] = 0.0
                                        
                                    # Add match context to the shot data
                                    shot.update({
                                        'h_team': match['h']['title'],
                                        'a_team': match['a']['title'],
                                        'h_goals': match['goals']['h'],
                                        'a_goals': match['goals']['a'],
                                        'date': match['datetime'],
                                        'match_id': match_id,
                                        'season': season
                                    })
                                    all_shots.append(shot)

                    logger.info(f"Successfully processed match {match_id}")
                    
                except InvalidMatch:
                    logger.warning(f"Invalid match ID: {match_id}, skipping...")
                except Exception as e:
                    logger.error(f"Error processing match {match_id}: {str(e)}")
                    continue
            
            # Convert to DataFrame and save
            if all_shots:
                shots_df = pd.DataFrame(all_shots)
                # Ensure xG is float type
                shots_df['xG'] = pd.to_numeric(shots_df['xG'], errors='coerce').fillna(0)
                output_file = f'tottenham_shots_{season}.csv'
                shots_df.to_csv(output_file, index=False)
                logger.info(f"Saved {len(shots_df)} shots to {output_file}")
                return shots_df, spurs_matches
            else:
                logger.warning("No shot data collected")
                return None, spurs_matches
                
        except Exception as e:
            logger.error(f"Error getting league data: {str(e)}")
            return None, None

def analyze_shots(shots_df: pd.DataFrame) -> pd.DataFrame:
    """
    Analyze shot data to generate insights.
    
    Args:
        shots_df: DataFrame containing shot data
    
    Returns:
        DataFrame with analysis results
    """
    if shots_df is None:
        return None
        
    # Add basic analysis
    analysis = shots_df.copy()
    
    # Convert date to datetime
    analysis['date'] = pd.to_datetime(analysis['date'])
    
    # Ensure xG is numeric
    analysis['xG'] = pd.to_numeric(analysis['xG'], errors='coerce').fillna(0)
    
    # Add shot outcome analysis
    analysis['is_goal'] = analysis['result'].eq('Goal')
    
    # Add team context
    analysis['is_spurs_shot'] = analysis.apply(
        lambda x: 'Tottenham' in (x['h_team'] if x['h_a'] == 'h' else x['a_team']),
        axis=1
    )
    
    return analysis

def main():
    # Get match data
    matches_df = get_tottenham_matches()
    
    # Get and analyze shots for both seasons
    shots_df, matches = get_tottenham_shots("2024")
    shots_df_23, matches_23 = get_tottenham_shots("2023")
    
    # Check if both DataFrames exist and are not None
    if shots_df is not None and shots_df_23 is not None:
        # Analyze shots
        analysis_df_24 = analyze_shots(shots_df)
        analysis_df_23 = analyze_shots(shots_df_23)
        
        # Combine the analysis DataFrames
        analysis_df = pd.concat([analysis_df_23, analysis_df_24], ignore_index=True)

        # Print summary
        print("\nShot data columns:", shots_df.columns.tolist())
        print("\nSample of shot data:")
        print(shots_df[['date', 'player', 'minute', 'result', 'xG']].head())
        
        # Print basic stats
        spurs_shots = analysis_df[analysis_df['is_spurs_shot']]
        print(f"\nTotal Spurs shots: {len(spurs_shots)}")
        print(f"Goals scored: {spurs_shots['is_goal'].sum()}")
        print(f"Average xG per shot: {spurs_shots['xG'].mean():.3f}")


if __name__ == "__main__":
    main()