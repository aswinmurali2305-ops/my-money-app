import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

# Custom CSS for Mobile & Buttons
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; }
    .delete-btn { background-color: #FF4B4B; color: white; }
    .edit-btn { background-color: #007BFF; color: white; }
    .paid-btn { background-color: #28A745; color: white; }
    </style>
    """, unsafe_allow_name_allowed=True)

# Initialize Session State for Dark Mode
if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- 2. DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read()
        required = ["Name", "Date", "Time", "Amount", "Status"]
        for col in required:
            if col not in data.columns: data[col] = None
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()

# --- 3. TOP NAVIGATION (Refresh & Dark Mode) ---
t1, t2, t3 = st.columns([1, 4, 1])
if t1.button("🔄 Refresh"):
    st.rerun()

with t3:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode

# --- 4. SIDEBAR MENU ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Log History", "Client Section", "Calendar"])

# --- 5. DASHBOARD PAGE ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    
    # Logic for Weekly/Monthly Stats
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday()) # Monday
    month_start = today.replace(day=1)
    
    this_month_df = df[df['Date'] >= month_start]
    this_week_df = df[df['Date'] >= start_of_week]
    
    # Top Metrics
    m1, m2 = st.columns(2)
    m1.metric("Services (Month)", len(this_month_df))
    m2.metric("Services (Week)", len(this_week_df))
    
    m3, m4 = st.columns(2)
    paid_total = this_month_df[this_month_df['Status'] == 'Paid']['Amount'].astype(float).sum()
    pending_total = df[df['Status'] == 'Pending']['Amount'].astype(float).sum()
    m3.metric("Money Received (Month)", f"${paid_total}")
    m4.metric("Total Pending", f"${pending_total}")

    st.divider()
    
    # Entry Section
    st.subheader("📝 New Entry")
    with st.form("entry_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        c_name = c1.text_input("Customer Name")
        c_date = c2.date_input("Date", today)
        c3, c4 = st.columns(2)
        c_time = c3.time_input("Time", datetime.now().time())
        
        if st.form_submit_button("Add Service"):
            new_row = pd.DataFrame([{
                "Name": c_name, "Date": str(c_date), 
                "Time": c_time.strftime("%I:%M %p"), 
                "Amount": 15.0, "Status": "Pending"
            }])
            updated = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated)
            st.success("Entry Added!")
            st.rerun()

    st.divider()
    
    # Export Section
    st.subheader("📤 Export Data")
    e1, e2 = st.columns(2)
    # Excel
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    e1.download_button("Export to Excel", data=output_excel.getvalue(), file_name="logs.xlsx")
    
    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Coaching Logs", ln=1, align='C')
    for i, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Date']} - {row['Name']} - ${row['Amount']}", ln=True)
    e2.download_button("Export to PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="logs.pdf")

# --- 6. LOG HISTORY PAGE ---
elif menu == "Log History":
    st.title("📂 Log History")
    f1, f2 = st.columns(2)
    sd = f1.date_input("Start Date", today - timedelta(days=30))
    ed = f2.date_input("End Date", today)
    
    filtered = df[(df['Date'] >= sd) & (df['Date'] <= ed)]
    
    for idx, row in filtered.iterrows():
        with st.expander(f"{row['Date']} | {row['Name']} | {row['Time']}"):
            st.write(f"Status: {row['Status']}")
            col1, col2 = st.columns(2)
            if col1.button("Edit", key=f"ed{idx}"): st.info("Edit mode coming soon")
            if col2.button("Delete", key=f"del{idx}"):
                new_df = df.drop(idx)
                conn.update(data=new_df)
                st.rerun()

# --- 7. CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Client Management")
    clients = df['Name'].unique()
    selected_client = st.selectbox("Select Customer", clients)
    
    client_df = df[df['Name'] == selected_client]
    total_due = client_df[client_df['Status'] == 'Pending']['Amount'].astype(float).sum()
    
    st.subheader(f"History for {selected_client}")
    for idx, row in client_df.iterrows():
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.write(f"{row['Date']} at {row['Time']}")
        if row['Status'] == 'Pending':
            if c2.button("Mark Paid", key=f"p{idx}"):
                df.at[idx, 'Status'] = 'Paid'
                conn.update(data=df)
                st.rerun()
        
        # Share Logic
        if c3.button("Share Link", key=f"sh{idx}"):
            msg = f"Hi {selected_client}, pending payment for {row['Date']} {row['Time']}. Total Due: ${total_due}. Please pay and share screenshot."
            st.code(msg) # Easy to copy on mobile

# --- 8. CALENDAR ---
elif menu == "Calendar":
    st.title("📅 Calendar View")
    cal_date = st.date_input("Select Date", today)
    cal_df = df[df['Date'] == cal_date]
    
    if not cal_df.empty:
        st.table(cal_df[['Time', 'Name', 'Amount', 'Status']])
    else:
        st.info("No services scheduled for this day.")
