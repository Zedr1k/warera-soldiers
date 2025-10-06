# app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
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
    "Japón": "6813b6d546e731854c7ac81d",
    "España": "6813b6d446e731854c7ac7a8",
    "Rumania": "6813b6d446e731854c7ac7b6",
    "Suecia": "6813b6d446e731854c7ac7f2",
    "Francia": "6813b6d446e731854c7ac79a",
    "Lituania": "6813b6d446e731854c7ac7b8",
    "Alemania": "6813b6d446e731854c7ac79c",
    "Saudi Arabia": "6813b6d546e731854c7ac8cb",
    "Iraq": "683ddd2c24b5a2e114af15c3",
    "Portugal": "6813b6d446e731854c7ac7aa",
    "Peru": "6813b6d546e731854c7ac83f",
    "Brasil": "6813b6d546e731854c7ac82f",
    "Mexico": "6813b6d446e731854c7ac7f8"
}

# Inicializar estado de actualización por país
if 'country_data' not in st.session_state:
    st.session_state.country_data = {}
    st.session_state.country_updated = {}
    st.session_state.refresh_states = {cid: True for cid in ALL_COUNTRIES.values()}


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

# Función para generar/actualizar el resumen
def update_summary():
    summary_data = []
    for name, cid_tmp in ALL_COUNTRIES.items():
        # Solo incluir países que están cargados
        if cid_tmp in st.session_state.country_data and st.session_state.country_data[cid_tmp] is not None:
            df_tmp = st.session_state.country_data[cid_tmp]
            
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
    
    # Almacenar en el estado de la sesión
    st.session_state.summary_data = pd.DataFrame(summary_data)

# Inicializar resumen si no existe
if 'summary_data' not in st.session_state:
    update_summary()


# Sidebar: country stats and selection
st.sidebar.title("Country Overview")
selected = st.sidebar.radio("Select a country:", list(ALL_COUNTRIES.keys()))
cid = ALL_COUNTRIES[selected]

st.sidebar.markdown("---")

tab_dashboard, tab_summary, = st.tabs([ "📊 Country Dashboard", "🌐 All Countries Summary"])

with tab_summary:
    # Sección de resumen global
    st.subheader("🌐 All Countries Summary")
    
    # Mostrar solo si hay datos cargados
    if not st.session_state.summary_data.empty:
        # Crear una versión formateada para visualización
        summary_display = st.session_state.summary_data.copy()
        
        # Formatear valores numéricos
        for col in ['Citizens', 'Eco', 'Soldiers', 'Buffed', 'Debuffed']:
            if col in summary_display:
                summary_display[col] = summary_display[col].astype(int).astype(str)
                
        for col in ['TotalDamage', 'TotalWealth']:
            if col in summary_display:
                summary_display[col] = summary_display[col].apply(fmt_num)
        
        # Mostrar la tabla formateada
        st.dataframe(summary_display, use_container_width=True)
    else:
        st.info("No hay datos de países cargados todavía. Por favor actualice algunos países primero.")


