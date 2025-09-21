import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_utils import read_exchanges, read_companies, get_financial_data, remove_duplicates, compute_kpis, add_meta_tags
from data_utils import get_or_fetch_data 
import os
import base64
import requests
import uuid
import textwrap
import numpy as np
import random

MEASUREMENT_ID = "G-Q5FDX0L1H2" # Il tuo ID GA4 
API_SECRET = "kRfQwfxDQ0aACcjkJNENPA" # Quello creato in GA4 

if "client_id" not in st.session_state:
    st.session_state["client_id"] = str(uuid.uuid4())

# --------------- Client-side GA4 -----------------
st.markdown(f"""
<!-- GA4 tracking client-side -->
<script async src="https://www.googletagmanager.com/gtag/js?id={MEASUREMENT_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{MEASUREMENT_ID}');
</script>
""", unsafe_allow_html=True)

def send_pageview():
    url = f"https://www.google-analytics.com/mp/collect?measurement_id={MEASUREMENT_ID}&api_secret={API_SECRET}"
    payload = {
        "client_id": st.session_state["client_id"],
        "events": [
            {
                "name": "page_view",
                "params": {
                    "page_title": "KPI_Dashboard",
                    "page_location": "https://www.balanceship.net/KPI_Dashboard",
                    "engagement_time_msec": 1
                }
            }
        ]
    }
    requests.post(url, json=payload)

send_pageview()

#Google tag:
add_meta_tags(
    title="KPI Dashboard",
    description="Explore company dashboards with smart insights",
    url_path="/KPI_Dashboard"
)

st.set_page_config(page_title="KPI Dashboard", layout="wide")
st.title("📊 KPI Dashboard")

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

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

color_palette = [
    "#6495ED",  # Cornflower Blue
    "#3CB371",  # Medium Sea Green
    "#FF6347",  # Tomato
    "#DAA520",  # Goldenrod
    "#4169E1",  # Royal Blue
    "#BA55D3",  # Medium Orchid
    "#FF8C00",  # Dark Orange
    "#40E0D0",  # Turquoise
    "#708090",  # Slate Gray
    "#B22222"   # Firebrick
]

# Lettura borse e aziende
exchanges = read_exchanges("exchanges.txt")
exchange_names = list(exchanges.keys())
exchange_names = ["All"] + exchange_names   # aggiungo opzione All

years_available = ['2021', '2022', '2023', '2024']
sectors_available = ['Communication Services', 'Consumer Cyclical', 'Consumer Defensive', 'Energy', 'Financial Services', 'Healthcare', 'Industrials', 'Real Estate', 'Technology', 'Utilities']

# --- Layout filtri in riga ---
col1, col2, col3, col4 = st.columns([1.2, 1.5, 2.2, 2])
with col1:
    selected_year = st.selectbox("Year", years_available, index=2, key="year_select")
with col2:
    selected_exchange = st.selectbox("Exchange", exchange_names, index=0, key="exchange_select")

# --- Carico lista aziende basata sulla selezione exchange ---
if selected_exchange == "All":
    companies = []
    for exch in exchanges.values():
        companies.extend(read_companies(exch))
else:
    companies = read_companies(exchanges[selected_exchange])

symbol_to_name = {c["ticker"]: c["description"] for c in companies}
name_to_symbol = {v: k for k, v in symbol_to_name.items()}
company_names = list(symbol_to_name.values())

with col3:
    selected_company_names = st.multiselect("Companies (up to 10)", options=sorted(company_names), max_selections=10, key="companies_select")
    selected_symbols = [name_to_symbol[name] for name in selected_company_names]

with col4:
    if selected_exchange == "All":
        selected_sector = st.selectbox("Sector", options=["All"], disabled=True, 
                                     help="Sector filter is disabled when 'All' exchanges are selected", key="sector_select_disabled")
    else:
        selected_sector = st.selectbox("Sector", options=["All"] + sectors_available, key="sector_select_enabled")

