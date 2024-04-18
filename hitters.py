import pandas as pd
import streamlit as st
import os
import altair as alt
import numpy as np

files = os.listdir('data')

yakker = pd.DataFrame()
for file in files:

    cur_yakker = pd.read_csv(f'data/{file}')
    file = file[:-4]

    split = file.split('_')
    date = f'{split[0]}/{split[1]}/{split[2]}'

    if len(split) == 4:
        team = split[3]
    elif len(split) == 5:
        team = f'{split[3]} {split[4]}'
    elif len(split) == 6:
        team = f'{split[3]} {split[4]} {split[5]}'
    elif len(split) == 7:
        team = f'{split[3]} {split[4]} {split[5]} {split[6]}'

    cur_yakker['Game'] = f'{date} - {team}'

    yakker = pd.concat([yakker, cur_yakker])

yakker = yakker[yakker['BatterTeam'] == 'Georgia tech']


upd_data = yakker.dropna(subset=['HorzBreak', 'InducedVertBreak', 'RelSpeed'])

upd_data['pitch'] = np.nan

for i in range(len(upd_data)):
    if (upd_data['PitcherThrows'].iloc[i] == "Right") & (upd_data['Pitcher'].iloc[i] in ["Emma Minghini", "Alyssa Faircloth", "Makayla Coffield"]):
        upd_data['HorzBreak'].iloc[i] = -upd_data['HorzBreak'].iloc[i]

    if ((upd_data['InducedVertBreak'].iloc[i] > 0) & (abs(upd_data['HorzBreak'].iloc[i]) < 5)):
        upd_data['pitch'].iloc[i] = "Riseball"
    elif ((upd_data['InducedVertBreak'].iloc[i] < 0) & (abs(upd_data['InducedVertBreak'].iloc[i]) > abs(upd_data['HorzBreak'].iloc[i]))):
        upd_data['pitch'].iloc[i] = "Dropball"
    elif (upd_data['HorzBreak'].iloc[i] < 0):
        upd_data['pitch'].iloc[i] = "Curveball"
    else:
        upd_data['pitch'].iloc[i] = "Screwball"

upd_data['max_RelSpeed'] = upd_data.groupby('Pitcher')['RelSpeed'].transform('max')
upd_data['pitch'] = np.where(upd_data['RelSpeed'] < upd_data['max_RelSpeed'] - 10, "Changeup", upd_data['pitch'])

yakker = upd_data.copy()

yakker['pitch'] = np.select([(yakker['pitch'] == "Riseball") & (yakker['InducedVertBreak'] > 5),
                             yakker['pitch'] == "Riseball",
                             (yakker['pitch'] == "Dropball") & (yakker['InducedVertBreak'] < -8),
                             yakker['pitch'] == "Dropball",
                             (yakker['pitch'] == "Curveball") & (yakker['HorzBreak'] < -6),
                             yakker['pitch'] == "Curveball",
                             yakker['pitch'] == "Changeup"],
                            ["Good Riseball", "Bad Riseball", "Good Dropball", "Bad Dropball", "Good Curveball", "Bad Curveball", "Changeup"],
                            default="")

yakker = yakker.dropna(subset=['pitch'])
yakker = yakker[yakker['pitch'] != '']

st.sidebar.header('GT Hitters')

hitter = st.sidebar.multiselect('Select Hitter', yakker['Batter'].unique())

result = st.sidebar.multiselect('Select Result', ['All', 'Hit', 'Hard Hit', 'Soft Contact', 'Whiff', 'StrikeCalled'])

pitches = ['All', 'Good Riseball', 'Bad Riseball', 'Good Dropball', 'Bad Dropball', 'Good Curveball', 'Bad Curveball', 'Changeup']

pitch = st.sidebar.multiselect('Select Pitch', pitches)

yakker = yakker[yakker['Batter'] == hitter]
yakker = yakker[(yakker['PlateLocSide'] > -2) & (yakker['PlateLocSide'] < 2) & (yakker['PlateLocHeight'] > 0) & (yakker['PlateLocHeight'] < 5)]
yakker = yakker[(yakker['pitch'].isin(pitch)) | ('All' in pitch)]

yakker['Result'] = yakker['PitchCall']

# if result is InPlay, change to HardHit if exit speed > 67.5
yakker.loc[(yakker['Result'] == 'InPlay') & ((yakker['ExitSpeed'] > 67.5) | (yakker['PlayResult'] == 'Home Run')), 'Result'] = 'Hard Hit'
yakker.loc[(yakker['Result'] == 'InPlay') & (yakker['ExitSpeed'] < 67.5), 'Result'] = 'Soft Contact'
yakker.loc[(yakker['Result'] == 'StrikeSwinging'), 'Result'] = 'Whiff'
yakker.loc[(yakker['Result'] == 'StrikeCalled'), 'Result'] = 'StrikeCalled'

