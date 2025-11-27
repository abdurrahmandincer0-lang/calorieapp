import streamlit as st
import google.generativeai as genai
from supabase import create_client, Client
from PIL import Image
import json
import time
from datetime import date, datetime, timedelta

# --- 1. AYARLAR ---
st.set_page_config(page_title="Caloria Cloud", page_icon="🥑", layout="centered")

# API Anahtarları
try:
    GENAI_KEY = st.secrets["GOOGLE_API_KEY"]
    SUPA_URL = st.secrets["SUPABASE_URL"]
    SUPA_KEY = st.secrets["SUPABASE_KEY"]
except:
    st.error("🚨 Sırlar bulunamadı. .streamlit/secrets.toml dosyasını kontrol et.")
    st.stop()

genai.configure(api_key=GENAI_KEY)

@st.cache_resource
def init_supabase():
    return create_client(SUPA_URL, SUPA_KEY)

supabase = init_supabase()

# --- 2. METİNLER ---
T = {
    "TR": {
        "welcome": "Hoş geldin", "streak": "Gün", "dash_remain": "KALAN", "dash_intake": "Alınan", "dash_target": "Hedef",
        "menu": "Menü", "water": "Su", "weight": "Kilo", "settings": "Ayarlar",
        "food_add": "Yemek Ekle", "analyze": "Analiz Et", "ai_working": "AI İnceliyor...",
        "save": "Kaydet", "update": "Güncelle", "logout": "Çıkış Yap",
        "coach_prompt": "Sen Türkçe konuşan bir diyetisyensin.",
        "onb_title": "Profilini Oluşturalım", "onb_desc": "Sana özel hedefler belirlememiz için bu bilgiler gerekli.",
        "water_target": "Su Hedefi (ml)", "manual_water": "Manuel Su Ekle (ml)"
    },
    "EN": { "welcome": "Welcome", "streak": "Day", "dash_remain": "REMAINING", "dash_intake": "Intake", "dash_target": "Target", "menu": "Menu", "water": "Water", "weight": "Weight", "settings": "Settings", "food_add": "Add Food", "analyze": "Analyze", "ai_working": "Processing...", "save": "Save", "update": "Update", "logout": "Logout", "coach_prompt": "You are a dietitian.", "onb_title": "Setup Profile", "onb_desc": "We need this info to set your goals.", "water_target": "Water Target (ml)", "manual_water": "Manual Add (ml)" },
    "AR": { "welcome": "Ahlan", "streak": "Yom", "dash_remain": "BA2Y", "dash_intake": "Akalt", "dash_target": "Hadaf", "menu": "Menu", "water": "Mayya", "weight": "Wazn", "settings": "E3dadat", "food_add": "Dakhal Akl", "analyze": "Hallel", "ai_working": "Lahza...", "save": "Hafez", "update": "Gaded", "logout": "Khorouj", "coach_prompt": "Enta doctor.", "onb_title": "Profil", "onb_desc": "Khallina netaraf 3alek.", "water_target": "Hadaf Mayya", "manual_water": "Edafa Yadawi" }
}

