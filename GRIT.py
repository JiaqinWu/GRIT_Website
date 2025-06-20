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



def send_email_mailjet(to_email, subject, body):
    api_key = st.secrets["mailjet"]["api_key"]
    api_secret = st.secrets["mailjet"]["api_secret"]
    sender = st.secrets["mailjet"]["sender"]

    mailjet = Client(auth=(api_key, api_secret), version='v3.1')

    data = {
        'Messages': [
            {
                "From": {
                    "Email": sender,
                    "Name": "GRIT Dashboard"
                },
                "To": [
                    {
                        "Email": to_email,
                        "Name": to_email.split("@")[0]
                    }
                ],
                "Subject": subject,
                "TextPart": body
            }
        ]
    }

    try:
        result = mailjet.send.create(data=data)
        #if result.status_code == 200:
            #st.success(f"📤 Email sent to {to_email}")
        #else:
            #st.warning(f"❌ Failed to email {to_email}: {result.status_code} - {result.json()}")
    except Exception as e:
        st.error(f"❗ Mailjet error: {e}")




# Example usage: Fetch data from Google Sheets
try:
    spreadsheet1 = client.open('GRIT')
    worksheet1 = spreadsheet1.worksheet('Sheet1')
    df = pd.DataFrame(worksheet1.get_all_records())
except Exception as e:
    st.error(f"Error fetching data from Google Sheets: {str(e)}")

#df['Submit Date'] = pd.to_datetime(df['Submit Date'], errors='coerce')
#df["Phone Number"] = df["Phone Number"].astype(str)

# Extract last Ticket ID from the existing sheet
#last_ticket = df["Ticket ID"].dropna().astype(str).str.extract(r"GU(\d+)", expand=False).astype(int).max()
#next_ticket_number = 1 if pd.isna(last_ticket) else last_ticket + 1
#new_ticket_id = f"GU{next_ticket_number:04d}"


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
    "JWu@pwcgov.org": {"password": "Qin8851216!", "role": "Coordinator", "name":"Jiaqin"},
}
lis_location = ["Maricopa Co. - Arizona", "Alameda Co. - California", "Los Angeles Co. - California", "Orange Co. - California", "Riverside Co. - California",\
                "Sacramento Co. - California", "San Bernadino Co. -California", "San Diego Co. - California", "San Francisco Co. - California",\
                "Broward Co. - Florida", "Duval Co. - Florida", "Hillsborough Co. - Florida", "Miami-Dade Co. - Florida","Orange Co. - Florida",\
                "Palm Beach Co. - Florida", "Pinellas Co. - Florida", "Cobb Co. - Georgia", "Dekalb Co. - Georgia", "Fulton Co. - Georgia",\
                "Gwinnett Co. - Georgia", "Cook Co. - Illinois", "Marion Co. - Indiana", "East Baton Rough Parish - Louisiana",\
                "Orleans Parish - Louisiana", "Baltimore City - Maryland", "Montgomery Co. - Maryland", "Prince George's Co. - Maryland",\
                "Suffolk Co. - Massachusetts", "Wayne Co. - Michigan", "Clark Co. - Neveda", "Essex Co. - New Jersey","Hudson Co. - New Jersey",\
                "Bronx Co. - New York", "Kings Co. - New York", "New York Co. - New York", "Queens Co. - New York", "Mecklenburg Co. - North Carolina",\
                "Cuyahoga Co. - Ohio", "Franklin Co. - Ohio", "Hamilton Co. - Ohio", "Philadelphia Co. - Pennsylvania", "Shelby Co. - Tennessee",\
                "Bexar Co. - Texas", "Dallas Co. - Texas","Harris Co. - Texas", "Tarrant Co. - Texas","Travis Co. - Texas","King Co. - Washington",\
                "Washington, DC", "San Juan Municipio - Puerto Rico", "Alabama", "Arkansas","Kentucky","Mississippi","Missouri","Oklahoma","South Carolina"]

