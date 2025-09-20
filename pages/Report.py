import streamlit as st
import pandas as pd
import os
import base64
from data_utils import read_exchanges, read_companies, get_or_fetch_data, compute_kpis
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import plotly.graph_objects as go

# Necessario per salvare grafici plotly come PNG
import plotly.io as pio

st.set_page_config(page_title="📑 Report Generator", layout="wide")
st.title("📑 Report Generator")

# ---------------- UTILS ----------------
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# ---------------- SIDEBAR ----------------
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

# ---------------- FILTRI ----------------
exchanges = read_exchanges("exchanges.txt")
exchange_names = list(exchanges.keys())

years_available = ['2021', '2022', '2023', '2024']
sectors_available = ['Communication Services', 'Consumer Cyclical', 'Consumer Defensive', 'Energy',
                     'Finance Services', 'Healthcare', 'Industrials', 'Real Estate', 'Technology', 'Utilities']

col1, col2, col3, col4 = st.columns([1.2, 1.5, 1.8, 1.2])

with col1:
    selected_year = st.selectbox("Year", years_available, index=2)

with col2:
    selected_exchange = st.selectbox("Exchange", exchange_names, index=0)

with col3:
    selected_sector = st.selectbox("Sector", options=["All"] + sectors_available)

with col4:
    selected_industry = st.text_input("Industry (optional)", "")

# ---------------- GENERA REPORT ----------------
if st.button("📄 Generate Report"):
    st.info("Generating report...")

    companies = read_companies(exchanges[selected_exchange])
    data = []
    for company in companies:
        desc = company.get("description", "")
        comp_sector = company.get("sector", "")
        comp_industry = company.get("industry", "")

        if selected_sector != "All" and comp_sector != selected_sector:
            continue
        if selected_industry and comp_industry != selected_industry:
            continue

        comp_data = get_or_fetch_data(company["ticker"], [selected_year], desc, selected_exchange)
        data.extend(comp_data)

    if not data:
        st.warning("No data found for the selected filters.")
    else:
        df = pd.DataFrame(data)
        df_kpi = compute_kpis(data)
        df_kpi = df_kpi[df_kpi["year"] == int(selected_year)]

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
        story.append(Paragraph(f"<b>Industry:</b> {selected_industry if selected_industry else 'All'}", styles["Normal"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("<b>Companies Analyzed:</b>", styles["Heading2"]))
        for c in df["description"].unique():
            story.append(Paragraph(f"- {c}", styles["Normal"]))

        story.append(PageBreak())
        story.append(Paragraph("<b>KPIs Charts</b>", styles["Heading1"]))
        story.append(Spacer(1, 12))

        # ---- Funzione per generare grafici Plotly e salvarli ----
        def save_kpi_chart(metric, title, filename):
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_kpi["symbol"],
                y=df_kpi[metric],
                text=df_kpi[metric].round(2),
                textposition="auto"
            ))
            fig.update_layout(title=title, height=400)
            pio.write_image(fig, filename)  # richiede kaleido
            return filename

        # Salvo i grafici e li aggiungo al PDF
        charts = [
            ("EBITDA Margin", "EBITDA Margin", "ebitda.png"),
            ("Debt/Equity", "Debt to Equity", "debt.png"),
            ("FCF Margin", "Free Cash Flow Margin", "fcf.png"),
            ("EPS", "Earnings Per Share", "eps.png")
        ]

        for metric, title, fname in charts:
            path = save_kpi_chart(metric, title, fname)
            story.append(Image(path, width=400, height=250))
            story.append(Spacer(1, 20))

        doc.build(story)

        # ---------------- DOWNLOAD LINK ----------------
        with open(pdf_filename, "rb") as f:
            pdf_bytes = f.read()
        b64_pdf = base64.b64encode(pdf_bytes).decode()
        href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="BalanceShip_Report.pdf">📥 Download Report</a>'
        st.markdown(href, unsafe_allow_html=True)

# ---------------- FOOTER ----------------
st.markdown("""
<hr style="margin-top:50px;"/>
<div style='text-align: center; font-size: 0.9rem; color: grey;'>
    &copy; 2025 BalanceShip. All rights reserved.
</div>
""", unsafe_allow_html=True)
