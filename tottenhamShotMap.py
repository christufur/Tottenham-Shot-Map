import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
import spurs2024
from datetime import datetime
import os

# Set page config
st.set_page_config(page_title="Spurs 2024 Shot Map", layout="wide")

st.title("Spurs 2024 Shot Map")
st.subheader("Filter to any team/player to see all of their shots!")

# Add a refresh button in the sidebar
st.sidebar.header("🔄 Data Controls")
if st.sidebar.button("Refresh Data"):
    # Run the main function to fetch new data
    with st.spinner("Fetching latest shot data..."):
        spurs2024.main()
    st.success("Data refreshed successfully!")
    # Clear the cache to force data reload
    st.cache_data.clear()

# Show last update time if file exists
if os.path.exists('tottenham_shots_2024.csv'):
    last_modified = datetime.fromtimestamp(os.path.getmtime('tottenham_shots_2024.csv'))
    st.sidebar.info(f"Last updated: {last_modified.strftime('%Y-%m-%d %H:%M:%S')}")

# Load data
@st.cache_data
def load_data():
    if os.path.exists('tottenham_shots_2024.csv'):
        df = pd.read_csv('tottenham_shots_2024.csv')
        # Ensure xG is numeric
        df['xG'] = pd.to_numeric(df['xG'], errors='coerce').fillna(0)
        return df
    else:
        # If file doesn't exist, fetch the data first
        with st.spinner("Initial data fetch..."):
            spurs2024.main()
        df = pd.read_csv('tottenham_shots_2024.csv')
        df['xG'] = pd.to_numeric(df['xG'], errors='coerce').fillna(0)
        return df

df = load_data()

# Create sidebar for filters
st.sidebar.header("⚽ Shot Map Filters")

setofteams = sorted(set(df['h_team'].unique()) | set(df['a_team'].unique()))
team = st.sidebar.selectbox('Select a Team', setofteams, index=None, 
                          placeholder="Choose a team...")

# Only show player selectbox if a team is selected
if team:
    team_shots = df[(df['h_team'] == team) | (df['a_team'] == team)]
    players = sorted(team_shots['player'].unique())
    player = st.sidebar.selectbox('Select a Player', players, index=None,
                                placeholder="Choose a player...")
else:
    player = None

def filter_data(df, team=None, player=None):
    filtered_df = df.copy()
    
    if team:
        filtered_df = filtered_df[(filtered_df['h_team'] == team) | 
                                (filtered_df['a_team'] == team)]
    if player:
        filtered_df = filtered_df[filtered_df['player'] == player]
    
    filtered_df['X'] = filtered_df['X'].astype(float)
    filtered_df['Y'] = filtered_df['Y'].astype(float)
    filtered_df['X'] = filtered_df['X'] * 100
    filtered_df['Y'] = filtered_df['Y'] * 100
    return filtered_df

filtered_df = filter_data(df, team, player)

# Create two columns for stats and plot
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 Shot Statistics")
    total_shots = len(filtered_df)
    goals = len(filtered_df[filtered_df['result'] == 'Goal'])
    total_xg = filtered_df['xG'].sum()
    
    st.metric("Total Shots", total_shots, 
              delta=f"{total_shots-goals} missed" if total_shots > 0 else None)
    st.metric("Goals Scored", goals)
    st.metric("Expected Goals (xG)", f"{total_xg:.2f}", 
              delta=f"{goals - total_xg:.2f} vs xG" if total_shots > 0 else None)
    st.metric("Conversion Rate", f"{(goals/total_shots*100):.1f}%" if total_shots > 0 else "N/A")

    # Add shot details table with improved styling
    if not filtered_df.empty:
        display_df = filtered_df[['player', 'minute', 'result', 'xG', 'situation', 'player_assisted']].copy()
        display_df = display_df.sort_values('minute')
        display_df['xG'] = display_df['xG'].round(3)
        display_df.columns = ['Player', 'Minute', 'Result', 'xG', 'Situation', 'Assisted By']
        st.dataframe(
            display_df,
            hide_index=True,
            column_config={
                "xG": st.column_config.NumberColumn(format="%.3f"),
                "Minute": st.column_config.NumberColumn(format="%d'")
            }
        )
    else:
        st.info("No shots available for the selected filters")

with col2:
    # Create the pitch plot
    pitch = VerticalPitch(
        pitch_type='opta', 
        half=True,
        pitch_color='#313332',
        line_color='#FFFFFF',
        line_alpha=0.3
    )
    fig, ax = pitch.draw(figsize=(10, 10))

    # Plot shots with fixed zorder values
    if not filtered_df.empty:
        # Plot non-goals first
        non_goals = filtered_df[filtered_df['result'] != 'Goal']
        if not non_goals.empty:
            # Ensure xG is numeric for scatter plot sizing
            sizes = non_goals['xG'].astype(float) * 900
            pitch.scatter(
                non_goals['X'].values,
                non_goals['Y'].values,
                s=sizes,
                c='#A6A6A6',
                alpha=0.6,
                edgecolors='white',
                linewidth=1,
                ax=ax,
                zorder=2
            )
        
        # Plot goals on top
        goals = filtered_df[filtered_df['result'] == 'Goal']
        if not goals.empty:
            # Ensure xG is numeric for scatter plot sizing
            sizes = goals['xG'].astype(float) * 900
            pitch.scatter(
                goals['X'].values,
                goals['Y'].values,
                s=sizes,
                c='#FF4B4B',
                alpha=0.8,
                edgecolors='white',
                linewidth=1,
                ax=ax,
                zorder=3
            )

    # Add title to the plot
    title = f"Shot Map for {team if team else 'All Teams'}"
    if player:
        title += f"\n{player}"
    ax.set_title(title, pad=20, color='white', fontsize=12)

    # Add legend
    legend_elements = [
        plt.scatter([], [], c='#FF4B4B', alpha=0.8, label='Goal', edgecolor='white'),
        plt.scatter([], [], c='#A6A6A6', alpha=0.6, label='Shot', edgecolor='white')
    ]
    ax.legend(handles=legend_elements, loc='upper center', 
             bbox_to_anchor=(0.5, -0.05), framealpha=0.3,
             facecolor='#313332', edgecolor='white', labelcolor='white')

    fig.patch.set_facecolor('#313332')
    st.pyplot(fig)