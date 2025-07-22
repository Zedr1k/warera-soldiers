# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
    /* Smaller refresh buttons */
    .small-button {
        padding: 0.1rem 0.5rem !important;
        font-size: 0.8rem !important;
    }
    /* Hide index in tables */
    table.dataframe th:first-child {
        display: none;
    }
    table.dataframe td:first-child {
        display: none;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# List of countries
ALL_COUNTRIES = {
    "Uruguay": "6813b6d546e731854c7ac835",
    "Argentina": "6813b6d546e731854c7ac832",
    "Chile": "6813b6d546e731854c7ac83c",
    "Polonia": "6813b6d446e731854c7ac7ae",
    "Venezuela": "6813b6d546e731854c7ac858",
    "España": "6813b6d446e731854c7ac7a8",
    "Rumania": "6813b6d446e731854c7ac7b6",
    "Suecia": "6813b6d446e731854c7ac7f2",
    "Francia": "6813b6d446e731854c7ac79a",
    "Lituania": "6813b6d446e731854c7ac7b8",
    "Saudi Arabia": "6813b6d546e731854c7ac8cb",
    "Iraq": "683ddd2c24b5a2e114af15c3",
    "Portugal": "6813b6d446e731854c7ac7aa"        
}

def fmt_num(n):
    if isinstance(n, str):
        return n
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f} M"
    if n >= 1_000:
        return f"{n/1_000:.1f} K"
    return str(n)

# Cache individual por país
@st.cache_data(ttl=3600, show_spinner=True)
def load_single_country_df(country_id: str):
    """Carga y cachea los datos de un solo país"""
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

# Inicializar estado de actualización por país
if 'country_data' not in st.session_state:
    st.session_state.country_data = {}
    st.session_state.country_updated = {}
    st.session_state.refresh_states = {cid: True for cid in ALL_COUNTRIES.values()}

# Sidebar: country stats and selection
st.sidebar.title("Country Overview")
selected = st.sidebar.radio("Select a country:", list(ALL_COUNTRIES.keys()))
cid = ALL_COUNTRIES[selected]

# Botón para actualizar todos los países
if st.sidebar.button("🔄 Refresh All Countries", key="refresh_all"):
    for cid in ALL_COUNTRIES.values():
        load_single_country_df.clear(cid)
        st.session_state.refresh_states[cid] = True
    st.rerun()

st.sidebar.markdown("---")

# Summary table for all countries
st.subheader("🌐 All Countries Summary")

# Crear tabla de resumen
summary_data = []
for name, cid_tmp in ALL_COUNTRIES.items():
    # Verificar si el país está cargado
    is_loaded = cid_tmp in st.session_state.country_data
    df_tmp = st.session_state.country_data.get(cid_tmp)
    
    # Usar -1 para indicar "no cargado" en lugar de strings
    if df_tmp is None or not is_loaded:
        summary_data.append({
            'Country': name,
            'Citizens': -1,
            'Eco': -1,
            'Soldiers': -1,
            'Buffed': -1,
            'Debuffed': -1,
            'TotalDamage': -1,
            'TotalWealth': -1
        })
    else:
        # Filtrar activos y nivel>=5
        df_active = df_tmp[(df_tmp['active']) & (df_tmp['level']>=5)]
        citizens = len(df_active)
        eco = df_active['primaryRole'].isin(['Trabajador','Super Trabajador','Empresario','Super Empresario']).sum()
        soldiers = df_active['primaryRole'].isin(['Soldado','Super Soldado']).sum()
        buffed = (df_active['Current Condition'] == 'Buffed').sum()
        debuffed = (df_active['Current Condition'] == 'Debuff').sum()
        total_damage = df_active['calculated_damage'].sum() if 'calculated_damage' in df_active else 0
        total_wealth = df_active['wealthValue'].sum() if 'wealthValue' in df_active else 0
        
        summary_data.append({
            'Country': name,
            'Citizens': citizens,
            'Eco': eco,
            'Soldiers': soldiers,
            'Buffed': buffed,
            'Debuffed': debuffed,
            'TotalDamage': total_damage,
            'TotalWealth': total_wealth
        })

