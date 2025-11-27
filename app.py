import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from PIL import Image
import json
import time
from datetime import date, datetime, timedelta
import pandas as pd

# --- 1. KONFİGÜRASYON VE BAĞLANTILAR ---
st.set_page_config(page_title="Caloria Cloud", page_icon="🥑", layout="centered")

# API Anahtarlarını Alalım (secrets.toml dosyasından)
try:
    GENAI_KEY = st.secrets["GOOGLE_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("🚨 HATA: .streamlit/secrets.toml dosyası bulunamadı veya eksik.")
    st.info("Lütfen proje klasörüne .streamlit klasörü açıp içine secrets.toml dosyasını ekleyin.")
    st.stop()

# Bağlantıları Kur
genai.configure(api_key=GENAI_KEY)

@st.cache_resource
def init_supabase():
    return create_client(SUPA_URL, SUPA_KEY)

supabase = init_supabase()

# --- 2. DİL SÖZLÜĞÜ ---
T = {
    "TR": {
        "login_title": "Giriş Yap", "signup_title": "Kayıt Ol", "email": "E-posta", "pass": "Şifre",
        "login_btn": "Giriş", "signup_btn": "Hesap Oluştur", "logout": "Çıkış Yap",
        "welcome": "Hoş geldin", "streak": "Gün", "dash_remain": "KALAN", "dash_intake": "Alınan", "dash_target": "Hedef",
        "menu": "Menü", "water": "Su", "weight": "Kilo", "settings": "Ayarlar",
        "food_add": "Yemek Ekle", "analyze": "Analiz Et", "ai_working": "AI İnceliyor...",
        "add_water": "Ekle", "save": "Kaydet", "update": "Güncelle", "dark_mode": "Tema Otomatiktir",
        "error_login": "Hatalı e-posta veya şifre.", "success_signup": "Kayıt başarılı! Giriş yapabilirsin.",
        "coach_btn": "AI Koç", "coach_prompt": "Sen Türkçe konuşan bir diyetisyensin.",
        "loading": "Veriler yükleniyor..."
    },
    "EN": { "login_title": "Login", "signup_title": "Sign Up", "email": "Email", "pass": "Password", "login_btn": "Login", "signup_btn": "Sign Up", "logout": "Logout", "welcome": "Welcome", "streak": "Day", "dash_remain": "REMAINING", "dash_intake": "Intake", "dash_target": "Target", "menu": "Menu", "water": "Water", "weight": "Weight", "settings": "Settings", "food_add": "Add Food", "analyze": "Analyze", "ai_working": "Processing...", "add_water": "Add", "save": "Save", "update": "Update", "dark_mode": "Auto Theme", "error_login": "Invalid credentials.", "success_signup": "Signed up! Please login.", "coach_btn": "AI Coach", "coach_prompt": "You are a dietitian.", "loading": "Loading data..." },
    "AR": { "login_title": "Dokhoul", "signup_title": "Tasgil", "email": "Email", "pass": "Password", "login_btn": "Dokhoul", "signup_btn": "Tasgil", "logout": "Khorouj", "welcome": "Ahlan", "streak": "Yom", "dash_remain": "BA2Y", "dash_intake": "Akalt", "dash_target": "Hadaf", "menu": "Menu", "water": "Mayya", "weight": "Wazn", "settings": "E3dadat", "food_add": "Dakhal Akl", "analyze": "Hallel", "ai_working": "Lahza...", "add_water": "Def", "save": "Hafez", "update": "Gaded", "dark_mode": "Auto Theme", "error_login": "Ghalat", "success_signup": "Tamam!", "coach_btn": "Coach", "coach_prompt": "Enta doctor.", "loading": "Tahmil..." }
}

# --- 3. CSS TASARIMI (Temiz & Otomatik Tema) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .block-container { padding-top: 2rem !important; padding-bottom: 5rem !important; }
    header, footer { visibility: hidden; }
    
    /* Tab Düzeni */
    button[data-baseweb="tab"] { flex: 1; font-weight: 600; padding: 0px !important; }
    
    /* Butonlar */
    div.stButton > button { background: linear-gradient(90deg, #7C3AED 0%, #5B21B6 100%) !important; color: white !important; border: none; border-radius: 12px; padding: 10px; }
    
    /* Kutlama */
    .kutlama-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.85); z-index: 9999; display: flex; justify-content: center; align-items: center; flex-direction: column; }
    
    /* Dashboard Renkleri */
    .yesil-yazi { color: #10B981 !important; }
    .kirmizi-yazi { color: #EF4444 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. OTURUM YÖNETİMİ (AUTH) ---
if 'user' not in st.session_state: st.session_state['user'] = None
if 'profile' not in st.session_state: st.session_state['profile'] = None

def login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state['user'] = response.user
        fetch_profile()
        st.rerun()
    except Exception as e:
        st.error(f"Giriş hatası: {e}")

def signup(email, password, name):
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        if response.user:
            # Profil ismini güncelle
            time.sleep(2) 
            supabase.table("profiles").update({"full_name": name}).eq("id", response.user.id).execute()
            st.success("Kayıt başarılı! Şimdi Giriş Yap sekmesinden giriş yapabilirsin.")
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state['user'] = None
    st.session_state['profile'] = None
    st.rerun()

# --- 5. VERİTABANI İŞLEMLERİ ---
def fetch_profile():
    if not st.session_state['user']: return
    uid = st.session_state['user'].id
    try:
        data = supabase.table("profiles").select("*").eq("id", uid).execute()
        if data.data:
            st.session_state['profile'] = data.data[0]
        else:
            # Profil yoksa oluştur (Trigger çalışmazsa yedek plan)
            supabase.table("profiles").insert({"id": uid, "email": st.session_state['user'].email}).execute()
            st.session_state['profile'] = {"id": uid, "language": "TR"}
    except Exception as e:
        st.error(f"Profil çekme hatası: {e}")

def get_todays_logs():
    uid = st.session_state['user'].id
    today = date.today().isoformat()
    response = supabase.table("logs").select("*").eq("user_id", uid).eq("date", today).execute()
    return response.data

def add_log_db(type, content):
    uid = st.session_state['user'].id
    today = date.today().isoformat()
    supabase.table("logs").insert({
        "user_id": uid, "date": today, "type": type, "content": content
    }).execute()
    
    # Streak Mantığı
    prof = st.session_state['profile']
    last_date = str(prof.get('last_log_date'))
    streak = prof.get('streak') or 0
    
    # Bugün daha önce işlem yapılmadıysa
    if last_date != today:
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        if last_date == yesterday:
            new_streak = streak + 1
        else:
            new_streak = 1
        
        supabase.table("profiles").update({
            "last_log_date": today, "streak": new_streak
        }).eq("id", uid).execute()
        
        # UI Güncelle ve Kutlama Yap
        st.session_state['profile']['streak'] = new_streak
        st.session_state['show_celebration'] = True

def update_profile_db(data):
    uid = st.session_state['user'].id
    supabase.table("profiles").update(data).eq("id", uid).execute()
    fetch_profile() # Günceli çek

# --- 6. HESAPLAMA & AI ---
def calc_target(p):
    w = float(p.get('current_weight') or 70)
    h = float(p.get('height') or 170)
    a = int(p.get('age') or 25)
    g = p.get('gender')
    target_w = float(p.get('target_weight') or 70)
    
    bmr = (10 * w) + (6.25 * h) - (5 * a)
    bmr += 5 if g in ['Erkek', 'Male', 'Ragel'] else -161
    tdee = bmr * 1.375
    
    if target_w < w: return int(tdee - 500)
    elif target_w > w: return int(tdee + 500)
    return int(tdee)

def ai_analyze(prompt, img, lang):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        p = f"Answer in {lang}. {prompt}. RETURN ONLY JSON."
        inp = [p, img] if img else [p]
        res = model.generate_content(inp)
        txt = res.text.replace("```json", "").replace("```", "")
        return json.loads(txt[txt.find('{'):txt.rfind('}')+1])
    except: return {"name": "Hata", "cal": 0, "pro": 0, "fat": 0, "carb": 0}

# =========================================================
#  UYGULAMA AKIŞI
# =========================================================

# A. GİRİŞ EKRANI (Login)
if not st.session_state['user']:
    st.markdown("<h1 style='text-align:center;'>⚡ Caloria Cloud</h1>", unsafe_allow_html=True)
    st.info("Bulut tabanlı, çok oyunculu diyet uygulaması.")
    
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta", key="l_email")
        password = st.text_input("Şifre", type="password", key="l_pass")
        if st.button("Giriş Yap", type="primary"):
            login(email, password)
            
    with tab2:
        n_name = st.text_input("Ad Soyad", key="s_name")
        n_email = st.text_input("E-posta", key="s_email")
        n_pass = st.text_input("Şifre (Min 6 karakter)", type="password", key="s_pass")
        if st.button("Hesap Oluştur"):
            if len(n_pass) < 6:
                st.warning("Şifre en az 6 karakter olmalı.")
            elif n_email and n_name: 
                signup(n_email, n_pass, n_name)
            else: st.warning("Bilgileri doldurun.")
    
    st.stop()

# B. ANA UYGULAMA (Logged In)
if not st.session_state['profile']:
    fetch_profile()

prof = st.session_state['profile']
LANG = prof.get('language', 'TR')
TXT = T[LANG]

# Verileri Çek
logs = get_todays_logs()
meals = [l['content'] for l in logs if l['type'] == 'meal']
water_logs = [l['content'] for l in logs if l['type'] == 'water']

total_cal = sum(m.get('cal', 0) for m in meals)
total_pro = sum(m.get('pro', 0) for m in meals)
total_fat = sum(m.get('fat', 0) for m in meals)
total_carb = sum(m.get('carb', 0) for m in meals)
total_water = sum(w.get('ml', 0) for w in water_logs)

TARGET = calc_target(prof)
REMAIN = TARGET - total_cal

# Header
col_h1, col_h2 = st.columns([3, 1])
col_h1.markdown(f"<h3>{TXT['welcome']}, <span style='color:#7C3AED;'>{prof.get('full_name', 'User')}</span></h3>", unsafe_allow_html=True)
col_h2.markdown(f"<div style='background:rgba(124,58,237,0.1); padding:5px; border-radius:10px; text-align:center; border:1px solid #7C3AED;'>🔥 {prof.get('streak', 0)} {TXT['streak']}</div>", unsafe_allow_html=True)

# Kutlama
if st.session_state.get('show_celebration'):
    st.markdown(f"""<div class="kutlama-overlay"><h1 style='color:white;'>🎉 {TXT['streak']}!</h1></div>""", unsafe_allow_html=True)
    st.balloons()
    time.sleep(2)
    st.session_state['show_celebration'] = False
    st.rerun()

# SEKMELER
tabs = st.tabs([f"🍽️ {TXT['menu']}", f"💧 {TXT['water']}", f"⚖️ {TXT['weight']}", f"⚙️ {TXT['settings']}"])

# 1. MENÜ SEKMESİ
with tabs[0]:
    # Dashboard Kartı
    with st.container(border=True):
        color_cls = "yesil-yazi" if REMAIN > 0 else "kirmizi-yazi"
        st.markdown(f"""
        <div style="text-align:center;">
            <p style="font-size:12px; opacity:0.7; letter-spacing:1px;">{TXT['dash_remain']}</p>
            <h1 class='{color_cls}' style="font-size:50px; margin:0;">{REMAIN}</h1>
            <hr style="opacity:0.2;">
            <div style="display:flex; justify-content:space-between;">
                <div><small>{TXT['dash_intake']}</small><h3>{total_cal}</h3></div>
                <div><small>{TXT['dash_target']}</small><h3>{TARGET}</h3></div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.write("")
    c1,c2,c3 = st.columns(3)
    c1.progress(min(total_pro/150, 1.0)); c1.caption(f"Pro: {total_pro}g")
    c2.progress(min(total_fat/70, 1.0)); c2.caption(f"Fat: {total_fat}g")
    c3.progress(min(total_carb/250, 1.0)); c3.caption(f"Carb: {total_carb}g")
    
    with st.expander(f"➕ {TXT['food_add']}", expanded=True):
        img = st.file_uploader(" ", type=["jpg","png","webp"], label_visibility="collapsed")
        if img and st.button(TXT['analyze']):
            with st.spinner(TXT['ai_working']):
                d = ai_analyze('JSON: {"name": "str", "cal": int, "pro": int, "fat": int, "carb": int}', Image.open(img), LANG)
                if d.get('cal', 0) > 0:
                    add_log_db('meal', d)
                    st.success("OK!")
                    time.sleep(1); st.rerun()
                else: st.error("AI okuyamadı.")

    st.markdown("### " + TXT['menu'])
    for m in meals:
        st.info(f"🍽️ {m.get('name')} — {m.get('cal')} kcal")
        
    if total_cal > 0 and st.button(TXT['coach_btn']):
        with st.spinner("..."):
            res = genai.GenerativeModel('gemini-2.0-flash').generate_content(f"{TXT['coach_prompt']} {meals}")
            st.info(res.text)

# 2. SU SEKMESİ
with tabs[1]:
    target_water = int(float(prof.get('current_weight') or 70) * 35)
    st.markdown(f"<h1 style='text-align:center; color:#3B82F6;'>{total_water} ml</h1>", unsafe_allow_html=True)
    st.progress(min(total_water/target_water, 1.0))
    
    c1, c2, c3 = st.columns(3)
    if c1.button("+200ml"): add_log_db('water', {'ml': 200}); st.rerun()
    if c2.button("+500ml"): add_log_db('water', {'ml': 500}); st.rerun()
    if c3.button("-200ml"): add_log_db('water', {'ml': -200}); st.rerun()

# 3. KİLO SEKMESİ
with tabs[2]:
    cur_w = st.number_input(TXT['weight'], value=float(prof.get('current_weight') or 70))
    if st.button(TXT['save']):
        add_log_db('weight', {'kg': cur_w})
        update_profile_db({'current_weight': cur_w})
        st.success("Kilo kaydedildi!")
        time.sleep(1); st.rerun()
    
    st.info("Veritabanı doldukça geçmiş grafiği burada belirecek.")

# 4. AYARLAR
with tabs[3]:
    st.header(TXT['settings'])
    with st.form("settings_form"):
        new_lang = st.selectbox("Language", ["TR", "EN", "AR"], index=["TR", "EN", "AR"].index(LANG))
        new_name = st.text_input("Name", value=prof.get('full_name', ''))
        new_age = st.number_input("Age", value=int(prof.get('age') or 25))
        new_target = st.number_input("Target Weight", value=float(prof.get('target_weight') or 70))
        
        if st.form_submit_button(TXT['update']):
            update_profile_db({
                "language": new_lang, "full_name": new_name, 
                "age": new_age, "target_weight": new_target
            })
            st.success("Profil güncellendi!")
            time.sleep(1); st.rerun()
            
    st.markdown("---")
    if st.button(TXT['logout'], type="primary"):
        logout()
