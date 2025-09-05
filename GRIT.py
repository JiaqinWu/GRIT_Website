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

st.set_page_config(
        page_title="GRIT Dashboard - OCS",
        page_icon="https://github.com/JiaqinWu/GRIT_Website/raw/main/logo1.png", 
        layout="centered"
    ) 


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
    #st.write("GRIT records:", grit_records)  # Debug
    grit_df = pd.DataFrame(grit_records)
    grit_df['Date'] = pd.to_datetime(grit_df['Date'], errors='coerce')
    worksheet2 = spreadsheet1.worksheet('IPE')
    ipe_records = worksheet2.get_all_records()
    #st.write("IPE records:", ipe_records)  # Debug
    ipe_df = pd.DataFrame(ipe_records)
    ipe_df['Date Received'] = pd.to_datetime(ipe_df['Date Received'], errors='coerce')
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
        "GRIT": {"password": "Qin88251216", "name": "Jiaqin Wu"},
        "IPE": {"password": "Qin88251216", "name": "Jiaqin Wu"}
    },
    "TYasin1@pwcgov.org": {
        "GRIT": {"password": "TYasin1", "name": "Tauheeda Martin Yasin"},
        "IPE": {"password": "TYasin1", "name": "Tauheeda Martin Yasin"}
    },
    "jkooyoomjian@pwcgov.org": {
        "GRIT": {"password": "jkooyoomjian", "name": "Jennifer Kooyoomijian"},
        "IPE": {"password": "jkooyoomjian", "name": "Jennifer Kooyoomiji"}
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
            col2.metric(label="# of Referrals from Last One Year", value= millify(pastyear_request, precision=2))
            col3.metric(label="# of Referrals from Last 30 Days", value= millify(pastmonth_request, precision=2))
            style_metric_cards(border_left_color="#DBF227")

            col4, col5 = st.columns(2)
            with col4:
                st.markdown('##### Time-series Plot of New Referrals:')
                
                # Filter data for current calendar year
                current_year = datetime.now().year
                current_year_data = grit_df[grit_df['Date'].dt.year == current_year].copy()
                
                if not current_year_data.empty:
                    # Group by month and count referrals
                    monthly_referrals = current_year_data.groupby(current_year_data['Date'].dt.month).size().reset_index()
                    monthly_referrals.columns = ['Month', 'Count']
                    
                    # Create month names for better display
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    monthly_referrals['Month_Name'] = monthly_referrals['Month'].map(lambda x: month_names[x-1])
                    
                    # Create complete dataset with all 12 months (including months with 0 referrals)
                    all_months = pd.DataFrame({'Month': range(1, 13)})
                    all_months['Month_Name'] = all_months['Month'].map(lambda x: month_names[x-1])
                    
                    # Merge and ensure Month_Name column exists
                    monthly_referrals_complete = all_months.merge(monthly_referrals, on='Month', how='left').fillna(0)
                    monthly_referrals_complete['Count'] = monthly_referrals_complete['Count'].astype(int)
                    
                    # Ensure Month_Name column exists and is properly formatted
                    if 'Month_Name' not in monthly_referrals_complete.columns:
                        monthly_referrals_complete['Month_Name'] = monthly_referrals_complete['Month'].map(lambda x: month_names[x-1])
                    monthly_referrals_complete['Month_Name'] = monthly_referrals_complete['Month_Name'].astype(str)
                    
                    # Create the chart
                    chart = alt.Chart(monthly_referrals_complete).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('Month_Name:O', title='Month', axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('Count:Q', title='Number of Referrals', scale=alt.Scale(domain=[0, None])),
                        tooltip=['Month_Name', 'Count']
                    ).properties(
                        width=400,
                        height=300,
                        title=f'Monthly New Referrals - {current_year}'
                    ).interactive()
                    
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info(f"No new referrals found for {current_year}")
            with col5:
                st.markdown('##### Time-series Plot of New Comments:')

                # Filter data for current calendar year
                current_year = datetime.now().year
                
                # Check if 'Day of Case Note' column exists and convert to datetime
                if 'Day of Case Note' in grit_df.columns:
                    # Convert to datetime if not already
                    grit_df['Day of Case Note'] = pd.to_datetime(grit_df['Day of Case Note'], errors='coerce')
                    current_year_data = grit_df[grit_df['Day of Case Note'].dt.year == current_year].copy()
                else:
                    current_year_data = pd.DataFrame()  # Empty dataframe if column doesn't exist
                
                if not current_year_data.empty:
                    # Group by month and count comments
                    monthly_comments = current_year_data.groupby(current_year_data['Day of Case Note'].dt.month).size().reset_index()
                    monthly_comments.columns = ['Month', 'Count']
                    
                    # Create month names for better display
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    monthly_comments['Month_Name'] = monthly_comments['Month'].map(lambda x: month_names[x-1])
                    
                    # Create complete dataset with all 12 months (including months with 0 comments)
                    all_months = pd.DataFrame({'Month': range(1, 13)})
                    all_months['Month_Name'] = all_months['Month'].map(lambda x: month_names[x-1])
                    
                    # Merge and ensure Month_Name column exists
                    monthly_comments_complete = all_months.merge(monthly_comments, on='Month', how='left').fillna(0)
                    monthly_comments_complete['Count'] = monthly_comments_complete['Count'].astype(int)
                    
                    # Ensure Month_Name column exists and is properly formatted
                    if 'Month_Name' not in monthly_comments_complete.columns:
                        monthly_comments_complete['Month_Name'] = monthly_comments_complete['Month'].map(lambda x: month_names[x-1])
                    monthly_comments_complete['Month_Name'] = monthly_comments_complete['Month_Name'].astype(str)
                    
                    # Create the chart
                    chart = alt.Chart(monthly_comments_complete).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('Month_Name:O', title='Month', axis=alt.Axis(labelAngle=0)),
                        y=alt.Y('Count:Q', title='Number of Comments', scale=alt.Scale(domain=[0, None])),
                        tooltip=['Month_Name', 'Count']
                    ).properties(
                        width=400,
                        height=300,
                        title=f'Monthly New Comments - {current_year}'
                    ).interactive()
                
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.info(f"No new comments found for {current_year}")

            with st.expander("📝 **Add New Referral**"):
                st.markdown("### 📝 Add New Referral")
                with st.form(key="add_referral_form"):
                    date_referral = st.date_input("Date of Referral:", value=datetime.today().date())
                    referral_agent = st.text_input("Referring Agent:")
                    agency = st.text_input("Agency:")
                    youth_name = st.text_input("Youth Name:")
                    dob_age = st.text_input("DOB/Age:")
                    day_of_case_note = st.date_input("Day of Case Note:", value=datetime.today().date())
                    case_notes = st.text_area("Enter your note:", height=100, placeholder="Type your note here...")
                    submit_button = st.form_submit_button("➕ Add Referral")
                    
                    if submit_button:
                        if youth_name.strip() and case_notes.strip():
                            try:
                                new_row_data = {
                                    'Youth Name': youth_name,
                                    'Date': date_referral.strftime('%m/%d/%Y'),
                                    'Referring Agent': referral_agent,
                                    'Agency': agency,
                                    'DOB/Age': dob_age,
                                    'Day of Case Note': day_of_case_note.strftime('%m/%d/%Y'),
                                    'Case Notes': case_notes
                                }
                                new_row = [new_row_data.get(col, '') for col in grit_df.columns]
                                worksheet1.append_row(new_row)
                                st.success("✅ Referral added successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Error adding referral: {str(e)}")
                        else:
                            st.warning("⚠️ Please fill in Youth Name and Case Notes before submitting.")

            with st.expander("📝 **Add New Note**"):
                # Add client filter in sidebar
                st.markdown("### 🔍 Filter by Youth")
                unique_youths = sorted(grit_df['Youth Name'].dropna().unique())
                selected_youth = st.selectbox(
                    "Select a youth:",
                    list(unique_youths),
                    index=0
                )
                
                
                # Filter data based on selected client
                filtered_df = grit_df[grit_df['Youth Name'] == selected_youth].copy()
                
                if not filtered_df.empty:
                    st.markdown("#### 📋 Youth Information")
                    
                    # Display main client information in narrative format
                    main_columns = ['Youth Name', 'Date', 'Referring Agent', 'Agency', 'DOB/Age']
                    
                    # Filter columns that exist in the dataframe
                    available_columns = [col for col in main_columns if col in filtered_df.columns]
                    
                    # Create narrative display
                    narrative_text = ""
                    for col in available_columns:
                        if col == 'Date':
                            # Special formatting for Date - YYYY-MM-DD format
                            value = filtered_df[col].iloc[0] if not filtered_df[col].isna().all() else "Not specified"
                            if pd.notna(value) and value != "Not specified":
                                try:
                                    # Convert to datetime and format as YYYY-MM-DD
                                    if isinstance(value, str):
                                        date_obj = pd.to_datetime(value, errors='coerce')
                                    else:
                                        date_obj = value
                                    if pd.notna(date_obj):
                                        formatted_date = date_obj.strftime('%Y-%m-%d')
                                        narrative_text += f"**{col}:** {formatted_date}\n"
                                    else:
                                        narrative_text += f"**{col}:** {value}\n"
                                except:
                                    narrative_text += f"**{col}:** {value}\n"
                            else:
                                narrative_text += f"**{col}:** Not specified\n"
                        else:
                            value = filtered_df[col].iloc[0] if not filtered_df[col].isna().all() else "Not specified"
                            if pd.isna(value) or value == "":
                                value = "Not specified"
                            narrative_text += f"**{col}:** {value}\n"
                    
                    # Display each line separately with proper spacing
                    lines = narrative_text.strip().split('\n')
                    for line in lines:
                        if line.strip():  # Only display non-empty lines
                            st.markdown(line)
                            st.markdown("")  # Add extra spacing between lines
                    
                    # Display case notes separately
                    st.markdown("#### 📝 Case Notes")
                    case_notes_columns = ['Day of Case Note', 'Case Notes']
                    case_notes_available = [col for col in case_notes_columns if col in filtered_df.columns]
                    
                    if case_notes_available:
                        case_notes_df = filtered_df[case_notes_available].dropna(subset=case_notes_available, how='all')
                        if not case_notes_df.empty:
                            # Reset index to remove index column from display
                            case_notes_df_display = case_notes_df.reset_index(drop=True)
                            st.table(case_notes_df_display)
                        else:
                            st.info("No case notes available for this youth.")
                    else:
                        st.info("Case notes columns not found in the dataset.")
                    
                    # Add new note section
                    st.markdown("#### 📝 Add New Note")
                    
                    with st.form(key=f"note_form_{selected_youth}"):
                        # Date selection for the new note
                        note_date = st.date_input(
                            "Note Date:",
                            value=datetime.today().date(),
                            key=f"note_date_{selected_youth}"
                        )
                        
                        # Text area for new note
                        new_note = st.text_area(
                            "Enter your note:",
                            height=100,
                            placeholder="Type your note here...",
                            key=f"new_note_{selected_youth}"
                        )
                        
                        # Add note button
                        submit_button = st.form_submit_button("➕ Add Note")
                        
                        if submit_button:
                            if new_note.strip():
                                try:
                                    # Format the date as string
                                    note_date_str = note_date.strftime('%m/%d/%y')
                                    
                                    # Prepare the new row data
                                    new_row_data = {
                                        'Youth Name': selected_youth,
                                        'Day of Case Note': note_date_str,
                                        'Case Notes': new_note.strip()
                                    }
                                    
                                    # Add empty values for other columns to maintain structure
                                    for col in grit_df.columns:
                                        if col not in new_row_data:
                                            new_row_data[col] = ''
                                    
                                    # Convert to list in the correct order
                                    new_row = [new_row_data.get(col, '') for col in grit_df.columns]
                                    
                                    # Append to Google Sheets
                                    worksheet1.append_row(new_row)
                                    
                                    st.success(f"✅ Note added successfully for {selected_youth} on {note_date_str}")
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"❌ Error adding note: {str(e)}")
                            else:
                                st.warning("⚠️ Please enter a note before adding.")
                else:
                    st.warning(f"No data found for youth: {selected_youth}")


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
            col2.metric(label="# of Referrals from Last Year", value= millify(pastyear_request_ipe, precision=2))
            col3.metric(label="# of Referrals from Last Month", value= millify(pastmonth_request_ipe, precision=2))
            style_metric_cards(border_left_color="#DBF227")

            # Add client filter in sidebar
            st.markdown("### 🔍 Filter by Client")
            unique_clients = sorted(ipe_df['Name of Client'].dropna().unique())
            selected_client = st.selectbox(
                "Select a client:",
                list(unique_clients),
                index=0
            )
            
            
            # Filter data based on selected client
            filtered_df = ipe_df[ipe_df['Name of Client'] == selected_client].copy()
            
            if not filtered_df.empty:
                st.markdown("#### 📋 Client Information")
                
                # Display main client information in narrative format
                main_columns = ['Name of Client', 'Type', 'Referral Agent', 'Date Received', 
                               'Service End Date', 'Consent Signed for GRIT/NVFS', 'Case Manager', 
                               'Progress Reports Sent to Referring Agent/CM']
                
                # Filter columns that exist in the dataframe
                available_columns = [col for col in main_columns if col in filtered_df.columns]
                
                # Create narrative display
                narrative_text = ""
                for col in available_columns:
                    if col == 'Progress Reports Sent to Referring Agent/CM':
                        # Special handling for Progress Reports - collect all non-empty values from all rows
                        progress_reports = filtered_df[col].dropna().unique()
                        if len(progress_reports) > 0:
                            narrative_text += f"**{col}:**\n"
                            for report in progress_reports:
                                if str(report).strip() and str(report).strip() != "nan":
                                    narrative_text += f"• {report}\n"
                        else:
                            narrative_text += f"**{col}:** Not specified\n"
                    elif col == 'Date Received':
                        # Special formatting for Date Received - YYYY-MM-DD format
                        value = filtered_df[col].iloc[0] if not filtered_df[col].isna().all() else "Not specified"
                        if pd.notna(value) and value != "Not specified":
                            try:
                                # Convert to datetime and format as YYYY-MM-DD
                                if isinstance(value, str):
                                    date_obj = pd.to_datetime(value, errors='coerce')
                                else:
                                    date_obj = value
                                if pd.notna(date_obj):
                                    formatted_date = date_obj.strftime('%Y-%m-%d')
                                    narrative_text += f"**{col}:** {formatted_date}\n"
                                else:
                                    narrative_text += f"**{col}:** {value}\n"
                            except:
                                narrative_text += f"**{col}:** {value}\n"
                        else:
                            narrative_text += f"**{col}:** Not specified\n"
                    else:
                        value = filtered_df[col].iloc[0] if not filtered_df[col].isna().all() else "Not specified"
                        if pd.isna(value) or value == "":
                            value = "Not specified"
                        narrative_text += f"**{col}:** {value}\n"
                
                # Display each line separately with proper spacing
                lines = narrative_text.strip().split('\n')
                for line in lines:
                    if line.strip():  # Only display non-empty lines
                        st.markdown(line)
                        st.markdown("")  # Add extra spacing between lines
                
                # Display case notes separately
                st.markdown("#### 📝 Case Notes")
                case_notes_columns = ['Day of Case Note', 'Case Notes']
                case_notes_available = [col for col in case_notes_columns if col in filtered_df.columns]
                
                if case_notes_available:
                    case_notes_df = filtered_df[case_notes_available].dropna(subset=case_notes_available, how='all')
                    if not case_notes_df.empty:
                        # Reset index to remove index column from display
                        case_notes_df_display = case_notes_df.reset_index(drop=True)
                        st.table(case_notes_df_display)
                    else:
                        st.info("No case notes available for this client.")
                else:
                    st.info("Case notes columns not found in the dataset.")
                
                # Add new note section
                st.markdown("#### 📝 Add New Note")
                
                with st.form(key=f"note_form_{selected_client}"):
                    # Date selection for the new note
                    note_date = st.date_input(
                        "Note Date:",
                        value=datetime.today().date(),
                        key=f"note_date_{selected_client}"
                    )
                    
                    # Text area for new note
                    new_note = st.text_area(
                        "Enter your note:",
                        height=100,
                        placeholder="Type your note here...",
                        key=f"new_note_{selected_client}"
                    )
                    
                    # Add note button
                    submit_button = st.form_submit_button("➕ Add Note")
                    
                    if submit_button:
                        if new_note.strip():
                            try:
                                # Format the date as string
                                note_date_str = note_date.strftime('%m/%d/%y')
                                
                                # Prepare the new row data
                                new_row_data = {
                                    'Name of Client': selected_client,
                                    'Day of Case Note': note_date_str,
                                    'Case Notes': new_note.strip()
                                }
                                
                                # Add empty values for other columns to maintain structure
                                for col in ipe_df.columns:
                                    if col not in new_row_data:
                                        new_row_data[col] = ''
                                
                                # Convert to list in the correct order
                                new_row = [new_row_data.get(col, '') for col in ipe_df.columns]
                                
                                # Append to Google Sheets
                                worksheet2.append_row(new_row)
                                
                                st.success(f"✅ Note added successfully for {selected_client} on {note_date_str}")
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"❌ Error adding note: {str(e)}")
                        else:
                            st.warning("⚠️ Please enter a note before adding.")
            else:
                st.warning(f"No data found for client: {selected_client}")