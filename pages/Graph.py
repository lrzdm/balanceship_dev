import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from data_utils import read_exchanges, read_companies, get_financial_data, compute_kpis, add_meta_tags
from cache_db import load_kpis_for_symbol_year, save_kpis_to_db, KPICache, Session
import json
import io
import os
import base64
import logging
import requests
import uuid


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Graph.py")

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()
    
st.set_page_config(page_title="Graphs", layout="wide")


COLUMN_LABELS = {
    "total_revenue": "Revenues",
    "net_income": "Net Income",
    "ebitda": "EBITDA",
    "gross_profit": "Gross Profit",
    "stockholders_equity": "Equity",
    "total_assets": "Total Assets",
    "basic_eps": "Basic EPS",
    "diluted_eps": "Diluted EPS"
}

# === FUNZIONI MIGLIORATE ===

USE_DB = True

@st.cache_data(show_spinner=False)
def load_kpis_filtered_by_exchange(symbols_filter=None):
    try:
        with Session() as session:
            query = session.query(KPICache)
            if symbols_filter:
                query = query.filter(KPICache.symbol.in_(symbols_filter))

            entries = query.all()
            kpi_data = []
            for e in entries:
                try:
                    val = json.loads(e.kpi_json) if isinstance(e.kpi_json, str) else e.kpi_json
                    if isinstance(val, dict):
                        val['symbol'] = e.symbol
                        val['year'] = e.year
                        val['description'] = e.description
                        val['stock_exchange'] = e.stock_exchange if hasattr(e, 'stock_exchange') else None
                        val['sector'] = e.sector if hasattr(e, 'sector') else None
                        kpi_data.append(val)
                except Exception as exc:
                    logger.warning(f"Errore parsing JSON per {e.symbol} {e.year}: {exc}")
        return pd.DataFrame(kpi_data)
    except Exception as e:
        st.error(f"Errore durante il caricamento KPI: {e}")
        return pd.DataFrame()

@st.cache_data(show_spinner=True)
def load_data_for_selection(selected_symbols, selected_years):
    from cache_db import load_many_from_db, save_kpis_to_db, Session, KPICache
    from data_utils import get_financial_data, compute_kpis

    results = {}
    to_fetch = []

    if USE_DB:
        # ✅ Caso semplice: carica dal DB tutto
        results = load_many_from_db(selected_symbols, selected_years)

    else:
        # 🔍 Verifica cosa manca nel DB
        with Session() as session:
            for symbol in selected_symbols:
                for year in selected_years:
                    exists = session.query(KPICache).filter_by(symbol=symbol, year=int(year)).first()
                    if exists:
                        logger.info(f"✅ KPI esistente per {symbol} {year}, carico da DB")
                        val = json.loads(exists.kpi_json) if isinstance(exists.kpi_json, str) else exists.kpi_json
                        val['symbol'] = symbol
                        val['year'] = year
                        val['description'] = exists.description
                        results[(symbol, year)] = val
                    else:
                        logger.info(f"🔄 KPI mancanti per {symbol} {year}, vanno calcolati")
                        to_fetch.append((symbol, year))

        # 🔁 Calcolo e salvataggio solo per i mancanti
        for symbol, year in to_fetch:
            try:
                raw_data = get_financial_data(symbol, int(year))
                if not raw_data:
                    logger.warning(f"Nessun dato finanziario per {symbol} {year}")
                    continue

                df_kpis = compute_kpis(raw_data)
                if df_kpis.empty:
                    logger.warning(f"KPI vuoti per {symbol} {year}")
                    continue

                save_kpis_to_db(df_kpis)

                for _, row in df_kpis.iterrows():
                    record = row.to_dict()
                    record['symbol'] = symbol
                    record['year'] = year
                    results[(symbol, year)] = record

            except Exception as e:
                logger.error(f"Errore nel calcolo o salvataggio KPI per {symbol} {year}: {e}")

    # 🔄 Ricostruzione lista di dizionari per DataFrame
    data = []
    for (symbol, year), record in results.items():
        if isinstance(record, dict) and record:
            record['symbol'] = symbol
            record['year'] = year
            data.append(record)

    return data


