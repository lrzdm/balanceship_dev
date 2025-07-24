import streamlit as st
import random
import time
from streamlit.components.v1 import html
import streamlit.components.v1 as components
import datetime
from cache_db import load_from_db
from data_utils import read_exchanges, read_companies
import base64
import os
from PIL import Image
import random

st.set_page_config(layout="wide")

quotes = [
    "Success is not final, failure is not fatal: It is the courage to continue that counts.",
    "Invest in yourself. Your career is the engine of your wealth.",
    "The stock market is designed to transfer money from the Active to the Patient.",
    "Risk comes from not knowing what you’re doing.",
    "Don’t put all your eggs in one basket.",
    "The goal of investing is to grow your money, not to impress others.",
    "Time in the market beats timing the market.",
    "Discipline is the bridge between goals and accomplishment.",
    "If you don’t find a way to make money while you sleep, you will work until you die.",
    "Every great achievement was once considered impossible.",
    "Your income can grow only to the extent you do.",
    "In investing, what is comfortable is rarely profitable.",
    "Success usually comes to those who are too busy to be looking for it.",
    "Small daily improvements are the key to staggering long-term results.",
    "Courage is being scared to death and saddling up anyway.",
    "A budget is telling your money where to go instead of wondering where it went.",
    "Wealth is the ability to fully experience life.",
    "It’s not about having more money. It’s about having more freedom.",
    "Opportunities don't happen. You create them.",
    "The best investment you can make is in your own knowledge."
]


# Quote del giorno basata sul giorno dell’anno
quote_of_the_day = random.choice(quotes)

# Base64 helper
def get_base64(path):
    with open(path, 'rb') as f: return base64.b64encode(f.read()).decode()

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# ---- KPI & AI PHRASE CONFIG ----
kpi_fields = [
    ("total_revenue", "revenue", "reported a revenue of {val}B USD"),
    ("ebit", "EBIT", "had an EBIT of {val}B USD"),
    ("ebitda", "EBITDA", "posted an EBITDA of {val}B USD"),
    ("free_cash_flow", "Free Cash Flow", "generated Free Cash Flow of {val}B USD"),
    ("net_income", "net profit", "achieved a net profit of {val}B USD"),
    ("basic_eps", "EPS", "had an EPS of {val}"),
    ("cost_of_revenue", "COGS", "reported COGS of {val}B USD"),
    ("total_debt", "total debt", "closed the year with total debt of {val}B"),
    ("total_assets", "total assets", "held total assets worth {val}B"),
    ("operating_income", "operating income", "reached operating income of {val}B"),
    ("gross_profit", "gross profit", "achieved gross profit of {val}B"),
    ("pretax_income", "pre-tax income", "earned pre-tax income of {val}B")
]

# ---- LOAD ALL TICKERS FROM DB ----
def get_all_tickers():
    exchanges = read_exchanges("exchanges.txt")
    tickers = []
    for ex in exchanges.values():
        companies = read_companies(ex)
        for c in companies:
            if 'ticker' in c:
                tickers.append(c['ticker'])
    return list(set(tickers))
    
@st.cache_data(ttl=3600)
def cached_all_tickers(limit=500):
    exchanges = read_exchanges("exchanges.txt")
    tickers = []
    for ex in exchanges.values():
        companies = read_companies(ex)
        for c in companies:
            if 'ticker' in c:
                tickers.append(c['ticker'])
    return random.sample(list(set(tickers)), min(limit, len(tickers)))

tickers = cached_all_tickers(limit=100)

# ---- LOAD TICKER DATA FOR BAR ----
@st.cache_data(ttl=300)
def load_ticker_bar_data(limit=10):
    tickers = cached_all_tickers(limit=limit)
    years = ["2021", "2022", "2023", "2024"]
    result = []

    for t in tickers:
        y = random.choice(years)
        data = load_from_db(t, [y])
        if data and isinstance(data[0], dict):
            d = data[0]
            key, label, _ = random.choice(kpi_fields)
            val = d.get(key)
            if val:
                try:
                    val_fmt = f"{float(val):.2f}"
                    b_metrics = [
                        "total_revenue", "ebit", "ebitda", "free_cash_flow", "net_income",
                        "cost_of_revenue", "total_debt", "total_assets", "operating_income",
                        "gross_profit", "pretax_income"
                    ]
                    val_str = f"{val_fmt}B" if key in b_metrics else val_fmt
                    result.append((t, y, f"{label.title()}: {val_str}"))
                except:
                    continue
    return result


