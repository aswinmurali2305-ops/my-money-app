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
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem; }
    </style>
    """, unsafe_allow_html=True)

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

# --- 3. TOP NAVIGATION ---
t1, t2, t3 = st.columns([1, 4, 1])
if t1.button("🔄 Refresh"):
    st.rerun()

with t3:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode

# --- 4. SIDEBAR MENU ---
st.sidebar.title("💰 Navigation")
menu = st.sidebar.radio("Go to", ["Dashboard", "Log History", "Client Section", "Calendar"])

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
    m1.metric("Services This Month", len(this_month_df))
    m2.metric("Services This Week", len(this_week_df))
    
    m3, m4 = st.columns(2)
    paid_total = this_month_df[this_month_df['Status'] == 'Paid']['Amount'].astype(float).sum()
    pending_total = df[df['Status'] == 'Pending']['Amount'].astype(float).sum()
    m3.metric("Money Received (Month)", f"{paid_total} CAD")
    m4.metric("Pending Total", f"{pending_total} CAD")

    st.divider()
    
    # Entry Section
    st.subheader("📝 Quick Service Entry")
    with st.form("entry_form", clear_on_submit=True):
        c_name = st.text_input("Customer Name")
        c1, c2 = st.columns(2)
        c_date = c1.date_input("Date of Service", today)
        c_time = c2.time_input("Time of Service", datetime.now().time())
        
        st.info("Cost is defaulted to 15 CAD | Payment: Pending")
        
        if st.form_submit_button("Save Entry"):
            if c_name:
                new_row = pd.DataFrame([{
                    "Name": c_name, "Date": str(c_date), 
                    "Time": c_time.strftime("%I:%M %p"), 
                    "Amount": 15.0, "Status": "Pending"
                }])
                updated = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated)
                st.success(f"Saved {c_name} to database!")
                st.rerun()
            else:
                st.error("Please enter a name.")

    st.divider()
    
    # Bottom Export
    st.subheader("📤 Export Database")
    e1, e2 = st.columns(2)
    # Excel
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    e1.download_button("Export to Excel", data=output_excel.getvalue(), file_name="coaching_logs.xlsx")
    
    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Aswin's Coaching Logs", ln=1, align='C')
    for i, row in df.iterrows():
        pdf.cell(200, 10, txt=f"{row['Date']} | {row['Name']} | {row['Time']} | {row['Amount']} CAD", ln=True)
    e2.download_button("Export to PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="coaching_logs.pdf")

# --- 6. LOG HISTORY PAGE ---
elif menu == "Log History":
    st.title("📂 Log History")
    f1, f2 = st.columns(2)
    sd = f1.date_input("Start Date", today - timedelta(days=30))
    ed = f2.date_input("End Date", today)
    
    filtered = df[(df['Date'] >= sd) & (df['Date'] <= ed)]
    
    for idx, row in filtered.iterrows():
        with st.expander(f"{row['Date']} - {row['Time']} - {row['Name']}"):
            col1, col2 = st.columns(2)
            if col1.button("Edit (Blue)", key=f"ed{idx}"): 
                st.info("Feature under development")
            if col2.button("Delete (Red)", key=f"del{idx}"):
                new_df = df.drop(idx)
                conn.update(data=new_df)
                st.rerun()

# --- 7. CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Client Management")
    clients = df['Name'].unique()
    selected_client = st.selectbox("Select Client", clients)
    
    client_df = df[df['Name'] == selected_client]
    total_due = client_df[client_df['Status'] == 'Pending']['Amount'].astype(float).sum()
    
    st.subheader(f"Service History: {selected_client}")
    for idx, row in client_df.iterrows():
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        c1.write(f"{row['Date']} at {row['Time']}")
        
        # Action Buttons
        if c2.button("Edit", key=f"ce{idx}"): st.info("Edit coming soon")
        if c3.button("Delete", key=f"cd{idx}"):
            df_dropped = df.drop(idx)
            conn.update(data=df_dropped)
            st.rerun()
        if row['Status'] == 'Pending':
            if c4.button("Mark Paid", key=f"cp{idx}"):
                df.at[idx, 'Status'] = 'Paid'
                conn.update(data=df)
                st.rerun()
    
    st.divider()
    # Sharing Message
    if total_due > 0:
        st.subheader("Send Payment Reminder")
        pending_list = client_df[client_df['Status'] == 'Pending']
        dates_times = ", ".join([f"{r['Date']} at {r['Time']}" for _, r in pending_list.iterrows()])
        message = f"Hi {selected_client}, this is a reminder regarding your pending payment for coaching on {dates_times}. Total due is {total_due} CAD. Please complete the payment as soon as possible and share the screenshot. Thanks!"
        st.text_area("Copy Message:", value=message, height=150)

# --- 8. CALENDAR ---
elif menu == "Calendar":
    st.title("📅 Calendar View")
    cal_date = st.date_input("Click a date to see services", today)
    cal_df = df[df['Date'] == cal_date]
    
    if not cal_df
