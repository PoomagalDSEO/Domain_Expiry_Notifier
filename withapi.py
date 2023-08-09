import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from configparser import ConfigParser
import whois
from datetime import datetime
import pandas as pd
import requests
import datetime
import json
import time

db_type = st.secrets["db_credentials"]["type"]
db_project_id = st.secrets["db_credentials"]["project_id"]
db_private_key_id = st.secrets["db_credentials"]["private_key_id"]
db_private_key = st.secrets["db_credentials"]["private_key"].replace("\\n", "\n")
db_client_email = st.secrets["db_credentials"]["client_email"]
db_client_id = st.secrets["db_credentials"]["client_id"]
db_auth_uri = st.secrets["db_credentials"]["auth_uri"]
db_token_uri = st.secrets["db_credentials"]["token_uri"]
db_auth_provider_x509_cert_url = st.secrets["db_credentials"]["auth_provider_x509_cert_url"]
db_client_x509_cert_url = st.secrets["db_credentials"]["client_x509_cert_url"]

info_dict = {
    "type": db_type,
    "project_id": db_project_id,
    "private_key_id": db_private_key_id,
    "private_key": db_private_key,
    "client_email": db_client_email,
    "client_id": db_client_id,
    "auth_uri": db_auth_uri,
    "token_uri": db_token_uri,
    "auth_provider_x509_cert_url": db_auth_provider_x509_cert_url,
    "client_x509_cert_url": db_client_x509_cert_url,
}

# Google Sheets API credentials
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(info_dict, scope)
client = gspread.authorize(creds)
sheet = client.open('Domain_Expiry_Master').worksheet('Active_Domains')
name_server_sheet = client.open('Domain_Expiry_Master').worksheet('name_servers')


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)


def check_api(domain):
    # Set the API key
    api_key = 'at_5uVv0b42dbFoIxjWm4H7JHVopgGR4'
    # Set the API endpoint URL
    api_url = 'https://www.whoisxmlapi.com/whoisserver/WhoisService'
    # Set the domain name for which you want to retrieve WHOIS information
    # Set the API parameters
    params = {
        'apiKey': api_key,
        'domainName': domain,
        'outputFormat': 'json'  # Specify the desired output format (e.g., json)
    }
    # Send the GET request to the API endpoint
    response = requests.get(api_url, params=params)
    # Check the response status code
    if response.status_code == 200:
        # Extract the JSON data from the response
        domain_info = response.json()
        # domain_info_str = json.dumps(domain_info, cls=DateTimeEncoder)
        expiry_date = domain_info['WhoisRecord']['registryData']['expiresDate']
        name_server = domain_info['WhoisRecord']['registryData']['nameServers']['hostNames']
        # expiry_date_str = json.dumps(expiry_date, cls=DateTimeEncoder)
        # print(expiry_date)
        expiry_date_str = str(expiry_date)
        # print(expiry_date_str)
        return expiry_date_str, name_server
        # return domain_info_str
        # print(expiry_date_str)
    else:
        # Handle the error response
        print(f"Request failed with status code: {response.status_code}")


def check_domain_expiry(domain_name):
    # Read the config file
    config = ConfigParser()
    config.read('config.ini')

    # Read the Discord section from the config file
    date_section = config['Date']
    try:
        # check_api(domain_name)
        # domain = 'digitalseo.in'
        expiry_date_str, name_server = check_api(domain_name)
        expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%dT%H:%M:%SZ')
        if isinstance(expiry_date, datetime.datetime):
            current_date = datetime.datetime.strptime(date_section['TODAY'], '%Y-%m-%d %H:%M:%S')
            days_remaining = (expiry_date - current_date).days
            return days_remaining, expiry_date
        else:
            # return 0, None
            return "No expiration date available in domain info"
    except Exception as e:
        # return 0, None
        return f"Error: {str(e)}"


