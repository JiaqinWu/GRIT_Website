import streamlit as st
import re
import pandas as pd
from millify import millify # shortens values (10_000 ---> 10k)
from streamlit_extras.metric_cards import style_metric_cards # beautify metric card with css
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt
import json
import time
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from mailjet_rest import Client


scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
#creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
# Use Streamlit's secrets management
creds_dict = st.secrets["gcp_service_account"]
# Extract individual attributes needed for ServiceAccountCredentials
credentials = {
    "type": creds_dict.type,
    "project_id": creds_dict.project_id,
    "private_key_id": creds_dict.private_key_id,
    "private_key": creds_dict.private_key,
    "client_email": creds_dict.client_email,
    "client_id": creds_dict.client_id,
    "auth_uri": creds_dict.auth_uri,
    "token_uri": creds_dict.token_uri,
    "auth_provider_x509_cert_url": creds_dict.auth_provider_x509_cert_url,
    "client_x509_cert_url": creds_dict.client_x509_cert_url,
}

# Create JSON string for credentials
creds_json = json.dumps(credentials)

# Load credentials and authorize gspread
creds = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(creds_json), scope)
client = gspread.authorize(creds)

# Fetch data from Google Sheets
try:
    spreadsheet1 = client.open('Referral Information')
    worksheet1 = spreadsheet1.worksheet('GRIT')
    grit_records = worksheet1.get_all_records()
    #st.write("GRIT records:", grit_records)
    grit_df = pd.DataFrame(grit_records)
    
    # -------- Robust date parsing helpers --------
    def _normalize_column_name(name: str) -> str:
        return re.sub(r"\s+", " ", str(name)).strip().lower()

    def _find_column_case_insensitive(df: pd.DataFrame, target_name: str):
        normalized_target = _normalize_column_name(target_name)
        for existing in df.columns:
            if _normalize_column_name(existing) == normalized_target:
                return existing
        return None

    def parse_date_column_robust(df: pd.DataFrame, target_name: str) -> pd.Series:
        existing_name = _find_column_case_insensitive(df, target_name)
        if existing_name is None:
            # Create an empty parsed column to avoid downstream KeyErrors
            df[target_name] = pd.NaT
            return df[target_name]

        series = df[existing_name]
        # Handle numeric Excel serials if present; otherwise parse strings
        try:
            if pd.api.types.is_numeric_dtype(series):
                parsed = pd.to_datetime(series, unit='d', origin='1899-12-30', errors='coerce')
            else:
                parsed = pd.to_datetime(series, errors='coerce', infer_datetime_format=True)
        except Exception:
            parsed = pd.to_datetime(series.astype(str), errors='coerce', infer_datetime_format=True)

        # Store under the canonical target_name to keep downstream code stable
        df[target_name] = parsed
        return df[target_name]

    # Map DataFrame index to Google Sheet absolute row number (1-based with header)
    def sheet_row_from_df_index(df_index: int) -> int:
        return int(df_index) + 2

    # Apply robust parsing for GRIT
    parse_date_column_robust(grit_df, 'Date')
    worksheet2 = spreadsheet1.worksheet('IPE')
    ipe_records = worksheet2.get_all_records()
    #st.write("IPE records:", ipe_records)  # Debug
    ipe_df = pd.DataFrame(ipe_records)
    # Apply robust parsing for IPE
    parse_date_column_robust(ipe_df, 'Date Received')
except Exception as e:
    st.error(f"Error fetching data from Google Sheets: {str(e)}")
    #st.write("Exception type:", type(e))

def format_phone(phone_str):
    # Remove non-digit characters
    digits = re.sub(r'\D', '', phone_str)
    
    # Format if it's 10 digits long
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    else:
        return phone_str  # Return original if not standard length

# Apply formatting
#df["Phone Number"] = df["Phone Number"].astype(str).apply(format_phone)

# --- Demo user database
USERS = {
    "JWu@pwcgov.org": {
        "GRIT": {"password": "Qin8851216", "name": "Jiaqin Wu"},
        "IPE": {"password": "Qin8851216", "name": "Jiaqin Wu"}
    }
}

# --- Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- Role selection
if st.session_state.role is None:
    #st.image("Georgetown_logo_blueRGB.png",width=200)
    #st.title("Welcome to the GU Technical Assistance Provider System")
    st.markdown(
        """
        <div style='
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: #f8f9fa;
            padding: 2em 0 1em 0;
            border-radius: 18px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.07);
            margin-bottom: 2em;
        '>
            <img src='https://github.com/JiaqinWu/GRIT_Website/raw/main/logo1.png' width='200' style='margin-bottom: 1em;'/>
            <h1 style='
                color: #1a237e;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-weight: 700;
                margin: 0;
                font-size: 2.2em;
                text-align: center;
            '>Welcome to the GRIT Monitor System</h1>
        </div>
        """,
        unsafe_allow_html=True
    )

    role = st.selectbox(
        "Select your dashboard",
        ["GRIT", "IPE"],
        index=None,
        placeholder="Select option..."
    )

    if role:
        st.session_state.role = role
        st.rerun()