bar_items = load_ticker_bar_data(limit=8)

def get_random_color():
    return random.choice(["#00ff00", "#ff0000", "#00ffff", "#ffa500", "#ff69b4", "#ffffff"])

# ---- LOAD LOGOS ----
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

logo1 = get_base64_image("images/logo1.png")
logo2 = get_base64_image("images/logo2.png")


# Inizio stringa HTML/CSS
html_code = f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');

  html, body, .main {{
    font-family: 'Open Sans', sans-serif !important;
    font-size: 16px !important;
    color: black;
  }}
  body, .block-container {{
    padding-left: 0 !important;
    padding-right: 0 !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
  }}
  .stApp, .main, .block-container {{
    background-color: rgba(0, 0, 0, 0) !important;
    background: transparent !important;
  }}
  .navbar {{
    position: fixed;
    top: 0;
    width: 100%;
    display: flex;
    align-items: center;
    background: rgba(255, 255, 255, 1);
    padding: 0.5rem 1rem;
    z-index: 999;
    gap: 2rem;
    color: black;
    margin-bottom: 50px;
  }}
  .navbar-left {{
    display: flex;
    align-items: center;
    gap: 15px;
    flex-shrink: 0;
  }}
  .navbar-right {{
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-left: 7rem;
  }}
  .navbar-left img {{
    height: 50px;
  }}
  .navbar a {{
    color: #0173C4;
    text-decoration: none;
    font-weight: bold;
    margin-left: 2rem;
    padding: 0.3rem 0.6rem;
    border-radius: 5px;
    transition: background-color 0.3s, color 0.3s;
    display: inline-block;
  }}
  .navbar a:hover {{
    background-color: #0173C4;
    color: white;
    cursor: pointer;
  }}
  .ticker-bar {{
    position: fixed;
    top: 70px;
    width: 100%;
    background-color: black;
    overflow: hidden;
    height: 40px;
    border-top: 2px solid #333;
    border-bottom: 2px solid #333;
    z-index: 998;
    display: flex;
    align-items: center;
  }}
  .ticker-content {{
    display: inline-block;
    white-space: nowrap;
    animation: ticker 40s linear infinite;
  }}
  @keyframes ticker {{
    from {{ transform: translateX(0%); }}
    to {{ transform: translateX(-50%); }}
  }}
  .ticker-item {{
    display: inline-block;
    margin: 0 2rem;
    font-size: 1rem;
    font-family: monospace;
    line-height: 40px;
  }}
  .video-background {{
    position: fixed;
    top: 110px;
    left: 0;
    width: 100vw;
    height: calc(100vh - 110px);
    z-index: -1;
    object-fit: cover;
    opacity: 0.8;
    background-color: black;
    pointer-events: none;
  }}
  @media (max-width: 768px) {{
    .navbar-right {{ flex-wrap: wrap; margin-left: 0; }}
    .profile-grid {{ flex-direction: column; align-items: center; }}
    .ticker-item {{ font-size: 0.8rem; margin: 0 1rem; }}
  }}
</style>

<video autoplay muted loop class="video-background">
  <source src="https://www.dropbox.com/scl/fi/ua937izl1la1hh2yp0xyk/Balanceship_video.mp4?rlkey=uztuba8wh6lgsbxqk5ne37h2n&raw=1" type="video/mp4">
  Your browser does not support the video tag.
</video>

<div class="navbar">
  <div class="navbar-left">
    <img src="data:image/png;base64,{logo1}" />
    <img src="data:image/png;base64,{logo2}" />
  </div>
  <div class="navbar-right" style="display: flex; align-items: center; justify-content: space-between; gap: 1rem; max-width: 100%; color: #0173C4; font-size: 14px; flex-grow: 1; overflow: hidden;">
    <div style="font-style: italic; flex-grow: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
      💡 {quote_of_the_day}
    </div>
  </div>
</div>

<div class="ticker-bar">
  <div class="ticker-content" id="ticker-content">
"""

# Riduce lo spazio sopra (puoi regolare)
st.markdown("<style>.main {{padding-top: 0rem !important;}}</style>", unsafe_allow_html=True)

# Aggiunge spazio sotto la barra
st.markdown("<div style='height:80px;'></div>", unsafe_allow_html=True)


# Aggiunta dinamica dei ticker (due volte per scorrimento fluido)
for t, y, val in bar_items * 2:  # duplica direttamente
    html_code += f'<span class="ticker-item" style="color:{get_random_color()};">{t} ({y}): {val}</span>'

# Chiusura blocco
html_code += """
  </div>