# Streamlit app
def add_new_domain():
    st.header("Add New Domain")
    #     # Define the Streamlit form
    with st.form(key='input_form_a'):
        col1, col2 = st.columns(2)

        with col1:
            domain_name = st.text_input("Enter domain name")
            client_name = st.text_input("Enter client name")
            # status = st.radio("Status of the domain", ("Active", "Defunct"))
            status = "Active"
        with col2:

            Maintained_by = st.radio("Maintained by", ("DigitalSEO", "Client"), horizontal=True)
            if Maintained_by == "DigitalSEO":
                text_value = st.text_input("Mail ID of our Team member", value="poomagal@digitalseo.in",
                                           key="my_text_input3", disabled=True)
                text_value = st.text_input("Mail ID of our Team member", value="deepa@digitalseo.in",
                                           key="my_text_input4",
                                           disabled=True)
                client_mail_id = st.text_input("Enter mail ID of client")
            elif Maintained_by == 'Client':
                text_value = st.text_input("Mail ID of our Team member", value="poomagal@digitalseo.in",
                                           key="my_text_input1", disabled=True)
                text_value = st.text_input("Mail ID of our Team member", value="deepa@digitalseo.in",
                                           key="my_text_input2",
                                           disabled=True)
                client_mail_id = st.text_input("Enter mail ID of client")
            # Submit button
            submitted = st.form_submit_button('Submit')
            if submitted:
                # if st.button("Submit"):
                # Get the current values in the serial number column
                serial_numbers = sheet.col_values(1)[1:]  # Exclude the header row

                # Find the maximum serial number
                if serial_numbers:
                    max_serial_number = max(map(int, serial_numbers))
                else:
                    max_serial_number = 0
                # Calculate the new serial number
                serial_number = max_serial_number + 1

                # Append the new domain details with the serial number
                expiry_date_str, name_servers = check_api(domain_name)
                # print(name_servers)
                remaining_days, expiry_date = check_domain_expiry(domain_name)
                # print(expiry_date)
                expiry_date_str = json.dumps(expiry_date, cls=DateTimeEncoder)
                # print(expiry_date_str)
                # expiry_date = datetime.datetime.strptime(expiry_date_str, '"%Y-%m-%dT%H:%M:%S"')
                # expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%d %H:%M:%S')
                current_date = datetime.datetime.now()
                # Format the current datetime as a string
                formatted_date = current_date.strftime('%Y-%m-%d')
                current_date_str = str(formatted_date)
                # print(expiry_date)
                expiry_date_str = str(expiry_date)
                name_servers= ', '.join(name_servers)
                name_server_sheet.append_row([serial_number, domain_name, name_servers, current_date_str])
                time.sleep(10)
                sheet.append_row([serial_number, domain_name, expiry_date_str, Maintained_by, client_mail_id, status, client_name])
                # Reorder the serial numbers properly
                column_values = sheet.col_values(2)
                domain_count = len(column_values) - 1
                # domain_count = len(sheet.get_all_values()) - 1  # Exclude the header row
                serial_numbers = [str(i) for i in range(1, domain_count + 1)]
                serial_number_column = sheet.range(f"A2:A{domain_count + 1}")
                for i, cell in enumerate(serial_number_column):
                    cell.value = serial_numbers[i]
                sheet.update_cells(serial_number_column)
                st.success("Domain details added successfully!")


def edit_existing_domain():
    # st.header("Edit Existing Domain")
    # with st.form(key='input_form_b'):
        col1, col2 = st.columns(2)
        # Get the list of domain names from the Google Sheet
        domain_names = sheet.col_values(2)[1:]  # Exclude the header row
        with col1:
            # Select the domain to edit
            st.subheader("Domain Details")
            selected_domain = st.selectbox("Select domain to edit", domain_names)
            try:
                # Display the existing domain details
                domain_row = sheet.find(selected_domain).row
                domain_data = sheet.row_values(domain_row)
                # st.subheader("Domain Details")
                st.write(f"Domain Name: {domain_data[1]}")
                st.write(f"Maintained by: {domain_data[3]}")
                if len(domain_data) >= 5:
                    st.write(f"Mail ID: {domain_data[4]}")
            except gspread.exceptions.CellNotFound:
                st.error("Domain not found in the Google Sheet")
        with col2:
            with st.form(key='input_form_b'):
                # Retrieve the existing domain details from the Google Sheet
                try:
                    domain_row = sheet.find(selected_domain).row
                    domain_data = sheet.row_values(domain_row)
                    # Allow editing of the domain details
                    st.subheader("Edit Domain Details")
                    new_domain_name = st.text_input("Enter new domain name", domain_data[1])
                    new_Maintained_by = st.radio("Maintained by", ("DigitalSEO", "Client"), index=0 if domain_data[3] == "DigitalSEO" else 1,horizontal= True)
                    if new_Maintained_by == "Client":
                        text_value = st.text_input("Mail ID of our Team member", value="poomagal@digitalseo.in",
                                                   key="my_text_input1", disabled=True)
                        text_value = st.text_input("Mail ID of our Team member", value="deepa@digitalseo.in",
                                                   key="my_text_input2", disabled=True)
                        client_mail_id = st.text_input("Enter mail ID of client")
                    else:
                        text_value = st.text_input("Mail ID of our Team member", value="poomagal@digitalseo.in",
                                                   key="my_text_input1", disabled=True)
                        text_value = st.text_input("Mail ID of our Team member", value="deepa@digitalseo.in",
                                                   key="my_text_input2", disabled=True)
                        client_mail_id = st.text_input("Enter mail ID of client")
                    new_mail_id = client_mail_id

                except gspread.exceptions.CellNotFound:
                    st.error("Domain not found in the Google Sheet")

                submitted = st.form_submit_button('Save Changes')
                if submitted:
                # if st.button("Save Changes"):
                    # Update the domain details in the Google Sheet
                    sheet.update_cell(domain_row, 2, new_domain_name)
                    sheet.update_cell(domain_row, 4, new_Maintained_by)
                    sheet.update_cell(domain_row, 5, new_mail_id)
                    st.success("Domain details updated successfully!")


