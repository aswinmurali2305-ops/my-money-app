import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. INITIAL CONFIG ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")

# Define 'today' at the very top so it's available everywhere
now = datetime.now()
today = now.date()

# Connect to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Read existing data
try:
    df = conn.read()
except Exception:
    # If sheet is empty, create a starting structure
    df = pd.DataFrame(columns=["Name", "Date", "Amount", "Status", "Time"])

# --- 2. SIDEBAR NAVIGATION ---
st.sidebar.title("💰 Navigation")
choice = st.sidebar.radio("Go to", ["Dashboard", "Add Record", "Calendar", "Log History"])

# --- 3. DASHBOARD ---
if choice == "Dashboard":
    st.title("📊 Business Overview")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Clients", len(df))
    with col2:
        # Convert Amount to numeric just in case
        total_amt = pd.to_numeric(df['Amount'], errors='coerce').sum()
        st.metric("Total Revenue", f"₹{total_amt:,.2f}")
    with col3:
        st.metric("Today's Entries", len(df[df['Date'].astype(str) == str(today)]))

    st.subheader("Recent Activity")
    st.dataframe(df.tail(10), use_container_width=True)

# --- 4. ADD RECORD ---
elif choice == "Add Record":
    st.subheader("📝 Register New Client")
    with st.form("entry_form"):
        name = st.text_input("Client Name")
        amount = st.number_input("Amount (₹)", min_value=0)
        date = st.date_input("Service Date", today)
        time = st.time_input("Time", now.time())
        status = st.selectbox("Status", ["Paid", "Pending"])
        
        if st.form_submit_button("Save to Google Sheets"):
            if name:
                new_data = pd.DataFrame([{
                    "Name": name,
                    "Date": str(date),
                    "Amount": amount,
                    "Status": status,
                    "Time": str(time)
                }])
                
                # Combine and update
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success(f"✅ Successfully added {name}!")
                st.balloons()
            else:
                st.error("Please enter a Name.")

# --- 5. CALENDAR VIEW ---
elif choice == "Calendar":
    st.subheader("📅 Service Calendar")
    sel_date = st.date_input("Select Date to View", today)
    
    day_df = df[df['Date'].astype(str) == str(sel_date)]
    
    if not day_df.empty:
        st.write(f"Showing records for {sel_date}:")
        st.table(day_df[['Name', 'Amount', 'Status', 'Time']])
    else:
        st.info("No records found for this date.")

# --- 6. LOG HISTORY ---
elif choice == "Log History":
    st.subheader("📂 Historical Data")
    # Filters
    search = st.text_input("Search Name")
    
    display_df = df.copy()
    if search:
        display_df = display_df[display_df['Name'].str.contains(search, case=False)]
    
    st.dataframe(display_df, use_container_width=True)
