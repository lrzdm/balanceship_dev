import streamlit as st
import pandas as pd
from data_utils import read_exchanges, read_companies, get_financial_data, remove_duplicates, get_or_fetch_data, add_meta_tags
from cache_db import save_to_db, load_from_db, load_many_from_db
import base64
import os
import io
from xlsxwriter import Workbook
from PIL import Image
#from pages import Graph, Who_we_are
import copy
import requests
import uuid

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
                    "page_title": "Database",
                    "page_location": "https://www.balanceship.net/Database",
                    "engagement_time_msec": 1
                }
            }
        ]
    }
    requests.post(url, json=payload)

send_pageview()

#Google tag:
add_meta_tags(
    title="Database",
    description="Explore company financial data in stock exchanges worldwide",
    url_path="/Database"
)


st.set_page_config(page_title="Financials", layout="wide")


def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

logo1_path = os.path.join("images", "logo1.png")
logo2_path = os.path.join("images", "logo2.png")

logo_html = ""
if os.path.exists(logo1_path):
    logo1_base64 = get_base64_of_bin_file(logo1_path)
    logo_html += f'<img src="data:image/png;base64,{logo1_base64}" class="logo logo-large">'

if os.path.exists(logo2_path):
    logo2_base64 = get_base64_of_bin_file(logo2_path)
    logo_html += f'<img src="data:image/png;base64,{logo2_base64}" class="logo logo-small">'

logo_html = f"<div class='logo-container'>{logo_html}</div>"

st.markdown(f"""
<style>
    .logo-container {{
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 30px;
        margin: 20px auto;
    }}
    .logo {{
        display: block;
    }}
    .logo-large {{
        height: 100px;
    }}
    .logo-small {{
        height: 60px;
    }}
</style>
{logo_html}
""", unsafe_allow_html=True)


st.markdown("<div class='main-container'>", unsafe_allow_html=True)

st.title("📊 Financial Data")

# Selezione anni, borse, settore, industria
exchanges = read_exchanges('exchanges.txt')
exchange_names = list(exchanges.keys())
years_available = ['2021', '2022', '2023', '2024']
sectors_available = ['Communication Services', 'Consumer Cyclical', 'Consumer Defensive', 'Energy', 'Finance Services', 'Healthcare', 'Industrials', 'Real Estate', 'Technology', 'Utilities']

financial_data = []
selected_years = ['2023']
selected_exchanges = ['NASDAQ']
selected_sectors = []
selected_industries = []

col1, col2, col3, col4 = st.columns(4)
with col1:
    selected_years = st.multiselect("Select Years", years_available, default=selected_years)
with col2:
    selected_exchanges = st.multiselect("Select Stock Exchanges", exchange_names, default=selected_exchanges)
with col3:
    selected_sectors = st.multiselect("Select Sector", sectors_available)


if st.button("Reset Filters"):
    selected_years = ['2023']
    selected_exchanges = ['NASDAQ']
    selected_sectors = []
    selected_industries = []
    st.rerun()

currency = "USD"
exchange_currency_mapping = {
    'NASDAQ': 'USD',
    'S&P 500': 'USD',
    'FTSE MIB': 'EUR',
    'FTSE 100': 'GBP',
    'Nikkei 225': 'JPY',
    'Hong Kong': 'HKD',
    'Shanghai': 'CNY',
}

if selected_exchanges:
    currency = exchange_currency_mapping.get(selected_exchanges[0], 'local currency')

currency_messages = {
    'USD': 'Numbers reported are in billions of USD.',
    'EUR': 'Numbers reported are in billions of EUR.',
    'GBP': 'Numbers reported are in billions of GBP.',
    'JPY': 'Numbers reported are in billions of JPY.',
    'HKD': 'Numbers reported are in billions of HKD.',
    'CNY': 'Numbers reported are in billions of CNY.'
}

st.markdown(f"<div class='currency-info'>{currency_messages.get(currency, 'Numbers reported are in billions of the local currency.')}</div>", unsafe_allow_html=True)

use_cache = True

financial_data = []
for exchange in selected_exchanges:
    companies = read_companies(exchanges[exchange])
    symbols = [c['ticker'] for c in companies]
    symbol_to_company = {c['ticker']: c for c in companies}

    print(f"Carico dati dal DB per {len(symbols)} simboli su {exchange}...")
    db_data = load_many_from_db(symbols, selected_years)
    print(f"Caricati dal DB: {len(db_data)} record")

    for k, v in list(db_data.items())[:5]:
        print(f"DB record esempio: {k} keys={list(v.keys()) if v else None}")

    for symbol in symbols:
        company = symbol_to_company[symbol]
        description = company.get('description', '')
        stock_exchange = exchange

        data_list = []
        missing_years = []

        for year in selected_years:
            y = int(year)
            data = db_data.get((symbol, y))
            if data:
                data_copy = copy.deepcopy(data)
                data_copy['description'] = description
                data_copy['stock_exchange'] = stock_exchange
                data_list.append(data_copy)
            else:
                missing_years.append(y)
                data_list.append(None)

        if not use_cache and missing_years:
            print(f"Fetch dati mancanti per {symbol}: anni {missing_years}", flush=True)
            fetched_data = get_or_fetch_data(symbol, missing_years, description, stock_exchange)
            # NON serve save_to_db qui perché già fatto dentro get_or_fetch_data
            for i, year in enumerate(selected_years):
                if data_list[i] is None and year in missing_years:
                    idx = missing_years.index(year)
                    data_list[i] = fetched_data[idx]

        financial_data.extend([d for d in data_list if d is not None])

