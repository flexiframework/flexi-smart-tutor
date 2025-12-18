import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import os
import time  # ضروري لنظام الانتظار
from google.api_core import exceptions  # للتعامل مع أخطاء الحصة

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
    st.header("👤 Profile")
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

# --- 5. Main Generation Logic (With Auto-Retry) ---
st.title("🎓 Flexi Academy AI Tutor")
topic = st.text_area("What would you like to learn?", placeholder="e.g., Photosynthesis")

if st.button("Generate Experience 🚀"):
    if not topic:
        st.error("Please enter a topic!")
    else:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""
            Role: Expert Tutor at Flexi Academy. Student: {name}, {gender}, {age} years old.
            Language: {lang}. Style: {style}. Path: {path}. Topic: {topic}. Academic Level: {level}.
            
            STRUCTURE:
            1. Lesson Text: Address the student correctly. If visual, insert 6 [[detailed image prompt]] tags.
            2. Assessment: Mandatory separator 'START_QUIZ'. Then 5 questions in this EXACT format:
               Q: [Question] | A: [Opt1] | B: [Opt2] | C: [Opt3] | Correct: [Letter] | Expl: [Why]
            """
            
            response_text = ""
            success = False
            
            with st.spinner('Flexi is building your lesson... (Checking Server Capacity)'):
                for attempt in range(3):  # محاولة الطلب 3 مرات في حال وجود ضغط
                    try:
                        resp = model.generate_content(prompt)
                        response_text = resp.text
                        success = True
                        break
                    except exceptions.ResourceExhausted:
                        wait_time = (attempt + 1) * 5
                        st.warning(f"Server busy. Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                
                if not success:
                    st.error("Google's servers are currently full. Please wait 1 minute and try again.")
                else:
                    # تقسيم المحتوى والاختبار
                    main_txt, quiz_txt = response_text.split('START_QUIZ') if 'START_QUIZ' in response_text else (response_text, "")
                    st.session_state.lesson_content = main_txt
                    
                    # استخراج الأسئلة
                    qs = re.findall(r"Q:(.*?) \| A:(.*?) \| B:(.*?) \| C:(.*?) \| Correct:(.*?) \| Expl:(.*)", quiz_txt)
                    st.session_state.quiz_data = qs
                    st.session_state.user_scores = {}
                    st.session_state.total_points = 0
                    
                    # إنشاء الصوت (تأكد من تنظيف النص من وسوم الصور)
                    clean_audio_txt = re.sub(r'\[\[.*?\]\]', '', main_txt[:800]).strip()
                    audio_lang = 'ar' if lang == 'العربية' else 'en'
                    tts = gTTS(text=clean_audio_txt, lang=audio_lang)
                    tts.save("voice.mp3")
                    st.rerun()
                    
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# --- 6. Content Rendering ---
if st.session_state.lesson_content:
    if os.path.exists("voice.mp3"):
        st.audio("voice.mp3")
        
    content = st.session_state.lesson_content
    direction = "rtl" if lang == "العربية" else "ltr"
    
    st.markdown(f'<div style="direction:{direction}">', unsafe_allow_html=True)
    segments = re.split(r'\[\[(.*?)\]\]', content)
    for i, seg in enumerate(segments):
        if i % 2 == 0:
            if seg.strip(): 
                st.markdown(f'<div class="lesson-box">{seg.strip().replace("\n", "<br>")}</div>', unsafe_allow_html=True)
        else:
            st.image(f"https://pollinations.ai/p/{seg.replace(' ', '%20')}?width=800&height=400&seed={i}")
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 7. Interactive Quiz Section ---
    st.divider()
    st.header("🧠 Knowledge Challenge")
    
    if st.session_state.quiz_data:
        for idx, (q, a, b, c, correct, expl) in enumerate(st.session_state.quiz_data):
            qid = f"q_status_{idx}"
            with st.container():
                st.markdown(f'<div class="quiz-container" style="direction:{direction}">', unsafe_allow_html=True)
                st.write(f"**Question {idx+1}:** {q.strip()}")
                
                # خيارات الراديو
                choice = st.radio("Choose your answer:", [f"A: {a}", f"B: {b}", f"C: {c}"], key=f"radio_q_{idx}")
                
                # زر التحقق لكل سؤال
                if st.button(f"Submit Q{idx+1} ✔️", key=f"btn_q_{idx}"):
                    user_letter = choice[0].upper()
                    correct_letter = correct.strip()[0].upper()
                    
                    if qid not in st.session_state.user_scores:
                        is_correct = (user_letter == correct_letter)
                        st.session_state.user_scores[qid] = {"correct": is_correct, "expl": expl, "correct_ans": correct_letter}
                        if is_correct:
                            st.session_state.total_points += 20
                        st.rerun()
                
                # إظهار النتيجة بعد الإجابة
                if qid in st.session_state.user_scores:
                    res = st.session_state.user_scores[qid]
                    if res["correct"]:
                        st.success("🌟 Correct!")
                    else:
                        st.error(f"❌ Incorrect. The answer is {res['correct_ans']}")
                        st.info(f"💡 Explanation: {res['expl']}")
                
                st.markdown('</div>', unsafe_allow_html=True)

    # الاحتفال بالتروفي
    if st.session_state.total_points >= 100:
        st.balloons()
        st.markdown("""
            <div style="text-align:center; background:#fff3cd; padding:30px; border-radius:20px; border:4px solid #f97316;">
                <h1 style="font-size:70px; margin:0;">🏆</h1>
                <h2 style="color:#1e3a8a;">Mastery Unlocked!</h2>
                <p style="font-size:18px; color:#1e3a8a;">Congratulations! You achieved a perfect score.</p>
            </div>
        """, unsafe_allow_html=True)
