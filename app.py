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

# --- 2. Professional UI Styling ---
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

# --- 3. Session State Initialization ---
if 'lesson_content' not in st.session_state: st.session_state.lesson_content = None
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = []
if 'user_scores' not in st.session_state: st.session_state.user_scores = {}
if 'total_points' not in st.session_state: st.session_state.total_points = 0

# --- 4. Sidebar ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=200)
    st.header("👤 Student Profile")
    name = st.text_input("Name:", "Learner")
    age = st.number_input("Age:", 5, 100, 12)
    gender = st.selectbox("Gender:", ["Male", "Female"])
    level = st.selectbox("Academic Level:", ["Beginner", "Intermediate", "Advanced"])
    lang = st.selectbox("Content Language:", ["English", "العربية", "Français"])
    style = st.selectbox("Learning Style:", ["Visual (6+ Images)", "Auditory", "Kinesthetic"])
    path = st.radio("Learning Path:", ["Standard Lesson", "Comic Story"])
    
    st.divider()
    st.subheader("📊 Progress")
    st.progress(min(st.session_state.total_points, 100) / 100)
    st.metric("Flexi Points 🎯", st.session_state.total_points)
    
    st.divider()
    st.components.v1.html("""
        <button onclick="window.print()" style="width:100%; background:#f97316; color:white; border:none; padding:10px; font-weight:bold; border-radius:8px; cursor:pointer;">🖨️ Print Lesson (PDF)</button>
    """, height=50)

# --- 5. Logic with Dynamic Model Selection ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_area("What would you like to learn?", placeholder="e.g., Quantum Physics simplified")

if st.button("Generate Experience 🚀"):
    if not topic:
        st.error("Please enter a topic!")
    else:
        try:
            # FIX: Trying multiple model naming conventions to avoid 404
            model = None
            for model_name in ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-pro"]:
                try:
                    model = genai.GenerativeModel(model_name)
                    # Test a small generation to verify model existence
                    model.generate_content("test", generation_config={"max_output_tokens": 1})
                    break 
                except:
                    continue
            
            if not model:
                st.error("Could not connect to any Gemini models. Please check your API key.")
                st.stop()

            prompt = f"""
            Role: Expert Tutor at Flexi Academy. Student: {name}, {gender}, {age} years old.
            Language: {lang}. Style: {style}. Path: {path}. Topic: {topic}. Level: {level}.
            
            STRUCTURE:
            1. Lesson Text: Personalize content. If visual style, insert exactly 6 [[detailed image prompt]] tags.
            2. Assessment: Mandatory separator 'START_QUIZ'. Then 5 questions exactly as:
               Q: [Question] | A: [Opt1] | B: [Opt2] | C: [Opt3] | Correct: [Letter] | Expl: [Why]
            """
            
            success = False
            with st.spinner('Flexi is building your lesson...'):
                for attempt in range(3):
                    try:
                        resp = model.generate_content(prompt)
                        response_text = resp.text
                        success = True
                        break
                    except exceptions.ResourceExhausted:
                        time.sleep((attempt + 1) * 5)
                
                if success:
                    main_txt, quiz_txt = response_text.split('START_QUIZ') if 'START_QUIZ' in response_text else (response_text, "")
                    st.session_state.lesson_content = main_txt
                    st.session_state.quiz_data = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz_txt)
                    st.session_state.user_scores = {}
                    st.session_state.total_points = 0
                    
                    audio_clean = re.sub(r'\[\[.*?\]\]', '', main_txt[:800]).strip()
                    tts = gTTS(text=audio_clean, lang='ar' if lang=='العربية' else 'en')
                    tts.save("voice.mp3")
                    st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 6 & 7. Rendering & Quiz (كما هي في النسخة المستقرة) ---
if st.session_state.lesson_content:
    if os.path.exists("voice.mp3"):
        st.audio("voice.mp3")
    
    st.markdown(f'<div style="direction:{"rtl" if lang == "العربية" else "ltr"}">', unsafe_allow_html=True)
    segments = re.split(r'\[\[(.*?)\]\]', st.session_state.lesson_content)
    for i, seg in enumerate(segments):
        if i % 2 == 0:
            if seg.strip(): st.markdown(f'<div class="lesson-box">{seg.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.image(f"https://pollinations.ai/p/{seg.replace(' ', '%20')}?width=800&height=400&seed={i}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.divider()
    st.header("🧠 Knowledge Challenge")
    for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz_data):
        qid = f"ans_{idx}"
        with st.container():
            st.markdown(f'<div class="quiz-container">', unsafe_allow_html=True)
            st.write(f"**Question {idx+1}:** {q.strip()}")
            choice = st.radio("Choose:", [f"A: {a}", f"B: {b}", f"C: {c}"], key=f"r_{idx}")
            if st.button(f"Submit Answer {idx+1}", key=f"b_{idx}"):
                actual = correct.strip()[0].upper()
                if qid not in st.session_state.user_scores:
                    is_r = (choice[0].upper() == actual)
                    st.session_state.user_scores[qid] = {"correct": is_r, "expl": expl, "ans": actual}
                    if is_r: st.session_state.total_points += 20
                    st.rerun()
            if qid in st.session_state.user_scores:
                res = st.session_state.user_scores[qid]
                if res["correct"]: st.success("✅ Correct!")
                else: st.error(f"❌ Answer is {res['ans']}. {res['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.total_points >= 100:
        st.balloons()
        st.success("🏆 Mastery Unlocked!")