# --- Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "role" not in st.session_state:
    st.session_state.role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

# --- Role selection
if st.session_state.role is None:
    st.image("logo1.png")
    st.title("Welcome to the GRIT Dashboard")

    role = st.selectbox(
        "Select your role",
        ["Requester", "Coordinator"],
        index=None,
        placeholder="Select option..."
    )

    if role:
        st.session_state.role = role
        st.rerun()

# --- Show view based on role
else:
    st.sidebar.title(f"Role: {st.session_state.role}")
    st.sidebar.button("🔄 Switch Role", on_click=lambda: st.session_state.update({
        "authenticated": False,
        "role": None,
        "user_email": ""
    }))
    # --- Submit button styling (CSS injection)
    st.markdown("""
        <style>
        .stButton > button {
            width: 100%;
            background-color: #cdb4db;
            color: black;
            font-weight: 600;
            border-radius: 8px;
            padding: 0.6em;
            margin-top: 1em;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Requester: No login needed
    if st.session_state.role == "Requester":
        st.image("logo1.png")
        st.header("Gang Response Intervention Team (G.R.I.T.) \n Referral Form")
        st.write("Please Contact Jennifer Kooyoomjian. GRIT Coordinator if you have any questions \n via email jkooyoomjian@pwcgov.org \n via phone (703) 792-6249")

        col1, col2 = st.columns(2)
        with col1:
            source = st.text_input("Referral Source *",placeholder="Enter text")
        with col2:
            phone = st.text_input("Phone Number *",placeholder="(201) 555-0123")    
        name_client = st.text_input("Name of Client *",placeholder="Enter text")

        st.write("Phone Numbers for Client")
        col3, col4 = st.columns(2)
        with col3:
            phone_home = st.text_input("Home",placeholder="(201) 555-0123")   
        with col4:
            work_home = st.text_input("Work",placeholder="(201) 555-0123")   

        col5, col6 = st.columns(2)
        with col5:
            cell_home = st.text_input("Cell",placeholder="(201) 555-0123")  

        address = st.text_input("Address of Client *",placeholder="Enter text")

        name_guardian = st.text_input("Name(s) of Parent(s)/Guardian(s) *",placeholder="Enter text")

        address_guardian = st.text_input("Address of Parent(s)/Guardian(s) (if different from child)",placeholder="Enter text")

        st.write("Phone Numbers for Parent(s)/Guardians")
        col7, col8 = st.columns(2)
        with col7:
            phone_home1 = st.text_input("Home",placeholder="(201) 555-0123")   
        with col8:
            work_home1 = st.text_input("Work",placeholder="(201) 555-0123")   

        col9, col10 = st.columns(2)
        with col9:
            cell_home1 = st.text_input("Cell",placeholder="(201) 555-0123")  

        reason_referral = st.text_area("Reason for Referral *", placeholder='Enter text', height=150) 

        safety_concerns = st.text_area("Safety Concerns", placeholder='Enter text') 

        transportation_needs = st.text_area("Does client/family have transportation needs?", placeholder='Enter text') 

        case_manager_name = st.text_input("Case manager's name (if applicable)",placeholder="Enter text")

        # --- Submit button styling (CSS injection)
        st.markdown("""
            <style>
            .stButton > button {
                width: 100%;
                background-color: #cdb4db;
                color: black;
                font-weight: 600;
                border-radius: 8px;
                padding: 0.6em;
                margin-top: 1em;
            }
            </style>
        """, unsafe_allow_html=True)

        # --- Submit logic
        if st.button("Submit"):
            def clean_and_format_us_phone(phone_input):
                digits = re.sub(r'\D', '', phone_input)
                if len(digits) == 10:
                    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                else:
                    return None

            errors = []

            formatted_phone = clean_and_format_us_phone(phone)
            formatted_phone_home = clean_and_format_us_phone(phone_home)
            formatted_phone_home1 = clean_and_format_us_phone(phone_home1)
            formatted_phone_cell = clean_and_format_us_phone(cell_home)
            formatted_phone_cell1 = clean_and_format_us_phone(cell_home1)
            formatted_phone_work = clean_and_format_us_phone(work_home)
            formatted_phone_work1 = clean_and_format_us_phone(work_home1)


            # Required field checks
            if not source: errors.append("Referral Source is required.")
            if not phone or not formatted_phone:
                errors.append("Please enter a valid U.S. phone number (10 digits).")
            if not name_client: errors.append("Name of Client is required.")
            if not address: errors.append("Address of Client is required.")
            if not name_guardian: errors.append("Name of Parent(s)/Guardian(s) is required.")
            if not reason_referral: errors.append("Reason for Referral is required.")


            # Show warnings or success
            if errors:
                for error in errors:
                    st.warning(error)
            else:
                # Add logic here to save to Google Sheet or database (add two more column "Submit Date" and "Status" marked as "Submitted" too)
                # Prepare the new row
                new_row = {
                    'Ticket ID': new_ticket_id,
                    'Jurisdiction': location,
                    'Organization': organization,
                    'Name': name,
                    'Title/Position': title,
                    'Email Address': email,
                    "Phone Number": formatted_phone,
                    "Focus Area": focus_area,
                    "TA Type": type_TA,
                    "Targeted Due Date": due_date.strftime("%Y-%m-%d"),
                    "TA Description":ta_description,
                    "Priority": priority_status,
                    "Submit Date": datetime.today().strftime("%Y-%m-%d"),
                    "Status": "Submitted",
                    "Assigned Date": pd.NA,
                    "Close Date": pd.NA,
                    "Assigned Coach": pd.NA,
                    "Coordinator Comment": pd.NA,
                    "Staff Comment": pd.NA,
                    "Document": drive_links
                }
                new_data = pd.DataFrame([new_row])

                try:
                    # Append new data to Google Sheet
                    updated_sheet = pd.concat([df, new_data], ignore_index=True)
                    updated_sheet = updated_sheet.applymap(
                        lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (datetime, pd.Timestamp)) else x
                    )
                    # Replace NaN with empty strings to ensure JSON compatibility
                    updated_sheet = updated_sheet.fillna("")
                    worksheet1.update([updated_sheet.columns.values.tolist()] + updated_sheet.values.tolist())
                    # -- Send email notifications to all coordinators
                    coordinator_emails = [email for email, user in USERS.items() if user["role"] == "Coordinator"]

                    subject = f"📥 New TA Request Submitted: {new_ticket_id}"
                    body = f"""
                    Hi Coordinator Team,

                    A new Technical Assistance request has been submitted:

                    🆔 Ticket ID: {new_ticket_id}
                    📍 Jurisdiction: {location}
                    🏢 Organization: {organization}
                    👤 Name: {name}
                    📝 Description: {ta_description}

                    📎 Attachments: {drive_links or 'None'}

                    Please review and assign this request via the dashboard: https://hrsa64dash-hu9htgdnmmpx2c6w5dmrou.streamlit.app/.

                    Best,
                    Your TA Dashboard Bot
                    """

                    for email in coordinator_emails:
                        try:
                            send_email_mailjet(
                                to_email=email,
                                subject=subject,
                                body=body,
                            )
                        except Exception as e:
                            st.warning(f"⚠️ Failed to email {email}: {e}")


                    st.success("✅ Submission successful!")
                    for key in list(st.session_state.keys()):
                        del st.session_state[key]
                    time.sleep(5)
                    st.rerun()

                except Exception as e:
                    st.error(f"Error updating Google Sheets: {str(e)}")
                
                


    # --- Coordinator or Staff: Require login
    elif st.session_state.role == "Coordinator":
        if not st.session_state.authenticated:
            st.subheader("🔐 Login Required")

            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login = st.button("Login")

            if login:
                user = USERS.get(email)
                if user and user["password"] == password and user["role"] == st.session_state.role:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials or role mismatch.")

        else:
            user_info = USERS.get(st.session_state.user_email)
            st.header("📬 Coordinator Dashboard")
            # Personalized greeting
            if user_info and "name" in user_info:
                st.markdown(f"#### 👋 Welcome, {user_info['name']}!")
            col1, col2, col3 = st.columns(3)
            # create column span
            today = datetime.today()
            last_week = today - timedelta(days=7)
            last_month = today - timedelta(days=30)
            undone_request = df[df['Status'] == 'Submitted'].shape[0]
            pastweek_request = df[df['Submit Date'] >= last_week].shape[0]
            pastmonth_request = df[df['Submit Date'] >= last_month].shape[0]
            col1.metric(label="# of Unassigned Requests", value= millify(undone_request, precision=2))
            col2.metric(label="# of Requests from past week", value= millify(pastweek_request, precision=2))
            col3.metric(label="# of Requests from past month", value= millify(pastmonth_request, precision=2))
            style_metric_cards(border_left_color="#DBF227")

            # Convert date columns
            df["Assigned Date"] = pd.to_datetime(df["Assigned Date"], errors="coerce")
            df["Targeted Due Date"] = pd.to_datetime(df["Targeted Due Date"], errors="coerce")
            df["Submit Date"] = pd.to_datetime(df["Submit Date"], errors="coerce")

            inprogress = df[df['Status'] == 'In Progress']
            next_month = today + timedelta(days=30)
            request_pastmonth = df[(df["Targeted Due Date"] <= next_month)&(df['Status'] == 'In Progress')]

            col4, col5 = st.columns(2)
            # --- Pie 1: In Progress
            with col4:
                st.markdown("#### 🟡 In Progress Requests by Coach")
                if not inprogress.empty:
                    chart_data = inprogress['Assigned Coach'].value_counts().reset_index()
                    chart_data.columns = ['Assigned Coach', 'Count']
                    pie1 = alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta(field="Count", type="quantitative"),
                        color=alt.Color(field="Assigned Coach", type="nominal"),
                        tooltip=["Assigned Coach", "Count"]
                    ).properties(width=250, height=250)
                    st.altair_chart(pie1, use_container_width=True)
                else:
                    st.info("No in-progress requests to show.")

            # --- Pie 2: Requests in Past Month
            with col5:
                st.markdown("#### 📅 Due in 30 Days by Coach")
                if not request_pastmonth.empty:
                    chart_data = request_pastmonth['Assigned Coach'].value_counts().reset_index()
                    chart_data.columns = ['Assigned Coach', 'Count']
                    pie2 = alt.Chart(chart_data).mark_arc(innerRadius=50).encode(
                        theta=alt.Theta(field="Count", type="quantitative"),
                        color=alt.Color(field="Assigned Coach", type="nominal"),
                        tooltip=["Assigned Coach", "Count"]
                    ).properties(width=250, height=250)
                    st.altair_chart(pie2, use_container_width=True)
                else:
                    st.info("No requests with coming dues to show.")
                

            staff_list = ["MM", "KK", "LL"]
            selected_staff = st.selectbox("Select a staff to view their requests", staff_list)


            # Date ranges
            today = datetime.today()
            last_month = today - timedelta(days=30)

            # Filter staff-specific data
            staff_dff = df[df["Assigned Coach"] == selected_staff].copy()

            # --- Metrics
            in_progress_count = staff_dff[staff_dff["Status"] == "In Progress"].shape[0]
            due_soon_count = staff_dff[
                (staff_dff["Status"] == "In Progress") & 
                (staff_dff["Targeted Due Date"] <= next_month)
            ].shape[0]
            completed_recently = staff_dff[
                (staff_dff["Status"] == "Completed") & 
                (staff_dff["Submit Date"] >= last_month)
            ].shape[0]

            # --- Metric Display
            col1, col2, col3 = st.columns(3)
            col1.metric("🟡 In Progress", in_progress_count)
            col2.metric("📅 Due in 30 Days", due_soon_count)
            col3.metric("✅ Completed (Last 30 Days)", completed_recently)

            # --- Detailed Table
            st.markdown("#### 📋 Detailed Request List")

            # --- Status filter
            status_options = ["In Progress", "Completed"]
            selected_status = st.multiselect(
                "Filter by request status",
                options=status_options,
                default=["In Progress"]
            )

            # Apply filters: staff and status
            staff_dfff = staff_dff[staff_dff["Status"].isin(selected_status)].copy()

            display_cols = [
                "Ticket ID", "Jurisdiction", "Organization", "Name", "Focus Area", "TA Type",
                "Targeted Due Date", "Priority", "Status", "TA Description","Document"
            ]

            # Sort by due date
            staff_dfff = staff_dfff.sort_values(by="Targeted Due Date")

            # Format dates for display
            staff_dfff["Targeted Due Date"] = staff_dfff["Targeted Due Date"].dt.strftime("%Y-%m-%d")

            st.dataframe(staff_dfff[display_cols].reset_index(drop=True))


            # Filter submitted requests
            submitted_requests = df[df["Status"] == "Submitted"].copy()

            st.subheader("📋 Unassigned Requests")

            if submitted_requests.empty:
                st.info("No submitted requests at the moment.")
            else:
                # Define custom priority order
                priority_order = {"Critical": 1, "High": 2, "Normal": 3, "Low": 4}

                # Create a temporary column for sort priority
                submitted_requests["PriorityOrder"] = submitted_requests["Priority"].map(priority_order)

                # Convert date columns if needed
                submitted_requests["Submit Date"] = pd.to_datetime(submitted_requests["Submit Date"], errors='coerce')
                submitted_requests["Targeted Due Date"] = pd.to_datetime(submitted_requests["Targeted Due Date"], errors='coerce')

                # Format dates to "YYYY-MM-DD" for display
                submitted_requests["Submit Date"] = submitted_requests["Submit Date"].dt.strftime("%Y-%m-%d")
                submitted_requests["Targeted Due Date"] = submitted_requests["Targeted Due Date"].dt.strftime("%Y-%m-%d")

                # Sort by custom priority, then submit date, then due date
                submitted_requests_sorted = submitted_requests.sort_values(
                    by=["PriorityOrder", "Submit Date", "Targeted Due Date"],
                    ascending=[True, True, True]
                )

                # Display clean table (exclude PriorityOrder column)
                st.dataframe(submitted_requests_sorted[[
                    "Ticket ID","Jurisdiction", "Organization", "Name", "Title/Position", "Email Address", "Phone Number",
                    "Focus Area", "TA Type", "Submit Date", "Targeted Due Date", "Priority", "TA Description","Document"
                ]].reset_index(drop=True))

                # Select request by index (row number in submitted_requests)
                request_indices = submitted_requests_sorted.index.tolist()
                selected_request_index = st.selectbox(
                    "Select a request to assign",
                    options=request_indices,
                    format_func=lambda idx: f"{submitted_requests_sorted.at[idx, 'Ticket ID']} | {submitted_requests_sorted.at[idx, 'Name']} | {submitted_requests_sorted.at[idx, 'Jurisdiction']}",
                )

                # Select coach
                selected_coach = st.selectbox(
                    "Assign a coach",
                    options=staff_list,
                    index=None,
                    placeholder="Select option..."
                )
                

                # Assign button
                if st.button("✅ Assign Coach and Start TA"):
                    try:
                        # Create a copy to avoid modifying the original df directly (optional but safe)
                        updated_df = df.copy()

                        # Update the selected row
                        updated_df.loc[selected_request_index, "Assigned Coach"] = selected_coach
                        updated_df.loc[selected_request_index, "Assigned Coordinator"] = user_info['name']
                        updated_df.loc[selected_request_index, "Status"] = "In Progress"
                        updated_df.loc[selected_request_index, "Assigned Date"] = datetime.today().strftime("%Y-%m-%d")

                        updated_df = updated_df.applymap(
                            lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (pd.Timestamp, datetime)) and not pd.isna(x) else x
                        )
                        updated_df = updated_df.fillna("") 

                        # Push to Google Sheet
                        worksheet1.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())

                        st.success(f"Coach {selected_coach} assigned! Status updated to 'In Progress'.")
                        time.sleep(2)
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error updating Google Sheets: {str(e)}")

                # --- Submit button styling (CSS injection)
                st.markdown("""
                    <style>
                    .stButton > button {
                        width: 100%;
                        background-color: #cdb4db;
                        color: black;
                        font-weight: 600;
                        border-radius: 8px;
                        padding: 0.6em;
                        margin-top: 1em;
                    }
                    </style>
                """, unsafe_allow_html=True)

                st.subheader("🚧 In-progress Requests")

                # Filter "In Progress" requests
                in_progress_df = df[df["Status"] == "In Progress"].copy()

                if in_progress_df.empty:
                    st.info("No requests currently in progress.")
                else:
                    # Convert date columns
                    in_progress_df["Assigned Date"] = pd.to_datetime(in_progress_df["Assigned Date"], errors="coerce")
                    in_progress_df["Targeted Due Date"] = pd.to_datetime(in_progress_df["Targeted Due Date"], errors="coerce")
                    in_progress_df['Expected Duration (Days)'] = (in_progress_df["Targeted Due Date"]-in_progress_df["Assigned Date"]).dt.days

                    # Format dates
                    in_progress_df["Assigned Date"] = in_progress_df["Assigned Date"].dt.strftime("%Y-%m-%d")
                    in_progress_df["Targeted Due Date"] = in_progress_df["Targeted Due Date"].dt.strftime("%Y-%m-%d")
                    

                    # --- Filters
                    st.markdown("#### 🔍 Filter Options")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        priority_filter = st.multiselect(
                            "Filter by Priority",
                            options=in_progress_df["Priority"].unique(),
                            default=in_progress_df["Priority"].unique(), key='in1'
                        )

                    with col2:
                        ta_type_filter = st.multiselect(
                            "Filter by TA Type",
                            options=in_progress_df["TA Type"].unique(),
                            default=in_progress_df["TA Type"].unique(), key='in2'
                        )

                    with col3:
                        focus_area_filter = st.multiselect(
                            "Filter by Focus Area",
                            options=in_progress_df["Focus Area"].unique(),
                            default=in_progress_df["Focus Area"].unique(), key='in3'
                        )
                    

                    # Apply filters
                    filtered_df = in_progress_df[
                        (in_progress_df["Priority"].isin(priority_filter)) &
                        (in_progress_df["TA Type"].isin(ta_type_filter)) &
                        (in_progress_df["Focus Area"].isin(focus_area_filter))
                    ]



                    # Display filtered table
                    st.dataframe(filtered_df[[
                        "Ticket ID","Jurisdiction", "Organization", "Name", "Title/Position", "Email Address", "Phone Number",
                        "Focus Area", "TA Type", "Assigned Date", "Targeted Due Date","Expected Duration (Days)","Priority",
                        "Assigned Coach", "TA Description","Document","Coordinator Comment"
                    ]].sort_values(by="Expected Duration (Days)").reset_index(drop=True))

                    # Select request by index (row number in submitted_requests)
                    request_indices1 = filtered_df.index.tolist()
                    selected_request_index1 = st.selectbox(
                        "Select a request to comment",
                        options=request_indices1,
                        format_func=lambda idx: f"{filtered_df.at[idx, 'Ticket ID']} | {filtered_df.at[idx, 'Name']} | {filtered_df.at[idx, 'Jurisdiction']}",
                    )

                    # Input + submit comment
                    comment_input = st.text_area("Comments", placeholder="Enter comments", height=150, key='comm')

                    if st.button("✅ Submit Comments"):
                        try:
                            # Find the actual row index in the original df (map back using ID or index)
                            selected_row_global_index = filtered_df.loc[selected_request_index1].name

                            # Copy and update df
                            updated_df = df.copy()
                            updated_df.loc[selected_row_global_index, "Coordinator Comment"] = comment_input
                            updated_df = updated_df.applymap(
                                lambda x: x.strftime("%Y-%m-%d") if isinstance(x, (pd.Timestamp, datetime)) and not pd.isna(x) else x
                            )
                            updated_df = updated_df.fillna("") 

                            # Push to Google Sheets
                            worksheet1.update([updated_df.columns.values.tolist()] + updated_df.values.tolist())

                            st.success("💬 Comment saved and synced with Google Sheets.")
                            time.sleep(2)
                            st.rerun()

                        except Exception as e:
                            st.error(f"Error updating Google Sheets: {str(e)}")


                st.subheader("✅ Completed Requests")

                # Filter "Completed" requests
                complete_df = df[df["Status"] == "Completed"].copy()

                if complete_df.empty:
                    st.info("No requests currently completed.")
                else:
                    # Convert date columns
                    complete_df["Assigned Date"] = pd.to_datetime(complete_df["Assigned Date"], errors="coerce")
                    complete_df["Close Date"] = pd.to_datetime(complete_df["Close Date"], errors="coerce")
                    complete_df["Targeted Due Date"] = pd.to_datetime(complete_df["Targeted Due Date"], errors="coerce")
                    complete_df['Expected Duration (Days)'] = (complete_df["Targeted Due Date"]-complete_df["Assigned Date"]).dt.days
                    complete_df['Actual Duration (Days)'] = (complete_df["Close Date"]-complete_df["Assigned Date"]).dt.days

                    # Format dates
                    complete_df["Assigned Date"] = complete_df["Assigned Date"].dt.strftime("%Y-%m-%d")
                    complete_df["Targeted Due Date"] = complete_df["Targeted Due Date"].dt.strftime("%Y-%m-%d")
                    complete_df["Close Date"] = complete_df["Close Date"].dt.strftime("%Y-%m-%d")

                    # --- Filters
                    st.markdown("#### 🔍 Filter Options")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        priority_filter1 = st.multiselect(
                            "Filter by Priority",
                            options=complete_df["Priority"].unique(),
                            default=complete_df["Priority"].unique(), key='com1'
                        )

                    with col2:
                        ta_type_filter1 = st.multiselect(
                            "Filter by TA Type",
                            options=complete_df["TA Type"].unique(),
                            default=complete_df["TA Type"].unique(), key='com2'
                        )

                    with col3:
                        focus_area_filter1 = st.multiselect(
                            "Filter by Focus Area",
                            options=complete_df["Focus Area"].unique(),
                            default=complete_df["Focus Area"].unique(), key='com3'
                        )

                    # Apply filters
                    filtered_df1 = complete_df[
                        (complete_df["Priority"].isin(priority_filter1)) &
                        (complete_df["TA Type"].isin(ta_type_filter1)) &
                        (complete_df["Focus Area"].isin(focus_area_filter1))
                    ]

                    # Display filtered table
                    st.dataframe(filtered_df1[[
                        "Ticket ID","Jurisdiction", "Organization", "Name", "Title/Position", "Email Address", "Phone Number",
                        "Focus Area", "TA Type", "Priority", "Assigned Coach", "TA Description","Document","Assigned Date",
                        "Targeted Due Date", "Close Date", "Expected Duration (Days)",
                        'Actual Duration (Days)', "Coordinator Comment", "Staff Comment"
                    ]].reset_index(drop=True))

