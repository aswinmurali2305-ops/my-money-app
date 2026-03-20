import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
import io

# --- 1. SETTINGS & THEME ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

# Custom CSS for Mobile UI
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; }
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

if 'dark_mode' not in st.session_state:
    st.session_state.dark_mode = False

# --- 2. DATA ENGINE ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ttl=0 ensures we don't show old cached data
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

# --- 3. TOP NAVIGATION (Refresh & Dark Mode) ---
t1, t2, t3 = st.columns([1, 4, 1])
if t1.button("🔄 Refresh"):
    st.rerun()

with t3:
    label = "🌙 Dark" if not st.session_state.dark_mode else "☀️ Light"
    if st.button(label):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# --- 4. SIDEBAR MENU ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Log History", "Client Section", "Calendar"])

# --- 5. DASHBOARD PAGE ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    
    today = datetime.now().date()
    # Week logic: Monday to Sunday
    start_of_week = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    this_month_df = df[df['Date'] >= month_start]
    this_week_df = df[df['Date'] >= start_of_week]
    
    # Metrics
    m1, m2 = st.columns(2)
    m1.metric("Services (Month)", len(this_month_df))
    m2.metric("Services (Week)", len(this_week_df))
    
    # Calculate totals safely
    paid_total = pd.to_numeric(this_month_df[this_month_df['Status'] == 'Paid']['Amount'], errors='coerce').sum()
    pending_total = pd.to_numeric(df[df['Status'] == 'Pending']['Amount'], errors='coerce').sum()
    
    m3, m4 = st.columns(2)
    m3.metric("Money Received (Month)", f"{paid_total} CAD")
    m4.metric("Pending Total Amount", f"{pending_total} CAD")

    st.divider()
    
    # Entry Section
    st.subheader("📝 Quick Service Entry")
    with st.form("entry_form", clear_on_submit=True):
        c_name = st.text_input("Customer Name")
        c1, c2 = st.columns(2)
        c_date = c1.date_input("Date of Service", today)
        c_time = c2.time_input("Time of Service", datetime.now().time())
        st.info("Default Cost: 15 CAD | Status: Pending")
        
        if st.form_submit_button("Save Entry"):
            if c_name:
                new_row = pd.DataFrame([{
                    "Name": c_name, 
                    "Date": str(c_date), 
                    "Time": c_time.strftime("%I:%M %p"), 
                    "Amount": 15.0, 
                    "Status": "Pending"
                }])
                updated = pd.concat([df, new_row], ignore_index=True)
                # CRITICAL: We explicitly name the worksheet to avoid UnsupportedOperationError
                conn.update(worksheet="Sheet1", data=updated)
                st.success(f"Saved entry for {c_name}!")
                st.rerun()
            else:
                st.error("Please enter a customer name.")

    st.divider()
    
    # Export Section
    st.subheader("📤 Export Data")
    e1, e2 = st.columns(2)
    # Excel
    output_excel = io.BytesIO()
    df.to_excel(output_excel, index=False, engine='openpyxl')
    e1.download_button("Export to Excel", data=output_excel.getvalue(), file_name="coaching_logs.xlsx")
    
    # PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Aswin's Coaching Records", ln=1, align='C')
    for _, row in df.iterrows():
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
            if col1.button("Edit", key=f"ed{idx}"): st.info("Edit feature coming soon")
            if col2.button("Delete", key=f"del{idx}"):
                new_df = df.drop(idx)
                conn.update(worksheet="Sheet1", data=new_df)
                st.rerun()

# --- 7. CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Client Section")
    clients = df['Name'].unique()
    if len(clients) > 0:
        selected_client = st.selectbox("Select Customer",
