import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- CONFIG ---
st.set_page_config(page_title="Aswin's Money Manager", layout="wide")
conn = st.connection("gsheets", type=GSheetsConnection)

def get_data():
    try:
        data = conn.read(ttl=0)
        if data is None or data.empty:
            return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])
        data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data
    except:
        return pd.DataFrame(columns=["Name", "Date", "Time", "Amount", "Status"])

df = get_data()

# --- NAVIGATION ---
menu = st.sidebar.radio("Menu", ["Dashboard", "History", "Clients", "Calendar"])

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("Aswin's Money Manager")
    today = datetime.now().date()
    
    # Metrics Logic
    m_start = today.replace(day=1)
    this_m = df[df['Date'] >= m_start]
    paid = pd.to_numeric(this_m[this_m['Status'] == 'Paid']['Amount'], errors='coerce').sum()
    pend = pd.to_numeric(df[df['Status'] == 'Pending']['Amount'], errors='coerce').sum()
    
    c1, c2 = st.columns(2)
    c1.metric("Received (Month)", f"{paid} CAD")
    c2.metric("Total Pending", f"{pend} CAD")

    st.divider()
    with st.form("entry", clear_on_submit=True):
        n = st.text_input("Name")
        d = st.date_input("Date", today)
        t = st.time_input("Time", datetime.now().time())
        if st.form_submit_button("Save Record"):
            if n:
                row = pd.DataFrame([{"Name":n, "Date":str(d), "Time":t.strftime("%I:%M %p"), "Amount":15.0, "Status":"Pending"}])
                conn.update(worksheet="Sheet1", data=pd.concat([df, row], ignore_index=True))
                st.success("Saved!"); st.rerun()

# --- HISTORY ---
elif menu == "History":
    st.title("📂 History")
    for i, r in df.iterrows():
        with st.expander(f"{r['Date']} - {r['Name']}"):
            if st.button("Delete", key=f"del{i}"):
                conn.update(worksheet="Sheet1", data=df.drop(i)); st.rerun()

# --- CLIENTS ---
elif menu == "Clients":
    st.title("👥 Clients")
    cl = df['Name'].unique()
    if len(cl) > 0:
        sel = st.selectbox("Select Client", cl)
        cdf = df[df['Name'] == sel]
        for i, r in cdf.iterrows():
            c1, c2 = st.columns([3, 1])
            c1.write(f"{r['Date']} @ {r['Time']} ({r['Status']})")
            if r['Status'] == 'Pending' and c2.button("Paid", key=f"p{i}"):
                df.at[i, 'Status'] = 'Paid'
                conn.update(worksheet="Sheet1", data=df); st.rerun()
        
        due = pd.to_numeric(cdf[cdf['Status'] == 'Pending']['Amount'], errors='coerce').sum()
        if due > 0:
            st.warning(f"Total Due: {due} CAD")
            st.text_area("Msg", f"Hi {sel}, pending total is {due} CAD. Please pay ASAP.")
    else:
        st.info("No records.")

# --- CALENDAR ---
elif menu == "Calendar":
    st.title("📅 Calendar")
    p = st.date_input("Check Date")
    res = df[df['Date'] == p]
    if not res.empty:
        st.table(res[['Time', 'Name', 'Status']])
    else:
        st.info("Empty.")
