import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Aswin's Money Manager", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        # ttl=0 ensures we don't see old cached data
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()
menu = st.sidebar.radio("Menu", ["Dashboard", "History", "Clients"])

if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    
    # Simple Metrics
    pend = pd.to_numeric(df[df['Status'] == 'Pending']['Amount'], errors='coerce').sum()
    st.metric("Total Pending", f"{pend} CAD")

    with st.form("entry", clear_on_submit=True):
        n = st.text_input("Customer Name")
        d = st.date_input("Date", datetime.now().date())
        t = st.time_input("Time", datetime.now().time())
        if st.form_submit_button("Save Record"):
            if n:
                new_row = pd.DataFrame([{
                    "Name": n, 
                    "Date": str(d), 
                    "Time": t.strftime("%I:%M %p"), 
                    "Amount": 15.0, 
                    "Status": "Pending"
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                # We target Sheet1 specifically to prevent the UnsupportedOperationError
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Saved to Google Sheets!"); st.rerun()

elif menu == "History":
    st.title("📂 Logs")
    for i, r in df.iterrows():
        with st.expander(f"{r['Date']} - {r['Name']}"):
            if st.button("Delete", key=f"del{i}"):
                conn.update(worksheet="Sheet1", data=df.drop(i)); st.rerun()

elif menu == "Clients":
    st.title("👥 Clients")
    cl = df['Name'].unique()
    if len(cl) > 0:
        sel = st.selectbox("Select Client", cl)
        cdf = df[df['Name'] == sel]
        for i, r in cdf.iterrows():
            st.write(f"{r['Date']} - {r['Status']}")
            if r['Status'] == 'Pending' and st.button("Mark Paid", key=f"p{i}"):
                df.at[i, 'Status'] = 'Paid'
                conn.update(worksheet="Sheet1", data=df); st.rerun()
