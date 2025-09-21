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

st.set_page_config(page_title="KPI Dashboard", layout="wide")
st.title("📊 KPI Dashboard")

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# SIDEBAR
logo_path = os.path.join("images", "logo4.png")
logo_base64 = get_base64_of_bin_file(logo_path) if os.path.exists(logo_path) else ""

instagram_icon_path = os.path.join("images", "IG.png")
linkedin_icon_path = os.path.join("images", "LIN.png")

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

color_palette = ["#6495ED", "#3CB371", "#FF6347", "#DAA520", "#4169E1", "#BA55D3", "#FF8C00", "#40E0D0", "#708090", "#B22222"]

# Lettura borse e aziende
exchanges = read_exchanges("exchanges.txt")
exchange_names = ["All"] + list(exchanges.keys())

years_available = ['2021', '2022', '2023', '2024']
sectors_available = ['Communication Services', 'Consumer Cyclical', 'Consumer Defensive', 'Energy', 'Financial Services', 'Healthcare', 'Industrials', 'Real Estate', 'Technology', 'Utilities']

# Layout filtri
col1, col2, col3, col4 = st.columns([1.2, 1.5, 2.2, 2])
with col1:
    selected_year = st.selectbox("Year", years_available, index=2, key="year_select")
with col2:
    selected_exchange = st.selectbox("Exchange", exchange_names, index=0, key="exchange_select")

# Carico lista aziende
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
        selected_sector = st.selectbox("Sector", options=["All"], disabled=True, help="Sector filter is disabled when 'All' exchanges are selected", key="sector_select_disabled")
    else:
        selected_sector = st.selectbox("Sector", options=["All"] + sectors_available, key="sector_select_enabled")

# Cache per dati settore
@st.cache_data(ttl=3600)
def load_all_sector_data(exchange_name, year, max_companies=100):
    """Carica tutti i dati di un exchange per calcolo settori"""
    try:
        exch_file = exchanges[exchange_name]
        all_companies = read_companies(exch_file)
        
        all_data = []
        companies_processed = 0
        
        for company in all_companies:
            if companies_processed >= max_companies:
                break
                
            desc = company.get("description", "")
            try:
                data = get_or_fetch_data(company["ticker"], [year], desc, exchange_name)
                if data:
                    all_data.extend(data)
                    companies_processed += 1
            except:
                continue
        
        if not all_data:
            return pd.DataFrame()
            
        # Calcola KPI
        df_all = compute_kpis(all_data)
        df_all = df_all[df_all["year"] == int(year)]
        
        # Merge con raw data per EPS e settore
        df_raw = pd.DataFrame(all_data)
        if "ticker" in df_raw.columns and "symbol" not in df_raw.columns:
            df_raw.rename(columns={"ticker": "symbol"}, inplace=True)
        
        df_all = pd.merge(df_all, df_raw[["symbol", "basic_eps", "sector"]], on="symbol", how="left")
        
        # Rinomina colonne
        df_all.rename(columns={"EBITDA Margin": "EBITDA Margin", "Debt/Equity": "Debt to Equity", "FCF Margin": "FCF Margin", "basic_eps": "EPS"}, inplace=True)
        
        return df_all
        
    except Exception as e:
        st.error(f"Error loading sector data: {e}")
        return pd.DataFrame()

# Caricamento dati aziende selezionate
financial_data = []
used_exchanges = set()

for symbol in selected_symbols:
    desc = symbol_to_name.get(symbol, "")
    if selected_exchange == "All":
        for exch_name, exch_file in exchanges.items():
            try:
                data = get_or_fetch_data(symbol, [selected_year], desc, exch_name)
                if data:
                    financial_data.extend(data)
                    used_exchanges.add(exch_name)
                    break
            except:
                continue
    else:
        data = get_or_fetch_data(symbol, [selected_year], desc, selected_exchange)
        if data:
            financial_data.extend(data)
            used_exchanges.add(selected_exchange)

# Carica dati completi per settore se necessario
df_all_sector = pd.DataFrame()
if selected_sector != "All" and selected_exchange != "All":
    with st.spinner(f"Loading {selected_sector} sector data from {selected_exchange}..."):
        df_all_sector = load_all_sector_data(selected_exchange, selected_year)

