import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import os
from datetime import date, timedelta
import time
import pandas as pd

# --- 1. KONFİGÜRASYON ---
API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=API_KEY)

st.set_page_config(page_title="FitAI Pro", page_icon="🔥", layout="centered")

# --- 2. VERİ YÖNETİMİ ---
DOSYA_ADI = "kullanici_verisi.json"

def veri_yukle():
    default_data = {
        "setup_tamamlandi": False,
        "profil": { 
            "isim": "Kullanıcı", 
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
            if "isim" not in data["profil"]: data["profil"]["isim"] = "Kullanıcı"
            return data
    except: return default_data

def veri_kaydet(data):
    with open(DOSYA_ADI, "w") as f: json.dump(data, f)

user_data = veri_yukle()

# --- 3. SESSION STATE ---
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

# --- 4. CSS TASARIMI (DÜZELTİLDİ) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    
    .stApp { background-color: #0F1116; }
    header {visibility: hidden;}
    
    /* Kart */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #1A1D26;
        border: 1px solid #2D3342;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Inputlar */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #0F1116 !important;
        color: white !important;
        border: 1px solid #2D3342 !important;
        border-radius: 10px !important;
    }
    
    /* Placeholder Rengi (Daha Görünür) */
    input::placeholder {
        color: #6B7280 !important;
        opacity: 1 !important;
    }
    
    /* Yazılar */
    label, .stMarkdown p { color: #A0A0A0 !important; }
    
    /* --- RADIO BUTTON DÜZELTMESİ --- */
    /* Sadece seçeneklerin (Erkek/Kadın) etrafını boya, başlığı elleme */
    div[role="radiogroup"] label {
        background-color: #0F1116 !important;
        border: 1px solid #2D3342 !important;
        color: #A0A0A0 !important;
        padding: 10px 20px !important;
        border-radius: 20px !important;
        transition: all 0.3s;
        margin-right: 10px;
    }
    /* Seçili Olan */
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: #7C3AED !important;
        color: white !important;
        border-color: #7C3AED !important;
    }

    /* Butonlar */
    div.stButton > button {
        background: linear-gradient(90deg, #7C3AED 0%, #5B21B6 100%);
        color: white; border: none; border-radius: 12px; padding: 15px; font-weight: 600;
        width: 100%; border: none !important;
    }
    
    div[data-testid="stFileUploader"] section { background-color: #1A1D26 !important; }
    .block-container { padding-top: 2rem !important; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
#  🚀 ONBOARDING (DÜZELTİLDİ: BOŞ KUTULAR + DOĞRU YAZILAR)
# =========================================================
if not user_data["setup_tamamlandi"]:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem;'>⚡ FitAI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.1rem; color:#A0A0A0;'>Seni tanımamız için son bir adım.</p>", unsafe_allow_html=True)
    
    with st.container(border=True):
        st.markdown("### 👋 Seni Tanıyalım")
        c_isim = st.text_input("Sana nasıl hitap edelim?", placeholder="Örn: Ahmet")
        
        st.write("")
        st.markdown("### 🧬 Fiziksel Bilgiler")
        
        # CİNSİYET BAŞLIĞI DÜZELDİ: Manuel yazı ekledik
        st.write("Cinsiyet")
        c_cinsiyet = st.radio("Gizli Başlık", ["Erkek", "Kadın"], horizontal=True, index=None, label_visibility="collapsed")
        
        st.write("")
        # VALUE=NONE YAPARAK KUTULARI BOŞALTTIM
        c_yas = st.number_input("Yaşın", min_value=10, max_value=100, value=None, placeholder="Örn: 25")
        
        c1, c2 = st.columns(2)
        with c1: 
            c_boy = st.number_input("Boy (cm)", min_value=100, max_value=250, value=None, placeholder="Örn: 175")
        with c2: 
            c_kilo = st.number_input("Mevcut Kilo (kg)", min_value=30.0, max_value=200.0, value=None, placeholder="Örn: 75.0")
        
        st.write("")
        st.markdown("### 🎯 Hedefler")
        c_aktivite = st.selectbox("Günlük Aktivite", ["Hareketsiz", "Az Hareketli", "Orta Hareketli", "Çok Hareketli"], index=None, placeholder="Seçiniz...")
        
        c_hedef_kilo = st.number_input("🎯 Hedef Kilo (kg)", min_value=30.0, max_value=200.0, value=None, placeholder="Örn: 70.0")
        
        st.write("")
        if st.button("Başla 🚀"):
            if not c_isim or c_cinsiyet is None or c_yas is None or c_boy is None or c_kilo is None or c_aktivite is None or c_hedef_kilo is None:
                st.warning("⚠️ Lütfen ismini ve tüm bilgileri gir.")
            else:
                user_data["profil"] = {
                    "isim": c_isim, "cinsiyet": c_cinsiyet, "yas": c_yas, 
                    "boy": c_boy, "kilo": c_kilo, "aktivite": c_aktivite, 
                    "hedef_kilo": c_hedef_kilo
                }
                user_data["kilo_gecmisi"] = [{"tarih": bugun, "kilo": c_kilo}]
                user_data["setup_tamamlandi"] = True
                veri_kaydet(user_data)
                st.rerun()
    st.stop()

# =========================================================
#  ANA UYGULAMA
# =========================================================

# --- Fonksiyonlar ---
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
    st.toast("Güncellendi", icon="✅")

def hesapla_hedef(p):
    bmr = (10*p["kilo"]) + (6.25*p["boy"]) - (5*p["yas"]) + (5 if p["cinsiyet"]=="Erkek" else -161)
    act = {"Hareketsiz": 1.2, "Az Hareketli": 1.375, "Orta Hareketli": 1.55, "Çok Hareketli": 1.725}
    tdee = bmr * act[p["aktivite"]]
    if p["hedef_kilo"] < p["kilo"]: return int(tdee - 500)
    elif p["hedef_kilo"] > p["kilo"]: return int(tdee + 500)
    return int(tdee)

def ai_analiz(prompt, img=None):
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        inp = [prompt, img] if img else [prompt]
        res = model.generate_content(inp)
        
        text = res.text
        if "```json" in text:
            text = text.replace("```json", "").replace("```", "")
        elif "```" in text:
            text = text.replace("```", "")
            
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end != 0:
            json_str = text[start:end]
            return json.loads(json_str)
        else:
            raise ValueError("AI JSON formatında yanıt vermedi.")
            
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return {"yemek_adi": "Hata", "kalori": 0, "protein": 0, "yag": 0, "karbonhidrat": 0}

def yemek_ekle(ogun, data):
    st.session_state['gunluk_kayit'][ogun].append(data)
    st.session_state['toplam_kalori'] += data.get('kalori', 0)
    st.session_state['makrolar']['protein'] += data.get('protein', 0)
    st.session_state['makrolar']['yag'] += data.get('yag', 0)
    st.session_state['makrolar']['karb'] += data.get('karbonhidrat', 0)
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
kullanici_adi = profil.get("isim", "Kullanıcı")

# --- KUTLAMA ---
if st.session_state['kutlama_goster']:
    kp = st.empty()
    for i in range(3, 0, -1):
        y = int((i/3)*100)
        kp.markdown(f"""
        <div class="kutlama-overlay">
        <div class="kutlama-kutu">
        <div class="k-baslik">HARİKASIN! 🎉</div>
        <div class="k-alt">İstikrarlı ilerliyorsun</div>
        <div class="k-sayi">🔥 {st.session_state['yeni_streak_sayisi']} GÜN</div>
        <div style="width:100%; height:10px; background:rgba(255,255,255,0.2); border-radius:5px; margin-top:20px; overflow:hidden;">
        <div style="width:{y}%; height:100%; background:#FFD700; transition:width 0.5s;"></div>
        </div></div></div>
        """, unsafe_allow_html=True)
        if i==3: st.balloons()
        time.sleep(1)
    st.session_state['kutlama_goster'] = False
    st.rerun()

# --- HEADER ---
st.markdown(f"<h3 style='text-align:center; color:#E0E0E0; font-weight:300;'>Hoş geldin, <span style='color:#7C3AED; font-weight:600;'>{kullanici_adi}</span> 👋</h3>", unsafe_allow_html=True)
st.write("") 
st.write("") 

nav = st.radio("", ["Ana Sayfa", "Su & Kilo", "Profil"], horizontal=True, label_visibility="collapsed")

st.markdown(f"<div style='text-align:right; font-size:14px; margin-top:-45px; color:#A0A0A0;'>🔥 {mevcut_streak} Gün</div>", unsafe_allow_html=True)
st.write("")

# ==================== SAYFALAR ====================

if nav == "Ana Sayfa":
    st.markdown('<div class="modern-card">', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c1: 
        st.markdown("<p style='text-align:center; margin:0;'>Alınan</p>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center; margin:0; color:white;'>{st.session_state['toplam_kalori']}</h2>", unsafe_allow_html=True)
    with c2:
        renk = "#10B981" if kalan > 0 else "#EF4444"
        st.markdown(f"<h1 style='text-align:center; margin:0; font-size:3.5rem; color:{renk};'>{kalan}</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; margin:0;'>KALAN</p>", unsafe_allow_html=True)
    with c3:
        st.markdown("<p style='text-align:center; margin:0;'>Hedef</p>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center; margin:0; color:white;'>{HEDEF}</h2>", unsafe_allow_html=True)
    
    st.write("")
    h_p, h_y, h_k = int(profil["kilo"]*1.8), int((HEDEF*0.3)/9), int((HEDEF-(profil["kilo"]*1.8*4 + HEDEF*0.3))/4)
    m1, m2, m3 = st.columns(3)
    with m1: st.progress(min(st.session_state['makrolar']['protein']/h_p, 1.0)); st.caption(f"Protein: {st.session_state['makrolar']['protein']}/{h_p}g")
    with m2: st.progress(min(st.session_state['makrolar']['yag']/h_y, 1.0)); st.caption(f"Yağ: {st.session_state['makrolar']['yag']}/{h_y}g")
    with m3: st.progress(min(st.session_state['makrolar']['karb']/h_k, 1.0)); st.caption(f"Karb: {st.session_state['makrolar']['karb']}/{h_k}g")
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Yemek Ekle")
    with st.container(border=True):
        tab1, tab2 = st.tabs(["📸 Fotoğraf", "✍️ Yazı"])
        with tab1:
            img = st.file_uploader(" ", type=["jpg","png","webp"], label_visibility="collapsed")
            ogun = st.selectbox("Öğün", ["Kahvaltı", "Öğle", "Akşam", "Ara"], key="o1")
            if img and st.button("Analiz Et"):
                with st.spinner("AI Çalışıyor..."):
                    d = ai_analiz('JSON: {"yemek_adi": "str", "kalori": int, "protein": int, "yag": int, "karbonhidrat": int}', Image.open(img))
                    if d.get("kalori") != 0:
                        yemek_ekle(ogun, d); st.rerun()
        with tab2:
            txt = st.text_input("Ne yedin?", placeholder="Örn: 1 Muz")
            ogun2 = st.selectbox("Öğün", ["Kahvaltı", "Öğle", "Akşam", "Ara"], key="o2")
            if st.button("Ekle"):
                with st.spinner("Hesaplanıyor..."):
                    d = ai_analiz(f'Yemek: {txt}. JSON: {{"yemek_adi": "str", "kalori": int, "protein": int, "yag": int, "karbonhidrat": int}}')
                    if d.get("kalori") != 0:
                        yemek_ekle(ogun2, d); st.rerun()

    st.subheader("Menü")
    for o, l in st.session_state['gunluk_kayit'].items():
        if l:
            st.markdown(f"**{o}** <span style='color:gray; font-size:12px'>{sum(x.get('kalori',0) for x in l)} kcal</span>", unsafe_allow_html=True)
            for x in l:
                st.markdown(f"""
                <div style="background:#1A1D26; padding:10px; border-radius:10px; margin-bottom:5px; display:flex; justify-content:space-between; border:1px solid #2D3342;">
                    <span>{x.get('yemek_adi', 'Yemek')}</span>
                    <span style="color:#7C3AED; font-weight:bold;">{x.get('kalori',0)}</span>
                </div>
                """, unsafe_allow_html=True)
    
    st.write("")
    if st.session_state['toplam_kalori'] > 0:
        if st.button("🧠 AI Koç Analizi"):
            with st.spinner("Analiz..."):
                try:
                    model_koc = genai.GenerativeModel('gemini-2.0-flash')
                    res_koc = model_koc.generate_content(f"Diyetisyen rolünde kısa yorum yap. Hedef: {HEDEF}, Yenenler: {st.session_state['gunluk_kayit']}")
                    st.info(res_koc.text)
                except: st.error("Koç şu an cevap veremiyor.")

elif nav == "Su & Kilo":
    c_su, c_kilo = st.columns(2)
    with c_su:
        st.subheader("Su Takibi")
        with st.container(border=True):
            hedef_su = user_data.get("manuel_su_hedefi") or int(profil["kilo"] * 35)
            icerilen = st.session_state['su_ml']
            st.markdown(f"<h1 style='text-align:center; color:#3B82F6; margin:0;'>{icerilen}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align:center; margin:0;'>/ {hedef_su} ml</p>", unsafe_allow_html=True)
            st.progress(min(icerilen/hedef_su, 1.0))
            st.write("")
            c_a, c_b = st.columns(2)
            if c_a.button("+200ml"): su_guncelle(200); st.rerun()
            if c_b.button("-200ml"): su_guncelle(-200); st.rerun()
            
            with st.expander("Manuel"):
                ms = st.number_input("ml", 0, 2000, 200, label_visibility="collapsed")
                if st.button("Ekle"): su_guncelle(ms); st.rerun()

    with c_kilo:
        st.subheader("Kilo Takibi")
        with st.container(border=True):
            kg = st.number_input("Güncel Kilo", value=float(profil["kilo"]), step=0.1)
            if st.button("Kaydet"): kilo_ekle(kg); st.rerun()
            if user_data["kilo_gecmisi"]:
                df = pd.DataFrame(user_data["kilo_gecmisi"])
                df["tarih"] = pd.to_datetime(df["tarih"])
                st.line_chart(df.set_index("tarih"), height=150, color="#7C3AED")

elif nav == "Profil":
    st.subheader("Profil")
    with st.container(border=True):
        n_isim = st.text_input("İsim", value=profil.get("isim", ""))
        n_kilo = st.number_input("Kilo", value=float(profil["kilo"]))
        n_hedef = st.number_input("Hedef Kilo", value=float(profil["hedef_kilo"]))
        n_aktivite = st.selectbox("Aktivite", ["Hareketsiz", "Az Hareketli", "Orta Hareketli", "Çok Hareketli"], index=["Hareketsiz", "Az Hareketli", "Orta Hareketli", "Çok Hareketli"].index(profil["aktivite"]))
        
        if st.button("Güncelle"):
            user_data["profil"].update({"isim":n_isim, "kilo":n_kilo, "hedef_kilo":n_hedef, "aktivite":n_aktivite})
            kilo_ekle(n_kilo)
            st.success("Güncellendi!")
            time.sleep(1); st.rerun()
            
        st.divider()
        if st.button("Sıfırla (Çıkış)", type="secondary"):
            os.remove(DOSYA_ADI)
            st.rerun()