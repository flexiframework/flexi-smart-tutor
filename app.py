import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- 1. Secure API Configuration ---
if "GEMINI_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ API Key not found in Secrets!")
    st.stop()

genai.configure(api_key=MY_API_KEY)

st.set_page_config(page_title="Flexy AI Smart Tutor", layout="wide", page_icon="🚀")

# --- 2. Enhanced UI Styling ---
st.markdown("""
    <style>
    .lesson-box { padding: 30px; border-radius: 20px; background-color: #ffffff; box-shadow: 0 10px 25px rgba(0,0,0,0.1); margin-bottom: 25px; border-left: 8px solid #4CAF50; }
    .resource-card { background: #e3f2fd; padding: 15px; border-radius: 12px; border: 1px dashed #1e88e5; margin: 10px 0; }
    .activity-box { background: #fff3e0; padding: 15px; border-radius: 12px; border: 2px solid #ffb74d; font-weight: bold; }
    .quiz-container { background-color: #f1f8e9; padding: 25px; border-radius: 20px; border: 1px solid #c5e1a5; margin-bottom: 25px; }
    @media print { .no-print { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Smart Model Resolver ---
def get_model_name():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority = ["models/gemini-1.5-flash", "models/gemini-pro"]
        for p in priority:
            if p in available: return p
        return available[0]
    except: return "models/gemini-1.5-flash"

# --- 4. Helper Functions ---
def clean_text_for_audio(text):
    text = re.sub(r'\[\[.*?\]\]|PANEL \d+|VISUAL:.*|CAPTION:|DIALOGUE:|{.*?}', '', text)
    return re.sub(r'\s+', ' ', text).strip()

# --- 5. Session State ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- 6. Sidebar (Personalization Settings) ---
with st.sidebar:
    st.header("⚙️ Student Profile")
    student_name = st.text_input("Name:", value="Learner")
    age = st.number_input("Age:", 5, 18, 12)
    level = st.selectbox("Academic Level:", ["Beginner", "Intermediate", "Advanced"])
    style = st.selectbox("Learning Style:", ["Visual (Images & Descriptions)", "Auditory (Deep Explanations)", "Kinesthetic (Activities & Simulation)"])
    lang = st.selectbox("Content Language:", ["English", "العربية", "Français"])
    st.divider()
    st.metric("Total Score 🎯", st.session_state.score)
    st.markdown("### 🖨️ Export")
    st.components.v1.html("""<button onclick="window.print()" style="width:100%;background:#1a73e8;color:white;border:none;padding:12px;border-radius:10px;cursor:pointer;font-weight:bold;">🖨️ Save as PDF</button>""", height=60)

# --- 7. Main Interface ---
st.title("🚀 Flexy AI: Adaptive Learning Experience")
topic = st.text_area("What topic should we explore?", placeholder="e.g., How the heart works, Laws of Motion, etc.")

if st.button("Build My Experience 🪄"):
    if not topic: st.error("Please enter a topic!")
    else:
        try:
            model = genai.GenerativeModel(get_model_name())
            # الـ Prompt الجديد الذي يركز على نمط التعلم والمصادر
            prompt = f"""
            System: Expert Pedagogical Tutor. Content Language: {lang}.
            Student: {student_name}, Age: {age}, Level: {level}, Style: {style}.
            
            Adaptation Strategy:
            - If Visual: Include at least 4 Image Prompts in [[Description]]. Provide vivid descriptive language.
            - If Auditory: Provide long, detailed, and rhythmic explanations suitable for TTS. Focus on storytelling.
            - If Kinesthetic: Include 3 "Hands-on Activities" or "Home Experiments" in {{Activity}} tags. Focus on "How to do".
            
            Structure:
            1. Engaging Introduction.
            2. Core Content (Adapted to Style).
            3. {lang} "External Exploration" section: Provide 2 links to reputable educational sites (like NASA, Khan Academy, PhET Simulations, or National Geographic Kids) specifically for {topic}.
            4. 5 Interactive MCQs (Q:, A) B) C), Correct:, Explanation:).
            """
            with st.spinner('Orchestrating your personalized learning journey...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                # Audio
                audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                lang_code = {"العربية": "ar", "English": "en", "Français": "fr"}[lang]
                gTTS(text=audio_text[:1000], lang=lang_code).save("voice.mp3")
                st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- 8. Dynamic Content Display ---
if st.session_state.lesson_data:
    raw = st.session_state.lesson_data
    dir_css = "rtl" if lang == "العربية" else "ltr"
    st.audio("voice.mp3")

    # معالجة الصور المتعددة (للنمط البصري)
    lesson_part = raw.split("Q:")[0]
    images = re.findall(r'\[\[(.*?)\]\]', lesson_part)
    
    # عرض المحتوى الأساسي
    main_text = re.sub(r'\[\[.*?\]\]|{.*?}', '', lesson_part)
    st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{main_text.replace("###", "📌").replace("\n","<br>")}</div>', unsafe_allow_html=True)

    # عرض الصور الموزعة (Visual Support)
    if images:
        st.subheader("🖼️ Visual Aids")
        cols = st.columns(len(images[:4]))
        for idx, img_p in enumerate(images[:4]):
            with cols[idx]:
                st.image(f"https://pollinations.ai/p/{img_p.replace(' ', '%20')}?width=500&height=500&seed={idx}", caption=f"Visual Guide {idx+1}")

    # عرض الأنشطة (Kinesthetic Support)
    activities = re.findall(r'{(.*?)}', lesson_part)
    if activities:
        st.subheader("🛠️ Hands-on Activities")
        for act in activities:
            st.markdown(f'<div class="activity-box">🏃 {act}</div>', unsafe_allow_html=True)

    # عرض الروابط الخارجية (Simulation & Resources)
    st.subheader("🌐 Explore & Interact")
    links = re.findall(r'(https?://[^\s]+)', raw)
    if links:
        for link in list(set(links))[:3]:
            st.markdown(f'<div class="resource-card">🔗 Recommended Resource: <a href="{link}" target="_blank">{link}</a></div>', unsafe_allow_html=True)
    else:
        st.info("Check educational platforms like PhET Simulations or NASA Kids for more interative fun!")

    # --- 9. Interactive Quiz ---
    st.divider()
    st.header("🧠 Challenge Your Mind")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", raw, re.DOTALL)
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"quiz_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            st.write(f"**Q{i+1}:** {q_raw.split('A)')[0].strip()}")
            options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            if options:
                ans = st.radio(f"Choose carefully:", options, key=f"ans_{i}")
                if st.button(f"Verify Q{i+1}", key=f"btn_{i}"):
                    is_correct = ans[0] == correct.strip()
                    st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                    if is_correct: st.session_state.score += 10
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]: st.success("🎯 Correct!")
                    else: st.error(f"❌ Not quite. The answer is {res['ans']}. {res['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.score >= 40:
        st.balloons()
        st.markdown(f'<div class="trophy-box"><h1>🏆</h1><h2>Mastery Unlocked!</h2><p>Excellent work, {student_name}!</p></div>', unsafe_allow_html=True)
