import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# --- 1. CONFIG ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

# Custom CSS for Mobile and Buttons
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
        data = conn.read()
        for col in ["Name", "Date", "Time", "Amount", "Status"]:
            if col not in data.columns: data[col] = None
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()

# --- 3. TOP BAR (Refresh & Dark Mode) ---
h_left, h_mid, h_right = st.columns([1, 4, 1])
if h_left.button("🔄"):
    st.rerun()
with h_right:
    label = "🌙" if not st.session_state.dark_mode else "☀️"
    if st.button(label):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Log History", "Client Section", "Calendar"])

# --- 5. DASHBOARD PAGE ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    
    today = datetime.now().date()
    # Monday to Sunday logic
    start_of_week = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    this_month = df[df['Date'] >= month_start]
    this_week = df[df['Date'] >= start_of_week]
    
    # Metrics
    c1, c2 = st.columns(2)
    c1.metric("Services (Month)", len(this_month))
    c2.metric("Services (Week)", len(this_week))
    
    paid_m = this_month[this_month['Status'] == 'Paid']['Amount'].astype(float).sum()
    pending_total = df[df['Status'] == 'Pending']['Amount'].astype(float).sum()
    
    c3, c4 = st.columns(2)
    c3.metric("Money Received (Month)", f"{paid_m} CAD")
    c4.metric("Pending Total Amount", f"{pending_total} CAD")

    st.divider()
    st.subheader("📝 Quick Service Entry")
    with st.form("entry_form", clear_on_submit=True):
        name = st.text_input("Customer Name")
        f1, f2 = st.columns(2)
        d_val = f1.date_input("Date", today)
        t_val = f2.time_input("Time", datetime.now().time())
        st.caption("Default: 15 CAD | Status: Pending")
        
        if st.form_submit_button("Add Service"):
            if name:
                new_row = pd.DataFrame([{
                    "Name": name, "Date": str(d_val), 
                    "Time": t_val.strftime("%I:%M %p"), 
                    "Amount": 15.0, "Status": "Pending"
                }])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                st.success("Entry Saved!")
                st.rerun()

    st.divider()
    # Bottom Export
    ex1, ex2 = st.columns(2)
    excel_data = io.BytesIO()
    df.to_excel(excel_data, index=False, engine='openpyxl')
    ex1.download_button("📂 Export to Excel", data=excel_data.getvalue(), file_name="logs.xlsx")
    
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Aswin's Money Manager Logs", ln=1, align='C')
    for _, r in df.iterrows():
        pdf.cell(200, 10, txt=f"{r['Date']} | {r['Name']} | {r['Amount']} CAD", ln=True)
    ex2.download_button("📂 Export to PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="logs.pdf")

# --- 6. LOG HISTORY PAGE ---
elif menu == "Log History":
    st.title("📂 Log History")
    col_a, col_b = st.columns(2)
    sd = col_a.date_input("Start Date", datetime.now().date() - timedelta(days=30))
    ed = col_b.date_input("End Date", datetime.now().date())
    
    filtered = df[(df['Date'] >= sd) & (df['Date'] <= ed)]
    for i, r in filtered.iterrows():
        with st.expander(f"{r['Date']} at {r['Time']} - {r['Name']}"):
            b1, b2 = st.columns(2)
            if b1.button("Edit", key=f"e{i}"): st.info("Edit mode active")
            if b2.button("Delete", key=f"d{i}"):
                conn.update(data=df.drop(i)); st.rerun()

# --- 7. CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Client Section")
    u_clients = df['Name'].unique()
    target = st.selectbox("Select Client", u_clients)
    c_hist = df[df['Name'] == target]
    
    for i, r in c_hist.iterrows():
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        col1.write(f"{r['Date']} @ {r['Time']}")
        if col2.button("Edit", key=f"ce{i}"): pass
        if col3.button("Delete", key=f"cd{i}"):
            conn.update(data=df.drop(i)); st.rerun()
        if r['Status'] == 'Pending':
            if col4.button("Paid", key=f"cp{i}"):
                df.at[i, 'Status'] = 'Paid'
                conn.update(data=df); st.rerun()
    
    st.divider()
    due = c_hist[c_hist['Status'] == 'Pending']['Amount'].astype(float).sum()
    if due > 0:
        log_txt = "\n".join([f"{r['Date']} {r['Time']}" for _, r in c_hist[c_hist['Status']=='Pending'].iterrows()])
        msg = f"Hi {target}, your coaching sessions on: {log_txt} are pending. Total amount due is {due} CAD. Please complete the payment ASAP and share the screenshot. Thanks!"
        st.text_area("Payment Reminder Message", msg, height=150)

# --- 8. CALENDAR ---
elif menu == "Calendar":
    st.title("📅 Calendar View")
    p_date = st.date_input("Pick a date")
    res = df[df['Date'] == p_date]
    if not res.empty:
        st.write(f"Customers