</div>
"""

# Rendering
html(html_code, height=800)


# ---- HEADLINE ----
st.markdown("""
<div style='margin-top: 100px; margin-bottom: 100px; color:#0173C4; text-align:center;'>
    <h1>Welcome to BalanceShip!</h1>
    <p>Smart data. Make better financial decisions.</p>
</div>
""", unsafe_allow_html=True)


#----BOX COUNTER AND MAP--------

n_companies = len(get_all_tickers())
n_years = 4
n_records = n_companies * n_years * 34
stock_exchanges = 6

n_companies_fmt = format(n_companies, ",")
n_years_fmt = format(n_years, ",")
n_records_fmt = format(n_records, ",")
stock_exchanges_fmt = format(stock_exchanges, ",")


new_width = 300
map_base64 = get_base64_image("images/Map_Chart.png")



# CSS per le card animate in stile profili
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700&display=swap');
@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css');

.profile-grid {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 2rem;
    margin-top: 3rem;
}

.profile-card {
    width: 220px;
    height: 250px;
    perspective: 1000px;
}

.profile-inner {
    width: 100%;
    height: 100%;
    transition: transform 0.8s;
    transform-style: preserve-3d;
    position: relative;
    cursor: pointer;
}

.profile-card:hover .profile-inner {
    transform: rotateY(180deg);
}

.profile-front,
.profile-back {
    position: absolute;
    width: 100%;
    height: 100%;
    backface-visibility: hidden;
    border-radius: 15px;
    box-shadow: 0 4px 15px rgba(1, 115, 196, 0.2);
    font-family: 'Open Sans', sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    box-sizing: border-box;
}

.profile-front {
    background-color: #0173C4;
    color: white;
    padding: 1rem;
}

.profile-front i {
    font-size: 3rem;
    line-height: 1;
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.profile-front h4 {
    font-size: 1.1rem;
    font-weight: 600;
    margin-top: 0.5rem;
    min-height: 1.2em;
}

.profile-back {
    background-color: #01c4a7;
    color: white;
    transform: rotateY(180deg);
    font-size: 2.2rem;
    font-weight: bold;
    justify-content: center;
    align-items: center;
    padding: 1rem;
}

</style>
""", unsafe_allow_html=True)



# Header
st.markdown("<h3 style='text-align:center; color:#0173C4;'>📊 Our Data in Numbers</h3>", unsafe_allow_html=True)

# HTML delle card con variabili dinamiche
cards = f"""
<div class='profile-grid'>
  <div class='profile-card'>
    <div class='profile-inner'>
      <div class='profile-front'>
        <i class='fas fa-building'></i>
        <h4>Companies</h4>
      </div>
      <div class='profile-back'>
        {n_companies_fmt}
      </div>
    </div>
  </div>

  <div class='profile-card'>
    <div class='profile-inner'>
      <div class='profile-front'>
        <i class='fas fa-database'></i>
        <h4>Records</h4>
      </div>
      <div class='profile-back'>
        {n_records_fmt}
      </div>
    </div>
  </div>

  <div class='profile-card'>
    <div class='profile-inner'>
      <div class='profile-front'>
        <i class='fas fa-calendar-alt'></i>
        <h4>Years</h4>
      </div>
      <div class='profile-back'>
        {n_years_fmt}
      </div>
    </div>
  </div>

  <div class='profile-card'>
    <div class='profile-inner'>
      <div class='profile-front'>
        <i class='fas fa-chart-line'></i>
        <h4>Stock Exchanges</h4>
      </div>
      <div class='profile-back'>
        {stock_exchanges_fmt}
      </div>
    </div>
  </div>
</div>
"""

# Mostra le card
st.markdown(cards, unsafe_allow_html=True)
st.markdown("<div style='height: 50px;'></div>", unsafe_allow_html=True)

# Map section
st.markdown(f"""
<div class='map-box'>
  <h3 style='text-align:center; color:#0173C4;'>🌍 Stock Exchanges on our Databases</h3>
  <img src="data:image/png;base64,{map_base64}" class="map-img"/>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

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


st.markdown("""
<hr style="margin-top:50px;"/>
<div style='text-align: center; font-size: 0.9rem; color: grey;'>
    &copy; 2025 BalanceShip. All rights reserved.
</div>
""", unsafe_allow_html=True)
