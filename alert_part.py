import dns.resolver
import os
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
import validators
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
import requests
import json
from configparser import ConfigParser
import time
import logging

logging.basicConfig(filename='domainexpirylogger.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
def handle_google_sheets_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except APIError as e:
            print(f"Google Sheets API Error: {e}")
            # Handle the API error appropriately, such as retrying, logging, or displaying an error message
        except SpreadsheetNotFound:
            print("Spreadsheet not found. Please check the spreadsheet name or permissions.")
            # Handle the error, such as displaying an error message or exiting the program
        except WorksheetNotFound:
            print("Worksheet not found. Please check the worksheet name or permissions.")
            # Handle the error, such as displaying an error message or continuing with an alternative workflow

    return wrapper

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
# Function to authenticate and access Google Sheets
@handle_google_sheets_exceptions
def access_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(info_dict, scopes = scope)
    client = gspread.authorize(creds)
    sheet = client.open('Domain_Expiry_Master').worksheet('Active_Domains')
    return sheet

def client_email(message, client_mail_ID):
# Read the config file
    config = ConfigParser()
    config.read('config.ini')

# Read the Email section from the config file
    email_section = config['Email']

# Get the email details from the config file
    sender_email = email_section['sender_email']
    sender_password = email_section['sender_password']
    recipient_email = client_mail_ID

# Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = email_section['subject']

# Add the message body
    msg.attach(MIMEText(message, 'plain'))

    try:
        # Create a secure SSL/TLS connection with the SMTP server
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()

        # Log in to the email account
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email sent successfully.")

        # Disconnect from the server
        server.close()
    except Exception as e:
        print(f"Error sending email: {str(e)}")


def check_api(domain):
    config = ConfigParser()
    config.read('config.ini')

    # Read the Discord section from the config file
    date_section = config['Date']
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
        # expiry_date_str = json.dumps(expiry_date, cls=DateTimeEncoder)
        # print(expiry_date)
        expiry_date_str = str(expiry_date)
        # print(expiry_date_str)
        expiry_date = datetime.datetime.strptime(expiry_date_str, '%Y-%m-%dT%H:%M:%SZ')
        # expiry_date = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d %H:%M:%S")
        # print(expiry_date)
        current_date = datetime.datetime.strptime(date_section['TODAY'], '%Y-%m-%d %H:%M:%S')
        # current_date = datetime.datetime.strptime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        days_remaining = (expiry_date - current_date).days
        return days_remaining, expiry_date
    else:
        # Handle the error response
        print(f"Request failed with status code: {response.status_code}")


def check_domain_expiry(sheet, domain_name):
    config = ConfigParser()
    config.read('config.ini')

    # Read the Discord section from the config file
    date_section = config['Date']
    try:
        domain_cells = sheet.findall(domain_name)
        # return domain_cells
        if domain_cells:
            # current_date = datetime.datetime.now()
            # Get the corresponding expiry da   te value from column C
            expiry_date_str = sheet.cell(domain_cells[0].row, 3).value
            expiry_date = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d %H:%M:%S")
            current_date = datetime.datetime.strptime(date_section['TODAY'], '%Y-%m-%d %H:%M:%S')
            days_remaining = (expiry_date - current_date).days
            return days_remaining
    except Exception as e:
        return f"Error: {str(e)}"


@handle_google_sheets_exceptions
def update_index_sheet(last_run, domain, remaining_days, status):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open('Domain_Expiry_Master').worksheet('index')
    index_values = sheet.get_all_values()

    # Find the row index of the corresponding domain name (assuming domain name is in column B)
    row_index = None
    for i, row in enumerate(index_values):
        if row[1] == domain:
            row_index = i + 1  # Adding 1 to account for 1-indexed row numbers in Google Sheets
            break
    index_sheet_data = []
    if row_index is not None:
        # Update the corresponding column values with the new ones
        sheet.update(f'A{row_index}', last_run)
        sheet.update(f'C{row_index}', remaining_days)
        sheet.update(f'D{row_index}', status)
        print(f"Updated index sheet for domain '{domain}' at {last_run}.")
    else:
        # Add a new row for the domain and update the column values
        new_row = [last_run, domain, remaining_days, status]
        sheet.append_row(new_row)
        print(f"Added a new row for domain '{domain}' at {last_run}.")

def send_discord_notification(message):
    # Read the config file
    config = ConfigParser()
    config.read('config.ini')

    # Read the Discord section from the config file
    discord_section = config['Discord']

    # Get the webhook URL and user ID from the config file
    WEBHOOK_URL = discord_section['webhook_url']
    USER_ID_LAKSHMI = discord_section['user_id_lakshmi']
    USER_ID_JAYAPRIYA = discord_section['user_id_jayapriya']
    USER_ID_DEEPA = discord_section['user_id_deepa']
    USER_ID_POOMAGAL = discord_section['user_id_poomagal']
    message_content = f'Hello <@{USER_ID_LAKSHMI}> and <@{USER_ID_JAYAPRIYA}>! {message}.'
    # message_content = f'Hello <@{USER_ID}>! This is a tagged message.'
    payload = {'content':  message_content}
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(payload)
    response = requests.post(WEBHOOK_URL, headers=headers, data=data)
    # response = requests.post(webhook_url, json=payload, headers=headers)
    if response.status_code == 204:
        print("Discord notification sent.")
    else:
        print("Failed to send Discord notification.")


def send_email(message):
# Read the config file
    config = ConfigParser()
    config.read('config.ini')

# Read the Email section from the config file
    email_section = config['Email']

# Get the email details from the config file
    sender_email = email_section['sender_email']
    sender_password = email_section['sender_password']
    recipient_email = email_section['recipient_email']

# Create the email message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = email_section['subject']

# Add the message body
    msg.attach(MIMEText(message, 'plain'))

    try:
        # Create a secure SSL/TLS connection with the SMTP server
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()

        # Log in to the email account
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print("Email sent successfully.")

        # Disconnect from the server
        server.close()
    except Exception as e:
        print(f"Error sending email: {str(e)}")


def main():
    sheet = access_google_sheets()
    domain_data = sheet.col_values(2)[1:]  # Assuming the domain names start from the second row of the second column
    domains_expiring_lately= []
    expiring_domains = []
    domains_expiring_in_a_day = []
    for domain in domain_data:
            if validators.domain(domain):
                domain_cells = sheet.findall(domain)
                status = sheet.cell(domain_cells[0].row, 6).value
                if status == "Active":
                    mail_ID = sheet.cell(domain_cells[0].row, 5).value
                    remaining_days = check_domain_expiry(sheet, domain)
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    # index_sheet_data.append(f"{current_time}, {domain}, {remaining_days}, Success")
                    update_index_sheet(current_time, f"{domain}", f"{remaining_days}", "Success")
                    time.sleep(10)
                    if 15 < remaining_days <= 30:
                        # print(remaining_days)
                        expiring_domains.append(f"{domain} is expiring in  {remaining_days} days")
                        message1 = "The following domains are expiring within 200 days:\n\n"
                        message1 += '\n'.join(expiring_domains)
                        if mail_ID:
                            client_email(f"{domain} is expiring in  {remaining_days} days", mail_ID)
                    elif remaining_days == 15:
                        remaining_days, expiry_date = check_api(domain)
                        if remaining_days <= 15:
                            message = f"{domain} in expiring in {remaining_days} days"
                            send_discord_notification(message)
                            send_email(message)
                        else:
                            domain_cells = sheet.findall(domain)
                            sheet.update_cell(domain_cells[0].row, 3, expiry_date)

                    elif remaining_days < 10:
                        remaining_days, expiry_date = check_api(domain)
                        if 0 < remaining_days <= 10:
                            domains_expiring_in_a_day.append(f"{domain} is expiring in  {remaining_days} days")
                            message2 = "The following domains are expiring within 10 day:\n\n"
                            message2 += '\n'.join(domains_expiring_in_a_day)
                            message3 = f"{domain} is expiring in {remaining_days} days"
                            send_discord_notification(message3)
                            send_email(message3)
                            if mail_ID:
                                client_email(message3, mail_ID)
                        else:
                            domain_cells = sheet.findall(domain)
                            formatted_expiry_date = expiry_date.strftime("%Y-%m-%d %H:%M:%S")
                            print(formatted_expiry_date)
                            sheet.update_cell(domain_cells[0].row, 3, formatted_expiry_date)
                        if remaining_days <= 0:
                            message4 = f"{domain} is expired on {expiry_date}."
                            send_discord_notification(message4)
                            send_email(message4)
                            if mail_ID:
                                client_email(message4, mail_ID)

                    else:
                        domains_expiring_lately.append(f"{domain} is expiring in  {remaining_days} days")
                        message3 = "The following domains are not expiring within 200 days:\n\n"
                        message3 += '\n'.join(domains_expiring_lately)
                    # print(expiring_domains)
            else:
                print("domains_data is not valid(Not a valid domain).")
            # name_servers = get_name_servers(domain)
            # if name_servers:
            #     update_name_server_sheet(name_servers, domain)
            #     print(f"Name servers for the {domain}: {', '.join(name_servers)}")

    if expiring_domains:
         send_discord_notification(f"Daily status check completed - {message1}")
         send_email(f"Daily status check completed - {message1}")
    elif domains_expiring_in_a_day:
         send_discord_notification("Daily status check completed")
         send_email("Daily status check completed")
    else:
         send_discord_notification("Daily status check completed for the day - No domains are expiring soon")
         send_email("Daily status check completed for the day - No domains are expiring soon")
        # index_sheet(index_sheet_data)
if __name__ == "__main__":
    main()
