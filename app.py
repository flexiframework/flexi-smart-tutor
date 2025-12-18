import streamlit as st
import google.generativeai as genai
import re  # تم تصحيح الخطأ هنا (إزالة حرف ض)
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- 1. API Configuration & Smart Resolver ---
if "GEMINI_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ API Key not found in Secrets!")
    st.stop()

genai.configure(api_key=MY_API_KEY)

def get_smart_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = ["models/gemini-1.5-flash", "models/gemini-pro"]
        for model_path in priority_list:
            if model_path in available_models: return model_path
        return available_models[0]
    except: return "models/gemini-1.5-flash"

# --- 2. UI Styling ---
st.set_page_config(page_title="Flexi Academy AI Tutor", layout="wide", page_icon="🎓")
st.markdown("""
    <style>
    :root { --flexi-blue: #1e3a8a; --flexi-orange: #f97316; }
    .lesson-box { padding: 30px; border-radius: 15px; background: white; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-top: 5px solid var(--flexi-blue); margin-bottom: 20px; }
    .comic-panel { border: 3px solid var(--flexi-blue); padding: 15px; background: white; border-radius: 12px; margin-bottom: 20px; text-align: center; }
    .quiz-container { background-color: #f1f8e9; padding: 25px; border-radius: 20px; border: 1px solid #c5e1a5; margin-top: 20px; }
    .stProgress > div > div > div > div { background-color: var(--flexi-orange); }
    img { border-radius: 15px; margin: 15px 0; border: 1px solid #ddd; }

    @media print {
        section[data-testid="stSidebar"], .stButton, .stAudio, footer, header, button { 
            display: none !important; 
        }
        .main .block-container { padding: 0 !important; margin: 0 !important; }
        .lesson-box { border: none !important; box-shadow: none !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Session State ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- 4. Sidebar ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=220)
    student_name = st.text_input("Student Name:", value="Learner")
    age = st.number_input("Age:", 5, 100, 12)
    content_lang = st.selectbox("Language:", ["English", "العربية", "Français"])
    style = st.selectbox("Learning Style:", ["Visual (Many Images)", "Auditory (Deep Text)", "Kinesthetic (Activities)"])
    path = st.radio("Learning Path:", ["Standard Interactive Lesson", "Comic Story Experience"])
    
    st.divider()
    st.subheader("📊 Progress")
    st.progress(min(st.session_state.score, 100) / 100)
    st.metric("Flexi Points 🎯", st.session_state.score)

    st.divider()
    st.markdown("### 📄 خيارات الحفظ")
    # زر الطباعة المدمج في القائمة الجانبية
    st.components.v1.html("""
        <script>function printPage() { window.print(); }</script>
        <button onclick="printPage()" style="
            width: 100%; background-color: #f97316; color: white; border: none;
            padding: 12px; text-align: center; font-size: 16px; font-weight: bold;
            cursor: pointer; border-radius: 10px; transition: 0.3s;">
            🖨️ طباعة الدرس (PDF)
        </button>
    """, height=70)
    st.caption("نصيحة: اختر 'Save as PDF' من خيارات الطباعة.")

# --- 5. Main Logic ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_area("What topic should we explore?", placeholder="e.g., Water Cycle")

if st.button("Generate Experience 🚀"):
    if not topic: st.error("Please enter a topic!")
    else:
        try:
            model = genai.GenerativeModel(get_smart_model())
            prompt = f"""
            Role: Expert Tutor at Flexi Academy. Language: {content_lang}.
            Student: {student_name}, Age: {age}, Style: {style}. Topic: {topic}. Path: {path}.
            
            Structure:
            1. Core Lesson: 
               - If Visual: Must include 6 different [[Image Description]] tags spaced out between paragraphs.
               - If Kinesthetic: Include 3 {{Activity}} boxes.
            2. Comic Path: 4 Panels with (PANEL X, CAPTION, DIALOGUE, VISUAL Description).
            3. Resources: 2 real URLs.
            4. Assessment: Exactly 5 MCQs (Q:, A) B) C), Correct:, Explanation:).
            """
            with st.spinner('Building your Flexi lesson...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- 6. Content Rendering ---
if st.session_state.lesson_data:
    raw = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    
    parts = raw.split("Q:")
    lesson_part = parts[0]
    quiz_part = "Q:" + "Q:".join(parts[1:]) if len(parts) > 1 else ""

    if "Comic" in path:
        st.subheader("🖼️ Your Learning Story")
        panels = re.split(r'PANEL \d+', lesson_part)[1:]
        cols = st.columns(2)
        for i, p in enumerate(panels[:4]):
            with cols[i % 2]:
                st.markdown(f'<div class="comic-panel" style="direction:{dir_css}">', unsafe_allow_html=True)
                cap = re.search(r'CAPTION:(.*?)(?=DIALOGUE:|VISUAL:|$)', p, re.S)
                vis = re.search(r'VISUAL:(.*?)(?=$)', p, re.S)
                if cap: st.write(f"🎬 {cap.group(1).strip()}")
                if vis: st.image(f"https://pollinations.ai/p/comic%20style%20{vis.group(1).strip().replace(' ', '%20')}?width=600&height=400&seed={i}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div style="direction:{dir_css}">', unsafe_allow_html=True)
        text_segments = re.split(r'\[\[(.*?)\]\]', lesson_part)
        for idx, segment in enumerate(text_segments):
            if idx % 2 == 0:
                if segment.strip(): st.markdown(f'<div class="lesson-box">{segment.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
            else:
                st.image(f"https://pollinations.ai/p/{segment.strip().replace(' ', '%20')}?width=800&height=400&seed={idx}", caption=f"Visual: {segment.strip()}")
        
        activities = re.findall(r'{(.*?)}', lesson_part)
        for act in activities:
            st.markdown(f'<div class="activity-box">🏃 Activity: {act}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # --- Interactive Quiz Section ---
    st.divider()
    st.header("🧠 Knowledge Challenge")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", quiz_part, re.DOTALL)
    
    if not q_blocks:
        st.warning("⚠️ Questions are being prepared...")
    else:
        trophy_placeholder = st.empty()
        for i, (q_raw, correct, expl) in enumerate(q_blocks):
            qid = f"quiz_q_{i}"
            with st.container():
                st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
                question_text = q_raw.split('A)')[0].strip()
                st.write(f"**Question {i+1}:** {question_text}")
                opts = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
                
                if opts:
                    user_ans = st.radio(f"Choose answer for Q{i+1}:", opts, key=f"radio_ans_{i}")
                    if st.button(f"Verify Answer {i+1} ✔️", key=f"verify_btn_{i}"):
                        is_correct = user_ans[0] == correct.strip()
                        if qid not in st.session_state.quiz_results:
                            st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                            if is_correct: st.session_state.score += 20
                            st.rerun()
                    
                    if qid in st.session_state.quiz_results:
                        res = st.session_state.quiz_results[qid]
                        if res["correct"]: st.success(f"🌟 Correct answer!")
                        else: st.error(f"❌ Wrong. Answer is {res['ans']}. {res['expl']}")
                st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.score >= 100:
            st.balloons()
            with trophy_placeholder:
                st.markdown("""
                    <div style="text-align:center; padding:30px; background-color:#fff3cd; border:4px solid #f97316; border-radius:20px;">
                        <h1 style="font-size:60px; margin:0;">🏆</h1>
                        <h2 style="color:#1e3a8a;">Flexi Mastery Award!</h2>
                    </div>
                """, unsafe_allow_html=True)