# --- 3. CSS (Temiz Görünüm) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .block-container { padding-top: 2rem !important; padding-bottom: 5rem !important; }
    header, footer { visibility: hidden; }
    div.stButton > button { background: linear-gradient(90deg, #7C3AED 0%, #5B21B6 100%) !important; color: white !important; border: none; border-radius: 12px; padding: 10px; }
    .kutlama-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background-color: rgba(0,0,0,0.85); z-index: 9999; display: flex; justify-content: center; align-items: center; flex-direction: column; }
    .yesil-yazi { color: #10B981 !important; }
    .kirmizi-yazi { color: #EF4444 !important; }
    </style>
""", unsafe_allow_html=True)

# --- 4. OTURUM YÖNETİMİ ---
if 'user' not in st.session_state: st.session_state['user'] = None
if 'profile' not in st.session_state: st.session_state['profile'] = None
if 'show_celebration' not in st.session_state: st.session_state['show_celebration'] = False

def login(email, password):
    try:
        res = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state['user'] = res.user
        fetch_profile()
        st.rerun()
    except Exception as e:
        st.error(f"Giriş başarısız: {e}")

def signup(email, password, name, lang):
    try:
        res = supabase.auth.sign_up({"email": email, "password": password})
        if res.user:
            # Profil oluştur ve dili kaydet
            time.sleep(1) # Supabase trigger beklemek için
            supabase.table("profiles").update({"full_name": name, "language": lang}).eq("id", res.user.id).execute()
            # Otomatik giriş yap
            login(email, password)
    except Exception as e:
        st.error(f"Kayıt hatası: {e}")

def logout():
    supabase.auth.sign_out()
    st.session_state['user'] = None
    st.session_state['profile'] = None
    st.rerun()

def fetch_profile():
    if not st.session_state['user']: return
    uid = st.session_state['user'].id
    try:
        data = supabase.table("profiles").select("*").eq("id", uid).execute()
        if data.data:
            st.session_state['profile'] = data.data[0]
        else:
            # Profil yoksa oluştur
            supabase.table("profiles").insert({"id": uid, "email": st.session_state['user'].email}).execute()
            st.session_state['profile'] = {"id": uid, "language": "TR"}
    except: pass

# --- 5. LOG & DATABASE İŞLEMLERİ ---
def get_todays_logs():
    uid = st.session_state['user'].id
    today = date.today().isoformat()
    # Tarihe göre filtrele
    response = supabase.table("logs").select("*").eq("user_id", uid).eq("date", today).execute()
    return response.data

def add_log_db(type, content):
    uid = st.session_state['user'].id
    today = date.today().isoformat()
    
    supabase.table("logs").insert({
        "user_id": uid, "date": today, "type": type, "content": content
    }).execute()
    
    # Streak Logic (Sadece Yemekte)
    if type == 'meal':
        prof = st.session_state['profile']
        last_date = str(prof.get('last_log_date'))
        current_streak = prof.get('streak') or 0
        
        if last_date != today:
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            new_streak = current_streak + 1 if last_date == yesterday else 1
            
            supabase.table("profiles").update({"last_log_date": today, "streak": new_streak}).eq("id", uid).execute()
            st.session_state['profile']['streak'] = new_streak
            st.session_state['show_celebration'] = True # Sadece burada true yapıyoruz

def update_profile_db(data):
    uid = st.session_state['user'].id
    supabase.table("profiles").update(data).eq("id", uid).execute()
    fetch_profile()

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

# 1. GİRİŞ YAPILMAMIŞSA -> Login/Signup Ekranı
if not st.session_state['user']:
    st.markdown("<h1 style='text-align:center;'>⚡ Caloria Cloud</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["Giriş Yap", "Kayıt Ol"])
    
    with tab1:
        email = st.text_input("E-posta", key="l_email")
        password = st.text_input("Şifre", type="password", key="l_pass")
        if st.button("Giriş Yap", type="primary"):
            login(email, password)
            
    with tab2:
        n_name = st.text_input("Ad Soyad")
        n_email = st.text_input("E-posta", key="s_email")
        n_pass = st.text_input("Şifre (Min 6)", type="password", key="s_pass")
        n_lang = st.selectbox("Dil / Language", ["TR", "EN", "AR"])
        
        if st.button("Hesap Oluştur"):
            if n_email and len(n_pass) >= 6: 
                signup(n_email, n_pass, n_name, n_lang)
            else: st.warning("Bilgileri kontrol et.")
    st.stop()

# 2. GİRİŞ YAPILMIŞ AMA PROFİL EKSİKSE -> Onboarding
if not st.session_state['profile']: fetch_profile()
prof = st.session_state['profile']
LANG = prof.get('language', 'TR')
TXT = T[LANG]

# Profilde kilo veya boy yoksa Onboarding'e at
if not prof.get('current_weight') or not prof.get('height'):
    st.markdown(f"## {TXT['onb_title']}")
    st.info(TXT['onb_desc'])
    
    with st.form("onboarding"):
        c1, c2 = st.columns(2)
        yas = c1.number_input("Yaş", 10, 100, 25)
        boy = c2.number_input("Boy (cm)", 100, 250, 170)
        kilo = st.number_input("Kilo (kg)", 30.0, 200.0, 70.0)
        hedef = st.number_input("Hedef Kilo (kg)", 30.0, 200.0, 65.0)
        cinsiyet = st.selectbox("Cinsiyet", ["Erkek", "Kadın"])
        aktivite = st.selectbox("Aktivite", ["Hareketsiz", "Az Hareketli", "Orta", "Çok Hareketli"])
        
        if st.form_submit_button(TXT['save']):
            update_profile_db({
                "age": yas, "height": boy, "current_weight": kilo, 
                "target_weight": hedef, "gender": cinsiyet, "activity_level": aktivite
            })
            st.rerun()
    st.stop()

# 3. ANA UYGULAMA (Main Dashboard)
logs = get_todays_logs()
meals = [l['content'] for l in logs if l['type'] == 'meal']
water_logs = [l['content'] for l in logs if l['type'] == 'water']

# Hesaplamalar
total_cal = sum(m.get('cal', 0) for m in meals)
total_pro = sum(m.get('pro', 0) for m in meals)
total_fat = sum(m.get('fat', 0) for m in meals)
total_carb = sum(m.get('carb', 0) for m in meals)
total_water = sum(w.get('ml', 0) for w in water_logs)

# Hedefler
bmr = (10 * float(prof['current_weight'])) + (6.25 * float(prof['height'])) - (5 * float(prof['age']))
bmr += 5 if prof.get('gender') == 'Erkek' else -161
target_cal = int(bmr * 1.375)
remain_cal = target_cal - total_cal

water_target = int(prof.get('water_target') or (float(prof['current_weight']) * 35))

# --- HEADER ---
c1, c2 = st.columns([3, 1])
c1.markdown(f"<h3>{TXT['welcome']}, <span style='color:#7C3AED;'>{prof.get('full_name')}</span></h3>", unsafe_allow_html=True)
c2.markdown(f"<div style='border:1px solid #7C3AED; border-radius:10px; text-align:center; padding:5px; background:rgba(124,58,237,0.1);'>🔥 {prof.get('streak', 0)} {TXT['streak']}</div>", unsafe_allow_html=True)

# KUTLAMA (Sadece show_celebration true ise)
if st.session_state['show_celebration']:
    st.balloons()
    time.sleep(2)
    st.session_state['show_celebration'] = False
    st.rerun()

# --- SEKMELER ---
tabs = st.tabs([f"🍽️ {TXT['menu']}", f"💧 {TXT['water']}", f"⚖️ {TXT['weight']}", f"⚙️ {TXT['settings']}"])

# TAB 1: YEMEK
with tabs[0]:
    # Skor Kartı
    col_cls = "yesil-yazi" if remain_cal > 0 else "kirmizi-yazi"
    st.markdown(f"""
    <div style="background:rgba(255,255,255,0.05); padding:20px; border-radius:20px; text-align:center; border:1px solid #444;">
        <small>{TXT['dash_remain']}</small>
        <h1 class='{col_cls}' style='font-size:50px; margin:0;'>{remain_cal}</h1>
        <hr style='opacity:0.2;'>
        <div style='display:flex; justify-content:space-between;'>
            <div><small>{TXT['dash_intake']}</small><h3>{total_cal}</h3></div>
            <div><small>{TXT['dash_target']}</small><h3>{target_cal}</h3></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.write("")
    c1, c2, c3 = st.columns(3)
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

    st.markdown("---")
    for m in meals:
        st.info(f"🍽️ {m.get('name')} — {m.get('cal')} kcal")

# TAB 2: SU
with tabs[1]:
    st.markdown(f"<h1 style='text-align:center; color:#3B82F6;'>{total_water} ml</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; opacity:0.7;'>/ {water_target} ml</p>", unsafe_allow_html=True)
    st.progress(min(total_water/water_target, 1.0))
    
    c1, c2, c3 = st.columns(3)
    if c1.button("+200ml"): add_log_db('water', {'ml': 200}); st.rerun()
    if c2.button("+500ml"): add_log_db('water', {'ml': 500}); st.rerun()
    if c3.button("-200ml"): add_log_db('water', {'ml': -200}); st.rerun()
    
    st.markdown("---")
    with st.expander(TXT['manual_water']):
        man_ml = st.number_input("ml", 0, 2000, 200)
        if st.button("Ekle", key="w_man"):
            add_log_db('water', {'ml': man_ml})
            st.rerun()

# TAB 3: KİLO
with tabs[2]:
    cur_w = float(prof.get('current_weight') or 70)
    st.metric(TXT['weight'], f"{cur_w} kg")
    
    new_w = st.number_input("Yeni Kilo", value=cur_w)
    if st.button(TXT['save']):
        add_log_db('weight', {'kg': new_w})
        update_profile_db({'current_weight': new_w})
        st.success("Kaydedildi!")
        time.sleep(1); st.rerun()

# TAB 4: AYARLAR
with tabs[3]:
    st.header(TXT['settings'])
    with st.form("settings"):
        f_lang = st.selectbox("Language", ["TR", "EN", "AR"], index=["TR", "EN", "AR"].index(LANG))
        f_name = st.text_input("Name", value=prof.get('full_name', ''))
        f_target_w = st.number_input("Target Weight", value=float(prof.get('target_weight') or 70))
        # Su Hedefi Ayarı
        f_water_target = st.number_input(TXT['water_target'], value=int(prof.get('water_target') or 2500))
        
        if st.form_submit_button(TXT['update']):
            update_profile_db({
                "language": f_lang, "full_name": f_name, 
                "target_weight": f_target_w, "water_target": f_water_target
            })
            st.success("OK!")
            time.sleep(1); st.rerun()
            
    st.markdown("---")
    if st.button(TXT['logout'], type="primary"): logout()