with tab_dashboard:
    # Main display for selected country
    st.title(f"📊 {selected} Dashboard")
    
    # Cargar datos del país seleccionado
    if st.session_state.refresh_states.get(cid, True):
        with st.spinner(f"Loading {selected} data..."):
            df, last_updated = load_single_country_df(cid)
            st.session_state.country_data[cid] = df
            st.session_state.country_updated[cid] = last_updated
            st.session_state.refresh_states[cid] = False
            
            # Actualizar el resumen después de cargar nuevos datos
            update_summary()
    else:
        df = st.session_state.country_data.get(cid)
        last_updated = st.session_state.country_updated.get(cid, datetime.utcnow())

    if df is None or df.empty:
        st.warning(f"No data available for {selected}. Try refreshing.")
        st.stop()

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

    # Filtrar solo usuarios activos
    if 'active' in df.columns:
        df = df[df['active']]
    if 'level' in df.columns:
        df = df[df['level'] >= 5]

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

    # Sección de gráfico de daño en debuff a lo largo del tiempo
    st.subheader("📉 Proyección de Daño en Debuff")

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
            
            # Obtener la hora actual en UTC
            now = datetime.utcnow()
            
            # Crear una lista de eventos: (tiempo, cambio de daño, jugador)
            events = []
            
            # Para jugadores en debuff actualmente
            debuffed = buff_debuff_df[buff_debuff_df['Current Condition'] == 'Debuff']
            for _, row in debuffed.iterrows():
                damage = row['calculated_damage']
                time_left = row['horas_restantes']
                # Evento de inicio (ahora)
                events.append((0, damage, f"{row['username']} entra en debuff"))
                # Evento de fin
                events.append((time_left, -damage, f"{row['username']} sale de debuff"))
            
            # Para jugadores en buff actualmente
            buffed = buff_debuff_df[buff_debuff_df['Current Condition'] == 'Buffed']
            for _, row in buffed.iterrows():
                damage = row['calculated_damage']
                buff_time_left = row['horas_restantes']
                # Evento de entrada en debuff
                events.append((buff_time_left, damage, f"{row['username']} entra en debuff"))
                # Evento de salida del debuff (24 horas después)
                events.append((buff_time_left + 16, -damage, f"{row['username']} sale de debuff"))
            
            # Ordenar eventos por tiempo
            events.sort(key=lambda x: x[0])
            
            # Crear una línea de tiempo con puntos cada 0.1 horas (6 minutos)
            max_time = max(event[0] for event in events) + 1
            timeline = np.arange(0, max_time, 0.1)
            
            # Calcular el daño acumulado en cada punto de la línea de tiempo
            current_damage = 0
            damage_timeline = []
            event_index = 0
            active_events = []  # Para seguimiento de eventos activos
            
            for t in timeline:
                # Aplicar todos los eventos que ocurren antes o en este tiempo
                while event_index < len(events) and events[event_index][0] <= t:
                    time_event, delta, desc = events[event_index]
                    current_damage += delta
                    # Mantener seguimiento de eventos activos para tooltips
                    if delta > 0:
                        active_events.append((desc, delta))
                    else:
                        # Eliminar el evento correspondiente
                        player_name = desc.replace(" sale de debuff", "")
                        active_events = [e for e in active_events if player_name not in e[0]]
                    event_index += 1
                
                damage_timeline.append(current_damage)
            
            # Crear texto para tooltips
            hover_text = []
            for t, damage in zip(timeline, damage_timeline):
                # Calcular hora exacta
                event_time = now + timedelta(hours=t)
                time_str = event_time.strftime("%Y-%m-%d %H:%M UTC")
                
                text = f"Tiempo: {time_str}<br>Daño total: {damage:,.0f}"
                
                hover_text.append(text)
            
            # Crear gráfico
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=timeline,
                y=damage_timeline,
                mode='lines',
                name='Daño total en debuff',
                line=dict(color='red', width=3),
                hoverinfo='text',
                hovertext=hover_text,
                fill='tozeroy',
                fillcolor='rgba(255,0,0,0.1)'
            ))
            
            
            # Configurar layout
            fig.update_layout(
                title='Evolución del Daño Total en Debuff',
                xaxis_title='Horas desde ahora',
                yaxis_title='Daño Total en Debuff',
                hovermode='closest',
                height=600,
                showlegend=False,
                xaxis=dict(
                    showgrid=True,
                    zeroline=True,
                    showline=True,
                    tickmode='linear',
                    dtick=6  # Mostrar marcas cada 6 horas
                ),
                yaxis=dict(
                    showgrid=True,
                    zeroline=True,
                    showline=True
                )
            )
            
            total_damage_country = df['calculated_damage'].sum()  # Ajusta según tu lógica

            # 2. Añadir línea constante del daño total
            fig.add_trace(go.Scatter(
                x=timeline,
                y=[total_damage_country] * len(timeline),  # Valor constante
                mode='lines',
                name='Daño Total del País',
                line=dict(color='blue', width=2, dash='dot'),
                hoverinfo='y+name',
                hovertemplate='Daño Total: %{y:,.0f}<extra></extra>'
            ))

            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.info("No hay ciudadanos con buff o debuff activo actualmente")
    else:
        st.warning("Datos de buff/debuff no disponibles")




