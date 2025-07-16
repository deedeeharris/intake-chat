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
    .stChatInput > div {
        flex-direction: row-reverse;
    }
    </style>
""", unsafe_allow_html=True)

# ====== Login ======
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state.get("password") == st.secrets.get("password"):
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if not st.session_state.get("password_correct"):
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.stop()
    return True

check_password()

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
    st.error(f"Secret key not found: {e}. Please ensure all required secrets are set.")
    st.stop()

# ====== Sidebar ======
with st.sidebar:
    st.header("אפשרויות")
    if st.button("שיחה חדשה"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.get("messages"):
        if st.button("נתח את כל השיחה לפי קטגוריות"):
            # Analysis logic remains the same
            chat_history_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
            )
            gpt_prompt = (
                "שוחחת עם מועמד/ת במסלול קדם-צבאי. להלן היסטוריית השיחה המלאה, ולאחר מכן בקשה לניתוח חינוכי דידקטי :"
                "\n---\n" + chat_history_text + "\n---\n" + ANALYSIS_PROMPT_HE
            )
            st.info("הבקשה נשלחת לניתוח ב-GPT-4, המתן/י בסבלנות...")
            with st.spinner("ניתוח האינטייק..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4-turbo",
                        messages=[
                            {"role": "system", "content": "אתה יועץ חינוכי, מראיין, ומסכם צ'אט אינטייק למועמד/ת בגישה מקצועית בעברית."},
                            {"role": "user", "content": gpt_prompt}
                        ],
                        temperature=0.3,
                        max_tokens=1200
                    )
                    st.session_state.analysis = response.choices[0].message.content
                except Exception as e:
                    st.error(f"Error during analysis: {e}")

# ====== Chat Initialization & First Message LOGIC ======
if "messages" not in st.session_state:
    st.session_state.messages = []

# If the chat is empty, fetch the initial greeting but DO NOT display it here.
if not st.session_state.messages:
    with st.spinner("מכין את הצ'אט..."):
        try:
            initial_prompt = [
                {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
                {"role": "user", "content": "Please start the conversation in Hebrew by introducing yourself and asking your first question."}
            ]
            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=initial_prompt,
            )
            initial_message = response.choices[0].message.content
            # Add the AI's first message to the session state
            st.session_state.messages.append({"role": "assistant", "content": initial_message})
            # Rerun the script to display the message from the history
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred while starting the chat: {e}")
            st.stop()

# ====== Display Full Chat History (Single Source of Truth) ======
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ====== Handle User Input ======
if prompt := st.chat_input("כתבו כאן..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display the user's message immediately
    with st.chat_message("user"):
        st.markdown(prompt)

    messages_for_api = [{"role": "system", "content": INTAKE_SYSTEM_PROMPT}]
    messages_for_api.extend(st.session_state.messages)

    try:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            stream = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages_for_api,
                stream=True,
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    response_placeholder.markdown(full_response + "▌")
            response_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    except Exception as e:
        st.error(f"An error occurred: {e}")

# ====== Display Analysis Result ======
if "analysis" in st.session_state:
    with st.expander("ניתוח האינטייק לקטגוריות:", expanded=True):
        st.markdown(st.session_state.analysis)
