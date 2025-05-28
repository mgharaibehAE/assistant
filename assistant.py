import streamlit as st
import openai
import pyperclip
import time
import requests
from io import BytesIO
from docx import Document

# Streamlit app configuration
st.set_page_config(page_title="Assistant", page_icon="🤖", layout="centered")

# Constants from secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
ASSISTANT_ID = st.secrets["ASSISTANT_ID"]
PASSWORD = st.secrets["login"]["password"]

# Sidebar for clearing chat and additional information
with st.sidebar:
    st.markdown("""
    **Disclaimer:** Regulatory Assistant can make mistakes. Check important info carefully.
    """)
    st.markdown("""
    **Instructions:**
    - Enter your queries clearly.
    - Use the "Clear Chat" button to reset your conversation.
    - Copy important responses using provided buttons.
    - Export chat history if needed.
    """)
    if st.button("Clear Chat"):
        for key in ["messages", "thread_id", "authenticated"]:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

# Authentication logic (fixed)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd_input = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if pwd_input == PASSWORD:
            st.session_state.authenticated = True
            st.success("Login successful! Refreshing...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

st.title("Cleco Regulatory Assistant")

# Tabs setup
chat_tab, summary_tab = st.tabs(["Chat", "Document Summaries"])

with chat_tab:
    # Setup OpenAI API key
    openai.api_key = OPENAI_API_KEY

    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Initialize thread
    if "thread_id" not in st.session_state:
        thread = openai.beta.threads.create()
        st.session_state.thread_id = thread.id

    # Display previous messages
    for idx, message in enumerate(st.session_state.messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                clipboard_button(message["content"], f"Copy Response {idx}")


    # User input and interaction
    if prompt := st.chat_input("Ask a question..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        openai.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        run = openai.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=ASSISTANT_ID
        )

        with st.spinner("Assistant is typing..."):
            while run.status not in ("completed", "failed"):
                time.sleep(1)
                run = openai.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )

        if run.status == "completed":
            messages = openai.beta.threads.messages.list(
                thread_id=st.session_state.thread_id
            )

            response = ""
            for msg in messages.data:
                if msg.role == "assistant":
                    response = msg.content[0].text.value
                    break

            st.session_state.messages.append({"role": "assistant", "content": response})

            with st.chat_message("assistant"):
                st.markdown(response)
                if st.button("Copy Response", key=f"copy_latest_{len(st.session_state.messages)}"):
                    pyperclip.copy(response)
                    st.toast("Copied to clipboard!")
        else:
            st.error("The assistant run failed. Please try again.")

    # Export chat history
    def export_chat_history(messages):
        chat_history = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" for msg in messages
        )
        st.download_button(
            "Download Chat History", chat_history, file_name="chat_history.txt"
        )

    export_chat_history(st.session_state.messages)

with summary_tab:
    GITHUB_USER = "mgharaibehAE"
    GITHUB_REPO = "assistant"
    BRANCH = "main"
    DOCS_FOLDER = "docs"

    api_url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{DOCS_FOLDER}?ref={BRANCH}"

    response = requests.get(api_url)

    if response.status_code == 200:
        files = [file['name'] for file in response.json() if file['name'].endswith('.docx')]

        if files:
            selected_file = st.selectbox("Select a document:", files)

            if st.button("Go to Summary"):
                file_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}/{DOCS_FOLDER}/{selected_file}"
                file_response = requests.get(file_url)

                if file_response.status_code == 200:
                    doc_stream = BytesIO(file_response.content)
                    doc = Document(doc_stream)
                    content = "\n\n".join(para.text for para in doc.paragraphs)
                    st.markdown(content, unsafe_allow_html=True)
                else:
                    st.error(f"Failed to retrieve document content. (HTTP {file_response.status_code})")
        else:
            st.error("No Word (.docx) documents found in the specified directory.")
    else:
        st.error(f"Failed to fetch file list from GitHub. (HTTP {response.status_code})")