# Crear DataFrame y luego formatear para visualización
summary_df = pd.DataFrame(summary_data)

# Función para formatear valores (-1 → "Loading...")
def format_value(val, is_loaded):
    if val == -1:
        return "Loading..." if is_loaded else "Not loaded"
    if isinstance(val, (int, float)):
        return fmt_num(val) if val >= 0 else str(val)
    return val

# Crear una versión formateada para visualización
summary_display = summary_df.copy()
for idx, row in summary_df.iterrows():
    cid_tmp = ALL_COUNTRIES[row['Country']]
    is_loaded = cid_tmp in st.session_state.country_data
    
    for col in summary_df.columns:
        if col != 'Country':
            summary_display.at[idx, col] = format_value(row[col], is_loaded)



# Main display for selected country
st.title(f"📊 {selected} Dashboard")

# Cargar datos del país seleccionado
if st.session_state.refresh_states.get(cid, True):
    with st.spinner(f"Loading {selected} data..."):
        df, last_updated = load_single_country_df(cid)
        st.session_state.country_data[cid] = df
        st.session_state.country_updated[cid] = last_updated
        st.session_state.refresh_states[cid] = False
else:
    df = st.session_state.country_data.get(cid)
    last_updated = st.session_state.country_updated.get(cid, datetime.utcnow())

if df is None or df.empty:
    st.warning(f"No data available for {selected}. Try refreshing.")
    st.stop()

# Filtrar solo usuarios activos
if 'active' in df.columns:
    df = df[df['active']]
if 'level' in df.columns:
    df = df[df['level'] >= 5]

# Botón de actualización para el país seleccionado
if st.button(f"🔄 Refresh {selected} Data", key=f"refresh_selected_{cid}"):
    load_single_country_df.clear(cid)
    st.session_state.refresh_states[cid] = True
    st.rerun()

# Relative time to last update
if last_updated:
    now = datetime.utcnow()
    delta = now - last_updated
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    parts = []
    if days:
        parts.append(f"{days} día{'s' if days>1 else ''}")
    if hours:
        parts.append(f"{hours} hora{'s' if hours>1 else ''}")
    if minutes and not days:
        parts.append(f"{minutes} minuto{'s' if minutes>1 else ''}")
    rel_time = ' y '.join(parts) if parts else 'just now'
    st.caption(f"Last updated: {rel_time} ago")
else:
    st.caption("Last updated: unknown")