# --- Cache avanzata per mediane di settore (24 ore) ---
@st.cache_data(ttl=86400)  # Cache per 24 ore
def get_sector_medians_cached(sector, exchange, year):
    """Calcola e cachea le mediane di settore"""
    try:
        all_sector_data = []
        sectors_found = {}  # Per debug
        exch_file = exchanges[exchange]
        companies_in_exchange = read_companies(exch_file)
        
        # Limita a massimo 50 aziende per settore (sample rappresentativo)
        companies_processed = 0
        max_companies = 50
        companies_checked = 0
        
        for company in companies_in_exchange:
            if companies_processed >= max_companies:
                break
                
            companies_checked += 1
            desc = company.get("description", "")
            try:
                data = get_or_fetch_data(company["ticker"], [year], desc, exchange)
                for d in data:
                    company_sector = d.get("sector")
                    if company_sector:
                        # Conta tutti i settori trovati (per debug)
                        if company_sector not in sectors_found:
                            sectors_found[company_sector] = 0
                        sectors_found[company_sector] += 1
                        
                        # Match più flessibile del settore
                        if (company_sector == sector or 
                            company_sector.strip().lower() == sector.strip().lower()):
                            all_sector_data.append(d)
                            companies_processed += 1
            except:
                continue
        
        # Debug info (restituiamo anche questo)
        debug_info = {
            "companies_checked": companies_checked,
            "sectors_found": sectors_found,
            "target_sector": sector,
            "companies_matched": len(all_sector_data)
        }
        
        if not all_sector_data:
            return {}, 0, debug_info
            
        # Calcola KPI
        df_all_sector = compute_kpis(all_sector_data)
        df_all_sector = df_all_sector[df_all_sector["year"] == int(year)]
        
        # Merge con dati raw per EPS
        df_raw_sector = pd.DataFrame(all_sector_data)
        if "ticker" in df_raw_sector.columns and "symbol" not in df_raw_sector.columns:
            df_raw_sector.rename(columns={"ticker": "symbol"}, inplace=True)
        
        df_all_sector = pd.merge(
            df_all_sector,
            df_raw_sector[["symbol", "basic_eps", "sector"]],
            on="symbol",
            how="left"
        )
        
        # Rinomina colonne
        df_all_sector.rename(columns={
            "EBITDA Margin": "EBITDA Margin",
            "Debt/Equity": "Debt to Equity", 
            "FCF Margin": "FCF Margin",
            "basic_eps": "EPS"
        }, inplace=True)
        
        # Calcola mediane
        medians = {}
        metrics = ["EBITDA Margin", "FCF Margin", "Debt to Equity", "EPS"]
        for metric in metrics:
            medians[metric] = _safe_median(df_all_sector, metric)
            
        return medians, len(df_all_sector), debug_info
        
    except Exception as e:
        return {}, 0, {"error": str(e)}

# --- Caricamento dati aziende selezionate ---
financial_data = []
used_exchanges = set()  # Traccia le borse effettivamente usate

for symbol in selected_symbols:
    desc = symbol_to_name.get(symbol, "")
    # se All → ciclo su tutte le borse, altrimenti solo quella selezionata
    if selected_exchange == "All":
        # ciclo su tutte le borse per trovare l'azienda
        for exch_name, exch_file in exchanges.items():
            try:
                data = get_or_fetch_data(symbol, [selected_year], desc, exch_name)
                if data:  # se trovo dati, li aggiungo e passo al prossimo symbol
                    financial_data.extend(data)
                    used_exchanges.add(exch_name)  # Traccia borsa usata
                    break
            except:
                continue
    else:
        data = get_or_fetch_data(symbol, [selected_year], desc, selected_exchange)
        if data:
            financial_data.extend(data)
            used_exchanges.add(selected_exchange)  # Traccia borsa usata

# --- Calcolo mediana di settore ottimizzato ---
metrics = ["EBITDA Margin", "FCF Margin", "Debt to Equity", "EPS"]
sector_medians = {}
sector_count = 0

if selected_sector != "All" and selected_exchange != "All":
    # Carica da cache o calcola (con progress limitato)
    with st.spinner(f"Loading {selected_sector} sector benchmark..."):
        sector_medians, sector_count, debug_info = get_sector_medians_cached(
            selected_sector, selected_exchange, selected_year
        )
    
    if sector_count > 0:
        st.success(f"✅ Sector benchmark from {sector_count} {selected_sector} companies ({selected_exchange})")
    else:
        st.warning(f"⚠️ No {selected_sector} companies found in {selected_exchange}")
        
        # Mostra debug info per capire il problema
        if "sectors_found" in debug_info:
            st.write("**🔍 Debug - Sectors found in data:**")
            sorted_sectors = sorted(debug_info["sectors_found"].items(), key=lambda x: x[1], reverse=True)
            for sector_name, count in sorted_sectors[:10]:  # Top 10
                if sector_name.lower() == selected_sector.lower():
                    st.write(f"- **{sector_name}**: {count} companies ⭐ (MATCH)")
                else:
                    st.write(f"- {sector_name}: {count} companies")
            
            st.write(f"Companies checked: {debug_info.get('companies_checked', 0)}")
            st.write(f"Target sector: '{debug_info.get('target_sector', '')}'")
        
