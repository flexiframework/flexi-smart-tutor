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
    st.error("⚠️ API Key not found! Please add 'GEMINI_API_KEY' to Streamlit Secrets.")
    st.stop()

genai.configure(api_key=MY_API_KEY)

# --- 2. Flexi Academy Branding & UI Styling ---
st.set_page_config(page_title="Flexi Academy AI Tutor", layout="wide", page_icon="🎓")

st.markdown("""
    <style>
    /* Flexi Academy Main Colors */
    :root {
        --flexi-blue: #1e3a8a;
        --flexi-orange: #f97316;
        --flexi-light-bg: #f8fafc;
    }
    
    /* Global Styles */
    .main { background-color: var(--flexi-light-bg); }
    h1, h2, h3 { color: var(--flexi-blue) !important; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    
    /* Lesson Box */
    .lesson-box { 
        padding: 30px; border-radius: 15px; background-color: #ffffff; 
        box-shadow: 0 4px 20px rgba(0,0,0,0.08); margin-bottom: 25px; 
        border-top: 5px solid var(--flexi-blue); border-bottom: 5px solid var(--flexi-orange);
    }
    
    /* Side Bar Customization */
    [data-testid="stSidebar"] { background-color: #ffffff; border-right: 2px solid #e2e8f0; }
    
    /* Buttons */
    .stButton>button {
        background-color: var(--flexi-blue) !important; color: white !important;
        border-radius: 8px !important; border: none !important; font-weight: bold !important;
        padding: 10px 24px !important; transition: 0.3s;
    }
    .stButton>button:hover { background-color: var(--flexi-orange) !important; transform: scale(1.02); }

    /* Comic & Activities */
    .comic-panel { border: 3px solid var(--flexi-blue); padding: 15px; background: white; border-radius: 12px; margin-bottom: 20px; }
    .activity-box { background: #fff7ed; padding: 15px; border-radius: 10px; border: 2px dashed var(--flexi-orange); color: #9a3412; font-weight: 600; }
    
    /* Resource Card */
    .resource-card { background: #eff6ff; padding: 12px; border-radius: 8px; border-left: 5px solid var(--flexi-blue); margin: 10px 0; }
    
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- 3. Helper Functions ---
def clean_text_for_audio(text):
    text = re.sub(r'\[\[.*?\]\]|PANEL \d+|VISUAL:.*|CAPTION:|DIALOGUE:|{.*?}', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def get_youtube_video(query, lang):
    suffix = " educational" if lang != "العربية" else " تعليمي"
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

# --- 5. Sidebar (Flexi Academy Profile) ---
with st.sidebar:
    # Adding School Logo
    st.image("https://flexiacademy.com/wp-content/uploads/2022/10/Flexi-Academy-Logo.png", width=200)
    st.header("👤 Student Profile")
    student_name = st.text_input("Name:", value="Learner")
    age = st.number_input("Age:", 5, 18, 12)
    gender = st.selectbox("Gender:", ["Male", "Female"])
    content_lang = st.selectbox("Language of Content:", ["English", "العربية", "Français", "Deutsch"])
    academic_level = st.selectbox("Academic Level:", ["Elementary", "Middle School", "High School", "University"])
    learning_style = st.selectbox("Learning Style:", ["Visual (Images)", "Auditory (Deep Text)", "Kinesthetic (Activities)"])
    
    st.divider()
    output_format = st.radio("Learning Path:", ["Standard Interactive Lesson", "Comic Story Experience"])
    st.divider()
    st.metric("My Flexi Points 🎯", st.session_state.score)
    st.divider()
    st.markdown("### 📄 Export Lesson")
    st.components.v1.html("""<button onclick="window.print()" style="width:100%;background:#f97316;color:white;border:none;padding:12px;border-radius:10px;cursor:pointer;font-weight:bold;">🖨️ Print as PDF</button>""", height=60)

# --- 6. Main Hub ---
st.title("🎓 Flexi Academy Smart Tutor")
st.caption("Empowering you to learn at your own pace with AI.")

topic = st.text_area("What topic would you like to explore?", placeholder="e.g., Global Warming, Calculus, World War II...")

if st.button("Start My Learning Journey 🚀"):
    if not topic:
        st.error("Please enter a topic to begin!")
    else:
        try:
            model = genai.GenerativeModel("models/gemini-1.5-flash")
            
            prompt = f"""
            Role: Expert Tutor at Flexi Academy.
            Audience: {student_name}, Age: {age}, Level: {academic_level}, Style: {learning_style}.
            Content Language: {lang}.
            Topic: {topic}.
            
            Instructions:
            1. If "Standard Interactive Lesson":
               - Visual Style: Include 4+ rich image descriptions in [[Prompt]].
               - Auditory Style: Provide detailed, engaging prose suitable for listening.
               - Kinesthetic Style: Include 3 hands-on experiments/activities in {{Activity: Description}} tags.
            2. If "Comic Story Experience": Provide 4 Panels (PANEL X, CAPTION, DIALOGUE, VISUAL).
            3. Section "Recommended Explorations": Provide 2-3 links to real educational websites (e.g. NASA, Khan Academy, PhET, NatGeo Kids).
            4. Assessment: 5 MCQs (Q:, A) B) C), Correct:, Explanation:).
            """
            
            with st.spinner('Preparing your Flexi experience...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                
                # Audio
                audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                lang_map = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}
                gTTS(text=audio_text[:1000], lang=lang_map[content_lang]).save("voice.mp3")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 7. Display Content ---
if st.session_state.lesson_data:
    raw = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    st.audio("voice.mp3")

    # A. Comic View
    if "Comic" in output_format:
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
    
    # B. Standard View
    else:
        v_url = get_youtube_video(topic, content_lang)
        if v_url: st.markdown(f'<iframe width="100%" height="500" src="{v_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
        
        lesson_body = raw.split("Q:")[0]
        # Visual Support
        images = re.findall(r'\[\[(.*?)\]\]', lesson_body)
        if images:
            st.subheader("📸 Visual Gallery")
            img_cols = st.columns(len(images[:3]))
            for idx, img_p in enumerate(images[:3]):
                img_cols[idx].image(f"https://pollinations.ai/p/{img_p.replace(' ', '%20')}?width=500&height=400&seed={idx}")

        # Core Text
        main_text = re.sub(r'\[\[.*?\]\]|{.*?}', '', lesson_body)
        st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{main_text.replace("###", "📌").replace("\n","<br>")}</div>', unsafe_allow_html=True)

        # Kinesthetic Activities
        activities = re.findall(r'{(.*?)}', lesson_body)
        if activities:
            st.subheader("🛠️ Hands-on Activities")
            for act in activities:
                st.markdown(f'<div class="activity-box">🏃 {act}</div>', unsafe_allow_html=True)

    # C. External Exploration
    st.subheader("🌐 External Resources & Simulations")
    links = re.findall(r'(https?://[^\s]+)', raw)
    if links:
        for link in list(set(links))[:3]:
            clean_l = link.strip(').,')
            st.markdown(f'<div class="resource-card">🔗 Recommended: <a href="{clean_l}" target="_blank">{clean_l}</a></div>', unsafe_allow_html=True)

    # D. Interactive Quiz
    st.divider()
    st.header("🧠 Knowledge Challenge")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", raw, re.DOTALL)
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"quiz_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            st.write(f"**Q{i+1}:** {q_raw.split('A)')[0].strip()}")
            options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            if options:
                ans = st.radio(f"Select choice:", options, key=f"ans_{i}")
                if st.button(f"Submit Q{i+1}", key=f"btn_{i}"):
                    is_correct = ans[0] == correct.strip()
                    st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                    if is_correct: st.session_state.score += 10
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]: st.success("Great job! Correct.")
                    else: st.error(f"The correct answer is {res['ans']}. {res['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    # E. Achievement
    if st.session_state.score >= 40:
        st.balloons()
        st.markdown(f'<div class="trophy-box"><h1>🏆</h1><h2>Flexi Excellence Award!</h2><p>Congratulations {student_name}!</p></div>', unsafe_allow_html=True)
