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
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    st.error(f"Error initializing OpenAI: {e}")
    st.stop()

# ====== Prompts ======
try:
    ANALYSIS_PROMPT_HE = st.secrets["ANALYSIS_PROMPT_HE"]
    INTAKE_SYSTEM_PROMPT = st.secrets["INTAKE_SYSTEM_PROMPT"]
except KeyError as e:
    st.error(f"Secret key not found: {e}. Please ensure ANALYSIS_PROMPT_HE and INTAKE_SYSTEM_PROMPT are set in your Streamlit secrets.")
    st.stop()


# ====== Sidebar ======
with st.sidebar:
    st.header("אפשרויות")
    if st.button("שיחה חדשה"):
        st.session_state.clear()
        st.rerun()

    if "messages" in st.session_state and st.session_state.messages:
        if st.button("נתח את כל השיחה לפי קטגוריות"):
            chat_history_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
            )
            gpt_prompt = (
                "שוחחת עם מועמד/ת במסלול קדם-צבאי. להלן היסטוריית השיחה המלאה, ולאחר מכן בקשה לניתוח חינוכי דידקטי :"
                "\n---\n"
                + chat_history_text
                + "\n---\n"
                + ANALYSIS_PROMPT_HE
            )
            st.info("הבקשה נשלחת לניתוח ב-GPT-4.1, המתן/י בסבלנות...")
            with st.spinner("ניתוח האינטייק..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4.1", # Using a powerful model for analysis
                        messages=[
                            {"role": "system", "content": "אתה יועץ חינוכי, מראיין, ומסכם צ'אט אינטייק למועמד/ת בגישה מקצועית בעברית."},
                            {"role": "user", "content": gpt_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=1200
                    )
                    analysis_result = response.choices[0].message.content
                    st.session_state.analysis = analysis_result
                except Exception as e:
                    st.error(f"Error during analysis: {e}")


# ====== Chat Initialization ======
if "messages" not in st.session_state:
    st.session_state.messages = []


# ====== Display Chat History ======
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ====== User Input ======
if prompt := st.chat_input("כתבו כאן..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Construct the message history for the API call
    # The system prompt is always first
    messages_for_api = [{"role": "system", "content": INTAKE_SYSTEM_PROMPT}]
    # Then add all the messages from the session state
    messages_for_api.extend(st.session_state.messages)

    try:
        with st.spinner("חושב..."):
            # Call the ChatCompletion API
            response = client.chat.completions.create(
                model="gpt-4.1", # Specify the desired model
                messages=messages_for_api,
                temperature=0.3, # Adjust temperature as needed for conversation
                max_tokens=1000
            )
            assistant_msg = response.choices[0].message.content

            st.session_state.messages.append(
                {"role": "assistant", "content": assistant_msg}
            )
            with st.chat_message("assistant"):
                st.markdown(assistant_msg)
            # We need to rerun to show the latest message immediately
            st.rerun()

    except Exception as e:
        st.error(f"An error occurred: {e}")


# ====== Display Analysis Result ======
if "analysis" in st.session_state:
    with st.expander("ניתוח האינטייק לקטגוריות:", expanded=True):
        st.markdown(st.session_state.analysis)
