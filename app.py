import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os
from datetime import date, timedelta
import time
import pandas as pd
import re

# --- 1. KONFİGÜRASYON ---
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="Caloria", page_icon="🥑", layout="centered")

# --- 2. DİL SÖZLÜĞÜ ---
T = {
    "TR": {
        "welcome": "Hoş geldin", "streak": "Gün", "onboard_title": "👋 Merhaba!",
        "onboard_desc": "Caloria'ya hoş geldin. Seni tanıyalım.", "name_ask": "Sana nasıl hitap edelim?",
        "gender": "Cinsiyet", "male": "Erkek", "female": "Kadın",
        "age": "Yaşın", "height": "Boy (cm)", "weight": "Mevcut Kilo (kg)",
        "activity": "Günlük Aktivite", "target_weight": "🎯 Hedef Kilo (kg)", "start_btn": "Başla 🚀",
        "missing_info": "⚠️ Lütfen tüm alanları doldur.", "dash_intake": "Alınan", "dash_remain": "KALAN", "dash_target": "Hedef",
        "food_add": "Yemek Ekle", "photo_tab": "📸 Fotoğraf", "text_tab": "✍️ Yazı",
        "analyze_btn": "Analiz Et", "ai_working": "AI Çalışıyor...", "add_btn": "Ekle", "what_eat": "Ne yedin?",
        "menu_title": "Bugünün Menüsü", "coach_btn": "🧠 AI Koç Analizi",
        "coach_prompt": "Sen Türkçe konuşan samimi bir diyetisyensin.",
        "water_title": "💧 Su Takibi", "water_cup": "+200 ml", "water_bottle": "+500 ml", "water_remove": "Sil",
        "manual_add": "Manuel Ekle", "weight_title": "⚖️ Kilo Takibi", "save": "Kaydet", "settings": "Profil Ayarları",
        "update": "Güncelle", "reset": "Sıfırla (Çıkış)", "lang_select": "Dil / Language",
        "act_sedentary": "Hareketsiz", "act_light": "Az Hareketli", "act_mod": "Orta Hareketli", "act_active": "Çok Hareketli",
        "congrats": "HARİKASIN!", "closing": "saniye içinde kapanıyor...",
        "meal_breakfast": "Kahvaltı", "meal_lunch": "Öğle", "meal_dinner": "Akşam", "meal_snack": "Ara Öğün"
    },
    "EN": {
        "welcome": "Welcome", "streak": "Day", "onboard_title": "👋 Hello!",
        "onboard_desc": "Welcome to Caloria. Let's get to know you.", "name_ask": "What should we call you?",
        "gender": "Gender", "male": "Male", "female": "Female",
        "age": "Age", "height": "Height (cm)", "weight": "Current Weight (kg)",
        "activity": "Daily Activity", "target_weight": "🎯 Target Weight (kg)", "start_btn": "Get Started 🚀",
        "missing_info": "⚠️ Please fill in all fields.", "dash_intake": "Intake", "dash_remain": "REMAINING", "dash_target": "Target",
        "food_add": "Add Food", "photo_tab": "📸 Photo", "text_tab": "✍️ Text",
        "analyze_btn": "Analyze", "ai_working": "AI Processing...", "add_btn": "Add", "what_eat": "What did you eat?",
        "menu_title": "Today's Menu", "coach_btn": "🧠 AI Coach Analysis",
        "coach_prompt": "You are a professional dietitian. Respond in English.",
        "water_title": "💧 Water Tracker", "water_cup": "+200 ml", "water_bottle": "+500 ml", "water_remove": "Remove",
        "manual_add": "Manual Add", "weight_title": "⚖️ Weight Tracker", "save": "Save", "settings": "Profile Settings",
        "update": "Update", "reset": "Reset (Logout)", "lang_select": "Language",
        "act_sedentary": "Sedentary", "act_light": "Lightly Active", "act_mod": "Moderately Active", "act_active": "Very Active",
        "congrats": "AWESOME!", "closing": "closing in seconds...",
        "meal_breakfast": "Breakfast", "meal_lunch": "Lunch", "meal_dinner": "Dinner", "meal_snack": "Snack"
    },
    "AR": { 
        "welcome": "Ahlan bik", "streak": "yōm", "onboard_title": "👋 Ahlan!",
        "onboard_desc": "Ahlan bik fi Caloria. Khallina netaraf 3alek.", "name_ask": "Esmak eh?",
        "gender": "El No3", "male": "Ragel", "female": "Set",
        "age": "El Senn", "height": "El Tool (cm)", "weight": "El Wazn (kg)",
        "activity": "Haraktak eh?", "target_weight": "🎯 Hadafak kam (kg)?", "start_btn": "Yalla Bina 🚀",
        "missing_info": "⚠️ Men fadlak, emla kol el khanat.", "dash_intake": "Elly akalto", "dash_remain": "BA2Y", "dash_target": "Hadaf",
        "food_add": "Dakhal Akl", "photo_tab": "📸 Sowar", "text_tab": "✍️ Ketaba",
        "analyze_btn": "Hallel", "ai_working": "AI Beyfakar...", "add_btn": "Def", "what_eat": "Akalt eh?",
        "menu_title": "Menu El Naharda", "coach_btn": "🧠 Ra2y el Coach",
        "coach_prompt": "Enta doctor diet masri shater. Rod bel lahga el masreya (Egyptian Arabic).",
        "water_title": "💧 Mayya", "water_cup": "+200 ml", "water_bottle": "+500 ml", "water_remove": "Shil",
        "manual_add": "Edafa Yadawi", "weight_title": "⚖️ El Wazn", "save": "Hafez", "settings": "E3dadat el Profil",
        "update": "Gaded", "reset": "Ekhrog (Reset)", "lang_select": "El Logha / Language",
        "act_sedentary": "Antakh (Hareketsiz)", "act_light": "Noss Noss", "act_mod": "Haraka Helwa", "act_active": "Riyadi Gidan",
        "congrats": "YA GAMED!", "closing": "sawany...",
        "meal_breakfast": "Fetar", "meal_lunch": "Ghada", "meal_dinner": "3asha", "meal_snack": "Tasbira"
    }
}