elif selected_sector != "All" and selected_exchange == "All":
    st.info("💡 Sector comparison disabled when 'All' exchanges selected")

# --- Se non c'è nulla, stop ---
if not financial_data:
    st.warning("No data available for the selected companies.")
    st.stop()

# --- Unisco dati selezionati e settore (per calcolo media) ---
combined_data = financial_data  # Solo dati delle aziende selezionate

# --- Calcolo KPI ---
df_kpi_all = compute_kpis(combined_data)
df_kpi_all = df_kpi_all[df_kpi_all["year"] == int(selected_year)]

# --- EPS e settore dal raw data ---
df_raw = pd.DataFrame(combined_data)
if "ticker" in df_raw.columns and "symbol" not in df_raw.columns:
    df_raw.rename(columns={"ticker": "symbol"}, inplace=True)

df_kpi_all = pd.merge(
    df_kpi_all,
    df_raw[["symbol", "basic_eps", "sector"]],
    on="symbol",
    how="left"
)

# Rinomina chiara
df_kpi_all.rename(columns={
    "EBITDA Margin": "EBITDA Margin",
    "Debt/Equity": "Debt to Equity",
    "FCF Margin": "FCF Margin",
    "basic_eps": "EPS"
}, inplace=True)

# Aggiungi descrizione azienda
df_kpi_all["company_name"] = df_kpi_all["symbol"].map(symbol_to_name)

# Split: dati visibili vs per media di settore
df_visible = df_kpi_all[df_kpi_all["symbol"].isin(selected_symbols)]

def legend_chart():
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="lines",
        line=dict(color="red", dash="dash"),
        name="Companies Median"
    ))
    fig.add_trace(go.Scatter(
        x=[None], y=[None],
        mode="lines",
        line=dict(color="blue", dash="dot"),
        name="Sector Median"
    ))
    fig.update_layout(
        height=50,
        margin=dict(t=0, b=0, l=0, r=0),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1,
            xanchor="center",
            x=0.5
        )
    )
    return fig

# Mostro legenda sotto filtri, sopra grafici
st.plotly_chart(legend_chart(), use_container_width=True)

def _safe_median(df, col):
    """Restituisce la mediana sicura (gestisce NaN, inf, col mancanti)."""
    if df is None or df.empty or col not in df.columns:
        return np.nan
    series = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return np.nan
    return float(series.median())

