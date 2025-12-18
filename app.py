import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import os
import time
from google.api_core import exceptions

# --- 1. API Configuration ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("⚠️ API Key not found in Secrets!")
    st.stop()

# --- 2. Smart Model Discovery ---
@st.cache_resource
def get_available_model():
    """يكتشف الموديلات المتاحة في حسابك لتجنب خطأ 404"""
    try:
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # الأولوية لـ Flash لسرعته، ثم Pro
        for target in ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-pro"]:
            if target in models:
                return target
        return models[0] if models else None
    except Exception as e:
        st.error(f"Failed to list models: {e}")
        return None

# --- 3. UI Styling ---
st.set_page_config(page_title="Flexi Academy AI Tutor", layout="wide")
st.markdown("""
    <style>
    :root { --flexi-blue: #1e3a8a; --flexi-orange: #f97316; }
    .lesson-box { padding: 25px; border-radius: 15px; background: white; border-left: 5px solid var(--flexi-blue); margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); color: #333; }
    .quiz-container { background-color: #f8fafc; padding: 20px; border-radius: 15px; border: 1px solid #e2e8f0; margin-bottom: 15px; }
    .stProgress > div > div > div > div { background-color: var(--flexi-orange); }
    img { border-radius: 12px; margin: 15px 0; width: 100%; max-height: 400px; object-fit: contain; background: #f1f5f9; }
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- 4. Session State ---
if 'lesson_content' not in st.session_state: st.session_state.lesson_content = None
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = []
if 'user_scores' not in st.session_state: st.session_state.user_scores = {}
if 'total_points' not in st.session_state: st.session_state.total_points = 0

# --- 5. Sidebar ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=200)
    st.header("👤 Profile")
    name = st.text_input("Name:", "Learner")
    age = st.number_input("Age:", 5, 100, 12)
    gender = st.selectbox("Gender:", ["Male", "Female"])
    level = st.selectbox("Academic Level:", ["Beginner", "Intermediate", "Advanced"])
    lang = st.selectbox("Language:", ["English", "العربية", "Français"])
    style = st.selectbox("Learning Style:", ["Visual (6+ Images)", "Auditory", "Kinesthetic"])
    path = st.radio("Path:", ["Standard Lesson", "Comic Story"])
    
    st.divider()
    st.progress(min(st.session_state.total_points, 100) / 100)
    st.metric("Flexi Points 🎯", st.session_state.total_points)
    
    st.components.v1.html("""
        <button onclick="window.print()" style="width:100%; background:#f97316; color:white; border:none; padding:10px; font-weight:bold; border-radius:8px; cursor:pointer;">🖨️ Print Lesson (PDF)</button>
    """, height=50)

# --- 6. Generation Logic ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_area("What do you want to learn?", placeholder="e.g., How stars are born")

chosen_model = get_available_model()

if st.button("Generate Lesson 🚀"):
    if not topic or not chosen_model:
        st.error("Topic empty or No models found!")
    else:
        try:
            model = genai.GenerativeModel(chosen_model)
            prompt = f"""
            Tutor: Flexi Academy. Student: {name}, {gender}, {age}. Level: {level}.
            Language: {lang}. Style: {style}. Path: {path}. Topic: {topic}.
            
            STRUCTURE:
            1. Lesson Content: If Visual, include 6 [[detailed image prompt]] tags.
            2. Assessment: Mandatory 'START_QUIZ' separator. Then 5 MCQs as:
               Q: [Question] | A: [Opt1] | B: [Opt2] | C: [Opt3] | Correct: [Letter] | Expl: [Why]
            """
            
            with st.spinner(f'Using {chosen_model}... Building lesson...'):
                response_text = ""
                for attempt in range(3):
                    try:
                        resp = model.generate_content(prompt)
                        response_text = resp.text
                        break
                    except exceptions.ResourceExhausted:
                        time.sleep(5)
                
                if response_text:
                    main_txt, quiz_txt = response_text.split('START_QUIZ') if 'START_QUIZ' in response_text else (response_text, "")
                    st.session_state.lesson_content = main_txt
                    st.session_state.quiz_data = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz_txt)
                    st.session_state.user_scores = {}
                    st.session_state.total_points = 0
                    
                    audio_txt = re.sub(r'\[\[.*?\]\]', '', main_txt[:800])
                    tts = gTTS(text=audio_txt, lang='ar' if lang=='العربية' else 'en')
                    tts.save("voice.mp3")
                    st.rerun()
        except Exception as e:
            st.error(f"Error with {chosen_model}: {e}")

# --- 7. Rendering Content ---
if st.session_state.lesson_content:
    if os.path.exists("voice.mp3"): st.audio("voice.mp3")
    
    st.markdown(f'<div style="direction:{"rtl" if lang == "العربية" else "ltr"}">', unsafe_allow_html=True)
    segments = re.split(r'\[\[(.*?)\]\]', st.session_state.lesson_content)
    for i, seg in enumerate(segments):
        if i % 2 == 0:
            if seg.strip(): st.markdown(f'<div class="lesson-box">{seg.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.image(f"https://pollinations.ai/p/{seg.replace(' ', '%20')}?width=800&height=400&seed={i}")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 8. Interactive Quiz ---
    st.divider()
    st.header("🧠 Knowledge Challenge")
    for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz_data):
        qid = f"q_{idx}"
        with st.container():
            st.markdown(f'<div class="quiz-container">', unsafe_allow_html=True)
            st.write(f"**Q{idx+1}:** {q.strip()}")
            ans = st.radio("Select:", [f"A: {a}", f"B: {b}", f"C: {c}"], key=f"r_{idx}")
            if st.button(f"Submit Q{idx+1}", key=f"b_{idx}"):
                if qid not in st.session_state.user_scores:
                    is_correct = ans[0].upper() == correct.strip()[0].upper()
                    st.session_state.user_scores[qid] = {"res": is_correct, "expl": expl, "c": correct}
                    if is_correct: st.session_state.total_points += 20
                    st.rerun()
            if qid in st.session_state.user_scores:
                r = st.session_state.user_scores[qid]
                if r["res"]: st.success("🌟 Correct!")
                else: st.error(f"❌ Correct is {r['c']}. {r['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.total_points >= 100:
        st.balloons()
        st.success("🏆 Perfect Score!")
