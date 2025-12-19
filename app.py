import streamlit as st
import google.generativeai as genai
import re
from gtts import gTTS
import urllib.request
import urllib.parse
import os

# --- API Config ---
if "GEMINI_API_KEY" in st.secrets:
    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
else:
    st.error("خطأ: مفتاح API غير موجود. يرجى إضافته في إعدادات Secrets في Streamlit Cloud باسم GEMINI_API_KEY.")
    st.stop()

genai.configure(api_key=MY_API_KEY)
st.set_page_config(page_title="Flexy AI Tutor", layout="wide", page_icon="🎓")

# --- UI Styling ---
st.markdown("""
    <style>
    .lesson-box { padding: 25px; border-radius: 15px; border-left: 10px solid #1a73e8; background-color: #ffffff; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px; color: #2c3e50; }
    .comic-panel { border: 4px solid #000; padding: 15px; background: white; box-shadow: 8px 8px 0px #000; margin-bottom: 20px; }
    .caption-tag { background: #ffde59; color: black; padding: 5px 10px; font-weight: bold; border: 2px solid #000; margin-bottom: 10px; display: inline-block; }
    .dialogue-text { background: #f0f0f0; border-radius: 10px; padding: 10px; border-left: 5px solid #333; font-style: italic; margin-top: 10px; }
    .quiz-container { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
    .correct-feedback { color: #155724; background-color: #d4edda; padding: 10px; border-radius: 10px; border: 1px solid #c3e6cb; margin-top: 10px; font-weight: bold; }
    .wrong-feedback { color: #721c24; background-color: #f8d7da; padding: 10px; border-radius: 10px; border: 1px solid #f5c6cb; margin-top: 10px; font-weight: bold; }
    @media print { section[data-testid="stSidebar"], .stButton, .stAudio, footer, header, iframe, .no-print { display: none !important; } }
    </style>
    """, unsafe_allow_html=True)

# --- Helper Functions ---
def get_youtube_video(query, language):
    suffix = " educational" if language != "العربية" else " تعليمي"
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

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("⚙️ Settings")
    student_name = st.text_input("Student Name:", value="Student")
    age = st.number_input("Age:", min_value=5, value=12)
    language = st.selectbox("Language:", ["English", "العربية", "Français", "Deutsch"])
    level = st.selectbox("Level:", ["Beginner", "Intermediate", "Advanced"])
    style = st.selectbox("Learning Style:", ["Visual", "Auditory", "Kinesthetic"])
    output_format = st.radio("Output Format:", ["Standard Lesson", "Comic Story"])
    
    st.divider()
    st.metric("Total Score", st.session_state.score)
    
    print_btn = """<button onclick="window.print()" style="width: 100%; background-color: #1a73e8; color: white; padding: 12px; border: none; border-radius: 10px; cursor: pointer; font-weight: bold;">🖨️ Save as PDF</button>"""
    st.components.v1.html(print_btn, height=60)

# --- Main Content ---
st.title("🌟 Flexy AI Interactive Learning")
topic = st.text_area("ماذا تحب أن تتعلم اليوم؟", placeholder="مثلاً: كيف تعمل البراكين؟")

if st.button("ابدأ التعلم الآن 🚀"):
    if not topic:
        st.error("الرجاء إدخال موضوع أولاً!")
    else:
        try:
            # --- منطق اختيار الموديل مع دعم الموديلات الجديدة التي وجدتها في حسابك ---
            model = None
            # أضفنا gemini-1.5-pro كخيار قوي جداً متاح لك
            available_models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
            
            with st.spinner('جاري الاتصال بذكاء Flexy...'):
                for model_name in available_models:
                    try:
                        test_model = genai.GenerativeModel(model_name)
                        # فحص سريع للاتصال
                        test_model.generate_content("test", generation_config={"max_output_tokens": 1})
                        model = test_model
                        break 
                    except Exception:
                        continue
            
            if model is None:
                st.error("عذراً، لم نتمكن من الاتصال بالخادم. يرجى التحقق من مفتاح API في الإعدادات (Secrets).")
                st.stop()

            # --- إعداد البرومبت ---
            is_comic = "Comic" in output_format
            prompt = f"""
            System: You are a professional tutor. Language: {language}.
            Student: {student_name}, Age: {age}, Level: {level}, Style: {style}.
            Task: Create an educational {output_format} about {topic}.
            Rules:
            1. Response must be 100% in {language}.
            2. If Comic: 4 Panels (PANEL X, CAPTION, DIALOGUE, VISUAL [English Description]).
            3. If Lesson: Use ### for headers and [[Visual Description]].
            4. At the end, add 4 MCQs. FORMAT:
               Q: [Question]
               A) [Option]
               B) [Option]
               C) [Option]
               Correct: [Letter]
               Explanation: [Brief note]
            """
            
            with st.spinner('جاري تحضير درسك التفاعلي...'):
                response = model.generate_content(prompt)
                
                if not response.text:
                    raise Exception("استجابة فارغة من الذكاء الاصطناعي")
                    
                st.session_state.lesson_data = response.text
                st.session_state.score = 0
                st.session_state.quiz_results = {}
                
                # إنشاء ملف الصوت بشكل آمن
                try:
                    # تنظيف النص من أكواد الميك لتوليد صوت نقي
                    audio_text = clean_text_for_audio(st.session_state.lesson_data.split("Q:")[0])
                    lang_code = {"العربية": "ar", "English": "en", "Français": "fr", "Deutsch": "de"}[language]
                    tts = gTTS(text=audio_text[:600], lang=lang_code)
                    tts.save("voice.mp3")
                except Exception:
                    st.warning("تم توليد الدرس، ولكن حدث خطأ في إنشاء الملف الصوتي.")

                st.rerun()
                
        except Exception as e: 
            st.error(f"حدث خطأ: {e}")
            st.info("تأكد من أنك قمت بإضافة GEMINI_API_KEY في إعدادات Secrets على Streamlit Cloud.")