print(f"Totale dati caricati in financial_data: {len(financial_data)}")
print("Esempio dati caricati:", financial_data[:3])



financial_data = remove_duplicates(financial_data)
if selected_sectors:
    industries_available = list(set(d['industry'] for d in financial_data if 'industry' in d and d['sector'] in selected_sectors))
else:
    industries_available = list(set(d['industry'] for d in financial_data if 'industry' in d))

# Mostra il multiselect per l'industria con le opzioni basate sulle industrie disponibili
with col4:
    selected_industries = st.multiselect("Select Industry", industries_available, default=selected_industries)


if selected_sectors:
    financial_data = [d for d in financial_data if d.get('sector') in selected_sectors]
if selected_industries:
    financial_data = [d for d in financial_data if d.get('industry') in selected_industries]

financial_data = [x for x in financial_data if isinstance(x, dict) and 'symbol' in x and 'year' in x]
financial_data.sort(key=lambda x: (x['symbol'], x['year']))


if financial_data:
    df = pd.DataFrame(financial_data)
    column_order = [
    'symbol', 'description', 'sector', 'industry', 'stock_exchange', 'year',
    'total_revenue', 'operating_revenue', 'cost_of_revenue', 'gross_profit',
    'operating_expense', 'sg_and_a', 'r_and_d', 'operating_income',
    'net_non_operating_interest_income_expense', 'interest_expense_non_operating',
    'pretax_income', 'tax_provision', 'net_income_common_stockholders',
    'net_income', 'net_income_continuous_operations', 'basic_eps', 'diluted_eps',
    'basic_average_shares', 'diluted_average_shares', 'total_expenses',
    'normalized_income', 'interest_expense', 'net_interest_income',
    'ebit', 'ebitda', 'reconciled_depreciation', 'normalized_ebitda',
    'total_assets', 'stockholders_equity', 'free_cash_flow', 'changes_in_cash',
    'working_capital', 'invested_capital', 'total_debt'
    ]

    df = df[column_order]  # applica l'ordine delle colonne
    st.success(f"{len(df)} records loaded.")
    COLUMN_LABELS = {
    "symbol": "Ticker",
    "sector": "Sector",
    "industry": "Industry",
    "description": "Company Name",
    "stock_exchange": "Exchange",
    "year": "Year",
    "total_revenue": "Total Revenue",
    "operating_revenue": "Operating Revenue",
    "cost_of_revenue": "Cost of Revenue",
    "gross_profit": "Gross Profit",
    "operating_expense": "Operating Expense",
    "sg_and_a": "SG&A",
    "r_and_d": "R&D",
    "operating_income": "Operating Income",
    "net_non_operating_interest_income_expense": "Non-Operating Interest Income/Expense",
    "interest_expense_non_operating": "Interest Expense (Non-Op)",
    "pretax_income": "Pre-tax Income",
    "tax_provision": "Tax Provision",
    "net_income_common_stockholders": "Net Income to Stockholders",
    "net_income": "Net Income",
    "net_income_continuous_operations": "Net Income (Cont. Ops)",
    "basic_eps": "Basic EPS",
    "diluted_eps": "Diluted EPS",
    "basic_average_shares": "Avg. Shares (Basic)",
    "diluted_average_shares": "Avg. Shares (Diluted)",
    "total_expenses": "Total Expenses",
    "normalized_income": "Normalized Income",
    "interest_expense": "Interest Expense",
    "net_interest_income": "Net Interest Income",
    "ebit": "EBIT",
    "ebitda": "EBITDA",
    "reconciled_depreciation": "Reconciled Depreciation",
    "normalized_ebitda": "Normalized EBITDA",
    "total_assets": "Total Assets",
    "stockholders_equity": "Stockholders' Equity",
    "free_cash_flow": "Free Cash Flow",
    "changes_in_cash": "Changes in Cash",
    "working_capital": "Working Capital",
    "invested_capital": "Invested Capital",
    "total_debt": "Total Debt"
    }

    df.rename(columns=COLUMN_LABELS, inplace=True)

    # Crea un buffer per il file Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Financials')
    excel_data = output.getvalue()

    st.download_button(
        label="Download Excel",
        data=excel_data,
        file_name="financial_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.dataframe(df, use_container_width=True)
    #st.dataframe(df.style.format(str), height=600)
else:
    st.warning("No financial data available for the selected years and exchanges.")


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


