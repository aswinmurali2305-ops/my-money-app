import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# --- CONFIG ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- DATA ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read()
        for c in ["Name", "Date", "Time", "Amount", "Status"]:
            if c not in data.columns: data[c] = None
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = load_data()

# --- TOP BAR ---
c_top1, c_top2, c_top3 = st.columns([1, 4, 1])
if c_top1.button("🔄 Refresh"):
    st.rerun()
with c_top3:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# --- NAVIGATION ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Log History", "Client Section", "Calendar"])

# --- PAGE: DASHBOARD ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    
    t = datetime.now().date()
    # Monday-Sunday Logic
    w_start = t - timedelta(days=t.weekday())
    m_start = t.replace(day=1)
    
    m_df = df[df['Date'] >= m_start]
    w_df = df[df['Date'] >= w_start]
    
    col1, col2 = st.columns(2)
    col1.metric("Services (Month)", len(m_df))
    col2.metric("Services (Week)", len(w_df))
    
    paid_m = m_df[m_df['Status'] == 'Paid']['Amount'].astype(float).sum()
    pend_t = df[df['Status'] == 'Pending']['Amount'].astype(float).sum()
    
    col3, col4 = st.columns(2)
    col3.metric("Received (Month)", f"{paid_m} CAD")
    col4.metric("Total Pending", f"{pend_t} CAD")

    st.divider()
    st.subheader("📝 New Service Entry")
    with st.form("entry"):
        n = st.text_input("Customer Name")
        d = st.date_input("Date", t)
        tm = st.time_input("Time", datetime.now().time())
        st.caption("Auto-set: 15 CAD | Pending Payment")
        if st.form_submit_button("Add Record"):
            if n:
                row = pd.DataFrame([{"Name":n,"Date":str(d),"Time":tm.strftime("%I:%M %p"),"Amount":15.0,"Status":"Pending"}])
                conn.update(data=pd.concat([df, row], ignore_index=True))
                st.success("Saved!")
                st.rerun()

    st.divider()
    e1, e2 = st.columns(2)
    ex_io = io.BytesIO()
    df.to_excel(ex_io, index=False, engine='openpyxl')
    e1.download_button("📂 Excel", data=ex_io.getvalue(), file_name="logs.xlsx")
    
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Coaching Logs", ln=1, align='C')
    for _, r in df.iterrows():
        pdf.cell(200, 10, txt=f"{r['Date']} | {r['Name']} | {r['Amount']} CAD", ln=True)
    e2.download_button("📂 PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="logs.pdf")

# --- PAGE: LOG HISTORY ---
elif menu == "Log History":
    st.title("📂 History")
    f1, f2 = st.columns(2)
    sd = f1.date_input("From", datetime.now().date() - timedelta(days=30))
    ed = f2.date_input("To", datetime.now().date())
    
    filt = df[(df['Date'] >= sd) & (df['Date'] <= ed)]
    for i, r in filt.iterrows():
        with st.expander(f"{r['Date']} - {r['Name']}"):
            if st.button("Delete", key=f"d{i}"):
                conn.update(data=df.drop(i)); st.rerun()

# --- PAGE: CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Clients")
    u = df['Name'].unique()
    target = st.selectbox("Select Client", u)
    h = df[df['Name'] == target]
    
    for i, r in h.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"{r['Date']} @ {r['Time']}")
        if c2.button("Delete", key=f"cd{i}"):
            conn.update(data=df.drop(i)); st.rerun()
        if r['Status'] == 'Pending':
            if c3.button("Paid", key=f"cp{i}"):
                df.at[i, 'Status'] = 'Paid'
                conn.update(data=df); st.rerun()
    
    st.divider()
    due = h[h['Status'] == 'Pending']['Amount'].astype(float).sum()
    if due > 0:
        msg = f"Hi {target}, your coaching sessions are pending. Total: {due} CAD. Please pay ASAP!"
        st.text_area("Reminder", msg)

# --- PAGE: CALENDAR ---
elif menu == "Calendar":
    st.title("📅 Calendar")
    p = st.date_input("Pick Date")
    res = df[df['Date'] == p]
    if not res.empty:
        st.table(res[['Time', 'Name', 'Status']])
    else:
        st.info("No records.")