def off_existing_domain():
    # st.header("Status of the Existing Domain")
    with st.form(key='input_form_b'):
        col1, col2 = st.columns(2)
        # Get the list of domain names from the Google Sheet
        domain_names = sheet.col_values(2)[1:]  # Exclude the header row
        with col1:
            st.subheader("Domain Details")
            # Select the domain to edit
            selected_domain = st.selectbox("Select domain to edit", domain_names)
            try:
                # Display the existing domain details
                domain_row = sheet.find(selected_domain).row
                domain_data = sheet.row_values(domain_row)
                # st.subheader("Domain Details")
                st.write(f"Domain Name: {domain_data[1]}")
                st.write(f"Maintained by: {domain_data[3]}")
                if len(domain_data) >= 5:
                    st.write(f"Mail ID: {domain_data[4]}")
                if len(domain_data) >= 6:
                    st.write(f"Status: {domain_data[5]}")
            except gspread.exceptions.CellNotFound:
                st.error("Domain not found in the Google Sheet")
        with col2:
            try:
                # Allow marking the domain as OFF
                st.subheader("Domain Status")
                status_options = ["Keep Active", "Defunct", "Delete"]
                status = st.radio("Select status", status_options)
            except gspread.exceptions.CellNotFound:
                st.error("Domain not found in the Google Sheet. Please select a valid domain.")
            # if st.button("Save Changes"):
            submitted = st.form_submit_button('Save Changes')
            if submitted:
                # Update the domain status in the Google Sheet
                if status == "Defunct":
                    sheet.update_cell(domain_row, 6, "Defunct")
                    defunct_sheet = client.open('Domain_Expiry_Master').worksheet('defunct_page')
                    domain_row = sheet.find(selected_domain).row
                    domain_data = sheet.row_values(domain_row)
                    defunct_sheet.append_row(domain_data)
                    # Reorder the serial numbers properly
                    column_values = defunct_sheet.col_values(2)
                    domain_count = len(column_values) - 1
                    serial_numbers = [str(i) for i in range(1, domain_count + 1)]
                    serial_number_column = defunct_sheet.range(f"A2:A{domain_count + 1}")
                    for i, cell in enumerate(serial_number_column):
                        cell.value = serial_numbers[i]
                    defunct_sheet.update_cells(serial_number_column)
                elif status == "Keep Active":
                    # sheet.append_row(domain_data)
                    sheet.update_cell(domain_row, 6, "Active")
                    defunct_sheet = client.open('Domain_Expiry_Master').worksheet('defunct_page')
                    domain_cells = defunct_sheet.findall(selected_domain)
                    first_cell = domain_cells[0]
                    domain_row_index = first_cell.row
                    defunct_sheet.delete_row(domain_row_index)
                    #Reorder the serial numbers properly
                    column_values = sheet.col_values(2)
                    domain_count = len(column_values) - 1
                    # domain_count = len(sheet.get_all_values()) - 1  # Exclude the header row
                    serial_numbers = [str(i) for i in range(1, domain_count + 1)]
                    serial_number_column = sheet.range(f"A2:A{domain_count + 1}")
                    for i, cell in enumerate(serial_number_column):
                        cell.value = serial_numbers[i]
                    sheet.update_cells(serial_number_column)
                elif status == "Delete":
                    sheet.delete_row(domain_row)
                    domain_row = name_server_sheet.find(selected_domain).row
                    name_server_sheet.delete_row(domain_row)
                    # Reorder the serial numbers properly
                    column_values = sheet.col_values(2)
                    domain_count = len(column_values) - 1
                    # domain_count = len(sheet.get_all_values()) - 1  # Exclude the header row
                    serial_numbers = [str(i) for i in range(1, domain_count + 1)]
                    serial_number_column = sheet.range(f"A2:A{domain_count + 1}")
                    for i, cell in enumerate(serial_number_column):
                        cell.value = serial_numbers[i]
                    name_server_sheet.update_cells(serial_number_column)
                    sheet.update_cells(serial_number_column)
                    st.success("Domain details deleted successfully!")
                st.success("Domain status updated successfully!")

def report_existing_domains():
    st.header("Report for Domains")
    data = sheet.get_all_values()

    # Convert the data into a DataFrame
    df = pd.DataFrame(data)

    # Set column names if the first row contains headers
    df.columns = df.iloc[0]
    df = df[1:]
    hide_table_row_index = """<style>
                    thead tr th:first-child {display:none}
                    tbody th {display:none}
                    </style>"""
    st.markdown(hide_table_row_index, unsafe_allow_html=True)
        # Display the DataFrame using st.table
    st.table(df)

# Streamlit app
tabs = {
    "Add new domain": add_new_domain,
    "Edit existing domain": edit_existing_domain,
    "OFF existing domain": off_existing_domain,
    "Report for existing domains": report_existing_domains
}

st.title("Domain Expiry Management App")
selected_tab = st.sidebar.selectbox("Select an option", list(tabs.keys()))
tabs[selected_tab]()