# Funzione grafico ottimizzata (senza sovrapposizioni)
def kpi_chart(df_visible, metric, title, is_percent=True):

    fig = go.Figure()
    
    # --- Preparazioni ---
    company_names_raw = df_visible["company_name"].tolist()
    company_names_wrapped = [textwrap.fill(label, width=12) for label in company_names_raw]
    company_colors = {name: color_palette[i % len(color_palette)] for i, name in enumerate(company_names_raw)}

    # valori y
    y_series = pd.to_numeric(df_visible[metric], errors="coerce")
    y_values = y_series.values.astype(float)
    if is_percent:
        y_values = y_values * 100

    # --- Calcolo range per posizionamento smart ---
    valid_values = y_values[~np.isnan(y_values)]
    if len(valid_values) > 0:
        y_min, y_max = valid_values.min(), valid_values.max()
        y_range = y_max - y_min
        if y_range == 0:
            y_range = abs(y_max) * 0.1 if y_max != 0 else 1
    else:
        y_min, y_max, y_range = 0, 1, 1

    # --- Bar principale ---
    fig.add_trace(go.Bar(
        x=company_names_wrapped,
        y=y_values,
        marker_color=[company_colors[name] for name in company_names_raw],
        showlegend=False,
        hovertemplate='<b>%{x}</b><br>%{y:.1f}' + ('%' if is_percent else '') + '<extra></extra>'
    ))

    # --- Calcolo mediane ---
    global_median = _safe_median(df_visible, metric)
    if is_percent and not np.isnan(global_median):
        global_median *= 100

    sector_median = sector_medians.get(metric, np.nan)
    if is_percent and not np.isnan(sector_median):
        sector_median *= 100

    # --- Aggiungi valori sopra le barre ---
    for i, (name, val) in enumerate(zip(company_names_wrapped, y_values)):
        if not np.isnan(val):
            fig.add_annotation(
                x=name,
                y=val,
                text=f"{val:.1f}{'%' if is_percent else ''}",
                showarrow=False,
                yshift=8,
                font=dict(size=9, color="black"),
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor="rgba(0,0,0,0.1)",
                borderwidth=1
            )

    # --- Delta frecce con posizionamento smart ---
    if not np.isnan(global_median):
        for i, val in enumerate(y_values):
            if np.isnan(val):
                continue
            delta = val - global_median
            if abs(delta) < 0.05:
                continue
                
            arrow = "▲" if delta > 0 else "▼"
            color = "#28a745" if delta > 0 else "#dc3545"
            y_position = val + (y_range * 0.12)
            
            fig.add_annotation(
                x=company_names_wrapped[i],
                y=y_position,
                text=f"{arrow}{abs(delta):.1f}{'%' if is_percent else ''}",
                showarrow=False,
                font=dict(size=8, color=color, family="Arial Black"),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor=color,
                borderwidth=1
            )

    # --- Linee mediane con posizionamento smart ---
    annotation_positions = []
    
    if not np.isnan(global_median):
        companies_pos = "top left"
        fig.add_hline(
            y=global_median,
            line=dict(color="#dc3545", dash="dash", width=2),
            annotation_text=f"Companies: {global_median:.1f}{'%' if is_percent else ''}",
            annotation_position=companies_pos,
            annotation_font=dict(color="#dc3545", size=10),
            annotation_bgcolor="rgba(255,255,255,0.9)",
            annotation_bordercolor="#dc3545",
            annotation_borderwidth=1
        )
        annotation_positions.append(("companies", companies_pos))

    if not np.isnan(sector_median):
        sector_pos = "top right" if any(pos[1] == "top left" for pos in annotation_positions) else "bottom right"
        fig.add_hline(
            y=sector_median,
            line=dict(color="#007bff", dash="dot", width=2),
            annotation_text=f"Sector: {sector_median:.1f}{'%' if is_percent else ''}",
            annotation_position=sector_pos,
            annotation_font=dict(color="#007bff", size=10),
            annotation_bgcolor="rgba(255,255,255,0.9)",
            annotation_bordercolor="#007bff",
            annotation_borderwidth=1
        )

    # --- Layout ---
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Arial")),
        yaxis_title=f"{metric}{' (%)' if is_percent else ''}",
        height=350,
        margin=dict(t=60, b=70, l=50, r=50),
        showlegend=False,
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=10),
        yaxis=dict(range=[y_min - (y_range * 0.1), y_max + (y_range * 0.25)])
    )

    return fig

# --- Mostro i grafici ---
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(kpi_chart(df_visible, "EBITDA Margin", "EBITDA Margin", is_percent=True), use_container_width=True)
    st.plotly_chart(kpi_chart(df_visible, "FCF Margin", "FCF Margin", is_percent=True), use_container_width=True)
with col2:
    st.plotly_chart(kpi_chart(df_visible, "Debt to Equity", "Debt to Equity", is_percent=False), use_container_width=True)
    st.plotly_chart(kpi_chart(df_visible, "EPS", "Earnings per Share (EPS)", is_percent=False), use_container_width=True)

