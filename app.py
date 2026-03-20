import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- PAGE SETUP ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

# --- STYLE CUSTOMIZATION (Red/Blue Buttons) ---
st.markdown("""
    <style>
    div.stButton > button:first-child { background-color: #007bff; color: white; } /* Default Blue */
    div.stButton > button:contains("Delete") { background-color: #ff4b4b; color: white; } /* Red for Delete */
    div.stButton > button:contains("Mark as Paid") { background-color: #28a745; color: white; } /* Green */
    </style>
""", unsafe_allow_html=True)

# --- GOOGLE SHEETS CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    return conn.read(ttl="0") # Force refresh every time

# --- HEADER ---
col_ref, col_title, col_dark = st.columns([1, 5, 1])
with col_ref:
    if st.button("🔄"): st.rerun()
with col_title:
    st.markdown("<h2 style='text-align: center;'>Aswin's Money Manager</h2>", unsafe_allow_html=True)
with col_dark:
    st.button("🌙")

# --- NAVIGATION ---
menu = ["Dashboard", "Log History", "Client Section", "Calendar"]
choice = st.sidebar.radio("Go to", menu)
df = get_data()

# --- 1. DASHBOARD ---
if choice == "Dashboard":
    # Metrics Logic
    df['Date'] = pd.to_datetime(df['Date']).dt.date
    today = datetime.now().date()
    start_week = today - timedelta(days=today.weekday()) # Monday start
    
    month_count = len(df[pd.to_datetime(df['Date']).dt.month == today.month])
    week_count = len(df[df['Date'] >= start_week])
    
    m1, m2 = st.columns(2)
    m1.metric("Services (Month)", month_count)
    m2.metric("Services (Week)", week_count)
    
    m3, m4 = st.columns(2)
    m3.metric("Received (CAD)", df[df['Status'] == 'Paid']['Cost'].sum())
    m4.metric("Pending (CAD)", df[df['Status'] == 'Pending']['Cost'].sum())

    st.subheader("Quick Entry")
    with st.form("add_entry", clear_on_submit=True):
        name = st.text_input("Customer Name")
        date = st.date_input("Date", today)
        time = st.time_input("Time", datetime.now())
        if st.form_submit_button("Save Record"):
            new_row = pd.DataFrame([{"Name": name, "Date": str(date), "Time": time.strftime("%I:%M %p"), "Cost": 15, "Status": "Pending"}])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success("Saved!")
            st.rerun()

    st.divider()
    st.download_button("Export to Excel", df.to_csv().encode('utf-8'), "records.csv")

# --- 2. LOG HISTORY ---
elif choice == "Log History":
    st.subheader("All Logs")
    s_date = st.date_input("Start", today - timedelta(days=7))
    e_date = st.date_input("End", today)
    
    # Filter and Display
    for idx, row in df.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"**{row['Name']}** | {row['Date']} @ {row['Time']}")
        c2.button("Edit", key=f"e{idx}") # CSS makes this blue
        if c3.button("Delete", key=f"d{idx}"): # CSS makes this red
            new_df = df.drop(idx)
            conn.update(data=new_df)
            st.rerun()

# --- 3. CLIENT SECTION ---
elif choice == "Client Section":
    client = st.selectbox("Select Client", df['Name'].unique())
    c_logs = df[df['Name'] == client]
    
    for idx, row in c_logs.iterrows():
        st.write(f"{row['Date']} | {row['Time']} | {row['Status']}")
        col1, col2, col3 = st.columns(3)
        col1.button("Edit", key=f"ce{idx}")
        col2.button("Delete", key=f"cd{idx}")
        if row['Status'] == "Pending":
            if col3.button("Mark as Paid", key=f"cp{idx}"):
                df.at[idx, 'Status'] = 'Paid'
                conn.update(data=df)
                st.rerun()
    
    # WhatsApp Logic
    pending_amt = c_logs[c_logs['Status'] == 'Pending']['Cost'].sum()
    if pending_amt > 0:
        msg = f"Hi! Pending payment for session on {c_logs.iloc[-1]['Date']}. Total: {pending_amt} CAD. Please share screenshot after payment. Thanks!"
        st.link_button("Share Record to Customer", f"https://wa.me/?text={msg}")

# --- 4. CALENDAR ---
elif choice == "Calendar":
    sel_date = st.date_input("View Date", today)
    day_df = df[df['Date'].astype(str) == str(sel_date)]
    if not day_df.empty:
        st.table(day_df[['Name', 'Time']])
    else:
        st.info("No records for this date.")
