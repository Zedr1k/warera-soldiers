# app.py
import streamlit as st
import pandas as pd
import time
from datetime import datetime
from fetch_data import fetch_all_user_ids, fetch_user_record, assign_roles, calculate_damage

st.set_page_config(page_title="WarEra Country Dashboard", layout="wide")

# Widen sidebar via custom CSS
st.markdown(
    """
    <style>
    /* Adjust sidebar width */
    [data-testid="stSidebar"] {
        width: 300px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# List of countries
ALL_COUNTRIES = {
    "Uruguay": "6813b6d546e731854c7ac835",
    #"Brasil":  "6813b6d546e731854c7ac82f",
    "Argentina": "6813b6d546e731854c7ac832",
    #"Croatia" : "6813b6d446e731854c7ac7bc",
    "Chile": "6813b6d546e731854c7ac83c",
    "Polonia": "6813b6d446e731854c7ac7ae",
    "Venezuela": "6813b6d546e731854c7ac858",
    "España": "6813b6d446e731854c7ac7a8",
    "Rumania": "6813b6d446e731854c7ac7b6",
    "Suecia": "6813b6d446e731854c7ac7f2",
    "Francia": "6813b6d446e731854c7ac79a",
    "Lituania": "6813b6d446e731854c7ac7b8"        
}

def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} M"
    if n >= 1_000:
        return f"{n/1_000:.1f} K"
    return str(n)

# Cache full data per country
@st.cache_data(ttl=3600, show_spinner=False)
def load_country_df(country_id: str):
    ids = fetch_all_user_ids(country_id)
    records = []
    for uid in ids:
        rec = fetch_user_record(uid)
        rec = assign_roles(rec)
        rec = calculate_damage(rec)
        records.append(rec)
    df = pd.DataFrame(records)
    updated = datetime.utcnow()
    return df, updated

# Sidebar: country stats and selection
st.sidebar.title("Country Overview")
selected = st.sidebar.radio("Select a country:", list(ALL_COUNTRIES.keys()))

st.sidebar.markdown("---")

# Summary table for all countries
summary_rows = []
for name, cid in ALL_COUNTRIES.items():
    try:
        df_tmp, _ = load_country_df(cid)
        summary_rows.append({
            'Country': name,
            'Citizens': (df_tmp['active'] == True).sum(),
            'Eco': fmt_num(int(df_tmp['wealthValue'].sum())),
            'Soldiers': df_tmp['primaryRole'].isin(['Soldado','Super Soldado']).sum(),
            'Buffed': (df_tmp['Current Condition']=='Buffed').sum(),
            'Debuffed': (df_tmp['Current Condition']=='Debuff').sum(),
            'TotalDamage': fmt_num(int(df_tmp['calculated_damage'].sum())),
            'TotalWealth': fmt_num(int(df_tmp['wealthValue'].sum())),
        })
    except:
        summary_rows.append({'Country': name, 'Citizens': 'N/A', 'Eco': 'N/A',
                             'Soldiers': 'N/A', 'Buffed': 'N/A', 'Debuffed': 'N/A',
                             'TotalDamage': 'N/A', 'TotalWealth': 'N/A'})
summary_df = pd.DataFrame(summary_rows)
st.subheader("🌐 All Countries Summary")
st.dataframe(summary_df, use_container_width=True)

# Main display for selected country
st.title(f"📊 {selected} Dashboard")
cid = ALL_COUNTRIES[selected]
df, last_updated = load_country_df(cid)
st.subheader(f"Last updated: {last_updated:%Y-%m-%d %H:%M UTC}")


# Prepare table: drop skill columns
columns_to_keep = [
    'username','level',
    'active','Current Condition','Tiempo restante',
    'wealthValue','damageValue',
    'calculated_damage', 'primaryRole','secondaryRoles'
]
df_display = df[columns_to_keep].copy()

# Sort by calculated_damage descending
df_display = df_display.sort_values('calculated_damage', ascending=False)

# Display using AgGrid for header filters
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode

# Color formatter
cellstyle_jscode = JsCode("""
function(params) {
    if (params.value == 'Buffed') {
        return { 'color': 'white', 'backgroundColor': 'green' };
    }
    if (params.value == 'Debuff') {
        return { 'color': 'white', 'backgroundColor': 'red' };
    }
    return null;
}
""")

gb = GridOptionsBuilder.from_dataframe(df_display)
gb.configure_default_column(filter=True, sortable=True, resizable=True)
gb.configure_column("Current Condition", cellStyle=cellstyle_jscode)
gb.configure_grid_options(domLayout='normal')

grid_options = gb.build()
AgGrid(df_display, gridOptions=grid_options, allow_unsafe_jscode=True, theme="balham")

# Refresh button
if st.sidebar.button("🔄 Refresh Data"):
    load_country_df.clear()
    st.rerun()