# --- 3. VERİ YÖNETİMİ ---
DOSYA_ADI = "kullanici_verisi.json"

def veri_yukle():
    default_data = {
        "setup_tamamlandi": False,
        "profil": { 
            "isim": "Kullanıcı", "dil": "TR", 
            "cinsiyet": None, "yas": None, "boy": None, "kilo": None,
            "aktivite": None, "hedef_kilo": None
        },
        "streak": 0, "son_yemek_tarihi": "", "kilo_gecmisi": [],
        "su_takibi": {"tarih": "", "ml": 0}, "manuel_su_hedefi": None
    }
    if not os.path.exists(DOSYA_ADI): return default_data
    try:
        with open(DOSYA_ADI, "r") as f:
            data = json.load(f)
            for key in default_data:
                if key not in data: data[key] = default_data[key]
            if "dil" not in data["profil"]: data["profil"]["dil"] = "TR"
            return data
    except: return default_data

def veri_kaydet(data):
    with open(DOSYA_ADI, "w") as f: json.dump(data, f)

user_data = veri_yukle()
LANG = user_data["profil"]["dil"] 
TXT = T[LANG]

# --- 4. SESSION STATE ---
if 'gunluk_kayit' not in st.session_state: st.session_state['gunluk_kayit'] = {"Kahvaltı": [], "Öğle Yemeği": [], "Akşam Yemeği": [], "Ara Öğün": []}
if 'toplam_kalori' not in st.session_state: st.session_state['toplam_kalori'] = 0
if 'makrolar' not in st.session_state: st.session_state['makrolar'] = {"protein": 0, "yag": 0, "karb": 0}
if 'karanlik_mod' not in st.session_state: st.session_state['karanlik_mod'] = True
if 'kutlama_goster' not in st.session_state: st.session_state['kutlama_goster'] = False
if 'yeni_streak_sayisi' not in st.session_state: st.session_state['yeni_streak_sayisi'] = 0

bugun = date.today().strftime("%Y-%m-%d")
if user_data["su_takibi"]["tarih"] != bugun:
    user_data["su_takibi"] = {"tarih": bugun, "ml": 0}
    veri_kaydet(user_data)
if 'su_ml' not in st.session_state: st.session_state['su_ml'] = user_data["su_takibi"]["ml"]

