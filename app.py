import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# --- 1. CONFIG ---
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
        req = ["Name", "Date", "Time", "Amount", "Status"]
        if data is None or data.empty:
            return pd.DataFrame(columns=req)
        for col in req:
            if col not in data.columns: data[col] = None
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data[req]
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()

# --- 3. TOP BAR ---
t1, t2, t3 = st.columns([1, 4, 1])
if t1.button("🔄 Refresh"):
    st.rerun()
with t3:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Log History", "Client Section", "Calendar"])

# --- 5. DASHBOARD ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    today = datetime.now().date()
    
    m_start = today.replace(day=1)
    w_start = today - timedelta(days=today.weekday())
    
    this_m = df[df['Date'] >= m_start]
    this_w = df[df['Date'] >= w_start]
    
    c1, c2 = st.columns(2)
    c1.metric("Services (Month)", len(this_m))
    c2.metric("Services (Week)", len(this_w))
    
    paid_val = pd.to_numeric(this_m[this_m['Status'] == 'Paid']['Amount'], errors='coerce').sum()
    pend_val = pd.to_numeric(df[df['Status'] == 'Pending']['Amount'], errors='coerce').sum()
    
    c3, c4 = st.columns(2)
    c3.metric("Received (Month)", f"{paid_val} CAD")
    c4.metric("Total Pending", f"{pend_val} CAD")

    st.divider()
    with st.form("entry_form", clear_on_submit=True):
        n = st.text_input("Customer Name")
        f1, f2 = st.columns(2)
        d = f1.date_input("Date", today)
        tm = f2.time_input("Time", datetime.now().time())
        if st.form_submit_button("Save Record"):
            if n:
                row = pd.DataFrame([{"Name": n, "Date": str(d), "Time": tm.strftime("%I:%M %p"), "Amount": 15.0, "Status": "Pending"}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, row], ignore_index=True))
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
            if st.button("Delete Entry", key=f"del{i}"):
                conn.update(worksheet="Sheet1", data=df.drop(i))
                st.rerun()

# --- 7. CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Clients")
    cl = df['Name'].unique()
    if len(cl) > 0:
        sel = st.selectbox("Select Customer", cl)
        cdf = df[df['Name'] == sel]
        for i, r in cdf.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.write(f"{r['Date']} @ {r['Time']}")
            if col2.button("Del", key=f"cd{i}"):
                conn.update(worksheet="Sheet1", data=df.drop(i))
                st.rerun()
            if r['Status'] == 'Pending' and col3.button("Paid", key=f"cp{i}"):
                df.at[i, 'Status'] = 'Paid'
                conn.update(worksheet="Sheet1", data=df)
                st.rerun()
        
        st.divider()
        due = pd.to_numeric(cdf[cdf['Status'] == 'Pending']['Amount'], errors='coerce').sum()
        if due > 0:
            st.text_area("Reminder Message", f"Hi {sel}, sessions are pending. Total: {due} CAD. Please pay ASAP!")
    else:
        st.info("No records.")

# --- 8. CALENDAR ---
elif menu == "Calendar":
    st.title("📅 Calendar")
    p = st.date_input("Check
