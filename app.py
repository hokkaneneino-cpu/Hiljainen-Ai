import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Hiljainen AI – Prosessianalyysi", layout="centered")

@st.cache_data
def load_data():
    df = pd.read_csv('jira_export.csv', parse_dates=['status_changed_at', 'created_at'])
    df = df.sort_values(['issue_key', 'status_changed_at']).reset_index(drop=True)
    rows = []
    for key, grp in df.groupby('issue_key'):
        grp = grp.sort_values('status_changed_at').reset_index(drop=True)
        meta = grp.iloc[0][['issue_type','priority','assignee','component']].to_dict()
        for i in range(len(grp)-1):
            duration_h = (grp.loc[i+1,'status_changed_at'] - grp.loc[i,'status_changed_at']).total_seconds() / 3600
            entered_at = grp.loc[i, 'status_changed_at']
            rows.append({
                'issue_key':    key,
                'status':       grp.loc[i, 'status'],
                'duration_h':   round(duration_h, 2),
                'entered_at':   entered_at,
                'weekday_name': entered_at.strftime('%A'),
                **meta
            })
    return pd.DataFrame(rows)

durations = load_data()

AVG_HOURLY_COST  = 75
IMPACT_FACTOR    = 0.6
WASTE_MULTIPLIER = 2.0
DATA_MONTHS      = 4

stages = ['Backlog', 'In Progress', 'Code Review', 'QA']
waste_rows = []
for stage in stages:
    s = durations[durations['status'] == stage]['duration_h']
    threshold = s.median() * WASTE_MULTIPLIER
    waste = (s - threshold).clip(lower=0)
    waste_rows.append({'Vaihe': stage, 'Hukkatunnit': int(waste.sum())})
waste_df = pd.DataFrame(waste_rows)

total_waste_h = waste_df['Hukkatunnit'].sum()
monthly_cost  = total_waste_h * AVG_HOURLY_COST * IMPACT_FACTOR / DATA_MONTHS

cr = durations[durations['status'] == 'Code Review']
qa = durations[durations['status'] == 'QA']

infra_med = cr[cr['component']=='infra']['duration_h'].median()
other_med = cr[cr['component']!='infra']['duration_h'].median()
fri_med   = qa[qa['weekday_name']=='Friday']['duration_h'].median()
arki_med  = qa[qa['weekday_name'].isin(['Monday','Tuesday','Wednesday'])]['duration_h'].median()
dave_med  = cr[cr['assignee']=='dave']['duration_h'].median()
team_med  = cr['duration_h'].median()

st.title("Prosessianalyysi")
st.caption("Hiljainen AI – Jira-data syyskuu–joulukuu 2024")
st.divider()

st.markdown("## Prosessikitka maksaa arviolta")
st.markdown(f"# :red[{monthly_cost:,.0f} €/kk]")
st.divider()

st.subheader("Pullonkaulat")
col1, col2, col3 = st.columns(3)

with col1:
    st.error("**Infra – Code Review**")
    st.metric("Infra", f"{infra_med:.0f}h", delta=f"+{infra_med-other_med:.0f}h vs muut", delta_color="inverse")
    st.caption("Infra-tiketeille ei riitä review-kapasiteettia.")

with col2:
    st.error("**Perjantai-efekti – QA**")
    st.metric("Perjantai", f"{fri_med:.0f}h", delta=f"+{fri_med-arki_med:.0f}h vs arki", delta_color="inverse")
    st.caption("Tiketit jäävat viikonlopun yli odottamaan.")

with col3:
    st.error("**Dave – Code Review**")
    st.metric("Dave", f"{dave_med:.0f}h", delta=f"+{dave_med-team_med:.0f}h vs tiimi", delta_color="inverse")
    st.caption("Tiketeille ei ole selkeaa review-paria.")

st.divider()

st.subheader("Hukkatunnit vaiheittain")
fig, ax = plt.subplots(figsize=(8, 3))
colors = ['#e05c5c' if s == 'Code Review' else '#d0d0d0' for s in waste_df['Vaihe']]
bars = ax.bar(waste_df['Vaihe'], waste_df['Hukkatunnit'], color=colors, edgecolor='none')
ax.bar_label(bars, fmt='%d h', padding=4, fontsize=10)
ax.set_ylabel('Hukkatunteja (4kk)')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
st.pyplot(fig)
