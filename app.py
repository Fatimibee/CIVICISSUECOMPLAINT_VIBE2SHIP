import streamlit as st
import requests
import json

# Set page layout configuration
st.set_page_config(page_title="Civic Shield Admin Dashboard", page_icon="🏢", layout="wide")

# Custom styling
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🏢 Civic Issue Reporting System")
st.subheader("AI-Powered Workflow Routing & Automated Dispatch")
st.write("---")

import os
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# Maintain state management across app interactions
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None
if "current_draft" not in st.session_state:
    st.session_state.current_draft = ""

col1, col2 = st.columns([1, 1.5], gap="large")

with col1:
    st.markdown("### 📤 Step 1: File Incident Report")
    user_email = st.text_input("Citizen Email Address", placeholder="e.g., citizen@email.com")
    location = st.text_input("Incident Location / Landmark", placeholder="e.g., Ward No. 4, SKIT Campus")
    uploaded_file = st.file_uploader("Upload Infrastructure Evidence (Image)", type=["jpg", "jpeg", "png"])
    
    submit_btn = st.button("🚀 Process & Route Issue", type="primary")

with col2:
    st.markdown("### ⚙️ Graph Workflow Processing Monitor")
    
    if submit_btn:
        if not user_email or not location or not uploaded_file:
            st.error("🚨 Please fill out all fields and provide an image file.")
        else:
            with st.spinner("Uploading binary image and streaming agent nodes..."):
                try:
                    # 1. Structure the multipart data payload instead of JSON
                    file_payload = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    form_payload = {
                        "userEmail": user_email,
                        "location": location
                    }
                    
                    # Hit your exact /start_issue endpoint using files and data parameters
                    response = requests.post(
                        f"{BACKEND_URL}/start_issue", 
                        files=file_payload, 
                        data=form_payload
                    )
                    
                    if response.status_code == 200:
                        res_data = response.json()
                        status = res_data.get("status")
                        
                        if status == "IMAGE_TOO_UNCLEAR":
                            st.error(f"❌ Core Reject Node: {res_data.get('message')}")
                            
                        elif status == "WAITING_FOR_APPROVAL":
                            st.session_state.thread_id = res_data.get("thread_id")
                            st.session_state.current_draft = res_data.get("emailDraft", "")
                            st.success(f"🟢 Classification complete: Recognized '{res_data.get('issue')}' layout context.")
                    else:
                        st.error(f"Server integration failure code: {response.status_code}")
                        st.json(response.json()) # Inspect validation complaints if any remain
                        
                except Exception as ex:
                    st.error(f"Failed to communicate with system cluster backend: {ex}")

    # 2. Render Human-in-the-Loop review panel once thread_id is locked in state
    if st.session_state.thread_id:
        st.write("---")
        st.markdown("### 📝 Step 2: Human-in-the-Loop Review Panel")
        
        editable_draft = st.text_area("Review / Tweak Department Email Payload", value=st.session_state.current_draft, height=250)
        
        review_col1, review_col2 = st.columns(2)
        
        with review_col1:
            if st.button("✅ Approve & Dispatch Email", type="primary"):
                with st.spinner("Confirming graph execution state changes..."):
                    # Match your Pydantic HumanAction structure (Sent as clean JSON body)
                    action_payload = {
                        "thread_id": st.session_state.thread_id,
                        "approval": True,
                        "suggestion": None
                    }
                    res = requests.post(f"{BACKEND_URL}/human_action", json=action_payload)
                    if res.status_code == 200:
                        st.balloons()
                        st.success("🎉 Transaction Completed! Email sent and database logs updated successfully.")
                        st.session_state.thread_id = None
                        st.session_state.current_draft = ""
                    else:
                        st.error("Failed to post final graph approval sequence.")
                        
        with review_col2:
            feedback = st.text_input("Enter rewrite suggestions for the AI:")
            if st.button("🔄 Request Regeneration"):
                if not feedback:
                    st.warning("Please specify modification parameters before executing regeneration routing.")
                else:
                    with st.spinner("Rewriting dynamic state metrics..."):
                        action_payload = {
                            "thread_id": st.session_state.thread_id,
                            "approval": False,
                            "suggestion": feedback
                        }
                        res = requests.post(f"{BACKEND_URL}/human_action", json=action_payload)
                        if res.status_code == 200:
                            st.info("🔄 Suggestion applied! (Note: Refresh graph stream to pull updated model output text layout)")