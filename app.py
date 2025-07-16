import streamlit as st
from openai import OpenAI
import time

# ====== הצגת RTL ב-Streamlit ======
st.markdown("""
    <style>
    .element-container, .stChatMessage { direction: rtl !important; }
    .stTextInput input { text-align: right; }
    </style>
""", unsafe_allow_html=True)

# ====== הגדרת קטגוריות ו-PROMPT לניתוח ======
ANALYSIS_PROMPT_HE = """
קיבלת צ'אט מלא של אינטייק תוכנית מכינה בעברית בין מועמד/ת לעוזר דיגיטלי.
לסיום, נתח את תשובות המועמד/ת לפי הקטגוריות הבאות. לכל קטגוריה כתוב סיכום קצר, התייחס לכוחות, אתגרים ותפיסות עיקריות שעלו מהתשובות, וצטט תשובות רלוונטיות בקצרה:
1. התפתחות אישית ותפיסת עצמי
2. מוטיבציה ושאיפות
3. מעורבות חברתית ומודעות קהילתית
4. פתיחות וגיוון
5. קבלת החלטות ועצמאות
6. מידע נוסף

סיים בתמצית תובנות מרכזיות על המועמד/ת בלשון מחנכים. אל תעתיק את השאלות אלא התמקד בניתוח של התוכן.
"""

# ====== הפעלה ======
OPENAI_API_KEY = st.secrets["openai_api_key"]
ASSISTANT_ID = st.secrets["assistant_id"]
client = OpenAI(api_key=OPENAI_API_KEY)

APP_TITLE = "אינטייק - תצוגת תכלית ראושנית"
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# ====== אתחול שיחה ======
if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "messages" not in st.session_state:
    st.session_state.messages = []

# ====== הצגת כל ההודעות מהיסטוריית השיחה ======
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ====== קלט משתמש ======
if prompt := st.chat_input("כתבו כאן..."):
    # עדכון תצוגה
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    # הוספה ל-assistant
    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )
    with st.spinner("האסיסטנט חושב..."):
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=ASSISTANT_ID,
        )
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                st.error("האסיסטנט נכשל בשליחה.")
                break
            time.sleep(1)
        # תשובה אחרונה מהאסיסטנט
        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread_id
        )
        assistant_msg = None
        for message in reversed(messages.data):
            if message.role == "assistant":
                assistant_msg = message.content[0].text.value
                break
        if assistant_msg:
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_msg}
            )
            with st.chat_message("assistant"):
                st.markdown(assistant_msg)
        else:
            st.error("לא התקבלה תגובה מהאסיסטנט.")

st.markdown("---")
# ====== הצגת היסטוריית שיחה ======
with st.expander("הצג היסטוריית שיחה"):
    for m in st.session_state.messages:
        st.write(f"**{m['role']}**: {m['content']}")

# ====== כפתור ניתוח לקטגוריות ב-gpt-4.1 ======
if st.button("נתח את כל השיחה לפי קטגוריות (gpt-4.1)"):
    chat_history_text = "\n".join(
        [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
    )
    gpt_prompt = (
        "שוחחת עם מועמד/ת במסלול קדם-צבאי. להלן היסטוריית השיחה המלאה, ולאחר מכן בקשה לניתוח חינוכי דידקטי לפי קטגוריות:"
        "\n---\n"
        + chat_history_text
        + "\n---\n"
        + ANALYSIS_PROMPT_HE
    )
    st.info("הבקשה נשלחת לניתוח ב-GPT-4.1, המתן/י בסבלנות...")
    with st.spinner("מנתח ב-GPT-4.1..."):
        response = client.chat.completions.create(
            model="gpt-4.1",  # עברנו למודל החדש ביותר[1][2][3][4][9]
            messages=[
                {"role": "system", "content": "אתה יועץ חינוכי, מראיין, ומסכם צ'אט אינטייק למועמד/ת בגישה מקצועית בעברית."},
                {"role": "user", "content": gpt_prompt}
            ],
            temperature=0.4,
            max_tokens=1200
        )
        analysis_result = response.choices[0].message.content
    st.subheader("ניתוח האינטייק לקטגוריות:")
    st.markdown(analysis_result)