if not financial_data:
    st.warning("No data available for the selected companies.")
    st.stop()

# Calcolo KPI per aziende selezionate
df_kpi_all = compute_kpis(financial_data)
df_kpi_all = df_kpi_all[df_kpi_all["year"] == int(selected_year)]

# EPS e settore dal raw data
df_raw = pd.DataFrame(financial_data)
if "ticker" in df_raw.columns and "symbol" not in df_raw.columns:
    df_raw.rename(columns={"ticker": "symbol"}, inplace=True)

df_kpi_all = pd.merge(df_kpi_all, df_raw[["symbol", "basic_eps", "sector"]], on="symbol", how="left")

# Rinomina colonne
df_kpi_all.rename(columns={"EBITDA Margin": "EBITDA Margin", "Debt/Equity": "Debt to Equity", "FCF Margin": "FCF Margin", "basic_eps": "EPS"}, inplace=True)

# Aggiungi descrizione azienda
df_kpi_all["company_name"] = df_kpi_all["symbol"].map(symbol_to_name)

# Split dati visibili
df_visible = df_kpi_all[df_kpi_all["symbol"].isin(selected_symbols)]

# Info settore
if selected_exchange != "All" and selected_sector != "All" and not df_all_sector.empty:
    sector_count = len(df_all_sector[df_all_sector["sector"] == selected_sector])
    if sector_count > 0:
        st.success(f"✅ Sector benchmark from {sector_count} {selected_sector} companies ({selected_exchange})")
    else:
        st.warning(f"⚠️ No {selected_sector} companies found in {selected_exchange}")
        
        # Debug: mostra settori disponibili
        if not df_all_sector.empty:
            available_sectors = df_all_sector["sector"].value_counts()
            st.write("**Available sectors in data:**")
            for sector, count in available_sectors.head(10).items():
                st.write(f"- {sector}: {count} companies")

def legend_chart():
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="red", dash="dash"), name="Companies Median"))
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line=dict(color="blue", dash="dot"), name="Sector Median"))
    fig.update_layout(height=50, margin=dict(t=0, b=0, l=0, r=0), legend=dict(orientation="h", yanchor="bottom", y=1, xanchor="center", x=0.5))
    return fig

st.plotly_chart(legend_chart(), use_container_width=True)

