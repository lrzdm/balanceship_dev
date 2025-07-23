
import streamlit as st
import os, base64
from PIL import Image
    
st.set_page_config(page_title="Who We Are", layout="wide")
    
# Base64 helper
def get_base64(path):
    with open(path, 'rb') as f: return base64.b64encode(f.read()).decode()

def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()


# --- CSS ---
st.markdown("""
<style>
/* ---------- BASE ---------- */
body {
  background-color: #eceff1;
  color: #263238;
}

/* ---------- LOGHI ---------- */
.logo-container {
  display: flex;
  justify-content: center;
  gap: 30px;
  margin: 30px auto;
  flex-wrap: wrap;
}
.logo-large { height: 90px; }
.logo-small { height: 60px; }

/* ---------- STARTUP BOX ---------- */
.startup-box {
  background: #f5f5f5;
  color: #263238 !important;
  border-left: 6px solid #0173C4;
  border-radius: 10px;
  padding: 30px;
  flex: 1;
  box-shadow: 0 4px 15px rgba(1, 115, 196, 0.3);
  max-width: 760px;
  width: 100%;
  margin: 20px auto;
}

/* ---------- DESCRIZIONE / CREDO BLOCK ---------- */
.description-block {
  background: #fff;
  color: #263238 !important;
  border-radius: 12px;
  box-shadow: 0 4px 15px rgba(1, 115, 196, 0.3);
  padding: 40px;
  margin: 20px;
}
.description-block div {
  margin-top: 30px;
  font-weight: bold;
  text-align: center;
}

/* ---------- GRIGLIA PROFILI ---------- */
.profile-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 2rem;
  margin: 3rem auto;
}

/* ---------- CARD PROFILO ---------- */
.profile-card {
  width: 220px;
  height: 280px;
  perspective: 1000px;
}

.profile-inner {
  width: 100%;
  height: 100%;
  transition: transform 0.8s;
  transform-style: preserve-3d;
  position: relative;
}

.profile-card:hover .profile-inner,
.profile-card:active .profile-inner {
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
  padding: 1rem;
}

.profile-front {
  background-color: #0173C4;
  color: white;
}

.profile-front img {
  border-radius: 50%;
  width: 100px;
  height: 100px;
  object-fit: cover;
  margin-bottom: 10px;
}

.profile-front h4 {
  font-size: 1.1rem;
  font-weight: 600;
  margin-top: 0.5rem;
  min-height: 1.2em;
}

.profile-back {
  background-color: #fff;
  color: #263238;
  transform: rotateY(180deg);
  font-size: 0.95rem;
  font-weight: 400;
  justify-content: flex-start;
  align-items: flex-start;
  overflow-y: auto;
}

/* ---------- TIMELINE ---------- */
.timeline {
  position: relative;
  max-width: 800px;
  margin: 60px auto;
}
.timeline::after {
  content: '';
  position: absolute;
  width: 6px;
  background-color: #0173C4;
  top: 0;
  bottom: 0;
  left: 50%;
  margin-left: -3px;
}
.timeline-box {
  padding: 20px 40px;
  position: relative;
  width: 50%;
}
.timeline-box.left {
  left: 0;
}
.timeline-box.right {
  left: 50%;
}
.timeline-box::after {
  content: '';
  position: absolute;
  width: 20px;
  height: 20px;
  right: -10px;
  background-color: #0173C4;
  border: 4px solid #fff;
  top: 15px;
  border-radius: 50%;
  z-index: 1;
}
.timeline-box.right::after {
  left: -10px;
}
.timeline-content {
  background-color: #fff;
  color: #263238 !important;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(1, 115, 196, 0.2);
}
.timeline-content h4 {
  margin-top: 0;
}

/* ---------- RESPONSIVE MOBILE ---------- */
@media screen and (max-width: 768px) {
  .profile-grid {
    flex-direction: column;
    align-items: center;
  }

  .profile-card {
    width: 90%;
    height: 280px;
  }

  .timeline::after {
    left: 8px;
  }

  .timeline-box {
    width: 100%;
    padding-left: 30px;
    padding-right: 20px;
    margin-bottom: 30px;
  }

  .timeline-box.left,
  .timeline-box.right {
    left: 0;
  }

  .timeline-box::after,
  .timeline-box.right::after {
    left: 0;
    margin-left: -10px;
  }

  .timeline-content {
    margin-left: 20px;
  }
}
</style>
""", unsafe_allow_html=True)


# --- Logo Top ---
logo_html = ""
for path, cls in [("images/logo1.png","logo-large"),("images/logo2.png","logo-small")]:
    if os.path.exists(path):
        logo_html += f'<img src="data:image/png;base64,{get_base64(path)}" class="{cls}">'
st.markdown(f"<div class='logo-container'>{logo_html}</div>", unsafe_allow_html=True)

