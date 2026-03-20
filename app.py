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
        # Use ttl=0 to ensure we always get the freshest data from your sheet
        data = conn.read(ttl=0)
        required = ["Name", "Date", "Time", "Amount", "Status"]
        if data.empty:
            return pd.DataFrame(columns=required)
        # Ensure all required columns exist
        for col in required:
            if col not in data.columns: data[col] = None
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data[required]
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()

# --- 3. TOP BAR ---
h1, h2, h3 = st.columns([1, 4, 1])
if h1.button("🔄"):
    st.rerun()
with h3:
    if st.button("🌙" if not st.session_state.dark_mode else "☀️"):
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()

# --- 4. NAVIGATION ---
menu = st.sidebar.radio("Navigation", ["Dashboard", "Log History", "Client Section", "Calendar"])

# --- 5. DASHBOARD ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    today = datetime.now().date()
    # Monday to Sunday Logic
    start_of_week = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    
    this_month = df[df['Date'] >= month_start]
    this_week = df[df['Date'] >= start_of_week]
    
    c1, c2 = st.columns(2)
    c1.metric("Services (Month)", len(this_month))
    c2.metric("Services (Week)", len(this_week))
    
    paid_m = pd.to_numeric(this_month[this_month['Status'] == 'Paid']['Amount'], errors='coerce').sum()
    pending_t = pd.to_numeric(df[df['Status'] == 'Pending']['Amount'], errors='coerce').sum()
    
    c3, c4 = st.columns(2)
    c3.metric("Received (Month)", f"{paid_m} CAD")
    c4.metric("Total Pending", f"{pending_t} CAD")

    st.divider()
    st.subheader("📝 New Entry")
    with st.form("entry", clear_on_submit=True):
        name = st.text_input("Customer Name")
        f1, f2 = st.columns(2)
        d_val = f1.date_input("Date", today)
        t_val = f2.time_input("Time", datetime.now().time())
        if st.form_submit_button("Save to Sheet"):
            if name:
                new_row = pd.DataFrame([{
                    "Name": name, "Date": str(d_val), 
                    "Time": t_val.strftime("%I:%M %p"), 
                    "Amount": 15.0, "Status": "Pending"
                }])
                # Force update to use the combined dataframe
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success("Successfully Saved!")
                st.rerun()

    st.divider()
    ex1, ex2 = st.columns(2)
    # Excel
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine='openpyxl')
    ex1.download_button("📂 Excel", data=buf.getvalue(), file_name="coaching.xlsx")
    # PDF
    pdf = FPDF()
    pdf.add_page(); pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Aswin's Coaching Logs", ln=1, align='C')
    for _, r in df.iterrows():
        pdf.cell(200, 10, txt=f"{r['Date']} | {r['Name']} | {r['Amount']} CAD", ln=True)
    ex2.download_button("📂 PDF", data=pdf.output(dest='S').encode('latin-1'), file_name="coaching.pdf")

# --- 6. LOG HISTORY ---
elif menu == "Log History":
    st.title("📂 History")
    col_a, col_b = st.columns(2)
    sd = col_a.date_input("From", datetime.now().date() - timedelta(days=30))
    ed = col_b.date_input("To", datetime.now().date())
    
    filt = df[(df['Date'] >= sd) & (df['Date'] <= ed)]
    for i, r in filt.iterrows():
        with st.expander(f"{r['Date']} - {r['Name']}"):
            if st.button("Delete (Red)", key=f"d{i}"):
                conn.update(data=df.drop(i)); st.rerun()

# --- 7. CLIENT SECTION ---
elif menu == "Client Section":
    st.title("👥 Clients")
    u = df['Name'].unique()
    if len(u) > 0:
        target = st.selectbox("Select Client", u)
        h = df[df['Name'] == target]
        for i, r in h.iterrows():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"{r['Date']} @ {r['Time']}")
            if c2.button("Delete", key=f"cd{i}"):
                conn.update(data=df.drop(i)); st.rerun()
            if r['Status'] == 'Pending':
                if c3.button("Mark Paid", key=f"cp{i}"):
                    df.at[i, 'Status'] = 'Paid'
                    conn.update(data=df); st.rerun()
        
        st.divider()
        due = pd.to_numeric(h[h['Status'] == 'Pending']['Amount'], errors='coerce').sum()
        if due > 0:
            log_txt = "\n".join([f"{r['Date']} {r['Time']}" for _, r in h[h['Status']=='Pending'].iterrows()])
            msg = f"Hi {target}, your coaching sessions on: {log_txt} are pending. Total: {due} CAD. Please pay and share screenshot."
            st.text_area("Share Reminder", msg, height=150)
    else:
        st.info("No clients found yet.")

# --- 8. CALENDAR ---
elif menu == "Calendar":
    st.title("📅 Calendar")
    p = st.date_input("Pick Date")
    res = df[df['Date'] == p]
    if not res.empty:
        st.table(res[['Time', 'Name', 'Status']])
    else:
        st.info("No records.")
