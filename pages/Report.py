import streamlit as st
import pandas as pd
import os
import base64
from data_utils import read_exchanges, read_companies, get_or_fetch_data, compute_kpis
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import plotly.graph_objects as go
import plotly.io as pio

# ---------------- CONFIGURAZIONE ----------------
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
    "Communication Services",
    "Consumer Cyclical",
    "Consumer Defensive",
    "Energy",
    "Finance Services",
    "Healthcare",
    "Industrials",
    "Real Estate",
    "Technology",
    "Utilities",
]

col1, col2, col3 = st.columns([1.2, 1.5, 1.8])

with col1:
    selected_year = st.selectbox("Year", years_available, index=2)
with col2:
    selected_exchange = st.selectbox("Exchange", exchange_names, index=0)
with col3:
    selected_sector = st.selectbox("Sector", options=["All"] + sectors_available)

# ---------------- GENERA REPORT ----------------
if st.button("📄 Generate Report"):
    st.info("Generating report...")

    # Carica aziende
    companies = read_companies(exchanges[selected_exchange])
    data = []
    for company in companies:
        if selected_sector != "All" and company.get("sector", "") != selected_sector:
            continue
        comp_data = get_or_fetch_data(
            company["ticker"], [selected_year], company.get("description", ""), selected_exchange
        )
        data.extend(comp_data)

    if not data:
        st.warning("No data found for the selected filters.")
    else:
        df = pd.DataFrame(data)
        df_kpi = compute_kpis(data)
        df_kpi = df_kpi[df_kpi["year"] == int(selected_year)]

        # Assicura che le colonne siano rinominate in modo coerente
        df_kpi.rename(columns={
            "Debt/Equity": "Debt to Equity",
            "basic_eps": "EPS"
        }, inplace=True)

        # Ora calcola le mediane
        median_values = df_kpi[["EBITDA Margin", "Debt to Equity", "FCF Margin", "EPS"]].median()

        # Calcolo mediana dei KPI
        #median_values = df_kpi[["EBITDA Margin", "Debt/Equity", "FCF Margin", "EPS"]].median()

        # ---------------- COMMENTI DINAMICI ----------------
        comments = []

        # EBITDA Margin
        ebitda = median_values["EBITDA Margin"]
        if ebitda > 20:
            comments.append("The sector shows strong profitability, with a robust EBITDA margin above 20%.")
        elif ebitda > 10:
            comments.append("The sector has a healthy profitability, with EBITDA margin in double digits.")
        else:
            comments.append("The sector struggles with profitability, as EBITDA margin is relatively low.")

        # Debt/Equity
        de_ratio = median_values["Debt/Equity"]
        if de_ratio > 2:
            comments.append("High leverage is evident, indicating strong reliance on debt financing.")
        elif de_ratio > 1:
            comments.append("Moderate leverage: companies balance equity with a fair amount of debt.")
        else:
            comments.append("Low leverage: the sector is generally equity-financed and less risky.")

        # FCF Margin
        fcf = median_values["FCF Margin"]
        if fcf > 15:
            comments.append("Strong cash generation capacity with high Free Cash Flow margins.")
        elif fcf > 5:
            comments.append("The sector shows positive but moderate Free Cash Flow margins.")
        else:
            comments.append("Weak Free Cash Flow margins may raise concerns about cash sustainability.")

        # EPS
        eps = median_values["EPS"]
        if eps > 5:
            comments.append("Solid earnings per share indicate strong profitability at company level.")
        elif eps > 1:
            comments.append("Moderate EPS performance suggests steady but not outstanding earnings.")
        else:
            comments.append("Low EPS reflects weak earnings generation within the sector.")

        # ---------------- CREAZIONE PDF ----------------
        pdf_filename = "report.pdf"
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        story.append(Paragraph("<b>BalanceShip Report</b>", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"<b>Exchange:</b> {selected_exchange}", styles["Normal"]))
        story.append(Paragraph(f"<b>Year:</b> {selected_year}", styles["Normal"]))
        story.append(Paragraph(f"<b>Sector:</b> {selected_sector}", styles["Normal"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("<b>Median KPIs:</b>", styles["Heading2"]))
        for kpi, val in median_values.items():
            story.append(Paragraph(f"{kpi}: {val:.2f}", styles["Normal"]))

        story.append(PageBreak())
        story.append(Paragraph("<b>KPI Charts</b>", styles["Heading1"]))
        story.append(Spacer(1, 12))

        # Funzione per generare grafico mediana
        def save_kpi_chart(median_values, filename):
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=median_values.index,
                        y=median_values.values,
                        text=median_values.round(2),
                        textposition="auto",
                    )
                ]
            )
            fig.update_layout(title="Median KPIs", height=400)
            pio.write_image(fig, filename)
            return filename

        chart_path = save_kpi_chart(median_values, "median_kpis.png")
        story.append(Image(chart_path, width=400, height=250))

        story.append(PageBreak())
        story.append(Paragraph("<b>Automated Insights</b>", styles["Heading1"]))
        story.append(Spacer(1, 12))
        for c in comments:
            story.append(Paragraph(f"- {c}", styles["Normal"]))

        # Build PDF
        doc.build(story)

        # Download link
        with open(pdf_filename, "rb") as f:
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
""",
    unsafe_allow_html=True,
)