yakker['HardHit'] = yakker['Result'].apply(lambda x: 1 if x == 'Hard Hit' else 0)
yakker['Hit'] = yakker['PlayResult'].apply(lambda x: 1 if x in ['Single', 'Double', 'Triple', 'HomeRun'] else 0)
yakker['Whiff'] = yakker['PitchCall'].apply(lambda x: 1 if x == 'StrikeSwinging' else 0)
yakker['StrikeCalled'] = yakker['PitchCall'].apply(lambda x: 1 if x == 'StrikeCalled' else 0)

yakker['Exit Velo'] = round(yakker['ExitSpeed'], 1)
yakker.loc[yakker['Exit Velo'].isna(), 'Exit Velo'] = ''

yakker['Pitch Speed'] = round(yakker['RelSpeed'], 1)
yakker.loc[yakker['Pitch Speed'].isna(), 'Pitch Speed'] = ''

final_yakker = pd.DataFrame()

if 'All' not in result:
    if 'Hit' in result:
        final_yakker = pd.concat([final_yakker, yakker[yakker['Hit'] == 1]])
    if 'Hard Hit' in result:
        final_yakker = pd.concat([final_yakker, yakker[yakker['HardHit'] == 1]])
    if 'Soft Contact' in result:
        final_yakker = pd.concat([final_yakker, yakker[(yakker['HardHit'] == 0 & ~(yakker['Exit Velo'].isna()))]])
    if 'Whiff' in result:
        final_yakker = pd.concat([final_yakker, yakker[yakker['Whiff'] == 1]])
    if 'StrikeCalled' in result:
        final_yakker = pd.concat([final_yakker, yakker[yakker['StrikeCalled'] == 1]])
else:
    final_yakker = yakker

yakker = final_yakker.copy()

if yakker.empty:
    st.write('No data available for selected filters')
    st.stop()

yakker = yakker.rename(columns={'pitch': 'Pitch'})

scatter = alt.Chart(yakker).mark_circle(size=100).encode(
    alt.X('PlateLocSide', axis=alt.Axis(labels=False, ticks=False, title='')),
    alt.Y('PlateLocHeight', axis=alt.Axis(labels=False, ticks=False, title='')),
    tooltip=['Pitcher', 'Game', 'Pitch', 'Result', 'Pitch Speed', 'Exit Velo']
).properties(
    height=500
)

# Define the lines
k_zone = pd.DataFrame({
    'x': [-17/24, 17/24, 17/24, -17/24, -17/24],
    'y': [5/4, 5/4, 3, 3, 5/4]
}).reset_index()

# Create the lines chart
k_zone_chart = alt.Chart(k_zone).mark_line(color='black').encode(
    x='x:Q',
    y='y:Q',
    order='index'
)

batters_box_1 = pd.DataFrame({
    'x': [-29/24, -29/24, -29/24],
    'y': [0, 5, 0]
})

batters_box_2 = pd.DataFrame({
    'x': [29/24, 29/24, 29/24],
    'y': [0, 5, 0]
})

vert_line = pd.DataFrame({
    'x': [0, 0],
    'y': [5/4, 3]
})

horz_line = pd.DataFrame({
    'x': [-17/24, 17/24],
    'y': [17/8, 17/8]
})

batter_box_1_chart = alt.Chart(batters_box_1).mark_line(color='black', strokeDash=[5,5]).encode(
    x='x:Q',
    y='y:Q'
)

batter_box_2_chart = alt.Chart(batters_box_2).mark_line(color='black', strokeDash=[5,5]).encode(
    x='x:Q',
    y='y:Q'
)

vert_line_chart = alt.Chart(vert_line).mark_line(color='black', strokeDash=[5,5]).encode(
    x='x:Q',
    y='y:Q'
)

horz_line_chart = alt.Chart(horz_line).mark_line(color='black', strokeDash=[5,5]).encode(
    x='x:Q',
    y='y:Q'
)


# Combine scatter plot and lines
combined_chart = scatter + k_zone_chart + batter_box_1_chart + batter_box_2_chart + vert_line_chart + horz_line_chart

st.altair_chart(combined_chart)

if len(yakker[yakker['PitchCall'].isin(['StrikeSwinging', 'Foul', 'InPlay'])]) == 0:
    whiff_rate = 0
else:
    whiff_rate = round((len(yakker[yakker['Whiff'] == 1]) / len(yakker[yakker['PitchCall'].isin(['StrikeSwinging', 'Foul', 'InPlay'])])) * 100, 1)

if len(yakker[yakker['Result'].isin(['Hard Hit', 'Soft Contact'])]) == 0:
    hard_hit_rate = 0
else:
    hard_hit_rate = round((len(yakker[yakker['HardHit'] == 1]) / len(yakker[yakker['Result'].isin(['Hard Hit', 'Soft Contact'])])) * 100, 1)

st.write(f'Whiff Rate: {whiff_rate}%')
st.write(f'Hard Hit Rate: {hard_hit_rate}%')