def _safe_median(df, col):
    if df is None or df.empty or col not in df.columns:
        return np.nan
    series = pd.to_numeric(df[col], errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return np.nan
    return float(series.median())

# Pre-calcola tutte le mediane di settore una volta sola
sector_medians = {}
if selected_sector != "All" and selected_exchange != "All" and not df_all_sector.empty:
    df_sector = df_all_sector[df_all_sector["sector"] == selected_sector]
    if not df_sector.empty:
        metrics = ["EBITDA Margin", "FCF Margin", "Debt to Equity", "EPS"]
        for metric in metrics:
            sector_medians[metric] = _safe_median(df_sector, metric)

def kpi_chart(df_visible, metric, title, is_percent=True):
    fig = go.Figure()
    
    company_names_raw = df_visible["company_name"].tolist()
    company_names_wrapped = [textwrap.fill(label, width=12) for label in company_names_raw]
    company_colors = {name: color_palette[i % len(color_palette)] for i, name in enumerate(company_names_raw)}

    y_series = pd.to_numeric(df_visible[metric], errors="coerce")
    y_values = y_series.values.astype(float)
    if is_percent:
        y_values = y_values * 100

    valid_values = y_values[~np.isnan(y_values)]
    if len(valid_values) > 0:
        y_min, y_max = valid_values.min(), valid_values.max()
        y_range = y_max - y_min
        if y_range == 0:
            y_range = abs(y_max) * 0.1 if y_max != 0 else 1
    else:
        y_min, y_max, y_range = 0, 1, 1

    # Bar principale
    fig.add_trace(go.Bar(x=company_names_wrapped, y=y_values, marker_color=[company_colors[name] for name in company_names_raw], showlegend=False, hovertemplate='<b>%{x}</b><br>%{y:.1f}' + ('%' if is_percent else '') + '<extra></extra>'))

    # Calcolo mediane
    global_median = _safe_median(df_visible, metric)
    if is_percent and not np.isnan(global_median):
        global_median *= 100

    # Usa la mediana pre-calcolata
    sector_median = sector_medians.get(metric, np.nan)
    if is_percent and not np.isnan(sector_median):
        sector_median *= 100

    # Valori sopra barre
    for i, (name, val) in enumerate(zip(company_names_wrapped, y_values)):
        if not np.isnan(val):
            fig.add_annotation(x=name, y=val, text=f"{val:.1f}{'%' if is_percent else ''}", showarrow=False, yshift=8, font=dict(size=9, color="black"), bgcolor="rgba(255,255,255,0.8)", bordercolor="rgba(0,0,0,0.1)", borderwidth=1)

    # Delta frecce
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
            fig.add_annotation(x=company_names_wrapped[i], y=y_position, text=f"{arrow}{abs(delta):.1f}{'%' if is_percent else ''}", showarrow=False, font=dict(size=8, color=color, family="Arial Black"), bgcolor="rgba(255,255,255,0.9)", bordercolor=color, borderwidth=1)

    # Linee mediane
    annotation_positions = []
    
    if not np.isnan(global_median):
        fig.add_hline(y=global_median, line=dict(color="#dc3545", dash="dash", width=2), annotation_text=f"Companies: {global_median:.1f}{'%' if is_percent else ''}", annotation_position="top left", annotation_font=dict(color="#dc3545", size=10), annotation_bgcolor="rgba(255,255,255,0.9)", annotation_bordercolor="#dc3545", annotation_borderwidth=1)
        annotation_positions.append(("companies", "top left"))

    if not np.isnan(sector_median):
        sector_pos = "top right" if any(pos[1] == "top left" for pos in annotation_positions) else "bottom right"
        fig.add_hline(y=sector_median, line=dict(color="#007bff", dash="dot", width=2), annotation_text=f"Sector: {sector_median:.1f}{'%' if is_percent else ''}", annotation_position=sector_pos, annotation_font=dict(color="#007bff", size=10), annotation_bgcolor="rgba(255,255,255,0.9)", annotation_bordercolor="#007bff", annotation_borderwidth=1)

    # Layout con range Y adattivo che include tutte le mediane
    all_important_values = []
    all_important_values.extend(valid_values.tolist())
    if not np.isnan(global_median):
        all_important_values.append(global_median)
    if not np.isnan(sector_median):
        all_important_values.append(sector_median)
    
    if all_important_values:
        actual_min = min(all_important_values)
        actual_max = max(all_important_values) 
        value_range = actual_max - actual_min
        if value_range == 0:
            value_range = abs(actual_max) * 0.1 if actual_max != 0 else 1
        
        # Range con padding del 15% per dare spazio alle annotazioni
        y_range_min = actual_min - (value_range * 0.15)
        y_range_max = actual_max + (value_range * 0.15)
    else:
        y_range_min = y_min - (y_range * 0.1)
        y_range_max = y_max + (y_range * 0.25)

    # Layout
    fig.update_layout(title=dict(text=title, font=dict(size=14, family="Arial")), yaxis_title=f"{metric}{' (%)' if is_percent else ''}", height=350, margin=dict(t=60, b=70, l=50, r=50), showlegend=False, plot_bgcolor='rgba(248,249,250,0.8)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family="Arial", size=10), yaxis=dict(range=[y_range_min, y_range_max]))

    return fig

# Grafici
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(kpi_chart(df_visible, "EBITDA Margin", "EBITDA Margin", is_percent=True), use_container_width=True)
    st.plotly_chart(kpi_chart(df_visible, "FCF Margin", "FCF Margin", is_percent=True), use_container_width=True)
with col2:
    st.plotly_chart(kpi_chart(df_visible, "Debt to Equity", "Debt to Equity", is_percent=False), use_container_width=True)
    st.plotly_chart(kpi_chart(df_visible, "EPS", "Earnings per Share (EPS)", is_percent=False), use_container_width=True)

# INSIGHTS
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
            options = [f"**{company}** demonstrates operational efficiency well above the sector norm, with an EBITDA margin of {ebitda_margin_pct:.1f}%.", f"The EBITDA margin of **{company}** ({ebitda_margin_pct:.1f}%) exceeds its industry average."]
            insight_list.append(random.choice(options))
        elif ebitda_margin_pct < avg_ebitda * 0.8:
            options = [f"**{company}** struggles to convert revenue into operating profit, with an EBITDA margin of only {ebitda_margin_pct:.1f}%.", f"The EBITDA performance of **{company}** ({ebitda_margin_pct:.1f}%) lags well behind sector peers."]
            insight_list.append(random.choice(options))

    # FCF Margin
    if not pd.isna(fcf_margin):
        fcf_margin_pct = fcf_margin * 100
        if fcf_margin_pct > avg_fcf * 1.2:
            options = [f"**{company}** stands out for its excellent cash flow generation, posting a FCF margin of {fcf_margin_pct:.1f}%.", f"With a FCF margin of {fcf_margin_pct:.1f}%, **{company}** ranks among the top in cash conversion."]
            insight_list.append(random.choice(options))
        elif fcf_margin_pct < avg_fcf * 0.8:
            options = [f"**{company}** underperforms in turning revenue into free cash flow, with a margin of {fcf_margin_pct:.1f}%.", f"**{company}** shows weakness in FCF efficiency compared to the sector (only {fcf_margin_pct:.1f}%)."]
            insight_list.append(random.choice(options))

    # Debt to Equity
    if not pd.isna(debt_equity):
        if debt_equity > avg_debt_equity * 1.3:
            options = [f"**{company}** is highly leveraged, with a debt-to-equity ratio of {debt_equity:.2f}, above the sector average.", f"Financial leverage is a concern for **{company}**, with D/E at {debt_equity:.2f}."]
            insight_list.append(random.choice(options))
        elif debt_equity < avg_debt_equity * 0.7:
            options = [f"**{company}** maintains a solid balance sheet with low reliance on debt (D/E: {debt_equity:.2f}).", f"**{company}** shows strong capital structure, with low debt levels (D/E: {debt_equity:.2f})."]
            insight_list.append(random.choice(options))

    # EPS
    if not pd.isna(eps):
        if eps > avg_eps * 1.2:
            options = [f"**{company}** delivers strong earnings per share of {eps:.2f}, outpacing its industry.", f"**{company}** posts robust EPS ({eps:.2f}) compared to the sector average."]
            insight_list.append(random.choice(options))
        elif eps < avg_eps * 0.8:
            options = [f"**{company}** trails the sector in earnings, with an EPS of just {eps:.2f}.", f"Earnings per share of **{company}** ({eps:.2f}) fall short of peer performance."]
            insight_list.append(random.choice(options))

# Shuffle insights
unique_insights = list(dict.fromkeys(insight_list))
random.shuffle(unique_insights)
insight_list = unique_insights[:30]

# Output insights
if insight_list:
    st.markdown("---")
    st.subheader("💡 Key Insights")

    is_dark_mode = st.get_option("theme.base") == "dark"

    def markdown_to_html(text):
        import re
        return re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", text)

    bg_color = "#1e1e1e" if is_dark_mode else "#f8f9fa"
    text_color = "#f1f1f1" if is_dark_mode else "#000000"
    border_color = "#0173C4"

    for insight in insight_list[:30]:
        html = markdown_to_html(insight)

        if any(x in insight.lower() for x in ["strong", "above", "leads", "efficient", "outpacing", "robust", "solid", "positive"]):
            icon = "📈"
        elif any(x in insight.lower() for x in ["below", "weak", "underperform", "negative", "lag", "risk", "fall", "short"]):
            icon = "📉"
        else:
            icon = "➡️"

        st.markdown(f"""
            <div style="background-color: {bg_color}; color: {text_color}; padding: 10px 14px; border-radius: 8px; margin-bottom: 8px; border-left: 4px solid {border_color}; font-size: 15px; line-height: 1.5;">
                <span style="margin-right: 6px;">{icon}</span>{html}
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("No insights available for the current filters.")

# Footer
st.markdown("""
<hr style="margin-top:50px;"/>
<div style='text-align: center; font-size: 0.9rem; color: grey;'>
    &copy; 2025 BalanceShip. All rights reserved.
</div>
""", unsafe_allow_html=True)

