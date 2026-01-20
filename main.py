import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import numpy as np

st.set_page_config(page_title="Aadhaar Enrolment Analytics Dashboard", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1 { color: #00D4FF; font-family: 'Segoe UI', sans-serif; font-size: 3rem; }
    h2 { color: #00D4FF; font-family: 'Segoe UI', sans-serif; font-size: 1.8rem; }
    .stMetric > label { color: #ffffff; font-size: 1.2rem; }
    .stMetric > div > div { color: #00D4FF; font-size: 2.5rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)


@st.cache_data
def load_and_clean_data():
    files = [
        r'api_data_aadhar_enrolment_0_500000.csv', 
        r'api_data_aadhar_enrolment_500000_1000000.csv', 
        r'api_data_aadhar_enrolment_1000000_1006029.csv'
    ]
    
    df_list = []
    for path in files:
        if os.path.exists(path):
            temp_df = pd.read_csv(path, low_memory=False)
            temp_df.columns = temp_df.columns.str.strip().str.lower()
            df_list.append(temp_df)
    
    df = pd.concat(df_list, ignore_index=True)
    

    df['child_enrol'] = 0.0
    df['adult_enrol'] = 0.0
    
    numeric_candidates = []
    for col in df.columns:
        if col in ['date', 'state', 'district', 'pin']:
            continue
        try:
            sample = pd.to_numeric(df[col].dropna().head(100), errors='coerce')
            if sample.notna().sum() > 5:
                numeric_candidates.append(col)
        except:
            continue
    
    if numeric_candidates:
        df['child_enrol'] = pd.to_numeric(df[numeric_candidates[0]], errors='coerce').fillna(0)
        if len(numeric_candidates) > 1:
            df['adult_enrol'] = pd.to_numeric(df[numeric_candidates[1]], errors='coerce').fillna(0)
    
    df['total_enrolments'] = df['child_enrol'] + df['adult_enrol']
    

    if 'state' in df.columns:
        df['state_raw'] = df['state'].astype(str).str.strip().str.lower()
        state_mapping = {
            'andaman & nicobar islands': 'Andaman and Nicobar Islands',
            'andaman and nicobar islands': 'Andaman and Nicobar Islands',
            'dadra & nagar haveli': 'Dadra and Nagar Haveli and Daman and Diu',
            'dadra and nagar haveli': 'Dadra and Nagar Haveli and Daman and Diu',
            'daman & diu': 'Dadra and Nagar Haveli and Daman and Diu',
            'daman and diu': 'Dadra and Nagar Haveli and Daman and Diu',
            'jammu & kashmir': 'Jammu and Kashmir',
            'jammu and kashmir': 'Jammu and Kashmir',
            'west bengal': 'West Bengal',
            'west bangal': 'West Bengal',
            'westbengal': 'West Bengal',
        }
        df['state_clean'] = df['state_raw'].replace(state_mapping)
        df['state_clean'] = df['state_clean'].str.title()
    
    if 'district' in df.columns:
        df['district_clean'] = df['district'].astype(str).str.strip()
        df['district_clean'] = df['district_clean'].str.replace(r'^\d+$', '', regex=True).str.strip()
        df = df[df['district_clean'] != '']
    
    return df

df = load_and_clean_data()
if len(df) == 0:
    st.error("No data found!")
    st.stop()

state_totals = df.groupby('state_clean')['total_enrolments'].sum().sort_values(ascending=False)
top10_states = state_totals.head(10).reset_index()
bottom10_states = state_totals.tail(10).reset_index()

child_vs_adult = df.groupby('state_clean')[['child_enrol', 'adult_enrol']].sum()
child_vs_adult['total'] = child_vs_adult['child_enrol'] + child_vs_adult['adult_enrol']
child_vs_adult['child_pct'] = (child_vs_adult['child_enrol'] / child_vs_adult['total'] * 100).round(1)


st.sidebar.title("🔍 Filters")

all_states = sorted(df['state_clean'].dropna().unique())
selected_state = st.sidebar.selectbox("Select State", all_states, index=0)

state_df = df[df['state_clean'] == selected_state]
districts = sorted(state_df['district_clean'].dropna().unique())
selected_district = st.sidebar.selectbox("District", ["ALL DISTRICTS"] + list(districts))

final_df = state_df if selected_district == "ALL DISTRICTS" else state_df[state_df['district_clean'] == selected_district]
region_label = f"{selected_state} ({selected_district if selected_district != 'ALL DISTRICTS' else 'All Districts'})"


st.title("🛡️ Aadhaar Analytics Dashboard")


col1, col2 = st.columns(2)
col1.metric("Region", region_label)
state_rank = list(state_totals.sort_values(ascending=False).index).index(selected_state) + 1
col2.metric("State Rank", f"#{state_rank}")


m1, m2, m3, m4 = st.columns(4)
total = final_df['total_enrolments'].sum()
child = final_df['child_enrol'].sum()
adult = final_df['adult_enrol'].sum()
m1.metric("Total Enrolments", f"{int(total):,}")
m2.metric("Children (5-17)", f"{int(child):,}")
m3.metric("Adults (17+)", f"{int(adult):,}")
m4.metric("Records", f"{len(final_df):,}")

st.markdown("---")


st.subheader("🏆 State Performance Rankings")
tab1, tab2 = st.tabs(["📊 Charts", "📋 Tables"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig_top = px.bar(top10_states, y='state_clean', x='total_enrolments', orientation='h',
                        template="plotly_dark", color='total_enrolments', color_continuous_scale="Viridis", height=500)
        fig_top.update_layout(showlegend=False)
        st.plotly_chart(fig_top, use_container_width=True)
    
    with col2:
        fig_bottom = px.bar(bottom10_states, y='state_clean', x='total_enrolments', orientation='h',
                           template="plotly_dark", color='total_enrolments', color_continuous_scale="Reds", height=500)
        fig_bottom.update_layout(showlegend=False)
        st.plotly_chart(fig_bottom, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top 10 States**")
        st.dataframe(top10_states.rename(columns={'total_enrolments': 'Enrolments'})
                    .style.format({'Enrolments': '{:,}'}).background_gradient(), height=350)
    with col2:
        st.markdown("**Bottom 10 States**")
        st.dataframe(bottom10_states.rename(columns={'total_enrolments': 'Enrolments'})
                    .style.format({'Enrolments': '{:,}'}).background_gradient(), height=350)

st.markdown("---")


st.subheader("📊 Univariate Analysis")
tab1, tab2 = st.tabs(["📊 Charts", "📋 Tables"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        district_stats = state_df.groupby('district_clean')['total_enrolments'].sum().nlargest(10)
        fig_district = px.bar(district_stats.reset_index(), y='district_clean', x='total_enrolments',
                             orientation='h', template="plotly_dark", color='total_enrolments', 
                             color_continuous_scale="Viridis", height=400)
        st.plotly_chart(fig_district, use_container_width=True)
    
    with col2:
        fig_pie = go.Figure(go.Pie(values=[child, adult], labels=['Children (5-17)', 'Adults (17+)'],
                                  hole=0.4, marker_colors=['#00D4FF', '#FF6B6B']))
        fig_pie.update_layout(template="plotly_dark", height=400)
        st.plotly_chart(fig_pie, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Top 10 Districts**")
        top_districts = state_df.groupby('district_clean')['total_enrolments'].sum().nlargest(10).reset_index()
        st.dataframe(top_districts.rename(columns={'total_enrolments': 'Enrolments'})
                    .style.format({'Enrolments': '{:,}'}).background_gradient(), height=350)
    
    with col2:
        st.markdown("**Age Breakdown**")
        age_data = pd.DataFrame({
            'Category': ['Children (5-17)', 'Adults (17+)'],
            'Enrolments': [child, adult],
            'Percentage': [f"{child/total*100:.1f}%" if total > 0 else "0%", f"{adult/total*100:.1f}%" if total > 0 else "0%"]
        })
        st.dataframe(age_data.style.format({'Enrolments': '{:,}'}).background_gradient(), height=250)

st.markdown("---")


st.subheader("📈 Bivariate Analysis")
tab1, tab2 = st.tabs(["📊 Charts", "📋 Tables"])

with tab1:
    col1, col2 = st.columns(2)
    with col1:
        fig_scatter = px.scatter(child_vs_adult.reset_index(), x='adult_enrol', y='child_enrol',
                               size='total', hover_name='state_clean', template="plotly_dark",
                               title="Child vs Adult Enrolments", height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    with col2:
        child_pct_sorted = child_vs_adult.sort_values('child_pct', ascending=False).head(10)
        fig_child = px.bar(child_pct_sorted.reset_index(), y='state_clean', x='child_pct',
                          orientation='h', template="plotly_dark", color='child_pct', 
                          color_continuous_scale="Blues", height=400)
        st.plotly_chart(fig_child, use_container_width=True)

with tab2:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Child vs Adult by State**")
        biv_table = child_vs_adult[['child_enrol', 'adult_enrol', 'total', 'child_pct']].round(0)
        st.dataframe(biv_table.style.format({
            'child_enrol': '{:,}', 'adult_enrol': '{:,}', 'total': '{:,}', 'child_pct': '{:.1f}%'
        }).background_gradient(), height=400)
    
    with col2:
        st.markdown("**Top 10 States by Child %**")
        top_child_states = child_vs_adult.sort_values('child_pct', ascending=False).head(10)
        st.dataframe(top_child_states[['child_pct']].style.format({'child_pct': '{:.1f}%'}).background_gradient(), height=400)

st.caption("Aadhaar Enrolment Analytics Dashboard - Charts & Tables")