# --- INSIGHT CLEAN (niente duplicati) ---
insight_list = []
for index, row in df_visible.iterrows():
    company = row["company_name"]
    sector = row["sector"]
    ebitda_margin = row["EBITDA Margin"]
    fcf_margin = row["FCF Margin"]
    debt_equity = row["Debt to Equity"]
    eps = row["EPS"]

    if pd.isna(sector):
        continue

    sector_df = df_kpi_all[df_kpi_all["sector"] == sector]
    avg_ebitda = sector_df["EBITDA Margin"].mean()
    avg_fcf = sector_df["FCF Margin"].mean()
    avg_debt_equity = sector_df["Debt to Equity"].mean()
    avg_eps = sector_df["EPS"].mean()

    # EBITDA Margin
    if not pd.isna(ebitda_margin):
        ebitda_margin_pct = ebitda_margin * 100
        if ebitda_margin_pct > avg_ebitda * 1.2:
            options = [
                f"**{company}** demonstrates operational efficiency well above the sector norm, with an EBITDA margin of {ebitda_margin_pct:.1f}%.",
                f"The EBITDA margin of **{company}** ({ebitda_margin_pct:.1f}%) exceeds its industry average."
            ]
            insight_list.append(random.choice(options))
        elif ebitda_margin_pct < avg_ebitda * 0.8:
            options = [
                f"**{company}** struggles to convert revenue into operating profit, with an EBITDA margin of only {ebitda_margin_pct:.1f}%.",
                f"The EBITDA performance of **{company}** ({ebitda_margin_pct:.1f}%) lags well behind sector peers."
            ]
            insight_list.append(random.choice(options))

    # FCF Margin
    if not pd.isna(fcf_margin):
        fcf_margin_pct = fcf_margin * 100
        if fcf_margin_pct > avg_fcf * 1.2:
            options = [
                f"**{company}** stands out for its excellent cash flow generation, posting a FCF margin of {fcf_margin_pct:.1f}%.",
                f"With a FCF margin of {fcf_margin_pct:.1f}%, **{company}** ranks among the top in cash conversion."
            ]
            insight_list.append(random.choice(options))
        elif fcf_margin_pct < avg_fcf * 0.8:
            options = [
                f"**{company}** underperforms in turning revenue into free cash flow, with a margin of {fcf_margin_pct:.1f}%.",
                f"**{company}** shows weakness in FCF efficiency compared to the sector (only {fcf_margin_pct:.1f}%)."
            ]
            insight_list.append(random.choice(options))

    # Debt to Equity
    if not pd.isna(debt_equity):
        if debt_equity > avg_debt_equity * 1.3:
            options = [
                f"**{company}** is highly leveraged, with a debt-to-equity ratio of {debt_equity:.2f}, above the sector average.",
                f"Financial leverage is a concern for **{company}**, with D/E at {debt_equity:.2f}."
            ]
            insight_list.append(random.choice(options))
        elif debt_equity < avg_debt_equity * 0.7:
            options = [
                f"**{company}** maintains a solid balance sheet with low reliance on debt (D/E: {debt_equity:.2f}).",
                f"**{company}** shows strong capital structure, with low debt levels (D/E: {debt_equity:.2f})."
            ]
            insight_list.append(random.choice(options))

    # EPS
    if not pd.isna(eps):
        if eps > avg_eps * 1.2:
            options = [
                f"**{company}** delivers strong earnings per share of {eps:.2f}, outpacing its industry.",
                f"**{company}** posts robust EPS ({eps:.2f}) compared to the sector average."
            ]
            insight_list.append(random.choice(options))
        elif eps < avg_eps * 0.8:
            options = [
                f"**{company}** trails the sector in earnings, with an EPS of just {eps:.2f}.",
                f"Earnings per share of **{company}** ({eps:.2f}) fall short of peer performance."
            ]
            insight_list.append(random.choice(options))

# Shuffle e massimo 30
unique_insights = list(dict.fromkeys(insight_list))
random.shuffle(unique_insights)
insight_list = unique_insights[:30]

# Output nel frontend
if insight_list:
    st.markdown("---")
    st.subheader("💡 Key Insights")

    # Detect dark or light mode
    is_dark_mode = st.get_option("theme.base") == "dark"

    # Convert **text** to real <b>text</b> without style
    def markdown_to_html(text):
        import re
        return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

    # Set colors based on theme
    bg_color = "#1e1e1e" if is_dark_mode else "#f8f9fa"
    text_color = "#f1f1f1" if is_dark_mode else "#000000"
    border_color = "#0173C4"  # blu acceso, rimane lo stesso

    for insight in insight_list[:30]:
        html = markdown_to_html(insight)

        # Emoji logica (positivi/negativi/neutri)
        if any(x in insight.lower() for x in ["strong", "above", "leads", "efficient", "outpacing", "robust", "solid", "positive"]):
            icon = "📈"
        elif any(x in insight.lower() for x in ["below", "weak", "underperform", "negative", "lag", "risk", "fall", "short"]):
            icon = "📉"
        else:
            icon = "➡️"

        st.markdown(
            f"""
            <div style="
                background-color: {bg_color};
                color: {text_color};
                padding: 10px 14px;
                border-radius: 8px;
                margin-bottom: 8px;
                border-left: 4px solid {border_color};
                font-size: 15px;
                line-height: 1.5;">
                <span style="margin-right: 6px;">{icon}</span>{html}
            </div>
            """,
            unsafe_allow_html=True
        )

else:
    st.info("No insights available for the current filters.")

#-----footer-------
st.markdown("""
<hr style="margin-top:50px;"/>
<div style='text-align: center; font-size: 0.9rem; color: grey;'>
    &copy; 2025 BalanceShip. All rights reserved.
</div>
""", unsafe_allow_html=True)
