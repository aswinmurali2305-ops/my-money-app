import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# --- 1. SETTINGS ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- 2. DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl=0)
        required = ["Name", "Date", "Time", "Amount", "Status"]
        if data is None or data.empty:
            return pd.DataFrame(columns=required)
        for col in required:
            if col not in data.columns: data[col] = None
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data[required]
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()

# --- 3. TOP BAR ---
t1, t2, t3 = st.columns([1, 4, 1])
if t1.button("🔄 Refresh"):
    st.rerun()

with t3:
    label = "🌙" if not st.session_state.dark_mode else "☀️"
    if st.button(label):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Log History", "Client Section", "Calendar"])

# --- 5. DASHBOARD ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    this_month = df[df['Date'] >= month_start]
    this_week = df[df['Date'] >= start_of_week]
    
    m1, m2 = st.columns(2)
    m1.metric("Services (Month)", len(this_month))
    m2.metric("Services (Week)", len(this_week))
    
    paid_total = pd.to_numeric(this_month[this_month['Status'] == 'Paid']['Amount'], errors='coerce').sum()
    pend_total = pd.to_numeric(df[df['Status'] == 'Pending']['Amount'], errors='coerce').sum()
    
    m3, m4 = st.columns(2)
    m3.metric("Received (Month)", f"{paid_total} CAD")
    m4.metric("Total Pending", f"{pend_total} CAD")

    st.divider()
    st.subheader("📝 Quick Entry")
    with st.form("entry_form", clear_on_submit=True):
        c_name = st.text_input("Customer Name")
        c1, c2 = st.columns(2)
        c_date = c1.date_input("Date", today)
        c_time = c2.time_input("Time", datetime.now().time())
        st.info("Cost: 15 CAD | Status: Pending")
        
        if st.form_submit_button("Save Entry"):
            if c_name:
                new_row = pd.DataFrame([{
                    "Name": c_name, "Date": str(c_date), 
                    "Time": c_time.strftime("%I:%M %p"), 
                    "Amount": 15.0, "Status": "Pending"
                }])
                updated = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated)
                st.success("Saved!")
                st.rerun()

# --- 6. LOG HISTORY ---
elif menu == "Log History":
    st.title("📂 History")
    sd = st.date_input("From", datetime.now().date() - timedelta(days=30))
    ed = st.date_input("To", datetime.now().date())
    
    filt = df[(df['Date'] >= sd) & (df['Date'] <= ed)]
    for i, r in filt.iterrows():
        with st.expander(f"{r['Date']} - {r['Name']}"):
            if st.button("Delete", key=f"d{i}"):
                conn.update(worksheet="Sheet1", data=df.drop
