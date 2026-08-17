import streamlit as st

st.set_page_config(page_title="PrepPilot", page_icon="🚀")
st.title("PrepPilot")
st.caption("An AI prep & triage copilot for MBA students")

text = st.text_input("Say something")
if text:
    st.write("You said:", text)