# --- 5. CSS TASARIMI ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    
    .stApp { background-color: #0F1116; }
    header {visibility: hidden;}
    
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1A1D26; border: 1px solid #2D3342;
        border-radius: 16px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #0F1116 !important; color: white !important;
        border: 1px solid #2D3342 !important; border-radius: 10px !important;
    }
    input::placeholder { color: #6B7280 !important; opacity: 1 !important; }
    label, .stMarkdown p { color: #A0A0A0 !important; }
    
    div[data-testid="stRadio"] label {
        background-color: #1A1D26 !important; border: 1px solid #2D3342 !important;
        color: #A0A0A0 !important; padding: 10px 20px !important;
        border-radius: 20px !important; transition: all 0.3s; margin-right: 10px;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background-color: #7C3AED !important; color: white !important; border-color: #7C3AED !important;
    }
    div.stButton > button {
        background: linear-gradient(90deg, #7C3AED 0%, #5B21B6 100%);
        color: white; border: none; border-radius: 12px; padding: 15px; font-weight: 600; width: 100%;
    }
    div[data-testid="stFileUploader"] section { background-color: #1A1D26 !important; }
    .block-container { padding-top: 2rem !important; }
    
    .kutlama-overlay {
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background-color: rgba(0,0,0,0.85); backdrop-filter: blur(8px); z-index: 999999;
        display: flex; justify-content: center; align-items: center; flex-direction: column;
    }
    .k-baslik { font-size: 40px; font-weight: 900; color: white !important; margin: 0; }
    .k-sayi { font-size: 80px; font-weight: 900; color: #FFD700 !important; margin: 10px 0; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
#  ONBOARDING
# =========================================================
if not user_data["setup_tamamlandi"]:
    col_lang, _ = st.columns([1, 3])
    with col_lang:
        dil_secimi = st.selectbox("Language / Dil / اللغة", ["TR", "EN", "AR"])
        TXT_ONB = T[dil_secimi]

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem;'>⚡ Caloria</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; font-size: 1.1rem; color:#A0A0A0;'>{TXT_ONB['onboard_desc']}</p>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown(f"### {TXT_ONB['onboard_title']}")
        c_isim = st.text_input(TXT_ONB['name_ask'])
        st.write("")
        
        st.write(TXT_ONB['gender'])
        c_cinsiyet = st.radio("gizli", [TXT_ONB['male'], TXT_ONB['female']], horizontal=True, index=None, label_visibility="collapsed")
        
        c1, c2 = st.columns(2)
        with c1: c_yas = st.number_input(TXT_ONB['age'], 10, 100, value=None)
        with c2: c_boy = st.number_input(TXT_ONB['height'], 100, 250, value=None)
        c_kilo = st.number_input(TXT_ONB['weight'], 30.0, 200.0, value=None)
        
        st.write("")
        c_aktivite = st.selectbox(TXT_ONB['activity'], [TXT_ONB['act_sedentary'], TXT_ONB['act_light'], TXT_ONB['act_mod'], TXT_ONB['act_active']], index=None)
        c_hedef_kilo = st.number_input(TXT_ONB['target_weight'], 30.0, 200.0, value=None)
        
        st.write("")
        if st.button(TXT_ONB['start_btn']):
            if not c_isim or c_cinsiyet is None or c_yas is None or c_boy is None or c_kilo is None or c_aktivite is None or c_hedef_kilo is None:
                st.warning(TXT_ONB['missing_info'])
            else:
                user_data["profil"] = {
                    "isim": c_isim, "cinsiyet": c_cinsiyet, "yas": c_yas, 
                    "boy": c_boy, "kilo": c_kilo, "aktivite": c_aktivite, 
                    "hedef_kilo": c_hedef_kilo, "dil": dil_secimi 
                }
                user_data["kilo_gecmisi"] = [{"tarih": bugun, "kilo": c_kilo}]
                user_data["setup_tamamlandi"] = True
                veri_kaydet(user_data)
                st.rerun()
    st.stop()

# =========================================================
#  FONKSİYONLAR
# =========================================================
def streak_guncelle():
    d = veri_yukle(); s = d["streak"]; son = d["son_yemek_tarihi"]
    dun = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    yeni = False
    if son != bugun:
        if son == dun: s += 1
        else: s = 1
        d["streak"] = s; d["son_yemek_tarihi"] = bugun; veri_kaydet(d); yeni = True
    if yeni:
        st.session_state['kutlama_goster'] = True
        st.session_state['yeni_streak_sayisi'] = s

def kilo_ekle(k):
    d = veri_yukle(); g = d["kilo_gecmisi"]
    found = False
    for x in g:
        if x["tarih"] == bugun: x["kilo"] = k; found = True; break
    if not found: g.append({"tarih": bugun, "kilo": k})
    d["kilo_gecmisi"] = g; d["profil"]["kilo"] = k
    veri_kaydet(d)
    st.toast("OK!", icon="✅")

def hesapla_hedef(p):
    bmr = (10*p["kilo"]) + (6.25*p["boy"]) - (5*p["yas"])
    erkek_listesi = ["Erkek", "Male", "Ragel"]
    if p["cinsiyet"] in erkek_listesi: bmr += 5
    else: bmr -= 161
    tdee = bmr * 1.375 
    if p["hedef_kilo"] < p["kilo"]: return int(tdee - 500)
    elif p["hedef_kilo"] > p["kilo"]: return int(tdee + 500)
    return int(tdee)

# --- 🔥 GÜNCELLENMİŞ VE SAĞLAMLAŞTIRILMIŞ AI ANALİZ ---
def ai_analiz(prompt, img=None):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # PROMPT GÜNCELLEMESİ: Kesinlikle sayısal format zorluyoruz
        lang_prompt = f"Answer in {LANG}. " if LANG != "AR" else "Answer in Egyptian Arabic context, but KEEP NUMBERS AS STANDARD ENGLISH DIGITS (0-9). "
        
        full_prompt = lang_prompt + prompt + """
        IMPORTANT: 
        - Return ONLY JSON.
        - Use integer numbers for calories and macros (e.g., 200, not '٢٠٠').
        - Do not include any explanations.
        """
        
        inp = [full_prompt, img] if img else [full_prompt]
        res = model.generate_content(inp)
        
        text = res.text
        # Temizlik
        if "```json" in text: text = text.replace("```json", "").replace("```", "")
        elif "```" in text: text = text.replace("```", "")
        
        start = text.find('{'); end = text.rfind('}') + 1
        if start != -1 and end != 0: 
            json_data = json.loads(text[start:end])
            
            # Veri doğrulama: Eğer kalori string gelirse int'e çevir
            if 'kalori' in json_data:
                try:
                    json_data['kalori'] = int(str(json_data['kalori']).replace("kcal", "").strip())
                except:
                    json_data['kalori'] = 0
            
            return json_data
        else: 
            raise ValueError("JSON yok")
    except Exception as e:
        print(f"Hata: {e}") # Konsola yaz
        return {"yemek_adi": "Error / Hata", "kalori": 0, "protein": 0, "yag": 0, "karbonhidrat": 0}

def yemek_ekle(ogun, data):
    # Eğer kalori 0 geldiyse ekleme ve uyarı ver
    if int(data.get('kalori') or 0) == 0:
        st.error("Besin değerleri okunamadı veya 0 geldi. Lütfen tekrar deneyin.")
        return

    st.session_state['gunluk_kayit'][ogun].append(data)
    st.session_state['toplam_kalori'] += int(data.get('kalori') or 0)
    st.session_state['makrolar']['protein'] += int(data.get('protein') or 0)
    st.session_state['makrolar']['yag'] += int(data.get('yag') or 0)
    st.session_state['makrolar']['karb'] += int(data.get('karbonhidrat') or 0)
    streak_guncelle()

def su_guncelle(miktar):
    st.session_state['su_ml'] += miktar
    if st.session_state['su_ml'] < 0: st.session_state['su_ml'] = 0
    data = veri_yukle()
    data["su_takibi"] = {"tarih": date.today().strftime("%Y-%m-%d"), "ml": st.session_state['su_ml']}
    veri_kaydet(data)

# --- Hesaplamalar ---
profil = user_data["profil"]
HEDEF = hesapla_hedef(profil)
kalan = HEDEF - st.session_state['toplam_kalori']
mevcut_streak = user_data["streak"]
kullanici_adi = profil.get("isim", "User")

# --- KUTLAMA ---
if st.session_state['kutlama_goster']:
    kp = st.empty()
    for i in range(3, 0, -1):
        y = int((i/3)*100)
        kp.markdown(f"""
        <div class="kutlama-overlay"><div class="kutlama-kutu">
        <div class="k-baslik">{TXT['congrats']} 🎉</div>
        <div class="k-sayi">🔥 {st.session_state['yeni_streak_sayisi']} {TXT['streak']}</div>
        <div style="width:100%; height:10px; background:rgba(255,255,255,0.2); border-radius:5px; margin-top:20px; overflow:hidden;">
        <div style="width:{y}%; height:100%; background:#FFD700; transition:width 0.5s;"></div></div>
        <p style="color:white; margin-top:10px;">{TXT['closing']}</p>
        </div></div>""", unsafe_allow_html=True)
        if i==3: st.balloons()
        time.sleep(1)
    st.session_state['kutlama_goster'] = False
    st.rerun()

# --- HEADER & NAV ---
st.markdown(f"<h3 style='text-align:center; color:#E0E0E0; font-weight:300;'>{TXT['welcome']}, <span style='color:#7C3AED; font-weight:600;'>{kullanici_adi}</span> 👋</h3>", unsafe_allow_html=True)
st.write(""); st.write("") 

nav_options = [TXT['menu_title'], TXT['water_title'] + " & " + TXT['weight_title'], TXT['settings']]
nav = st.radio("", nav_options, horizontal=True, label_visibility="collapsed")

st.markdown(f"<div style='text-align:right; font-size:14px; margin-top:-45px; color:#A0A0A0;'>🔥 {mevcut_streak} {TXT['streak']}</div>", unsafe_allow_html=True)
st.write("")

# --- SAYFA 1: ANA SAYFA ---
if nav == nav_options[0]: 
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c1: st.markdown(f"<p style='text-align:center; margin:0;'>{TXT['dash_intake']}</p><h2 style='text-align:center; color:white;'>{st.session_state['toplam_kalori']}</h2>", unsafe_allow_html=True)
    with c2:
        renk = "#10B981" if kalan > 0 else "#EF4444"
        st.markdown(f"<h1 style='text-align:center; margin:0; font-size:3.5rem; color:{renk};'>{kalan}</h1><p style='text-align:center;'>{TXT['dash_remain']}</p>", unsafe_allow_html=True)
    with c3: st.markdown(f"<p style='text-align:center; margin:0;'>{TXT['dash_target']}</p><h2 style='text-align:center; color:white;'>{HEDEF}</h2>", unsafe_allow_html=True)
    st.write("")
    h_p, h_y, h_k = int(profil["kilo"]*1.8), int((HEDEF*0.3)/9), int((HEDEF-(profil["kilo"]*1.8*4 + HEDEF*0.3))/4)
    m1, m2, m3 = st.columns(3)
    with m1: st.progress(min(st.session_state['makrolar']['protein']/h_p, 1.0)); st.caption(f"Pro: {st.session_state['makrolar']['protein']}/{h_p}g")
    with m2: st.progress(min(st.session_state['makrolar']['yag']/h_y, 1.0)); st.caption(f"Fat: {st.session_state['makrolar']['yag']}/{h_y}g")
    with m3: st.progress(min(st.session_state['makrolar']['karb']/h_k, 1.0)); st.caption(f"Carb: {st.session_state['makrolar']['karb']}/{h_k}g")
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader(TXT['food_add'])
    with st.container(border=True):
        tab1, tab2 = st.tabs([TXT['photo_tab'], TXT['text_tab']])
        oguns = [TXT['meal_breakfast'], TXT['meal_lunch'], TXT['meal_dinner'], TXT['meal_snack']]
        ogun_keys = ["Kahvaltı", "Öğle Yemeği", "Akşam Yemeği", "Ara Öğün"]
        
        with tab1:
            img = st.file_uploader(" ", type=["jpg","png","webp"], label_visibility="collapsed")
            ogun_idx = st.selectbox(TXT['food_add'], oguns, key="o1")
            real_ogun = ogun_keys[oguns.index(ogun_idx)]
            if img and st.button(TXT['analyze_btn']):
                with st.spinner(TXT['ai_working']):
                    d = ai_analiz('JSON: {"yemek_adi": "str", "kalori": int, "protein": int, "yag": int, "karbonhidrat": int}', Image.open(img))
                    yemek_ekle(real_ogun, d); st.rerun()
        with tab2:
            txt = st.text_input(TXT['what_eat'])
            ogun_idx2 = st.selectbox(TXT['food_add'], oguns, key="o2")
            real_ogun2 = ogun_keys[oguns.index(ogun_idx2)]
            if st.button(TXT['add_btn']):
                with st.spinner("..."):
                    d = ai_analiz(f'Food: {txt}. JSON: {{"yemek_adi": "str", "kalori": int, "protein": int, "yag": int, "karbonhidrat": int}}')
                    yemek_ekle(real_ogun2, d); st.rerun()

    st.subheader(TXT['menu_title'])
    for o_key, o_label in zip(ogun_keys, oguns):
        l = st.session_state['gunluk_kayit'][o_key]
        if l:
            toplam_kal = sum(int(x.get('kalori') or 0) for x in l)
            st.markdown(f"**{o_label}** <span style='color:gray; font-size:12px'>{toplam_kal} kcal</span>", unsafe_allow_html=True)
            for x in l:
                ad = x.get('yemek_adi', 'Bilinmeyen Yemek')
                kal = int(x.get('kalori') or 0)
                st.markdown(f"<div style='background:#1A1D26; padding:10px; border-radius:10px; margin-bottom:5px; display:flex; justify-content:space-between; border:1px solid #2D3342;'><span>{ad}</span><span style='color:#7C3AED; font-weight:bold;'>{kal}</span></div>", unsafe_allow_html=True)
    st.write("")
    if st.session_state['toplam_kalori'] > 0:
        if st.button(TXT['coach_btn']):
            with st.spinner("..."):
                try:
                    p = TXT['coach_prompt'] + f" Target: {HEDEF}. Eaten: {st.session_state['gunluk_kayit']}"
                    res = genai.GenerativeModel('gemini-2.0-flash').generate_content(p)
                    st.info(res.text)
                except: st.error("Error")

# --- SAYFA 2: SU & KİLO ---
elif nav == nav_options[1]:
    c_su, c_kilo = st.columns(2)
    with c_su:
        st.subheader(TXT['water_title'])
        with st.container(border=True):
            hedef_su = user_data.get("manuel_su_hedefi") or int(profil["kilo"] * 35)
            icerilen = st.session_state['su_ml']
            st.markdown(f"<h1 style='text-align:center; color:#3B82F6; margin:0;'>{icerilen}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align:center; margin:0;'>/ {hedef_su} ml</p>", unsafe_allow_html=True)
            st.progress(min(icerilen/hedef_su, 1.0))
            st.write("")
            c_a, c_b = st.columns(2)
            if c_a.button(TXT['water_cup']): su_guncelle(200); st.rerun()
            if c_b.button(TXT['water_remove']): su_guncelle(-200); st.rerun()
            with st.expander(TXT['manual_add']):
                ms = st.number_input("ml", 0, 2000, 200, label_visibility="collapsed")
                if st.button(TXT['add_btn'], key="su_ekle"): su_guncelle(ms); st.rerun()

    with c_kilo:
        st.subheader(TXT['weight_title'])
        with st.container(border=True):
            kg = st.number_input(TXT['weight'], value=float(profil["kilo"]), step=0.1)
            if st.button(TXT['save']): kilo_ekle(kg); st.rerun()
            if user_data["kilo_gecmisi"]:
                df = pd.DataFrame(user_data["kilo_gecmisi"])
                df["tarih"] = pd.to_datetime(df["tarih"])
                st.line_chart(df.set_index("tarih"), height=150, color="#7C3AED")

# --- SAYFA 3: PROFIL ---
elif nav == nav_options[2]:
    st.subheader(TXT['settings'])
    with st.container(border=True):
        yeni_dil = st.selectbox(TXT['lang_select'], ["TR", "EN", "AR"], index=["TR", "EN", "AR"].index(LANG))
        n_isim = st.text_input(TXT['name_ask'], value=profil.get("isim", ""))
        n_kilo = st.number_input(TXT['weight'], value=float(profil["kilo"]))
        n_hedef = st.number_input(TXT['target_weight'], value=float(profil["hedef_kilo"]))
        
        if st.button(TXT['update']):
            user_data["profil"].update({"isim":n_isim, "kilo":n_kilo, "hedef_kilo":n_hedef, "dil":yeni_dil})
            kilo_ekle(n_kilo)
            veri_kaydet(user_data)
            st.success("OK!")
            time.sleep(1); st.rerun()
        st.divider()
        if st.button(TXT['reset'], type="secondary"): os.remove(DOSYA_ADI); st.rerun()
