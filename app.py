import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- API Configuration ---
# نستخدم Secrets للأمان، ونضع fallback للمفتاح اليدوي
try:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
except:
    MY_API_KEY = "AIzaSyAsPHlq9xzJ42VsVon5lK3141ahatiKGJs"

genai.configure(api_key=MY_API_KEY)

st.set_page_config(page_title="Flexy AI Learning Platform", layout="wide", page_icon="🏆")

# --- UI Styling (CSS) ---
st.markdown("""
    <style>
    .lesson-box { padding: 25px; border-radius: 15px; border-left: 10px solid #1a73e8; background-color: #ffffff; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; color: #2c3e50; }
    .quiz-container { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .trophy-box { text-align: center; padding: 30px; background-color: #fff3cd; border: 3px solid #ffeeba; border-radius: 20px; margin-top: 30px; }
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header, iframe { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- Smart Model Resolver (Fixes 404 Error) ---
def get_model_name():
    """البحث عن الاسم الصحيح للموديل لتجنب خطأ 404"""
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # ترتيب الأولويات: نبحث عن فلاش أولاً لاستقراره
        priority = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]
        for p in priority:
            if p in available: return p
        return available[0] # إذا لم يجد شيئاً، يأخذ أول موديل متاح
    except:
        return "models/gemini-1.5-flash" # الفرضية الافتراضية

# --- Helper Functions ---
def get_youtube_video(query, lang):
    suffix = " educational" if lang != "العربية" else " تعليمي"
    try:
        query_string = urllib.parse.urlencode({"search_query": query + suffix})
        format_url = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
        search_results = re.findall(r"watch\?v=(\S{11})", format_url.read().decode())
        if search_results: return "https://www.youtube.com/embed/" + search_results[0]
    except: return None

def clean_text_for_audio(text):
    text = re.sub(r'\[\[.*?\]\]|PANEL \d+|VISUAL:.*|CAPTION:|DIALOGUE:', '', text)
    text = re.sub(r'[^\w\s\u0621-\u064A.]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

# --- State Management ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ Personalization")
    student_name = st.text_input("Student Name:", value="Learner")
    content_lang = st.selectbox("Language:", ["English", "العربية", "Français", "Deutsch"])
    output_format = st.radio("Output Format:", ["Standard Lesson", "Comic Story"])
    st.divider()
    st.metric("Score 🎯", st.session_state.score)
    st.divider()
    st.markdown("### 🖨️ Export")
    st.components.v1.html("""<button onclick="window.print()" style="width:100%;background:#1a73e8;color:white;border:none;padding:10px;border-radius:10px;cursor:pointer;">Print as PDF</button>""", height=50)

# --- Main Area ---
st.title("🌟 Flexy AI Smart Learning")
topic = st.text_area("Enter topic:", placeholder="e.g., How electricity works")

if st.button("Generate 🚀"):
    if not topic:
        st.error("Please enter a topic!")
    else:
        try:
            # استخدام وظيفة البحث الذكي عن الموديل
            active_model = get_model_name()
            model = genai.GenerativeModel(active_model)
            
            prompt = f"Expert AI tutor. Response ONLY in {content_lang}. Subject: {topic}. Format: {output_format} with 4 MCQs at the end (Q:, A) B) C), Correct:, Explanation:)."
            
            with st.spinner(f'Using {active_model}...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                
                audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                lang_map = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}
                gTTS(text=audio_text[:600], lang=lang_map[content_lang]).save("voice.mp3")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- عرض المحتوى ---
if st.session_state.lesson_data:
    content = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    st.audio("voice.mp3")

    # عرض الدرس
    lesson_body = content.split("Q:")[0]
    st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{lesson_body.replace("\n","<br>")}</div>', unsafe_allow_html=True)

    # --- القسم التفاعلي للأسئلة ---
    st.divider()
    st.header("🧠 Test Your Knowledge")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", content, re.DOTALL)
    
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"q_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            st.write(f"**Question {i+1}:** {q_raw.split('A)')[0].strip()}")
            opts = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            if opts:
                user_choice = st.radio(f"Select answer:", opts, key=f"radio_{i}")
                if st.button(f"Confirm {i+1}", key=f"btn_{i}"):
                    is_correct = user_choice[0] == correct.strip()
                    st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                    if is_correct: st.session_state.score += 10
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]: st.success("Correct!")
                    else: st.error(f"Wrong. Answer is {res['ans']}")
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.score >= 40:
        st.balloons()
        st.markdown('<div class="trophy-box"><h1>🏆</h1><h2>Excellent!</h2></div>', unsafe_allow_html=True)
