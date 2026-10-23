import pandas as pd
import streamlit as st

from assistant_core import create_assistant
from business_logic import LEADS_FILE
from company_data import COMPANY_CONFIG

st.set_page_config(
    page_title=f"{COMPANY_CONFIG['company_name']} AI Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title(f"🤖 {COMPANY_CONFIG['company_name']} Assistant")
st.caption("A practical LangChain + Groq + Tools website assistant")

with st.sidebar:
    st.header("Company")
    st.write(COMPANY_CONFIG["about"])
    st.write(f"📍 {COMPANY_CONFIG['location']}")
    st.write(f"🕒 {COMPANY_CONFIG['working_hours']}")
    st.divider()
    if st.button("Clear chat"):
        st.session_state.messages = []
        st.rerun()

if "assistant" not in st.session_state:
    st.session_state.assistant = create_assistant()

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("Ask about services, prices, discounts or contact...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = st.session_state.assistant.invoke({
                "messages": st.session_state.messages
            })
            answer = result["messages"][-1].content
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

st.divider()

with st.expander("View captured leads"):
    if LEADS_FILE.exists():
        leads_df = pd.read_csv(LEADS_FILE)
        st.dataframe(leads_df, use_container_width=True)
    else:
        st.info("No leads captured yet.")
import urllib.parse

# Aap ka WhatsApp number links ho gaya hai
WHATSAPP_NUMBER = "923222620169" 

# WhatsApp Button Display Logic
default_text = "Hello PACK IT UP! I am using your AI Assistant and I want to place an order."
encoded_text = urllib.parse.quote(default_text)
whatsapp_url = f"https://wa.me{WHATSAPP_NUMBER}?text={encoded_text}"

st.markdown(
    f"""
    <a href="{whatsapp_url}" target="_blank" style="text-decoration: none;">
        <button style="
            background-color: #25D366;
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 16px;
            font-weight: bold;
            width: 100%;
            margin-top: 15px;
            box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
            text-align: center;">
            🟢 Order via WhatsApp
        </button>
    </a>
    """,
    unsafe_allow_html=True
)
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# Google Sheet connection setup
if "GSHEETS_URL" in st.secrets:
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Agar naya lead mila ho to check karein
        if st.session_state.get("captured_leads"):
            new_lead = st.session_state.captured_leads[-1]
            
            # Maujuda data sheet se read karein
            existing_data = conn.read(spreadsheet=st.secrets["GSHEETS_URL"])
            
            # Check karein agar ye email pehle se save to nahi
            if new_lead['email'] not in existing_data['Email'].values:
                # Naya row tayyar karein
                new_row = pd.DataFrame([{
                    "Name": "Customer",
                    "Email": new_lead['email'],
                    "Phone": new_lead['phone'],
                    "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                
                # Data combine kar ke sheet par update karein
                updated_data = pd.concat([existing_data, new_row], ignore_index=True)
                conn.update(spreadsheet=st.secrets["GSHEETS_URL"], data=updated_data)
                st.success("Lead successfully saved to Google Sheets!")
    except Exception as e:
        st.error(f"Database sync error: {e}")