# --- Show view based on role
else:
    st.sidebar.markdown(
        f"""
        <div style='
            background: #f8f9fa;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            padding: 1.2em 1em 1em 1em;
            margin-bottom: 1.5em;
            text-align: center;
            font-family: Arial, "Segoe UI", sans-serif;
        '>
            <span style='
                font-size: 1.15em;
                font-weight: 700;
                color: #1a237e;
                letter-spacing: 0.5px;
            '>
                Dashboard: {st.session_state.role}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.sidebar.button("🔄 Switch Dashboard", on_click=lambda: st.session_state.update({
        "authenticated": False,
        "role": None,
        "user_email": ""
    }))

    st.markdown("""
        <style>
        .stButton > button {
            width: 100%;
            background-color: #cdb4db;
            color: black;
            font-family: Arial, "Segoe UI", sans-serif;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.6em;
            margin-top: 1em;
            transition: background 0.2s;
        }
        .stButton > button:hover {
            background-color: #b197fc;
            color: #222;
        }
        </style>
    """, unsafe_allow_html=True)

    if not st.session_state.authenticated:
        st.subheader("🔐 Login Required")

        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login = st.button("Login")

        if login:
            user_roles = USERS.get(email)
            if user_roles and st.session_state.role in user_roles:
                user = user_roles[st.session_state.role]
                if user["password"] == password:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials or role mismatch.")
            else:
                st.error("Invalid credentials or role mismatch.")

    else:
        if st.session_state.role == "GRIT":
            user_info = USERS.get(st.session_state.user_email)
            GRIT_name = user_info["GRIT"]["name"]
            st.markdown(
                """
                <div style='
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background: #f8f9fa;
                    padding: 2em 0 1em 0;
                    border-radius: 18px;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
                    margin-bottom: 2em;
                '>
                    <img src='https://github.com/JiaqinWu/GRIT_Website/raw/main/logo1.png' width='200' style='margin-bottom: 1em;'/>
                    <h1 style='
                        color: #1a237e;
                        font-family: "Segoe UI", "Arial", sans-serif;
                        font-weight: 700;
                        margin: 0;
                        font-size: 2.2em;
                        text-align: center;
                    '>📬 GRIT Dashboard</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
            # Personalized greeting
            if user_info and "GRIT" in user_info:
                st.markdown(f"""
                <div style='                      
                background: #f8f9fa;                        
                border-radius: 12px;                        
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);                        
                padding: 1.2em 1em 1em 1em;                        
                margin-bottom: 1.5em;                        
                text-align: center;                        
                font-family: Arial, "Segoe UI", sans-serif;                    
                '>
                    <span style='                           
                    font-size: 1.15em;
                    font-weight: 700;
                    color: #1a237e;
                    letter-spacing: 0.5px;'>
                        👋 Welcome, {GRIT_name}!
                    </span>
                </div>
                """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            referral_num_grit = grit_df['Youth Name'].nunique()
            # create column span
            today = datetime.today()
            last_year = today - timedelta(days=365)
            last_month = today - timedelta(days=30)
            pastyear_request = grit_df[grit_df['Date'] >= last_year].shape[0]
            pastmonth_request = grit_df[grit_df['Date'] >= last_month].shape[0]


            col1.metric(label="# of Total Referrals", value= millify(referral_num_grit, precision=2))
            col2.metric(label="# of Referrals from Last Month", value= millify(pastmonth_request, precision=2))
            col3.metric(label="# of Referrals from Last Months", value= millify(pastyear_request, precision=2))
            style_metric_cards(border_left_color="#DBF227")


        elif st.session_state.role == "IPE":
            # Add staff content here
            user_info = USERS.get(st.session_state.user_email)
            ipe_name = user_info["IPE"]["name"] if user_info and "IPE" in user_info else None
            st.markdown(
                """
                <div style='
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    background: #f8f9fa;
                    padding: 2em 0 1em 0;
                    border-radius: 18px;
                    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
                    margin-bottom: 2em;
                '>
                    <img src='https://github.com/JiaqinWu/GRIT_Website/raw/main/logo1.png' width='200' style='margin-bottom: 1em;'/>
                    <h1 style='
                        color: #1a237e;
                        font-family: "Segoe UI", "Arial", sans-serif;
                        font-weight: 700;
                        margin: 0;
                        font-size: 2.2em;
                        text-align: center;
                    '>👷 IPE Dashboard</h1>
                </div>
                """,
                unsafe_allow_html=True
            )
            #st.header("👷 Staff Dashboard")
            # Personalized greeting
            if ipe_name:
                st.markdown(f"""
                <div style='                      
                background: #f8f9fa;                        
                border-radius: 12px;                        
                box-shadow: 0 2px 8px rgba(0,0,0,0.04);                        
                padding: 1.2em 1em 1em 1em;                        
                margin-bottom: 1.5em;                        
                text-align: center;                        
                font-family: Arial, "Segoe UI", sans-serif;                    
                '>
                    <span style='                           
                    font-size: 1.15em;
                    font-weight: 700;
                    color: #1a237e;
                    letter-spacing: 0.5px;'>
                        👋 Welcome, {ipe_name}!
                    </span>
                </div>
                """, unsafe_allow_html=True)
            col1, col2, col3 = st.columns(3)
            referral_num_ipe = ipe_df['Name of Client'].nunique()
            # create column span
            today = datetime.today()
            last_year = today - timedelta(days=365)
            last_month = today - timedelta(days=30)
            pastyear_request_ipe = ipe_df[ipe_df['Date Received'] >= last_year].shape[0]
            pastmonth_request_ipe = ipe_df[ipe_df['Date Received'] >= last_month].shape[0]


            col1.metric(label="# of Total Referrals", value= millify(referral_num_ipe, precision=2))
            col2.metric(label="# of Referrals from Last Month", value= millify(pastmonth_request_ipe, precision=2))
            col3.metric(label="# of Referrals from Last Months", value= millify(pastyear_request_ipe, precision=2))
            style_metric_cards(border_left_color="#DBF227")