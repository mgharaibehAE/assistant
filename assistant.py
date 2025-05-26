import streamlit as st
import openai
import pyperclip
import time

# Streamlit app configuration
st.set_page_config(page_title="ChatGPT Clone", page_icon="🤖", layout="centered")

# Constants from secrets
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
ASSISTANT_ID = st.secrets["ASSISTANT_ID"]
PASSWORD = st.secrets["PASSWORD"]

# Sidebar for clearing chat
with st.sidebar:
    if st.button("Clear Chat"):
        for key in ["messages", "thread_id", "authenticated"]:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

# Authentication
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    pwd_input = st.text_input("Enter Password", type="password")
    if st.button("Login"):
        if pwd_input == PASSWORD:
            st.session_state.authenticated = True
            st.experimental_rerun()
        else:
            st.error("Incorrect password")
    st.stop()

st.title("ChatGPT")

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
            if st.button(f"Copy Response {idx}", key=f"copy_{idx}"):
                pyperclip.copy(message["content"])
                st.toast("Copied to clipboard!")

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
