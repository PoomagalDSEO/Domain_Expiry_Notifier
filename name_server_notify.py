import dns.resolver
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound
from datetime import datetime, timedelta
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import requests
import json
import time
from configparser import ConfigParser


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


# Function to authenticate and access Google Sheets
@handle_google_sheets_exceptions
def access_google_sheets():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    # sheet = client.open('Domain_Expiry_Master').worksheet('Active_Domains')
    # return sheet
    name_server_sheet = client.open('Domain_Expiry_Master').worksheet('name_servers')
    return name_server_sheet

def send_discord_notification(message):
    # Read the config file
    config = ConfigParser()
    config.read('config.ini')

    # Read the Discord section from the config file
    discord_section = config['Discord']

    # Get the webhook URL and user ID from the config file
    WEBHOOK_URL = discord_section['webhook_url']
    USER_ID = discord_section['user_id']

    message_content = f'Hello <@{USER_ID}>!  {message}.'
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


def update_name_server_sheet(name_servers, domain):
    name_server_sheet = access_google_sheets()
    # scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    # client = gspread.authorize(creds)
    # name_server_sheet = client.open('Domain_Expiry_Master').worksheet('name_servers')
    # name_servers_values = sheet.get_all_values()
    current_date = datetime.datetime.now()
    # Format the current datetime as a string
    formatted_date = current_date.strftime('%Y-%m-%d')
    current_date_str = str(formatted_date)
    domain_cells = name_server_sheet.findall(domain)
    previous_name_servers = []
    previous_name_servers = name_server_sheet.cell(domain_cells[0].row, 3).value
    previously_updated_date = []
    previously_updated_date = name_server_sheet.cell(domain_cells[0].row, 4).value
    # print(previously_updated_date)
    latest_name_servers = []
    cell_value = ', '.join(name_servers)
    name_server_sheet.update_cell(domain_cells[0].row, 5, cell_value)
    latest_name_servers = name_server_sheet.cell(domain_cells[0].row, 5).value
    time.sleep(5)
    latest_updated_date = []
    name_server_sheet.update_cell(domain_cells[0].row, 6, current_date_str)
    latest_updated_date = name_server_sheet.cell(domain_cells[0].row, 6).value
    latest_updated_date = datetime.datetime.strptime(latest_updated_date, '%Y-%m-%d')
    # print(latest_updated_date)
    # print(type(latest_updated_date))
    previously_updated_date = datetime.datetime.strptime(previously_updated_date, '%Y-%m-%d')
    # print(previously_updated_date)
    # print(type(previously_updated_date))
    # if (latest_updated_date - previously_updated_date).days == 0:
    #     print('done')
    if sorted(latest_name_servers) != sorted(previous_name_servers):
        send_discord_notification(f"name server is changed for the {domain} on {current_date_str}")
        name_server_sheet.update_cell(domain_cells[0].row, 3, latest_name_servers)
        time.sleep(5)
        name_server_sheet.update_cell(domain_cells[0].row, 4, current_date_str)
        if (latest_updated_date - previously_updated_date).days <= 3:
            send_discord_notification(f"name server is changed for the {domain} on {previously_updated_date}")
    # else:
    #     print(f"name server not changed for {domain}")
def get_name_servers(domain):
    try:
        # Perform a DNS lookup for the name servers of the domain
        answers = dns.resolver.resolve(domain, 'NS')
        name_servers = [str(answer) for answer in answers]
        return name_servers
    except dns.resolver.NXDOMAIN:
        print(f"Domain '{domain}' does not exist.")
    except dns.resolver.NoAnswer:
        print(f"No name servers found for domain '{domain}'.")
    except dns.resolver.Timeout:
        print(f"DNS lookup timed out for domain '{domain}'.")
    except dns.exception.DNSException as e:
        print(f"An error occurred during the DNS lookup: {str(e)}")


def main():
    name_server_sheet = access_google_sheets()
    domain_data = name_server_sheet.col_values(2)[1:]  # Assuming the domain names start from the second row of the second column
    for domain in domain_data:
            name_servers = get_name_servers(domain)
            if name_servers:
                update_name_server_sheet(name_servers, domain)
                print(f"Name servers for the {domain}: {', '.join(name_servers)}")
if __name__ == "__main__":
    main()