# --- Startup Info + About us Side by Side ---
st.markdown(""" 
  <div style="display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; align-items: stretch; min-height: 400px; margin: 40px 0;">
  <div class='credo-box' style="max-width: 1200px; width: 100%; margin: 0; height: 100%; box-sizing: border-box; display: flex; background-color: #f9f9f9; border-left: 6px solid #0173C4; padding: 30px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="width: 100%;">
    <h2 style="text-align:center;">🌟 Our Credo</h2>

    <p><strong>🧭</strong><br/>
    At BalanceShip, we believe that financial data should be accessible, understandable, and actionable for everyone. We exist to remove the barriers to financial information, enabling smarter decisions through clarity and transparency. Our purpose is to make financial information open, visual, and comparable.</p>

    <p><strong>🌍</strong><br/>
    We aim to become the go-to platform for financial comparison, insight, and monitoring — empowering anyone to see and understand the financial world. Democratizing access to high-quality financial data is our main objective.</p>

    <p><strong>🚀</strong><br/>
    Our mission is to provide a smart, user-friendly dashboard to explore, compare, and visualize financial KPIs across companies worldwide. By combining accuracy, clarity, and intuitive design, we help investors, analysts, and finance enthusiasts turn data into insight.</p>

    <div style='margin-top: 30px; text-align: center; font-weight: bold; font-size: 1.1em; color: #0173C4;'>
      Navigate the financial sea with clarity ⚓
    </div>
  </div>
""", unsafe_allow_html=True)


# --- Team Profiles ---
st.markdown("<h2 style='text-align:center; margin-top:40px;'>👥 About Us</h2>", unsafe_allow_html=True)
profiles = [
  ("Lorenzo De Meo","Professional with an engineering background and an MBA, specializing in financial reporting, internal audit, and risk management.\
 Experienced in financial analysis, accounting, and managing financial risks to support strategic decision-making. Proficient in Power BI and \
Python.","images/Lorenzo De Meo_01.jpg"),
  ("William Herbert Gazzo","Professional with a solid business background and a professional training from SDA Bocconi. \
Specialized in project management and business planning. He boasts extensive experience in consulting firms \
and multinational companies, where he has held managerial roles.","images/William H Gazzo_01.jpg"),
  ("Gabriele Schininà","Professional with a solid financial background and training from SDA Bocconi. Specialized in financial modelling, \
  strategic planning, and budget management. He boasts extensive experience in listed and non-listed multinational companies, with roles in \
business controlling.","images/Gabriele Schinina_01.jpg"),
  ("Giovanni Serusi","Multidisciplinary business professional with a neuroscience background and executive pharma management training from SDA Bocconi. \
  Specialized in competitive intelligence and scouting of new investment opportunities with a focus on the life science sector.","images/Giovanni Serusi_01.jpg"),
]
cards = ""
for name, desc, img in profiles:
    if not os.path.exists(img): continue
    cards += f"""
    <div class='profile-card'>
      <div class='profile-inner'>
        <div class='profile-front'>
          <img src="data:image/jpeg;base64,{get_base64(img)}">
          <h4>{name}</h4>
        </div>
        <div class='profile-back'>
          <h4>{name}</h4>
          <p style='font-size:14px;'>{desc}</p>
        </div>
      </div>
    </div>"""
st.markdown(f"<div class='profile-grid'>{cards}</div>", unsafe_allow_html=True)

# --- TIMELINE ---
st.markdown("<h2 style='text-align: center;'>📈 Our Journey</h2>", unsafe_allow_html=True)
st.markdown("""
<div class='timeline'>
    <div class='timeline-box left'>
        <div class='timeline-content'>
            <h4>Q3 2025 – MVP Launch</h4>
            <p>Released the first version of our data platform for financial analysis and visualization.</p>
        </div>
    </div>
    <div class='timeline-box right'>
        <div class='timeline-content'>
            <h4>Q4 2025 – Worldwide data</h4>
            <p>Global Stock Exchanges full coverage.</p>
        </div>
    </div>
    <div class='timeline-box left'>
        <div class='timeline-content'>
            <h4>Q3 2026 – AI Implementation</h4>
            <p>Expansion of our core team with experts in AI, engineering, and finance.</p>
        </div>
    </div>
    <div class='timeline-box right'>
        <div class='timeline-content'>
            <h4>Q2 2027 – Strategic partnerships</h4>
            <p>Onboarding early enterprise clients and impementation of data collection to boost our features.</p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Contacts ---
insta, lin = get_base64("images/IG.png"), get_base64("images/LIN.png")
st.markdown(f"""
<div style='background:#f5f5f5;padding:40px;border-radius:12px; text-align:center; box-shadow:0 3px 10px rgba(0,0,0,0.05); margin:30px'>
  <h3>📬 Contact Us</h3>
  <p>Interested in collaborating? <a href='mailto:your-email@example.com'>Send us an email</a></p>
  <a href='#'><img src='data:image/png;base64,{insta}' width='40' style='margin:10px'></a>
  <a href='#'><img src='data:image/png;base64,{lin}' width='40' style='margin:10px'></a>
</div>
""", unsafe_allow_html=True)

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
<div style="
    margin: 40px auto 20px auto;
    max-width: 800px;
    font-style: italic;
    color: #666666;
    font-size: 0.85rem;
    text-align: center;
    padding: 10px 20px;
    border-top: 1px solid #ccc;
    opacity: 0.7;
">
    ⚠️ Disclaimer: The financial data presented on this site is for informational purposes only and does not constitute financial advice or investment recommendations.\
    The information is obtained from publicly available sources and is subject to change. This site is not affiliated with or endorsed by Yahoo Finance or any other data \
    providers.
</div>
""", unsafe_allow_html=True)


st.markdown("""
<hr style="margin-top:50px;"/>
<div style='text-align: center; font-size: 0.9rem; color: grey;'>
    &copy; 2025 BalanceShip. All rights reserved.
</div>
""", unsafe_allow_html=True)