# --- Display Area ---
if st.session_state.lesson_data:
    raw_content = st.session_state.lesson_data
    dir_css = "rtl" if language == "العربية" else "ltr"
    
    # عرض مشغل الصوت إذا كان متاحاً
    if os.path.exists("voice.mp3"):
        st.audio("voice.mp3")

    if "Comic" in output_format:
        # تقسيم المحتوى بناءً على اللوحات
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
                    # استخدام نموذج Flux لصور الكوميكس
                    vis_query = vis.group(1).strip().replace(' ', '%20')
                    st.image(f"https://pollinations.ai/p/comic%20style%20{vis_query}?width=600&height=400&seed={i}&model=flux")
                if dia: st.markdown(f'<div class="dialogue-text">💬 {dia.group(1).strip()}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        # عرض فيديو يوتيوب تعليمي
        v_url = get_youtube_video(topic, language)
        if v_url: 
            st.markdown(f'<iframe width="100%" height="500" src="{v_url}" frameborder="0" allowfullscreen style="border-radius:15px; margin-bottom:20px;"></iframe>', unsafe_allow_html=True)
        
        body = raw_content.split("Q:")[0]
        # استخراج الصور التوضيحية
        img_match = re.search(r'\[\[(.*?)\]\]', body)
        if img_match: 
            img_query = img_match.group(1).replace(' ', '%20')
            st.image(f"https://pollinations.ai/p/{img_query}?width=1024&height=500&model=flux")
        
        # تنسيق نص الدرس
        clean_body = re.sub(r"\[\[.*?\]\]", "", body).replace("###", "📌").replace("\n","<br>")
        st.markdown(f'<div class="lesson-box" style="direction:{dir_css}">{clean_body}</div>', unsafe_allow_html=True)

    # --- Interactive Quiz Section ---
    st.divider()
    st.header("🧠 اختبر معلوماتك")
    q_blocks = re.findall(r"Q:(.*?)Correct:(.*?)Explanation:(.*?)(?=Q:|$)", raw_content, re.DOTALL)
    
    for i, (q_raw, correct, expl) in enumerate(q_blocks):
        qid = f"quiz_{i}"
        with st.container():
            st.markdown(f'<div class="quiz-container" style="direction:{dir_css}">', unsafe_allow_html=True)
            q_text = q_raw.split("A)")[0].strip()
            st.write(f"**سؤال {i+1}:** {q_text}")
            
            options = re.findall(r"([A-C]\) .*?)(?=[A-C]\)|Correct:|$)", q_raw, re.DOTALL)
            
            if options:
                user_choice = st.radio(f"اختر الإجابة الصحيحة لـ س{i+1}:", options, key=f"radio_{i}", index=None)
                
                if st.button(f"تحقق من الإجابة ✔️", key=f"btn_{i}"):
                    if user_choice:
                        is_correct = user_choice[0] == correct.strip()
                        st.session_state.quiz_results[qid] = {"correct": is_correct, "expl": expl, "ans": correct.strip()}
                        if is_correct: st.session_state.score += 10
                        st.rerun()
                    else:
                        st.warning("الرجاء اختيار إجابة أولاً.")
                
                if qid in st.session_state.quiz_results:
                    res = st.session_state.quiz_results[qid]
                    if res["correct"]:
                        st.markdown(f'<div class="correct-feedback">✅ رائع يا {student_name}! إجابة صحيحة. <br> {res["expl"]}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<div class="wrong-feedback">❌ محاولة جيدة، لكن الإجابة الصحيحة هي {res["ans"]}. <br> {res["expl"]}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.score >= 40: 
        st.balloons()
        st.success(f"تهانينا {student_name}! لقد أتممت الدرس بنجاح وبدرجة كاملة! 🏆")
