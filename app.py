import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# --- 1. SETTINGS ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

# Custom CSS for UI and dark mode toggle support
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
    </style>
    """, unsafe_allow_html=True)

# Initialize Session State
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- 2. DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read()
        # Ensure correct columns exist
        for col in ["Name", "Date", "Time", "Amount", "Status"]:
            if col not in data.columns: data[col] = None
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()

# --- 3. TOP BAR (Refresh & Dark Mode) ---
head_left, head_mid, head_right = st.columns([1, 4, 1])
if head_left.button("🔄 Refresh"):
    st.rerun()

with head_right:
    if st.button("🌙 Dark Mode" if not st.session_state.dark_mode else "☀️ Light Mode"):
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
    
    # Metrics Calculation
    this_month = df[df['Date'] >= month_start]
    this_week = df[df['Date'] >= start_of_week]
    paid_total = this_month[this_month['Status'] == 'Paid']['Amount'].astype(float).sum()
    pending_total = df[df['Status'] == 'Pending']['Amount'].astype(float).sum()
    
    m1, m2 = st.columns(2)
    m1.metric("Services (Month)", len(this_month))
    m2.metric("Services (Week)", len(this_week))
    
    m3, m4 = st.columns(2)
    m3.metric("Received (Month)", f"{paid_total} CAD")
    m4.metric("Total Pending", f"{pending_total} CAD")

    st.divider()
    st.subheader("📝 Service Entry")
    with st.form("entry_form", clear_on_submit=True):
        name = st.text_input("Customer Name")
        c1, c2 = st.columns(2)
        date = c1.date_input("Date", today)
        time = c2.time_input("Time", datetime.now().time())
        st.caption("Default: 15 CAD | Status: Pending")
        
        if st.form_submit_button("Add Record"):
            if name:
                new_entry = pd.DataFrame([{
                    "Name": name, "Date": str(date), 
                    "Time": time.strftime("%I:%M %p"), 
                    "Amount": 15.0, "Status": "Pending"
                }])
                conn.update(data=pd.concat([df, new_entry], ignore_index=True))
                st.success("Record Saved!")
                st.rerun()
    
    st.divider()
    # Export Buttons at the bottom
    ex1, ex2 = st.columns(2)
    # Excel Export
    towrite = io.BytesIO()
    df.to_excel(towrite, index=False, engine='openpyxl')
    ex1.download_button("📥 Export to Excel", data=towrite.getvalue(), file_name="logs.xlsx")
    # PDF Export
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Aswin's Money Manager Logs", ln=1, align='C')
    for _, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Date']} | {row['Name']} | {row['Amount']} CAD", ln=True)
    ex2.download_button("📥 Export to PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="logs.pdf")

# --- 6. LOG HISTORY ---
elif menu == "Log History":
    st.title("📂 Log History")
    s_col, e_col = st.columns(2)
    start_filt = s_col.date_input("From", datetime.now().date() - timedelta(days=30))
    end_filt = e_col.date_input("To", datetime.now().date())
    
    logs = df[(df['Date'] >= start_filt) & (df['Date'] <= end_filt)]
    
    for i, r in logs.iterrows():
        with st.expander(f"{r['Date']} - {r['Name']} ({r['Time']})"):
            c1, c2 = st.columns(2)
            if c1.button("Edit", key=f"edit{i}", help="Blue"): st.info("Edit mode active")
            if c2.button("Delete", key=f"del{i}", help="Red"):
                conn.update(data=df.drop(i))
                st.rerun()

# --- 7. CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Client Section")
    client_list = df['Name'].unique()
    sel_client = st.selectbox("Select Client", client_list)
    
    c_df = df[df['Name'] == sel_client]
    st.write(f"### History for {sel_client}")
    
    for i, r in c
