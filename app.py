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

st.set_page_config(page_title="Flexy AI Smart Tutor", layout="wide", page_icon="🎓")

# --- 2. Enhanced UI Styling (CSS) ---
st.markdown("""
    <style>
    .lesson-box { padding: 30px; border-radius: 20px; background-color: #ffffff; box-shadow: 0 10px 25px rgba(0,0,0,0.05); margin-bottom: 25px; border-left: 8px solid #1a73e8; }
    .comic-panel { border: 4px solid #000; padding: 15px; background: white; box-shadow: 8px 8px 0px #000; margin-bottom: 20px; border-radius: 10px; }
    .caption-tag { background: #ffde59; color: black; padding: 5px 10px; font-weight: bold; border: 2px solid #000; margin-bottom: 10px; display: inline-block; border-radius: 5px; }
    .dialogue-text { background: #f0f0f0; border-radius: 10px; padding: 10px; border-left: 5px solid #333; font-style: italic; margin-top: 10px; }
    .resource-card { background: #e3f2fd; padding: 15px; border-radius: 12px; border: 1px dashed #1e88e5; margin: 10px 0; }
    .activity-box { background: #fff3e0; padding: 15px; border-radius: 12px; border: 2px solid #ffb74d; font-weight: bold; margin: 10px 0; }
    .quiz-container { background-color: #f1f8e9; padding: 25px; border-radius: 20px; border: 1px solid #c5e1a5; margin-bottom: 25px; }
    .trophy-box { text-align: center; padding: 30px; background-color: #fff3cd; border: 3px solid #ffeeba; border-radius: 20px; margin-top: 30px; animation: bounce 2s infinite; }
    @keyframes bounce { 0%, 100% {transform: translateY(0);} 50% {transform: translateY(-10px);} }
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

# --- 5. Sidebar (English UI) ---
with st.sidebar:
    st.header("⚙️ Student Profile")
    student_name = st.text_input("Name:", value="Learner")
    age = st.number_input("Age:", 5, 100, 12)
    gender = st.selectbox("Gender:", ["Male", "Female"])
    content_lang = st.selectbox("Language of Content:", ["English", "العربية", "Français", "Deutsch"])
    academic_level = st.selectbox("Academic Level:", ["Beginner", "Intermediate", "Advanced"])
    learning_style = st.selectbox("Learning Style:", ["Visual (Images)", "Auditory (Deep Text)", "Kinesthetic (Activities)"])
    
    st.divider()
    output_format = st.radio("Output Format:", ["Standard Lesson", "Comic Story"])
    st.divider()
    st.metric("Total Score 🎯", st.session_state.score)
    st.divider()
    st.markdown("### 🖨️ Export")
    st.components.v1.html("""<button onclick="window.print()" style="width:100%;background:#1a73e8;color:white;border:none;padding:12px;border-radius:10px;cursor:pointer;font-weight:bold;">🖨️ Save as PDF</button>""", height=60)

# --- 6. Main Interface ---
st.title("🌟 Flexy AI Smart Learning Platform")
topic = st.text_area("What would you like to learn about?", placeholder="e.g., Solar System, Photosynthesis, Ancient Egypt...")

if st.button("Generate My Experience 🚀"):
    if not topic:
        st.error("Please enter a topic!")
    else:
        try:
            model = genai.GenerativeModel("models/gemini-1.5-flash")
            
            prompt = f"""
            System: Expert Pedagogical Tutor. 
            Target Student: {student_name}, Age: {age}, Gender: {gender}, Level: {academic_level}, Style: {learning_style}.
            Instruction: Provide response ONLY in {content_lang}.
            
            Format Choice: {output_format}.
            
            Adaptation Rules:
            - If Standard Lesson & Visual: Include 4 Image prompts in [[Description]].
            - If Standard Lesson & Auditory: Provide long, rhythmic storytelling explanations.
            - If Standard Lesson & Kinesthetic: Include 3 Activities in {{Activity Name: Description}} tags.
            - If Comic Story: 4 Panels with (PANEL X, CAPTION, DIALOGUE, VISUAL description).
            
            Sections required for ALL:
            1. Core Educational Content.
            2. "External Exploration": Provide 2-3 real educational URLs (NASA, Khan Academy, PhET, etc.) related to {topic}.
            3. 5 Multiple Choice Questions (Q:, A) B) C), Correct:, Explanation:).
            """
            
            with st.spinner('Crafting your personalized lesson...'):
                response = model.generate_content(prompt)
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                
                # Audio Generation
                audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                lang_map = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}
                gTTS(text=audio_text[:1000], lang=lang_map[content_lang]).save("voice.mp3")
                st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

# --- 7. Display Content ---
if st.session_state.lesson_data:
    raw_content = st.session_state.lesson_data
    dir_css = "rtl" if content_lang == "العربية" else "ltr"
    st.audio("voice.mp3")

    # A. Comic Story View
    if "Comic" in output_format:
        st.subheader("🖼️ Educational Story Panels")
        panels = re.split(r'PANEL \d+', raw_content.split("Q:")[0])[1:]
        cols = st.columns(2)
        for i, p in enumerate(panels[:4]):
            with cols[i % 2]:
                st.markdown(f'<div class="comic-panel" style="direction:{dir_css}">', unsafe_allow_html=True)
                cap = re.search(r'CAPTION:(.*?)(?=DIALOGUE:|VISUAL:|$)', p, re.S)
                dia = re.search(r'DIALOGUE:(.*?)(?=VISUAL:|$)', p, re.S)
                vis = re.search(r'VISUAL:(.*?)(?=$)', p, re.S)
                if cap: st.markdown(f'<div class="caption-tag">🎬 {cap.group(1).strip()}</div>', unsafe_allow_html=True)
                if vis:
                    img_url = f"https://pollinations.ai/p/comic%20style%20{vis.group(1).strip().replace(' ', '%20')}?width=600&height=400&seed={i}"
                    st.image(img_url)
                if dia: st.markdown(f'<div class="dialogue-text">💬 {dia.group(1).strip()}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    
    # B. Standard Lesson View
    else:
        v_url = get_youtube_video(topic, content_lang)
        if v_url: st.markdown(f'<iframe width="100%" height="500" src="{v_url}" frameborder="0" allowfullscreen></iframe>', unsafe_allow_html=True)
        
        lesson_body = raw_content.split("Q:")[0]
        # Images for Visual Style
        images = re.findall(r'\[\[(.*?)\]\]', lesson_body)
        if images:
            st.subheader("🖼️ Visual Support")
            img_cols = st.columns(len(images[:3]))
            for idx, img_p in enumerate(images[:3]):
                img_cols[idx].image(f"https://pollinations.ai/p/{img_p.replace(' ', '%20')}?width=500&height=400&seed={idx}")

        # Core Text
        main_text = re.sub(r'\[\[.*?\]\]|{.*?}', '', lesson_body)
        st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{main_text.replace("###", "📌").replace("\n","<br>")}</div>', unsafe_allow_html=True)

        # Activities for Kinesthetic Style
        activities = re.findall(r'{(.*?)}', lesson_body)
        if activities:
            st.subheader("🛠️ Hands-on Activities")
            for act in activities:
                st.markdown(f'<div class="activity-box">🏃 {act}</div>', unsafe_allow_html=True)

    # C. External Exploration (Resources)
    st.subheader("🌐 Explore More & Simulations")
    links = re.findall(r'(https?://[^\s]+)', raw_content)
    if links:
        for link in list(set(links))[:3]:
            # تنظيف الرابط من أي أقواس أو علامات ترقيم زائدة في نهايته
            clean_link = link.strip(').,')
            st.markdown(f'<div class="resource-card">🔗 Resource: <a href="{clean_link}" target="_blank">{clean_link}</a></div>', unsafe_allow_html=True)

    # D. Interactive Quiz
    st.divider()
    st.header("🧠 Challenge Your Knowledge")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", raw_content, re.DOTALL)
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"quiz_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            st.write(f"**Question {i+1}:** {q_raw.split('A)')[0].strip()}")
            options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            if options:
                user_choice = st.radio(f"Select choice for Q{i+1}:", options, key=f"r_{i}")
                if st.button(f"Verify Answer {i+1} ✔️", key=f"b_{i}"):
                    is_correct = user_choice[0] == correct.strip()
                    st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                    if is_correct: st.session_state.score += 10
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]: st.success("Correct!")
                    else: st.error(f"Wrong. Answer is {res['ans']}. {res['expl']}")
            st.markdown('</div>', unsafe_allow_html=True)

    # E. Final Achievement
    if st.session_state.score >= 40:
        st.balloons()
        st.markdown(f'<div class="trophy-box"><h1>🏆</h1><h2>Mastery Unlocked!</h2><p>Excellent job, {student_name}! You scored {st.session_state.score} points!</p></div>', unsafe_allow_html=True)
