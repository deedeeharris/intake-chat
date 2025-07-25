import streamlit as st
from openai import OpenAI
import time

# ====== Page Configuration ======
APP_TITLE = "אינטייק - תצוגת תכלית"
st.set_page_config(page_title=APP_TITLE, layout="wide")
# The main title is now part of the login screen, so we can remove it from here if we want
# st.title(APP_TITLE) # You can uncomment this if you want the title on the main chat page too

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


# ====== NEW: Login & Introduction Function ======
def show_login_screen():
    """
    Displays the combined login and introduction screen.
    This function will take over the screen until the password is correct.
    """
    # Stop if the password is already correct
    if st.session_state.get("password_correct", False):
        return True

    # --- UI for the Login Screen ---
    st.title("אינטייק - תצוגת תכלית")
    st.header("👋 ברוכים הבאים!")

    # New, more detailed introduction
    st.markdown("""
    זוהי הדגמה (Proof of Concept) של מערכת אינטייק חכמה, המבוססת על צ'אט אינטראקטיבי.

    **המטרה שלנו היא כפולה:**
    1.  **לשפר את חווית המועמד/ת:** להחליף טפסים ארוכים ומייגעים בשיחה טבעית וזורמת שנעים יותר למלא.
    2.  **לייעל את עבודת המדריכים:** המערכת אוספת את כל המידע מהשיחה, מנתחת אותו באופן אוטומטי, ומפיקה סיכום תובנות ממוקד. זה חוסך זמן יקר ומכין את המדריך לפגישה הראשונה בצורה מיטבית.

    כדי להתחיל את ההדגמה, אנא הזינו את הסיסמה למטה.
    """)

    def password_entered():
        """Callback to check the password."""
        if st.session_state.get("password") == st.secrets.get("password"):
            st.session_state["password_correct"] = True
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
            st.error("הסיסמה שהוזנה אינה נכונה.")

    # Password input field
    st.text_input(
        "סיסמה",
        type="password",
        on_change=password_entered,
        key="password"
    )

    # This part is crucial: it stops the rest of the app from running
    # until the password is correct.
    st.stop()


# --- Call the login screen at the very start of the script ---
show_login_screen()


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

# ====== DELETED: The old toast/popup section is gone ======


# ====== Sidebar ======
with st.sidebar:
    st.header("אפשרויות")
    if st.button("שיחה חדשה"):
        # Clear session state but keep the password correct status
        is_authed = st.session_state.get("password_correct", False)
        st.session_state.clear()
        st.session_state.password_correct = is_authed
        st.rerun()

    if st.session_state.get("messages"):
        if st.button("נתח את כל השיחה לפי קטגוריות"):
            chat_history_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in st.session_state.messages]
            )
            gpt_prompt = (
                "שוחחת עם מועמד/ת במסלול קדם-צבאי. להלן היסטוריית השיחה המלאה, ולאחר מכן בקשה לניתוח חינוכי דידקטי :"
                "\n---\n" + chat_history_text + "\n---\n" + ANALYSIS_PROMPT_HE
            )
            st.info("הבקשה נשלחת לניתוח, המתן/י בסבלנות...")
            with st.spinner("מנתח את האינטייק..."):
                try:
                    response = client.chat.completions.create(
                        model="gpt-4.1",
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

if not st.session_state.messages:
    with st.spinner("מכין את הצ'אט..."):
        try:
            initial_prompt = [
                {"role": "system", "content": INTAKE_SYSTEM_PROMPT},
                {"role": "user", "content": "Please start the conversation in Hebrew by introducing yourself and asking your first question."}
            ]
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=initial_prompt,
                temperature=0.3
            )
            initial_message = response.choices[0].message.content
            st.session_state.messages.append({"role": "assistant", "content": initial_message})
            st.rerun()
        except Exception as e:
            st.error(f"An error occurred while starting the chat: {e}")
            st.stop()

# ====== Display Full Chat History ======
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ====== Handle User Input ======
if prompt := st.chat_input("כתבו כאן..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    messages_for_api = [{"role": "system", "content": INTAKE_SYSTEM_PROMPT}]
    messages_for_api.extend(st.session_state.messages)

    try:
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            full_response = ""
            stream = client.chat.completions.create(
                model="gpt-4.1",
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