# Prepare table: drop skill columns
columns_to_keep = [
    'username','level',
    'Current Condition','Tiempo restante',
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

# Sección de gráfico de buff/debuff
st.subheader("⏳ Tiempo Restante de Buff/Debuff ordenado por daño")

# Preparar datos para el gráfico
if 'Current Condition' in df.columns and 'Tiempo restante' in df.columns:
    # Filtrar solo ciudadanos con buff o debuff activo
    buff_debuff_df = df[df['Current Condition'].isin(['Buffed', 'Debuff'])].copy()
    
    if not buff_debuff_df.empty:
        # Función para convertir tiempo a horas
        def tiempo_a_horas(tiempo_str):
            if tiempo_str in ["-", "Expired"]:
                return 0
            try:
                horas = 0
                minutos = 0
                partes = tiempo_str.split()
                for parte in partes:
                    if 'h' in parte:
                        horas = int(parte.replace('h', ''))
                    if 'm' in parte:
                        minutos = int(parte.replace('m', ''))
                return horas + minutos / 60
            except:
                return 0
        
        # Aplicar conversión
        buff_debuff_df['horas_restantes'] = buff_debuff_df['Tiempo restante'].apply(tiempo_a_horas)
        
        # Para buffs: calcular el tiempo de debuff (siempre 24 horas)
        # Para debuffs: usar el tiempo restante real
        buff_debuff_df['horas_debuff'] = buff_debuff_df.apply(
            lambda row: 24 if row['Current Condition'] == 'Buffed' else row['horas_restantes'],
            axis=1
        )
        
        # Ordenar por daño (mayor daño primero)
        buff_debuff_df = buff_debuff_df.sort_values(
            by='calculated_damage', 
            ascending=True
        )
        
        # Crear gráfico
        fig = go.Figure()
        
        # Preparar listas para todos los usuarios
        all_users = buff_debuff_df['username'].tolist()
        buff_times = buff_debuff_df['horas_restantes'].tolist()
        debuff_times = buff_debuff_df['horas_debuff'].tolist()
        damage_values = buff_debuff_df['calculated_damage'].tolist()
        conditions = buff_debuff_df['Current Condition'].tolist()
        
        # Crear listas separadas para los buffed
        buffed_times = []
        buffed_users = []
        buffed_damage = []
        
        # Crear listas separadas para los debuffed
        debuffed_times = []
        debuffed_users = []
        debuffed_damage = []
        
        # Llenar las listas según la condición
        for i in range(len(all_users)):
            if conditions[i] == 'Buffed':
                buffed_times.append(buff_times[i])
                buffed_users.append(all_users[i])
                buffed_damage.append(damage_values[i])
            else:
                debuffed_times.append(debuff_times[i])
                debuffed_users.append(all_users[i])
                debuffed_damage.append(damage_values[i])
        
        # Agregar buffed al gráfico
        if buffed_users:
            # Barra de buff restante (verde)
            fig.add_trace(go.Bar(
                y=buffed_users,
                x=buffed_times,
                name='Buff Restante',
                orientation='h',
                marker=dict(color='#4CAF50'),
                hoverinfo='text',
                hovertext=[
                    f"Usuario: {user}<br>Buff restante: {time:.1f}h<br>Daño: {damage:,.0f}" 
                    for user, time, damage in zip(buffed_users, buffed_times, buffed_damage)
                ]
            ))
            
            # Barra de debuff próximo (rojo)
            fig.add_trace(go.Bar(
                y=buffed_users,
                x=[24] * len(buffed_users),  # Siempre 24 horas de debuff
                name='Debuff Próximo',
                orientation='h',
                marker=dict(color='#F44336'),
                hoverinfo='text',
                hovertext=[
                    f"Usuario: {user}<br>Debuff: {24 + time:.1f} horas<br>Daño: {damage:,.0f}" 
                    for user, damage, time in zip(buffed_users, buffed_damage, buffed_times)
                ]
            ))
        
        # Agregar debuffed al gráfico
        if debuffed_users:
            fig.add_trace(go.Bar(
                y=debuffed_users,
                x=debuffed_times,
                name='Debuff Actual',
                orientation='h',
                marker=dict(color='#F44336'),
                hoverinfo='text',
                hovertext=[
                    f"Usuario: {user}<br>Debuff restante: {time:.1f}h<br>Daño: {damage:,.0f}" 
                    for user, time, damage in zip(debuffed_users, debuffed_times, debuffed_damage)
                ]
            ))
        
        # Configurar layout
        fig.update_layout(
            barmode='stack',
            title='Tiempo Restante de Buff/Debuff',
            xaxis_title='Horas',
            yaxis_title='Usuario',
            height=600,
            showlegend=True,
            hovermode='closest',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            # Forzar el orden de los usuarios según el DataFrame ordenado
            yaxis=dict(categoryorder='array', categoryarray=all_users)
        )
        
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No hay ciudadanos con buff o debuff activo actualmente")
else:
    st.warning("Datos de buff/debuff no disponibles")
    


# Mostrar la tabla formateada
st.dataframe(summary_display, use_container_width=True)
