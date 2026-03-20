import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. SETTINGS ---
st.set_page_config(page_title="Money Tracker", layout="wide", initial_sidebar_state="expanded")

# Fix for the 'today' error
now = datetime.now()
today = now.date()

# --- 2. DATA CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        data = conn.read()
        # Force specific column names to keep the interface clean
        required = ["Name", "Date", "Amount", "Status", "Time"]
        for col in required:
            if col not in data.columns:
                data[col] = ""
        return data[required] # Only show these 5 columns
    except:
        return pd.DataFrame(columns=["Name", "Date", "Amount", "Status", "Time"])

df = load_data()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.markdown("## 💰 My Money App")
    choice = st.radio("Menu", ["📊 Dashboard", "📝 Add New Entry", "📂 View All Logs"])
    st.divider()
    st.info("Resyncs automatically with Google Sheets")

# --- 4. DASHBOARD ---
if choice == "📊 Dashboard":
    st.title("Business Overview")
    
    # Calculate metrics
    total_rev = pd.to_numeric(df['Amount'], errors='coerce').sum()
    today_data = df[df['Date'].astype(str) == str(today)]
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Revenue", f"₹{total_rev:,.0f}")
    m2.metric("Total Clients", len(df.dropna(subset=['Name'])))
    m3.metric("Entries Today", len(today_data))
    
    st.divider()
    st.subheader("Recent Activity")
    # Clean up display: remove empty rows and show only the last 5
    clean_df = df.dropna(subset=['Name']).tail(5)
    st.table(clean_df)

# --- 5. ADD ENTRY ---
elif choice == "📝 Add New Entry":
    st.title("New Registration")
    
    with st.form("add_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        name = col_a.text_input("Client Name")
        amt = col_b.number_input("Amount (₹)", min_value=0, step=100)
        
        col_c, col_d = st.columns(2)
        status = col_c.selectbox("Payment Status", ["Paid", "Pending"])
        note = col_d.text_input("Note (Optional)") # Extra column for details
        
        if st.form_submit_button("Save to Database"):
            if name:
                new_entry = pd.DataFrame([{
                    "Name": name,
                    "Date": str(today),
                    "Amount": amt,
                    "Status": status,
                    "Time": now.strftime("%I:%M %p")
                }])
                
                updated_df = pd.concat([df, new_entry], ignore_index=True)
                conn.update(data=updated_df)
                
                st.success(f"Successfully recorded ₹{amt} for {name}")
                st.balloons()
                st.rerun()
            else:
                st.error("Please enter a name.")

# --- 6. LOGS ---
elif choice == "📂 View All Logs":
    st.title("Full Transaction History")
    st.dataframe(df.dropna(subset=['Name']), use_container_width=True)
