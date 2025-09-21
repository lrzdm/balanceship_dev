import streamlit as st
import pandas as pd
import os
import base64
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import matplotlib.pyplot as plt
from data_utils import read_exchanges, read_companies, get_or_fetch_data, compute_kpis
from reportlab.lib import colors

# ---------------- CONFIGURAZIONE ----------------
st.set_page_config(page_title="📑 Report Generator", layout="wide")
st.title("📑 Report Generator")

# ---------------- FUNZIONI ----------------
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
    "Communication Services","Consumer Cyclical","Consumer Defensive",
    "Energy","Finance Services","Healthcare","Industrials","Real Estate",
    "Technology","Utilities"
]

col1, col2, col3 = st.columns([1.2, 1.5, 1.8])
with col1:
    selected_year = st.selectbox("Year", years_available, index=2)
with col2:
    selected_exchange = st.selectbox("Exchange", exchange_names, index=0)
with col3:
    selected_sector = st.selectbox("Sector", options=["All"] + sectors_available)

# ---------------- PLACEHOLDER ----------------
status_placeholder = st.empty()

# ---------------- SESSION STATE ----------------
if "payment_done" not in st.session_state:
    st.session_state.payment_done = False
if "report_generated" not in st.session_state:
    st.session_state.report_generated = False

# ---------------- GENERA REPORT ----------------
if st.button("📄 Generate Report"):
    status_placeholder.info("⏳ Generating report...")

    # Carica aziende dell'exchange selezionato
    companies = read_companies(exchanges[selected_exchange])
    data = []
    for company in companies:
        comp_data = get_or_fetch_data(
            company["ticker"], [selected_year], company.get("description", ""), selected_exchange
        )
        if selected_sector != "All":
            comp_data = [d for d in comp_data if d.get("sector") == selected_sector]
        data.extend(comp_data)

    if not data:
        st.warning("No data found for the selected filters.")
        st.stop()

    # Calcola KPI
    df_kpi = compute_kpis(data)
    df_kpi = df_kpi[df_kpi["year"] == int(selected_year)]

    kpi_cols = ["EBITDA Margin", "Debt/Equity", "FCF Margin", "EPS"]
    available_cols = [c for c in kpi_cols if c in df_kpi.columns]
    if not available_cols:
        st.error("❌ Nessuna colonna KPI disponibile.")
        st.stop()
    median_values = df_kpi[available_cols].median()

    # Commenti automatici
    comments = []
    if "EBITDA Margin" in median_values:
        ebitda = median_values["EBITDA Margin"]
        comments.append("EBITDA strong" if ebitda > 20 else "EBITDA moderate" if ebitda > 10 else "EBITDA weak")
    if "Debt/Equity" in median_values:
        de = median_values["Debt/Equity"]
        comments.append("High leverage" if de > 2 else "Moderate leverage" if de > 1 else "Low leverage")
    if "FCF Margin" in median_values:
        fcf = median_values["FCF Margin"]
        comments.append("Strong cash flow" if fcf > 15 else "Moderate cash flow" if fcf > 5 else "Weak cash flow")
    if "EPS" in median_values:
        eps = median_values["EPS"]
        comments.append("High EPS" if eps > 5 else "Moderate EPS" if eps > 1 else "Low EPS")

    # ---------------- CREAZIONE PDF ----------------
    pdf_file = "report.pdf"
    doc = SimpleDocTemplate( pdf_file, pagesize=A4, title="BalanceShip Report", author="BalanceShip", subject="Financial report", creator="BalanceShip Platform" )
    styles = getSampleStyleSheet()
    story = []

    # Logo
    logo1_path = os.path.join("images", "logo1.png")
    logo2_path = os.path.join("images", "logo2.png")
    logos = []
    if os.path.exists(logo1_path):
        logos.append(Image(logo1_path, width=80, height=70))
    if os.path.exists(logo2_path):
        logos.append(Image(logo2_path, width=160, height=40))
    if logos:
        table = Table([logos], hAlign='CENTER')
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                                   ('ALIGN',(0,0),(-1,-1),'CENTER'),
                                   ('LEFTPADDING',(0,0),(-1,-1),0),
                                   ('RIGHTPADDING',(0,0),(-1,-1),0),
                                   ('TOPPADDING',(0,0),(-1,-1),0),
                                   ('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        story.append(table)
        story.append(Spacer(1,12))

    story.append(Paragraph("<b>BalanceShip Report</b>", styles["Title"]))
    story.append(Spacer(1,12))
    story.append(Paragraph(f"<b>Exchange:</b> {selected_exchange}", styles["Normal"]))
    story.append(Paragraph(f"<b>Year:</b> {selected_year}", styles["Normal"]))
    story.append(Paragraph(f"<b>Sector:</b> {selected_sector}", styles["Normal"]))
    story.append(Spacer(1,12))

    story.append(Paragraph("<b>Median KPIs:</b>", styles["Heading2"]))
    for kpi, val in median_values.items():
        story.append(Paragraph(f"{kpi}: {val:.2f}", styles["Normal"]))

    story.append(PageBreak())
    story.append(Paragraph("<b>KPI Chart</b>", styles["Heading2"]))
    story.append(Spacer(1,12))

    chart_file = "kpi_chart.png"
    plt.figure(figsize=(6,4))
    median_values.plot(kind="bar", color="#0173C4")
    plt.title("Median KPIs")
    plt.ylabel("Value")
    plt.xticks(rotation=45, ha="right")
    for i, v in enumerate(median_values.values):
        plt.text(i, v + 0.5, f"{v:.2f}", ha='center')
    plt.tight_layout()
    plt.savefig(chart_file)
    plt.close()
    story.append(Image(chart_file, width=400, height=250))

    story.append(PageBreak())
    story.append(Paragraph("<b>Automated Insights</b>", styles["Heading1"]))
    story.append(Spacer(1,12))
    for c in comments:
        story.append(Paragraph(f"- {c}", styles["Normal"]))

    doc.build(story)

    st.session_state.report_generated = True
    status_placeholder.success("✅ Report completato e pronto per il download")

# ---------------- PAYPAL + DOWNLOAD SEMPLIFICATO ----------------
paypal_url = "https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=YOUR_BUTTON_ID"

if st.session_state.report_generated:
    # Messaggio informativo sul pagamento (disabilitato per ora)
    st.info(f"💳 Payment link (disabled for now): {paypal_url}", icon="🔒")

    # Pulsante download sempre abilitato
    with open(pdf_file, "rb") as f:
        st.download_button(
            label="📥 Download Report",
            data=f,
            file_name="BalanceShip_Report.pdf",
            mime="application/pdf"
        )



