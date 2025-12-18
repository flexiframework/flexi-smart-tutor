import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- 1. Secure API Configuration & Smart Resolver ---
if "GEMINI_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("⚠️ API Key not found! Please add 'GEMINI_API_KEY' to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=MY_API_KEY)

def get_smart_model():
    """هذه الوظيفة تحل مشكلة خطأ 404 عبر البحث عن الموديل المتاح في حسابك"""
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        priority_list = ["models/gemini-1.5-flash", "models/gemini-1.5-flash-latest", "models/gemini-pro"]
        for model_path in priority_list:
            if model_path in available_models:
                return model_path
        return available_models[0]
    except Exception:
        return "models/gemini-1.5-flash"

# --- 2. Flexi Academy Branding & UI Styling ---
st.set_page_config(page_title="Flexi Academy AI Tutor", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    :root { --flexi-blue: #1e3a8a; --flexi-orange: #f97316; --flexi-light-bg: #f8fafc; }
    .main { background-color: var(--flexi-light-bg); }
    h1, h2, h3 { color: var(--flexi-blue) !important; font-family: 'Segoe UI', sans-serif; }
    .lesson-box { 
        padding: 30px; border-radius: 15px; background-color: #ffffff; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 25px; 
        border-top: 5px solid var(--flexi-blue); border-bottom: 5px solid var(--flexi-orange);
    }
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 2px solid #e2e8f0; }
    .stButton>button {
        background-color: var(--flexi-blue) !important; color: white !important;
        border-radius: 8px !important; font-weight: bold !important; width: 100%; transition: 0.3s;
    }
    .stButton>button:hover { background-color: var(--flexi-orange) !important; transform: scale(1.02); }
    .comic-panel { border: 3px solid var(--flexi-blue); padding: 15px; background: white; border-radius: 12px; margin-bottom: 20px; }
    .activity-box { background: #fff7ed; padding: 15px; border-radius: 10px; border: 2px dashed var(--flexi-orange); color: #9a3412; font-weight: bold; margin: 10px 0; }
    .resource-card { background: #eff6ff; padding: 12px; border-radius: 8px; border-left: 5px solid var(--flexi-blue); margin: 10px 0; }
    .quiz-container { background-color: #f1f8e9; padding: 20px; border-radius: 15px; border: 1px solid #c5e1a5; margin-bottom: 20px; }
    .stProgress > div > div > div > div { background-color: var(--flexi-orange); }
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header, .stProgress { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Helper Functions ---
def clean_text_for_audio(text):
    return re.sub(r'\[\[.*?\]\]|PANEL \d+|VISUAL:.*|CAPTION:|DIALOGUE:|{.*?}', '', text).strip()

def get_youtube_video(query, lang_name):
    suffix = " educational" if lang_name != "العربية" else " تعليمي"
    try:
        query_string = urllib.parse.urlencode({"search_query": query + suffix})
        format_url = urllib.request.urlopen("https://www.youtube.com/results?" + query_string)
        search_results = re.findall(r"watch\?v=(\S{11})", format_url.read().decode())
        if search_results: return "https://www.youtube.com/embed/" + search_results[0]
    except: return None

# --- 4. Session State ---
if 'lesson_data' not in st.session_state: st.session_state.lesson_data = None
if 'score' not in st.session_state: st.session_state.score = 0
if 'quiz_results' not in st.session_state: st.session_state.quiz_results = {}

# --- 5. Sidebar ---
with st.sidebar:
    st.image("https://flexiacademy.com/assets/images/flexi-logo-2021.png", width=220)
    st.header("👤 Student Profile")
    student_name = st.text_input("Name:", value="Learner")
    age = st.number_input("Age:", 5, 100, 12)
    gender = st.selectbox("Gender:", ["Male", "Female"])
    content_lang = st.selectbox("Language:", ["English", "العربية", "Français", "Deutsch"])
    level = st.selectbox("Academic Level:", ["Beginner", "Intermediate", "Advanced"])
    style = st.selectbox("Learning Style:", ["Visual (Images)", "Auditory (Deep Text)", "Kinesthetic (Activities)"])
    st.divider()
    path = st.radio("Learning Path:", ["Standard Interactive Lesson", "Comic Story Experience"])
    st.divider()
    st.subheader("📊 Your Progress")
    st.progress(min(st.session_state.score, 100) / 100)
    st.metric("Flexi Points 🎯", st.session_state.score)
    st.components.v1.html("""<button onclick="window.print()" style="width:100%;background:#f97316;color:white;border:none;padding:12px;border-radius:10px;cursor:pointer;font-weight:bold;">🖨️ Print PDF</button>""", height=60)

# --- 6. Main Hub ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_area("What would you like to explore?", placeholder="e.g., Solar System")

if st.button("Start My Learning Journey 🚀"):
    if not topic: st.error("Please enter a topic!")
    else:
        try:
            active_model_name = get_smart_model()
            model = genai.GenerativeModel(active_model_name)
            prompt = f"""
            Role: Expert Tutor at Flexi Academy. Language: {content_lang}.
            Student: {student_name}, Age: {age}, Gender: {gender}, Level: {level}, Style: {style}.
            Topic: {topic}. Path: {path}.
            
            1. Core Content: If standard, adapt to style (Visual: [[Image Prompt]], Kinesthetic: {{Activity}}).
            2. Comic Story: 4 Panels if chosen (PANEL X, CAPTION, DIALOGUE, VISUAL).
            3. Resources: 2 real URLs (NASA, Khan Academy, PhET).
            4. Quiz: 5 MCQs (Q:, A) B) C), Correct:, Explanation:).
            """
            with st.spinner(f'Flexi AI is thinking (using {active_model_name})...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                lang_map = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}
                gTTS(text=audio_text[:1000], lang=lang_map[content_lang]).save("voice.mp3")
                st.rerun()
        except Exception as e: st.error(f"Error: {e}")

# --- 7. Display ---
if st.session_state.lesson_data:
    raw = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    st.audio("voice.mp3")

    if "Comic" in path:
        st.subheader("🖼️ Your Learning Story")
        panels = re.split(r'PANEL \d+', raw.split("Q:")[0])[1:]
        cols = st.columns(2)
        for i, p in enumerate(panels[:4]):
            with cols[i % 2]:
                st.markdown(f'<div class="comic-panel" style="direction:{dir_css}">', unsafe_allow_html=True)
                cap = re.search(r'CAPTION:(.*?)(?=DIALOGUE:|VISUAL:|$)', p, re.S)
                vis = re.search(r'VISUAL:(.*?)(?=$)', p, re.S)
                if cap: st.markdown(f'<div style="color:var(--flexi-orange); font-weight:bold;">🎬 {cap.group(1).strip()}</div>', unsafe_allow_html=True)
                if vis: st.image(f"https://pollinations.ai/p/comic%20style%20{vis.group(1).strip().replace(' ', '%20')}?width=600&height=400&seed={i}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        v_url = get_youtube_video(topic, content_lang)
        if v_url: st.markdown(f'<iframe width="100%" height="400" src="{v_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
        
        lesson_body = raw.split("Q:")[0]
        images = re.findall(r'\[\[(.*?)\]\]', lesson_body)
        if images:
            st.subheader("📸 Visual Gallery")
            img_cols = st.columns(len(images[:3]))
            for idx, img_p in enumerate(images[:3]):
                img_cols[idx].image(f"https://pollinations.ai/p/{img_p.replace(' ', '%20')}?width=500&height=400&seed={idx}")

        main_text = re.sub(r'\[\[.*?\]\]|{.*?}', '', lesson_body)
        st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{main_text.replace("###", "📌").replace("\n","<br>")}</div>', unsafe_allow_html=True)

        activities = re.findall(r'{(.*?)}', lesson_body)
        if activities:
            st.subheader("🛠️ Hands-on Activities")
            for act in activities:
                st.markdown(f'<div class="activity-box">🏃 {act}</div>', unsafe_allow_html=True)

    st.subheader("🌐 Recommended Resources")
    links = re.findall(r'(https?://[^\s]+)', raw)
    if links:
        for link in list(set(links))[:3]:
            st.markdown(f'<div class="resource-card">🔗 <a href="{link.strip(").,")}" target="_blank">{link.strip(").,")}</a></div>', unsafe_allow_html=True)

    st.divider()
    st.header("🧠 Knowledge Challenge")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", raw, re.DOTALL)
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"quiz_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            st.write(f"**Q{i+1}:** {q_raw.split('A)')[0].strip()}")
            opts = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            if opts:
                ans = st.radio(f"Select choice:", opts, key=f"ans_{i}")
                if st.button(f"Submit Answer {i+1}", key=f"btn_{i}"):
                    is_correct = ans[0] == correct.strip()
                    if qid not in st.session_state.quiz_results:
                        st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                        if is_correct: st.session_state.score += 20
                        st.rerun()
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]: st.success("Correct!")
                    else: st.error(f"Answer: {res['ans']}. {res['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.score >= 100:
        st.balloons()
        st.markdown(f'<div style="text-align:center; padding:30px; background:#fff3cd; border-radius:20px; border:3px solid var(--flexi-orange);"><h1>🏆</h1><h2>Perfect Score!</h2></div>', unsafe_allow_html=True)
