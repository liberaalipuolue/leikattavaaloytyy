from __future__ import print_function

import sys
import os.path
import configparser

CONFIG_INI = './secrets/credentials-wp.ini'

config = configparser.ConfigParser()
# The file contains sheets config, and wordpress stuff
# TODO: Add example ini file to git repo
config.read(CONFIG_INI)

# Google sheets
# How to run, see: https://developers.google.com/sheets/api/quickstart/python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
try:
    SPREADSHEET_ID = config.get('google', 'SPREADSHEET_ID')
    SHEET_NAME = config.get('google', 'SHEET_NAME')
    COLUMN_MOMENTTI_NRO = config.getint('google', 'COLUMN_INDEX_MOMENTTI_NRO')
    COLUMN_MOMENTTI_NIMI = config.getint('google', 'COLUMN_INDEX_MOMENTTI_NIMI')
except configparser.NoOptionError:
    print("Mandatory config key missing, please review %s" % CONFIG_INI)
    sys.exit(1)

# Wordpress
import requests
# Configuration
# Note: To generate app_password, see wp-admin, users, edit user
try:
    WORDPRESS_URL = config.get('wordpress', 'WORDPRESS_URL')
    PAGE_ID = config.getint('wordpress', 'PAGE_ID') 
    USERNAME = config.get('wordpress', 'USERNAME')
    APP_PASSWORD = config.get('wordpress', 'APP_PASSWORD')
except configparser.NoOptionError:
    print("Mandatory config key missing, please review %s" % CONFIG_INI)
    sys.exit(1)

# Headers for the API request
HEADERS = {
    'Authorization': f'{requests.auth._basic_auth_str(USERNAME, APP_PASSWORD)}',
    'Content-Type': 'application/json'
}

def get_data():
    """
    Acquires Vaihtoehtobudjetti data over Sheets API.
    TODO: Convert Sheets API return value to data object
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                './secrets/credentials-vaihtoehtobudjetti.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=SHEET_NAME).execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')
            return
        else:
            # TODO: Convert to data object
            return values
        
    except HttpError as err:
        raise err

def print_data(data):
    for row in data:
        print('%s, %s' % (row[COLUMN_MOMENTTI_NRO], row[COLUMN_MOMENTTI_NIMI]))    

def generate_html(data):
    html = "<h1>Hello world</h1>"
    for item in data:
        html += "<p>%s</p>" % data[COLUMN_MOMENTTI_NRO]
    return html

def update_wordpress_page(page_id, content):
    """
    Update Vaihtoehtobudjetti page at Wordpress site
    """
    # Endpoint URL for updating a page
    endpoint = f'{WORDPRESS_URL}/wp-json/wp/v2/pages/{page_id}'
    
    print(f'Writing to {endpoint}')

    # Page data
    page_data = {
        'content': content
    }
    response = requests.post(endpoint, headers=HEADERS, json=page_data)
    
    if response.status_code == 200:
        print("Page updated successfully!")
        return response.json()
    else:
        print(f"Failed to update the page. Status code: {response.status_code}")
        print(f"Error: {response}")
        return None

def get_wordpress_page(page_id):
    """
    Gets page content
    Note that content and title are returned as "rendered" (i.e. different than wordpress editor shows with shortcodes etc)
    Note that password protected pages can be returned as empty content
    Note that hidden pages can return 401
    """
    endpoint = f'{WORDPRESS_URL}/wp-json/wp/v2/pages/{page_id}'
    response = requests.get(endpoint, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get the page {page_id}. Status code: {response.status_code}")
        return None

def get_wordpress_pages():
    endpoint = f'{WORDPRESS_URL}/wp-json/wp/v2/pages'
    response = requests.get(endpoint, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get the pages. Status code: {response.status_code}")
        return None

def main():
    data = None
    try:
        data = get_data()        
    except HttpError as err:
        print(err)

    if data is None:
        print('No data found')
        sys.exit(10)
    
    print("Got data")
    # print_data(data)
    
    html = generate_html(data)
    if html is None:
        print("Failed to generate html")
        sys.exit(20)
    print("Generated HTML")
    
    response = update_wordpress_page(PAGE_ID, html)
    if response is None:
        print("Failed to update wordpress page")
        sys.exit(30)
    else:
        print("Page updated")

    print("Job's done")

if __name__ == '__main__':
    main()