# === RENDER KPIs ===
def render_kpis(exchanges_dict):
    st.header("📊 KPI Dashboard")

    exchange_names = list(exchanges_dict.keys())
    exchange_options = ["All"] + exchange_names

    # Imposta default "FTSE MIB"
    try:
        default_index = exchange_options.index("NASDAQ")
    except ValueError:
        default_index = 0

    selected_exchange = st.selectbox("Select Exchange", exchange_options, index=default_index)

    # Caricamento dati
    if selected_exchange != "All":
        companies_exchange = read_companies(exchanges_dict[selected_exchange])
        symbols_for_exchange = {c["ticker"] for c in companies_exchange if "ticker" in c}
        df_all_kpis = load_kpis_filtered_by_exchange(symbols_for_exchange)
    else:
        df_all_kpis = load_kpis_filtered_by_exchange()
        symbols_for_exchange = None

    # 🔄 Se mancano i KPI 2024, proviamo a caricarli
    years_present = df_all_kpis["year"].astype(str).unique().tolist()
    if selected_exchange != "All" and '2024' not in years_present:
        try:
            st.info("Caricamento dati 2024 in corso...")
            load_data_for_selection(list(symbols_for_exchange), ['2024'])

            # Ricarico i dati dopo l'import
            df_all_kpis = load_kpis_filtered_by_exchange(symbols_for_exchange)
            years_present = df_all_kpis["year"].astype(str).unique().tolist()

            if '2024' not in years_present:
                st.warning("I dati per il 2024 non sono ancora disponibili dopo il caricamento.")
        except Exception as e:
            st.error(f"Errore nel caricamento dati 2024: {e}")
            return

    if df_all_kpis.empty:
        st.warning("Nessun dato disponibile.")
        return

    # UI per selezione azienda e anni
    descriptions_dict = df_all_kpis.groupby("description")["symbol"].apply(lambda x: list(sorted(set(x)))).to_dict()
    descriptions_available = sorted(k for k in descriptions_dict if k is not None)
    years_available = sorted(df_all_kpis["year"].astype(str).unique())

    selected_desc = st.multiselect("Select Companies", descriptions_available, default=descriptions_available[:1])
    default_years_selection = ['2024'] if '2024' in years_available else years_available[-1:]
    selected_years = st.multiselect("Select Years", years_available, default=default_years_selection)

    if not selected_desc or not selected_years:
        st.warning("Please select at least one company.")
        return

    selected_symbols = []
    for d in selected_desc:
        selected_symbols.extend(descriptions_dict.get(d, []))

    df_filtered = df_all_kpis[
        (df_all_kpis['symbol'].isin(selected_symbols)) &
        (df_all_kpis['year'].astype(str).isin(selected_years)) &
        (df_all_kpis['description'].isin(selected_desc))
    ]

    if df_filtered.empty:
        st.warning("No data found.")
        return

    # Pivot per visualizzazione tabellare
    id_vars = ['symbol', 'description', 'year']
    value_vars = [col for col in df_filtered.columns if col not in id_vars and df_filtered[col].dtype != 'object']
    df_melt = df_filtered.melt(id_vars=id_vars, value_vars=value_vars, var_name='KPI', value_name='Value')
    df_melt['desc_year'] = df_melt['description'] + ' ' + df_melt['year'].astype(str)
    df_melt['KPI'] = df_melt['KPI'].apply(lambda k: COLUMN_LABELS.get(k, k))
    df_pivot = df_melt.pivot(index='KPI', columns='desc_year', values='Value')

    df_pivot = df_pivot.apply(pd.to_numeric, errors='coerce')
    df_clean = df_pivot.fillna(np.nan)

    st.subheader("📋 KPIs List")
    num_cols = df_clean.select_dtypes(include=['number']).columns
    styled = df_clean.style.format({col: "{:.2%}" for col in num_cols})
    st.dataframe(styled, height=600)

    
    import plotly.graph_objects as go

    # 🎨 Palette accesa e distinta
    color_palette = [
        "#E41A1C",  # Rosso acceso
        "#377EB8",  # Blu vivo
        "#4DAF4A",  # Verde brillante
        "#984EA3",  # Viola intenso
        "#FF7F00",  # Arancione acceso
        "#FFD700",  # Giallo oro
        "#00CED1",  # Turchese
        "#A65628",  # Bronzo/marrone
        "#F781BF",  # Rosa shocking
        "#000000",  # Nero
    ]
    
    st.subheader("📊 Confronto aziende sui KPI (Radar con area media e colori accesi)")
    
    id_vars = ['symbol', 'description', 'year']
    candidate_cols = [c for c in df_filtered.columns if c not in id_vars]
    
    if not candidate_cols:
        st.info("Nessun KPI numerico disponibile per il radar chart.")
    else:
        # dataset: media per azienda+anno
        radar_df = df_filtered[['description', 'year'] + candidate_cols].copy()
        radar_df = radar_df.groupby(['description', 'year']).mean().reset_index()
    
        # etichette KPI leggibili
        kpi_labels = [COLUMN_LABELS.get(c, c).replace('_', ' ').title() for c in candidate_cols]
    
        fig = go.Figure()
    
        # === Fascia media (riempimento grigio) ===
        mean_values = radar_df[candidate_cols].mean().tolist()
        mean_values_closed = mean_values + [mean_values[0]]
        labels_closed = kpi_labels + [kpi_labels[0]]
    
        fig.add_trace(go.Scatterpolar(
            r=mean_values_closed,
            theta=labels_closed,
            fill='toself',
            mode='lines',
            line=dict(color="lightgrey", dash="dot"),
            name="Media aziende",
            opacity=0.4
        ))
    
        # === Linee delle aziende con colori accesi ===
        for i, (_, row) in enumerate(radar_df.iterrows()):
            values = [row[c] if pd.notna(row[c]) else 0 for c in candidate_cols]
            values_closed = values + [values[0]]
    
            fig.add_trace(go.Scatterpolar(
                r=values_closed,
                theta=labels_closed,
                fill='none',
                mode='lines+markers',
                line=dict(color=color_palette[i % len(color_palette)], width=2),
                marker=dict(size=6, color=color_palette[i % len(color_palette)]),
                name=f"{row['description']} {row['year']}"
            ))
    
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),  # range auto adattato ai valori reali
            showlegend=True,
            margin=dict(l=20, r=20, t=40, b=20),
            height=650
        )
    
        st.plotly_chart(fig, use_container_width=True)


    
    # Download Excel
    buffer = io.BytesIO()
    df_filtered_clean = df_filtered.copy().replace({np.nan: ""})
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_filtered_clean.to_excel(writer, index=False, sheet_name='KPI')
    st.download_button(
        label="📥 Download Excel",
        data=buffer.getvalue(),
        file_name="kpi_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    # Bubble Chart
    st.subheader("🔵 Bubble Chart")
    bubble_cols = [col for col in df_filtered.columns if col not in ['symbol', 'description', 'year', 'exchange']]
    if len(bubble_cols) >= 3:
        col1, col2, col3 = st.columns(3)
        with col1:
            x_axis = st.selectbox("X Axis", bubble_cols, format_func=lambda x: COLUMN_LABELS.get(x, x))
        with col2:
            y_axis = st.selectbox("Y Axis", bubble_cols, index=1, format_func=lambda x: COLUMN_LABELS.get(x, x))
        with col3:
            size_axis = st.selectbox("Bubble Size", bubble_cols, index=2, format_func=lambda x: COLUMN_LABELS.get(x, x))

        df_plot = df_filtered.dropna(subset=[x_axis, y_axis, size_axis]).copy()
        df_plot[size_axis] = df_plot[size_axis].clip(lower=0.1)
        df_plot['label'] = df_plot['description'] + ' ' + df_plot['year'].astype(str)

        fig = px.scatter(
            df_plot,
            x=x_axis,
            y=y_axis,
            size=size_axis,
            color='description',
            hover_name='label',
            title="KPI Bubble Chart",
            labels={
                x_axis: COLUMN_LABELS.get(x_axis, x_axis),
                y_axis: COLUMN_LABELS.get(y_axis, y_axis),
                size_axis: COLUMN_LABELS.get(size_axis, size_axis)
            }
        )

        st.plotly_chart(fig, use_container_width=True)

# === GRAFICO SEPARATO ===
def render_sector_average_chart():
    st.header("📊 Metric Average per Sector")
    exchanges = read_exchanges("exchanges.txt")

    metrics_available = ["ebitda", "total_revenue", "net_income"]
    metric_sector_label = st.selectbox("Metric", [COLUMN_LABELS.get(m, m) for m in metrics_available], index=0)
    reverse_labels = {v: k for k, v in COLUMN_LABELS.items()}
    metric_sector = reverse_labels.get(metric_sector_label, metric_sector_label)

    selected_exchange = st.selectbox("Exchange", list(exchanges.keys()))
    selected_year = st.selectbox("Year", ['2021', '2022', '2023', '2024'], index=3)

    companies_exchange = read_companies(exchanges[selected_exchange])
    symbols_exchange = [c['ticker'] for c in companies_exchange]
    #df_sector = pd.DataFrame(load_data_for_selection(symbols_exchange, [selected_year]))
    df_sector = pd.DataFrame(
    load_data_for_selection(tuple(symbols_exchange), tuple([selected_year]))
    )
    
    if df_sector.empty:
        st.warning("Please select at least one exchange.")
        return

    df_sector['year'] = df_sector['year'].astype(str)
    df_sector['sector'] = df_sector['sector'].replace("null", np.nan)
    df_sector[metric_sector] = pd.to_numeric(df_sector[metric_sector], errors='coerce')
    df_sector = df_sector.dropna(subset=["sector", metric_sector])

    if df_sector.empty:
        st.warning("No data found.")
        return

    sector_avg = df_sector.groupby("sector")[metric_sector].mean().reset_index()
    fig = px.bar(
        sector_avg,
        x="sector",
        y=metric_sector,
        title=f"Average {COLUMN_LABELS.get(metric_sector, metric_sector)} in {selected_year} ({selected_exchange})",
        labels={metric_sector: COLUMN_LABELS.get(metric_sector, metric_sector), "sector": "Sector"}
    )
    st.plotly_chart(fig, use_container_width=True)


# === GRAFICI INTERATTIVI ===
def render_general_graphs():
    st.header("📈 Interactive Graphs")

    exchanges = read_exchanges("exchanges.txt")
    exchange_names = list(exchanges.keys())
    selected_exchange = st.selectbox("Select Exchange", ["All"] + exchange_names, index=0)

    companies_all = []
    if selected_exchange == "All":
        for path in exchanges.values():
            companies_all += read_companies(path)
    else:
        companies_all = read_companies(exchanges[selected_exchange])

    descriptions_dict = {c['description']: c['ticker'] for c in companies_all if 'description' in c and 'ticker' in c}
    descriptions_available = sorted(descriptions_dict.keys())

    selected_desc = st.multiselect("Select Companies", descriptions_available, default=descriptions_available[:1])
    if not selected_desc:
        st.warning("Please select at least one company.")
        return

    # Anni disponibili fissi nel range richiesto
    all_years = ['2021', '2022', '2023', '2024']
    selected_years = st.multiselect("Select Years", all_years, default=all_years)

    selected_symbols = [descriptions_dict[d] for d in selected_desc]
    df = pd.DataFrame(load_data_for_selection(selected_symbols, selected_years))

    if df.empty:
        st.warning("No data found.")
        return

    # Forza la conversione a stringa per uniformità
    df['year'] = df['year'].astype(str)

    # Filtra solo gli anni selezionati
    df = df[df['year'].isin(selected_years)]

    columns_to_plot = [
        "total_revenue", "net_income", "ebitda", "gross_profit",
        "stockholders_equity", "total_assets", "basic_eps", "diluted_eps"
    ]
    display_to_code = {COLUMN_LABELS.get(k, k): k for k in columns_to_plot}
    display_columns = list(display_to_code.keys())

    # GRAFICO 1
    st.subheader("📉 Graph 1: Metric over Time per Company")
    metric_label = st.selectbox("Select Metric", display_columns, index=0)
    metric = display_to_code[metric_label]
    df[metric] = pd.to_numeric(df[metric], errors='coerce')

    # Ordina gli anni in ordine naturale per evitare problemi sull'asse X
    df['year'] = pd.Categorical(df['year'], categories=all_years, ordered=True)

    fig = px.line(
        df,
        x="year",
        y=metric,
        color="description",
        markers=True,
        title=f"{COLUMN_LABELS.get(metric, metric)} over time"
    )
    fig.update_xaxes(type='category')  # forza asse discreto
    st.plotly_chart(fig, use_container_width=True)

    # GRAFICO 2
    st.subheader("📐 Graph 2: Custom Ratio Over Time")
    col1, col2 = st.columns(2)
    with col1:
        numerator_label = st.selectbox("Numerator", display_columns, index=2)
    with col2:
        denominator_label = st.selectbox("Denominator", display_columns, index=0)

    numerator = display_to_code[numerator_label]
    denominator = display_to_code[denominator_label]

    if numerator != denominator:
        df_ratio = df.copy()
        df_ratio[numerator] = pd.to_numeric(df_ratio[numerator], errors='coerce')
        df_ratio[denominator] = pd.to_numeric(df_ratio[denominator], errors='coerce')
        df_ratio['ratio'] = df_ratio[numerator] / df_ratio[denominator]

        fig2 = px.line(
            df_ratio,
            x='year',
            y='ratio',
            color='description',
            markers=True,
            title=f"{COLUMN_LABELS.get(numerator, numerator)} / {COLUMN_LABELS.get(denominator, denominator)} Over Time"
        )
        fig2.update_xaxes(type='category')  # asse discreto
        st.plotly_chart(fig2, use_container_width=True)


# === MAIN ===
def run():
    exchanges = read_exchanges("exchanges.txt")
    render_kpis(exchanges)
    st.markdown("---")
    render_sector_average_chart()
    st.markdown("---")
    render_general_graphs()

if __name__ == "__main__":
    run()

# --- SIDEBAR ---
logo_path = os.path.join("images", "logo4.png")
logo_base64 = get_base64_of_bin_file(logo_path) if os.path.exists(logo_path) else ""

# Percorsi delle icone
instagram_icon_path = os.path.join("images", "IG.png")
linkedin_icon_path = os.path.join("images", "LIN.png")

# Converti le immagini in base64
instagram_icon_base64 = get_base64_of_bin_file(instagram_icon_path)
linkedin_icon_base64 = get_base64_of_bin_file(linkedin_icon_path)

st.sidebar.markdown(f"""
    <div style='text-align: center;'>
        <img src="data:image/png;base64,{logo_base64}" style="height: 70px; display: inline-block; margin-top: 20px;"><br>
        <span style='font-size: 14px;'>Navigate financial sea with clarity ⚓</span><br>
        <a href='https://www.instagram.com/tuo_profilo' target='_blank' style="display: inline-block; margin-top: 20px;">
            <img src='data:image/png;base64,{instagram_icon_base64}' width='40' height='40'>
        <a href='https://www.linkedin.com/company/balanceship/' target='_blank' style="display: inline-block; margin-top: 20px;">
            <img src='data:image/png;base64,{linkedin_icon_base64}' width='40' height='40'>
    </div>

""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<hr style="margin-top:50px;"/>
<div style='text-align: center; font-size: 0.9rem; color: grey;'>
    &copy; 2025 BalanceShip. All rights reserved.
</div>
""", unsafe_allow_html=True)







