import streamlit as st
from openai import OpenAI
import time

# ====== Page Configuration ======
APP_TITLE = "אינטייק - תצוגת תכלית"
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

# ====== RTL Support ======
st.markdown("""
    <style>
    .element-container, .stChatMessage { direction: rtl !important; }
    .stTextInput input { text-align: right; }
    .stSidebar {
        position: fixed;
        top: 0;
        left: 0;
        height: 100%;
        width: 250px;
        padding: 20px;
    }
    </style>
""", unsafe_allow_html=True)

# ====== Login ======
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "Password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 סיסמה לא נכונה")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()

# ====== OpenAI Configuration ======
try:
    OPENAI_API_KEY = st.secrets["openai_api_key"]
    ASSISTANT_ID = st.secrets["assistant_id"]
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    st.error(f"Error initializing OpenAI: {e}")
    st.stop()


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

# ====== Sidebar ======
with st.sidebar:
    st.header("אפשרויות")
    if st.button("שיחה חדשה"):
        st.session_state.clear()
        st.experimental_rerun()

    if "messages" in st.session_state and st.session_state.messages:
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
                try:
                    response = client.chat.completions.create(
                        model="gpt-4.1",
                        messages=[
                            {"role": "system", "content": "אתה יועץ חינוכי, מראיין, ומסכם צ'אט אינטייק למועמד/ת בגישה מקצועית בעברית."},
                            {"role": "user", "content": gpt_prompt}
                        ],
                        temperature=0.4,
                        max_tokens=1200
                    )
                    analysis_result = response.choices[0].message.content
                    st.session_state.analysis = analysis_result
                except Exception as e:
                    st.error(f"Error during analysis: {e}")


# ====== Chat Initialization ======
if "thread_id" not in st.session_state:
    try:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.session_state.messages = []
    except Exception as e:
        st.error(f"Error creating new thread: {e}")
        st.stop()


# ====== Display Chat History ======
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ====== User Input ======
if prompt := st.chat_input("כתבו כאן..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
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
            while run.status != "completed":
                time.sleep(0.5)
                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )
                if run.status == "failed":
                    st.error("האסיסטנט נכשל בשליחה.")
                    break

            messages = client.beta.threads.messages.list(
                thread_id=st.session_state.thread_id
            )
            assistant_msg = messages.data[0].content[0].text.value
            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_msg}
            )
            with st.chat_message("assistant"):
                st.markdown(assistant_msg)

    except Exception as e:
        st.error(f"An error occurred: {e}")


# ====== Display Analysis Result ======
if "analysis" in st.session_state:
    with st.expander("ניתוח האינטייק לקטגוריות:", expanded=True):
        st.markdown(st.session_state.analysis)
