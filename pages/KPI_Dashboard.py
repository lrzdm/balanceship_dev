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
# Lettura borse e aziende
exchanges = read_exchanges("exchanges.txt")
exchange_names = list(exchanges.keys())
exchange_names = ["All"] + exchange_names   # aggiungo opzione All

years_available = ['2021', '2022', '2023', '2024']
sectors_available = ['Communication Services', 'Consumer Cyclical', 'Consumer Defensive', 'Energy', 'Finance Services', 'Healthcare', 'Industrials', 'Real Estate', 'Technology', 'Utilities']

# --- Layout filtri in riga ---
col1, col2, col3, col4 = st.columns([1.2, 1.5, 2.2, 2])
with col1:
    selected_year = st.selectbox("Year", years_available, index=2)
with col2:
    selected_exchange = st.selectbox("Exchange", exchange_names, index=0)

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
    selected_company_names = st.multiselect("Companies (up to 10)", options=company_names, max_selections=10)
    selected_symbols = [name_to_symbol[name] for name in selected_company_names]
with col4:
    if selected_exchange == "All":
        selected_sector = st.selectbox("Sector", options=["All"], disabled=True, 
                                     help="Sector filter is disabled when 'All' exchanges are selected")
    else:
        selected_sector = st.selectbox("Sector", options=["All"] + sectors_available)

# --- Cache semplificata per singola borsa ---
@st.cache_data(ttl=3600)  # Cache per 1 ora
def load_sector_data_cached(sector, exchange_name, year, excluded_symbols, max_companies=100):
    """Carica dati settore per una singola borsa"""
    sector_data = []
    companies_processed = 0
    
    try:
        exch_file = exchanges[exchange_name]
        companies_in_exchange = read_companies(exch_file)
        
        # Filtra aziende già selezionate
        companies_to_process = [c for c in companies_in_exchange 
                              if c["ticker"] not in excluded_symbols]
        
        for company in companies_to_process:
            if companies_processed >= max_companies:
                break
                
            desc = company.get("description", "")
            try:
                data = get_or_fetch_data(company["ticker"], [year], desc, exchange_name)
                sector_matches = [d for d in data if d.get("sector") == sector]
                if sector_matches:
                    sector_data.extend(sector_matches)
                    companies_processed += len(sector_matches)
            except:
                continue
    except:
        pass
    
    return sector_data

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

# --- Se settore selezionato e NON All exchange, carico dati settore ---
sector_data = []
if selected_sector != "All" and selected_exchange != "All":
    with st.spinner(f"Loading {selected_sector} sector data from {selected_exchange}..."):
        sector_data = load_sector_data_cached(
            selected_sector, 
            selected_exchange, 
            selected_year,
            selected_symbols
        )
    
    if sector_data:
        st.success(f"✅ Loaded {len(sector_data)} companies from {selected_sector} sector ({selected_exchange}) for comparison")
    else:
        st.warning(f"⚠️ No companies found in {selected_sector} sector for {selected_exchange}")

# --- Se non c'è nulla, stop ---
if not financial_data:
    st.warning("No data available for the selected companies.")
    st.stop()

# --- Info per l'utente (solo se borsa specifica e settore selezionato) ---
if selected_exchange != "All" and selected_sector != "All":
    st.info(f"🔍 Sector median calculated from {selected_sector} companies in {selected_exchange}")

# --- Unisco dati selezionati e settore (per calcolo media) ---
combined_data = financial_data + sector_data

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
def kpi_chart(df_visible, df_kpi_all, metric, title, is_percent=True,
              selected_year=None, selected_sector=None):

    fig = go.Figure()
    
    # --- Preparazioni ---
    company_names_raw = df_visible["company_name"].tolist()
    company_names_wrapped = [textwrap.fill(label, width=12) for label in company_names_raw]
    company_colors = {name: color_palette[i % len(color_palette)] for i, name in enumerate(company_names_raw)}

    # valori y per il grafico (converti in % se richiesto)
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
    global_median_raw = _safe_median(df_visible, metric)
    global_median = np.nan if np.isnan(global_median_raw) else (global_median_raw * (100 if is_percent else 1))

    sector_median = np.nan
    if selected_sector and selected_sector != "All" and "sector" in df_kpi_all.columns:
        df_temp = df_kpi_all.copy()
        if "year" in df_temp.columns:
            df_temp["year"] = df_temp["year"].astype(str)
            sel_year = str(selected_year)
            df_sector = df_temp[(df_temp["sector"] == selected_sector) & (df_temp["year"] == sel_year)]
        else:
            df_sector = df_temp[df_temp["sector"] == selected_sector]

        sector_median_raw = _safe_median(df_sector, metric)
        if not np.isnan(sector_median_raw):
            sector_median = sector_median_raw * (100 if is_percent else 1)

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
        companies_y_pos = y_max + (y_range * 0.05)
        
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
        annotation_positions.append(("companies", companies_pos, companies_y_pos))

    if not np.isnan(sector_median):
        if any(pos[1] == "top left" for pos in annotation_positions):
            sector_pos = "top right"
        else:
            sector_pos = "bottom right"
            
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

    # --- Layout ottimizzato ---
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, family="Arial")),
        yaxis_title=f"{metric}{' (%)' if is_percent else ''}",
        height=350,
        margin=dict(t=60, b=70, l=50, r=50),
        showlegend=False,
        plot_bgcolor='rgba(248,249,250,0.8)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Arial", size=10),
        yaxis=dict(
            range=[
                y_min - (y_range * 0.1),
                y_max + (y_range * 0.25)
            ]
        )
    )

    return fig


col1, col2 = st.columns(2)

with col1:
    st.plotly_chart(
        kpi_chart(df_visible, df_kpi_all, "EBITDA Margin", "EBITDA Margin", is_percent=True, selected_year=selected_year, selected_sector=selected_sector),
        use_container_width=True
    )
    st.plotly_chart(
        kpi_chart(df_visible, df_kpi_all, "FCF Margin", "FCF Margin", is_percent=True, selected_year=selected_year, selected_sector=selected_sector),
        use_container_width=True
    )

with col2:
    st.plotly_chart(
        kpi_chart(df_visible, df_kpi_all, "Debt to Equity", "Debt to Equity", is_percent=False, selected_year=selected_year, selected_sector=selected_sector),
        use_container_width=True
    )
    st.plotly_chart(
        kpi_chart(df_visible, df_kpi_all, "EPS", "Earnings per Share (EPS)", is_percent=False, selected_year=selected_year, selected_sector=selected_sector),
        use_container_width=True
    )

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



















