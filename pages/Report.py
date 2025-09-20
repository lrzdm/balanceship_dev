import streamlit as st
import pandas as pd
import os
import base64
from data_utils import read_exchanges, read_companies, get_or_fetch_data, compute_kpis
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import matplotlib.pyplot as plt
import io

# ---------------- CONFIG ----------------
st.set_page_config(page_title="📑 Report Generator", layout="wide")
st.title("📑 Report Generator")

def get_base64_of_bin_file(bin_file):
    with open(bin_file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# ---------------- SIDEBAR ----------------
logo_path = os.path.join("images", "logo4.png")
if os.path.exists(logo_path):
    logo_base64 = get_base64_of_bin_file(logo_path)
    st.sidebar.markdown(
        f"""
        <div style='text-align: center;'>
            <img src="data:image/png;base64,{logo_base64}" style="height: 70px;">
            <p style='font-size: 14px;'>Navigate financial sea with clarity ⚓</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------------- FILTRI ----------------
exchanges = read_exchanges("exchanges.txt")
exchange_names = list(exchanges.keys())
years_available = ["2021", "2022", "2023", "2024"]
sectors_available = [
    "Communication Services","Consumer Cyclical","Consumer Defensive","Energy",
    "Finance Services","Healthcare","Industrials","Real Estate","Technology","Utilities"
]

col1, col2, col3, col4 = st.columns([1.2, 1.5, 1.8, 2])

with col1:
    selected_year = st.selectbox("Year", years_available, index=2)
with col2:
    selected_exchange = st.selectbox("Exchange", exchange_names, index=0)
with col3:
    selected_sector = st.selectbox("Sector", options=["All"] + sectors_available)

# Carica tutte le aziende dell'exchange selezionato
companies = read_companies(exchanges[selected_exchange])

# Ottieni tutte le industry disponibili per le aziende e sector selezionato
if selected_sector != "All":
    industries_available = sorted(list(set([c.get("industry", "Unknown") for c in companies if c.get("sector") == selected_sector and c.get("industry")])))
else:
    industries_available = sorted(list(set([c.get("industry", "Unknown") for c in companies if c.get("industry")])))

with col4:
    selected_industry = st.selectbox("Industry", options=["All"] + industries_available)

# ---------------- GENERA REPORT ----------------
if st.button("📄 Generate Report"):
    st.info("Generating report...")

    # Filtra aziende per sector e industry
    filtered_companies = companies
    if selected_sector != "All":
        filtered_companies = [c for c in filtered_companies if c.get("sector") == selected_sector]
    if selected_industry != "All":
        filtered_companies = [c for c in filtered_companies if c.get("industry") == selected_industry]

    # Recupera dati finanziari
    financial_data = []
    for company in filtered_companies:
        data = get_or_fetch_data(company["ticker"], [selected_year], company.get("description",""), selected_exchange)
        financial_data.extend(data)

    if not financial_data:
        st.warning("No data found for the selected filters.")
        st.stop()

    df = pd.DataFrame(financial_data)
    df_kpi = compute_kpis(financial_data)
    df_kpi = df_kpi[df_kpi["year"] == int(selected_year)]

    # Rinomina colonne
    df_kpi.rename(columns={"Debt/Equity": "Debt to Equity", "basic_eps": "EPS"}, inplace=True)

    kpi_candidates = ["EBITDA Margin","Debt to Equity","FCF Margin","EPS"]
    available_cols = [col for col in kpi_candidates if col in df_kpi.columns]
    if not available_cols:
        st.error("❌ Nessuna colonna KPI disponibile.")
        st.stop()

    median_values = df_kpi[available_cols].median()
    st.write("✅ Colonne KPI disponibili per la mediana:", available_cols)

    # ---------------- COMMENTI ----------------
    comments = []
    if "EBITDA Margin" in median_values:
        ebitda = median_values["EBITDA Margin"]
        if ebitda > 20:
            comments.append("Strong profitability: EBITDA > 20%.")
        elif ebitda > 10:
            comments.append("Healthy profitability: EBITDA in double digits.")
        else:
            comments.append("Low profitability: EBITDA relatively low.")

    if "Debt to Equity" in median_values:
        de_ratio = median_values["Debt to Equity"]
        if de_ratio > 2:
            comments.append("High leverage: sector relies on debt.")
        elif de_ratio > 1:
            comments.append("Moderate leverage: balanced debt vs equity.")
        else:
            comments.append("Low leverage: sector mostly equity-financed.")

    if "FCF Margin" in median_values:
        fcf = median_values["FCF Margin"]
        if fcf > 15:
            comments.append("Strong cash flow: high FCF margin.")
        elif fcf > 5:
            comments.append("Moderate FCF margin.")
        else:
            comments.append("Weak FCF margin: cash concerns.")

    if "EPS" in median_values:
        eps = median_values["EPS"]
        if eps > 5:
            comments.append("Strong EPS performance.")
        elif eps > 1:
            comments.append("Moderate EPS performance.")
        else:
            comments.append("Low EPS performance.")

    # ---------------- CREAZIONE PDF ----------------
    pdf_filename = "report.pdf"
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("<b>BalanceShip Report</b>", styles["Title"]))
    story.append(Spacer(1,12))
    story.append(Paragraph(f"<b>Exchange:</b> {selected_exchange}", styles["Normal"]))
    story.append(Paragraph(f"<b>Year:</b> {selected_year}", styles["Normal"]))
    story.append(Paragraph(f"<b>Sector:</b> {selected_sector}", styles["Normal"]))
    story.append(Paragraph(f"<b>Industry:</b> {selected_industry}", styles["Normal"]))
    story.append(Spacer(1,12))

    story.append(Paragraph("<b>Median KPIs:</b>", styles["Heading2"]))
    for kpi, val in median_values.items():
        story.append(Paragraph(f"{kpi}: {val:.2f}", styles["Normal"]))

    story.append(PageBreak())
    story.append(Paragraph("<b>KPI Chart</b>", styles["Heading1"]))
    story.append(Spacer(1,12))

    # Grafico mediana
    plt.figure(figsize=(6,4))
    median_values.plot(kind="bar", color="#0173C4")
    plt.title("Median KPIs")
    plt.ylabel("Value")
    plt.xticks(rotation=45, ha='right')
    for i, v in enumerate(median_values.values):
        plt.text(i, v + 0.5, f"{v:.2f}", ha='center')
    plt.tight_layout()
    chart_path = "median_kpis.png"
    plt.savefig(chart_path)
    plt.close()
    story.append(Image(chart_path, width=400, height=250))

    story.append(PageBreak())
    story.append(Paragraph("<b>Automated Insights</b>", styles["Heading1"]))
    story.append(Spacer(1,12))
    for c in comments:
        story.append(Paragraph(f"- {c}", styles["Normal"]))

    doc.build(story)

    # Download
    with open(pdf_filename,"rb") as f:
        pdf_bytes = f.read()
    b64_pdf = base64.b64encode(pdf_bytes).decode()
    href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="BalanceShip_Report.pdf">📥 Download Report</a>'
    st.markdown(href, unsafe_allow_html=True)

# ---------------- FOOTER ----------------
st.markdown(
"""
<hr style="margin-top:50px;"/>
<div style='text-align: center; font-size: 0.9rem; color: grey;'>
    &copy; 2025 BalanceShip. All rights reserved.
</div>
""", unsafe_allow_html=True
)
