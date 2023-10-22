from __future__ import print_function
from collections import defaultdict

import datetime

import sys
import os.path
import configparser
from unicodedata import decimal

#
# TODO:
#   General tweaking
#   New content? - Small charts to summarize hallitus and lib difference per paaluokka ?
#

# Main config file, paths to secrets and google and worpress configuration
CONFIG_INI = 'vaihtoehtobudjetti-wordpress.ini'
print("Current working directory %s" % os.getcwd())
if not os.path.exists(CONFIG_INI):
    print("Mandatory config file missing, expected to find %s" % CONFIG_INI)
    sys.exit(1)
config = configparser.ConfigParser()
config.read(CONFIG_INI)

try:
    WORDPRESS_AUTHENTICATION_FILE = config.get('secrets', 'WORDPRESS_AUTHENTICATION')
    GOOGLE_AUTHENTICATION_FILE = config.get('secrets', 'GOOGLE_AUTHENTICATION')
    GOOGLE_TOKEN_FILE = config.get('secrets', 'GOOGLE_TOKEN')
except configparser.NoOptionError as e:
    print("Mandatory config key missing, please review %s. %r" % (CONFIG_INI, e))
    sys.exit(1)

# Wordpress authentication config
wpconfig = configparser.ConfigParser()
wpconfig.read(WORDPRESS_AUTHENTICATION_FILE)
try:
    WP_USERNAME = wpconfig.get('wordpress', 'USERNAME')
    WP_APP_PASSWORD = wpconfig.get('wordpress', 'APP_PASSWORD')
except configparser.NoOptionError as e:
    print("Mandatory config key missing, please review %s. %r" % (WORDPRESS_AUTHENTICATION_FILE, e))
    sys.exit(1)

# Google sheets
# How to run, see: https://developers.google.com/sheets/api/quickstart/python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file GOOGLE_TOKEN_FILE
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
try:
    SPREADSHEET_ID = config.get('google', 'SPREADSHEET_ID')
    SHEET_NAME = config.get('google', 'SHEET_NAME')
    SHEET_EXTRAS = config.get('google', 'SHEET_EXTRAS')
    COL_IDX_TULO = config.getint('google', 'COL_IDX_TULO')
    COL_IDX_SYVYYS = config.getint('google', 'COL_IDX_SYVYYS')
    COL_IDX_PAALUOKKA = config.getint('google', 'COL_IDX_PAALUOKKA')
    COL_IDX_PAALUOKKA_SELITE = config.getint('google', 'COL_IDX_PAALUOKKA_SELITE')
    COL_IDX_MENOLUOKKA = config.getint('google', 'COL_IDX_MENOLUOKKA')
    COL_IDX_MENOLUOKKA_SELITE = config.getint('google', 'COL_IDX_MENOLUOKKA_SELITE')
    COL_IDX_MOMENTTI = config.getint('google', 'COL_IDX_MOMENTTI')
    COL_IDX_MOMENTTI_SELITE = config.getint('google', 'COL_IDX_MOMENTTI_SELITE')    
    COL_IDX_HALLITUS = config.getint('google', 'COL_IDX_HALLITUS')
    COL_IDX_LIB = config.getint('google', 'COL_IDX_LIB')
    COL_IDX_PERUSTELU = config.getint('google', 'COL_IDX_PERUSTELU')
    COL_IDX_OSOITE = config.getint('google', 'COL_IDX_OSOITE')
    COL_IDX_LINKKI = config.getint('google', 'COL_IDX_LINKKI')
    COL_IDX_ERO = config.getint('google', 'COL_IDX_ERO')
    COL_IDX_ERO_PERCENT = config.getint('google', 'COL_IDX_ERO_PERCENT')
except configparser.NoOptionError as e:
    print("Mandatory config key missing, please review %s. %r" % (CONFIG_INI, e))
    sys.exit(1)

# Wordpress
import requests
# Configuration
# Note: To generate app_password, see wp-admin, users, edit user
try:
    WORDPRESS_URL = config.get('wordpress', 'WORDPRESS_URL')
    PAGE_ID = config.getint('wordpress', 'PAGE_ID') 
except configparser.NoOptionError:
    print("Mandatory config key missing, please review %s" % CONFIG_INI)
    sys.exit(1)

# Headers for the API request
HEADERS = {
    'Authorization': f'{requests.auth._basic_auth_str(WP_USERNAME, WP_APP_PASSWORD)}',
    'Content-Type': 'application/json'
}

# html generation
from yattag import Doc
from decimal import ConversionSyntax, Decimal, InvalidOperation
from dataclasses import dataclass
import locale # For currency formatting
locale.setlocale(locale.LC_ALL, 'fi_FI.UTF-8')

@dataclass
class DataObject:
    tulo: bool          # Tulo vai meno
    syvyys: int         # 1, 2 vai 3 tason rivi
    paaluokka: str      # Ensimmäinen nro
    paaluokka_selite: str # Ensimmäinen selite
    menoluokka: str       # Toinen nro
    menoluokka_selite: str # Toinen selite
    momentti: str      # Kolmas nro
    momentti_selite: str # Kolman selite
    osoite: str         # Ensimmainen nro.Toinen nro.Kolmas nro
    libLisays: bool     # Jos rivi on Liberaalipuolueen lisäys
    hallitus: Decimal   # Hallituksen esitys
    lib: Decimal # Liberaalipuolueen esitys
    ero: Decimal # Erotus, "Leikattavaa löytyy" -luku
    eroPercent: float # Erotus, desimaaleja
    perustelu: str      # Leikkauksen perustelu
    linkki: str         # Budjettikirjan linkki
    subrows: dict        # Sorttausta varten, alemman tason rivit

@dataclass
class SummaryDataObject:
    valtion_tehtavia_vahennetty: Decimal
    veronmaksajien_rahaa_saastetty: Decimal
    budjetista_leikattu_percent: Decimal
    budjetista_leikattu_percent_abs: Decimal
    tehtavia_siirretty_aluehallinnolle: Decimal
    alijaamaa: Decimal
    leikkausten_osuus: Decimal


def main():
    data = None
    summary = None
    try:
        data, summary = get_data()        
    except HttpError as err:
        print(err)

    if data is None:
        print('No data found')
        sys.exit(10)
    if summary is None:
        print('No summary found')
        sys.exit(10)
    
    print("Got data, %d rows" % (len(data)))    
    dataDict = sort_data(data)

    #print_sorted_data(dataDict)

    html = generate_html(dataDict, summary)
    if html is None:
        print("Failed to generate html")
        sys.exit(20)
    print("Generated HTML")
    html_file = 'output.html'
    with open(html_file, 'w') as file:
        file.write(html)
        print("Wrote to %s" % html_file)

    #sys.exit(0)    

    response = update_wordpress_page(PAGE_ID, html)
    if response is None:
        print("Failed to update wordpress page")
        sys.exit(30)
    else:
        print("Page updated")

    print("Job's done")



def get_data():
    """
    Acquires Varjobudjetti data over Sheets API.
    """
    creds = None
    # The file GOOGLE_TOKEN_FILE stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_AUTHENTICATION_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(GOOGLE_TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    values = False
    extras = False
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        # TODO?: use valueRenderOption='UNFORMATTED_VALUE', but it would require rewriting data parsing
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=SHEET_NAME).execute()
        values = result.get('values', [])
        
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=SHEET_EXTRAS, 
                                    valueRenderOption='UNFORMATTED_VALUE').execute()
        extras = result.get('values', [])
    except HttpError as err:
        raise err
    
    data = []
    if not values:
        print('No data found.')
        sys.exit(1)
    else:
        headerRow = True
        for row in values:            
            # Skip empty rows and first (header) row
            if not row:                
                continue
            if headerRow:
                headerRow = False
                continue
            
            try:
                # NOTE: Lenght of rows varies due Sheets API leaving out empty trailing cell values
                # XXX Handle varying row lengths by assuming default values and reading values only if row length is long enough
                lastIndex = len(row) - 1
                paaluokka_selite = ''
                menoluokka_selite = ''
                momentti_selite = ''
                perustelu = ''
                hallitusStr = ''
                libStr = ''
                tuloStr = ''
                syvyysStr = ''
                osoiteStr = ''
                linkkiStr = ''
                eroStr = ''
                eroPercentStr = ''
                if lastIndex >= COL_IDX_PAALUOKKA_SELITE:
                    paaluokka_selite=row[COL_IDX_PAALUOKKA_SELITE]
                if lastIndex >= COL_IDX_MENOLUOKKA_SELITE:
                    menoluokka_selite=row[COL_IDX_MENOLUOKKA_SELITE]
                if lastIndex >= COL_IDX_OSOITE:
                    osoiteStr=row[COL_IDX_OSOITE]
                if lastIndex >= COL_IDX_PERUSTELU:
                    perustelu=row[COL_IDX_PERUSTELU]
                if lastIndex >= COL_IDX_MOMENTTI_SELITE:
                    momentti_selite=row[COL_IDX_MOMENTTI_SELITE]
                if lastIndex >= COL_IDX_HALLITUS:
                    hallitusStr = row[COL_IDX_HALLITUS]
                if lastIndex >= COL_IDX_LIB:
                    libStr = row[COL_IDX_LIB]
                if lastIndex >= COL_IDX_TULO:
                    tuloStr = row[COL_IDX_TULO]
                if lastIndex >= COL_IDX_SYVYYS:
                    syvyysStr = row[COL_IDX_SYVYYS]
                if lastIndex >= COL_IDX_LINKKI:
                    linkkiStr = row[COL_IDX_LINKKI]
                if lastIndex >= COL_IDX_ERO_PERCENT:
                    eroPercentStr = row[COL_IDX_ERO_PERCENT]
                if lastIndex >= COL_IDX_ERO:
                    eroStr = row[COL_IDX_ERO]

                # FIXME: API/Sheet is returning 1 for 11 in for some rows
                #     due unknown issue.
                # Skip accessing number cells and extract values from osoite cell            
                #paaluokkaInt = 0
                #paaluokkaStr = row[COL_IDX_MENOLUOKKA]
                #try:
                #    paaluokkaInt = int(paaluokkaStr)
                #except ValueError:
                #    pass
                #menoLuokkaInt = 0
                #menoLuokkaStr = row[COL_IDX_PAALUOKKA]
                #try:
                #    menoLuokkaInt = int(menoLuokkaStr)
                #except ValueError:
                #    pass
                # Empty with lib additions
                #momenttiInt = 0
                #momenttiStr = row[COL_IDX_MOMENTTI]
                #try:
                #    momenttiInt = int(momenttiStr)
                #except ValueError:
                #    pass                
                (paaluokka, menoLuokka, momentti, libLisays) = extract_osoite(osoiteStr)

                #print("%s was parsed to %r.%r.%r" % (osoiteStr, paaluokka, menoLuokka, momentti))

                tuloBool = tuloStr == 'tulo'

                syvyysInt = 0
                try:
                    syvyysInt = int(syvyysStr)
                except ValueError:
                    pass

                hallitusDecimal = Decimal('0.0')
                if (len(hallitusStr) > 0):
                    # Remove non-breaking spaces
                    hallitusStr = hallitusStr.replace('\xa0', '')
                    # XXX Another header row? Not sure, but filter it out
                    if hallitusStr == 'Määräraha':
                        print("Skipping another header row like row.")
                        continue
                    try:
                        hallitusDecimal = Decimal(hallitusStr)
                    except InvalidOperation:
                        print("Failed to convert hallitusStr %r to Decimal %r" % (hallitusStr, row))
                        continue

                libDecimal = Decimal('0.0')
                if (len(libStr) > 0):
                    # Remove non-breaking spaces
                    libStr = libStr.replace('\xa0', '')
                    try:
                        libDecimal = Decimal(libStr)
                    except InvalidOperation:
                        print("Failed to convert libStr %r to Decimal" % libStr)
                        continue                    

                # Euroja
                # From sheet
                eroDecimal = Decimal('0.0')
                if (len(eroStr) > 0):
                    eroStr = eroStr.replace('\xa0', '')
                    eroStr = eroStr.replace('−', '-')
                    try:
                        eroDecimal = Decimal(eroStr)
                    except InvalidOperation:
                        print("Failed to convert eroDecimal %r to Decimal" % eroStr)
                        continue
                # Code
                #eroDecimal = hallitusDecimal - libDecimal                
                #eroDecimal = -eroDecimal
                

                # %
                eroPercentDecimal = Decimal('0.0')
                if (len(eroPercentStr) > 0):
                    try:
                        eroPercentDecimal = parse_localized_percent(eroPercentStr)
                    except ValueError:
                        print("Failed to convert eroPercentStr %r to Decimal" % eroPercentStr)
                        continue


                dataObj = DataObject(
                    tulo=tuloBool,
                    syvyys=syvyysInt,
                    paaluokka=paaluokka,
                    paaluokka_selite=paaluokka_selite,
                    menoluokka=menoLuokka,
                    menoluokka_selite=menoluokka_selite,
                    momentti=momentti,
                    momentti_selite=momentti_selite,
                    osoite=osoiteStr,
                    libLisays=libLisays,
                    hallitus=hallitusDecimal,
                    lib=libDecimal,
                    ero=eroDecimal,
                    eroPercent=eroPercentDecimal,
                    perustelu=perustelu,
                    linkki=linkkiStr,
                    subrows={}
                )
                data.append(dataObj)
            except Exception as e:
                print("Failed to process row %r due %r" % (row, e))
    
    summary = None

    valtion_tehtavia_vahennetty = Decimal('0')
    veronmaksajien_rahaa_saastetty = Decimal('0')
    budjetista_leikattu_percent = Decimal('0')
    tehtavia_siirretty_aluehallinnolle = Decimal('0')
    alijaamaa = Decimal('0')
    leikkausten_osuus = Decimal('0')
    if not extras:
        print('No extra data found.')
        sys.exit(1)
    else:
        for row in extras:
            if len(row) < 2:
                print("Unexpected row length on extras: %r" % row)
                sys.exit(1)
            else:
                key = row[0]
                value = row[1]
                if key == 'Valtion tehtäviä vähennetty':
                    try:
                        valtion_tehtavia_vahennetty = Decimal(value)
                    except InvalidOperation:
                        print("Failed to convert %r to Decimal" % value)
                elif key == 'Veronmaksajien rahaa säästetty':
                    try:
                        veronmaksajien_rahaa_saastetty = Decimal(value)
                    except InvalidOperation:
                        print("Failed to convert %r to Decimal" % value)
                elif key == 'Valtion budjetista leikattu':
                    try:
                        round_2_value = round(value*100, 2)
                        budjetista_leikattu_percent = Decimal(round_2_value)
                        abs_value = abs(round(value*100,0))
                        budjetista_leikattu_percent_abs = Decimal(abs_value)
                    except InvalidOperation:
                        print("Failed to convert %r to Decimal" % value)
                elif key == 'Tehtäviä siirretty aluehallinnoille':
                    try:
                        tehtavia_siirretty_aluehallinnolle = Decimal(value)
                    except InvalidOperation:
                        print("Failed to convert %r to Decimal" % value)
                elif key == 'Alijäämää varjobudjetissa':
                    try:
                        alijaamaa = Decimal(value)
                    except InvalidOperation:
                        print("Failed to convert %r to Decimal" % value)
                elif key == 'Leikkausten osuus':
                    try:
                        value = round(value*100, 0)
                        leikkausten_osuus = Decimal(value)
                    except InvalidOperation:
                        print("Failed to convert %r to Decimal" % value)
                else:
                    if len(key) > 0:
                        print("Unknown extra key %r" % key)
                
                
    summary = SummaryDataObject(valtion_tehtavia_vahennetty=valtion_tehtavia_vahennetty,
        veronmaksajien_rahaa_saastetty=veronmaksajien_rahaa_saastetty, 
        budjetista_leikattu_percent=budjetista_leikattu_percent,
        budjetista_leikattu_percent_abs=budjetista_leikattu_percent_abs,
        tehtavia_siirretty_aluehallinnolle=tehtavia_siirretty_aluehallinnolle,
        alijaamaa=alijaamaa,
        leikkausten_osuus=leikkausten_osuus)   

    return (data, summary)

def extract_osoite_int(osoite: str) -> (int, int, int, bool):
    """
    Extracts and converts to ints. Cannot be used due sheet using non-numeric identiefiers too, such as 30.lib.60.
    """
    # Check for 'lib' ending
    isLib = osoite.endswith('lib') or osoite.endswith('lib.')
    
    # Remove 'lib' or 'lib.' or ' lib' if it's there
    osoite = osoite.replace('lib.', '')
    osoite = osoite.replace(' lib', '')
    osoite = osoite.replace('lib', '')
    
    # Split by dot and ensure we have three segments
    parts = osoite.split('.') + [0, 0, 0]
    
    # Convert to integers and return
    return int(parts[0] or 0), int(parts[1] or 0), int(parts[2] or 0), isLib

def extract_osoite(osoite: str) -> (str, str, str, bool):
    # Check for 'lib' ending
    isLib = 'lib' in osoite
    
    # Normalize ' lib' to 'lib
    osoite = osoite.replace(' lib', 'lib')
    
    # Split by dot and ensure we have three segments
    parts = osoite.split('.') + ['', '', '']
    
    # Convert to integers and return
    return parts[0], parts[1], parts[2], isLib

def parse_localized_percent(percent_str):
    # Already set
    #locale.setlocale(locale.LC_ALL, 'fi_FI.utf8')
    percent_str = percent_str.replace('\xa0', ' ')
    percent_str = percent_str.strip('%')
    # Replace weird character with normal negative sign
    percent_str = percent_str.replace('−', '-')

    # Parse the localized string to a float
    try:
        percent_value = locale.atof(percent_str)
        #percent_str = percent_str.replace(',','.')
        #percent_value = float(percent_str)
    except ValueError as e:
        # Handle invalid input gracefully
        print("Invalid input:", percent_str)
        raise e

    # Convert the parsed value to the standard percentage (e.g., 55.2% becomes 0.552)
    percent_value /= 100.0

    return percent_value

def sort_data(data: list[DataObject]) -> dict:
    """
    Groups dataRows based on their common paaluokka and menoluokka numbers
    
    Returns
        dict of top level rows, other rows inserted into subrows dicts inside each row object
    """
    # XXX Initial sort required, as we want to first assign top level rows to dict, then second level and finally third level
    initial_sort = sorted(data, key=lambda row:(row.syvyys, row.paaluokka, row.menoluokka, row.momentti))

    tempDict = {}
    sorted_count = 0

    for row in initial_sort:
        # Skip suspicious rows -> 
        if not validate_syvyys(row):
            continue

        #print("Sorted a row %s" % row.osoite)

        if row.syvyys == 3:
            if row.paaluokka not in tempDict:
                print("Unknown paaluokka in row with syvyys 3. Implementation error")
                print("%r" % row)
                sys.exit(2)
            else:  
                if row.menoluokka not in tempDict[row.paaluokka].subrows:
                    print("Unknown menoluokka %r in paaluokka %r in row with syvyys 3. Implementation error" % (row.menoluokka, row.paaluokka))
                    print("%r" % row)
                    print("%r" % tempDict[row.paaluokka].subrows)
                    sys.exit(2)
                else:
                    tempDict[row.paaluokka].subrows[row.menoluokka].subrows[row.momentti] = row
                    sorted_count += 1
        elif row.syvyys == 2:
            if row.paaluokka not in tempDict:
                print("Unknown paaluokka in row with syvyys 2. Unable to find paaluokka %r. Implementation error?" % row.paaluokka)
                print("Known paaluokka values:")
                for paaluokkaRow in tempDict.values():
                    print("%r" % paaluokkaRow.paaluokka)
                print("%r" % row)
                sys.exit(2)
            else:
                tempDict[row.paaluokka].subrows[row.menoluokka] = row
                sorted_count += 1
        elif row.syvyys == 1:
            tempDict[row.paaluokka] = row            
            sorted_count += 1
        else:
            print("Unexpected syvyys value %r, don't know what to do!" % row.syvyys)

    print("Sorted data contains %d rows" % sorted_count)
    
    return tempDict

def validate_syvyys(row) -> bool:
    """
    @deprecated: due lib values, can not assume int values
    Just check that syvyys is 1, 2, or 3

    Expecting syvyys = 1 row to have integer value in paaluokka
    Expecting syvyys = 2 row to have integer value in paaluokka and menoluokka
    Expecting syvyys = 3 row to have integer value in paaluokka and menoluokka and momentti
    Any other value for syvyys, assume invalid row
    Return True if syvyys validates OK
    """
    return row.syvyys in [1,2,3]
    
    try:
        if row.syvyys == 3:
            int(row.paaluokka)
            int(row.menoluokka)
            int(row.momentti)
        elif row.syvyys == 2:
            int(row.paaluokka)
            int(row.menoluokka)
        elif row.syvyys == 1:
            int(row.paaluokka)
        else:
            return False
        return True
    except ValueError:
        print("Row %r failed syvyys validation" % row)
        return False

def print_sorted_data(dataDict) -> None:    
    for row in dataDict.values():
        print("%r %r %r subrows" % (row.osoite, row.paaluokka_selite, len(row.subrows)))        
        for subrow in row.subrows.values():
            print("%r %r %r subrows" % (subrow.osoite, subrow.menoluokka_selite, len(subrow.subrows)))
            for subsubrow in subrow.subrows.values():
                print("%r %r %r subrows" % (subsubrow.osoite, subsubrow.momentti_selite, len(subsubrow.subrows)))

def update_wordpress_page(page_id, content):
    """
    Update content to Wordpress page

    Note: Page must be saved in "Classic editor" mode for REST api pushed content to be visible
          If page is saved using "Advanced Layout Editor" active, the will have completly different content
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

def euros(number) -> str:
    """
    Format currency
    """
    formatted = locale.currency(number, grouping=True, symbol=False)
    # Remove empty cents
    formatted = formatted.replace(",00", '')
    formatted += ' €'
    return formatted

def calc_saastoja_percent(hallitus, lib):
    percentage = 100 - (lib/hallitus) * 100
    rounded = round(percentage, 0)
    rounded = abs(max(rounded, 0))
    return rounded

def generate_html(data, summary) -> str:

    doc, tag, text = Doc().tagtext()
    doc.asis(generate_intro())
    
    doc.asis(generate_summary(data, summary))
    doc.asis(generate_menot_summary(data))
    # Too broad to be useful
    #doc.asis(generate_tulot_summary(data))

    with tag('div', klass='main_color av_default_container_wrap container_wrap fullsize'):
        with tag('div', klass='template-page content  av-content-full alpha units'):
            with tag('div', klass='entry-content-wrapper clearfix'):
                with tag('div', klass='flex_column av_one_full  flex_column_div av-zero-column-padding first  avia-builder-el-56  el_after_av_layout_row  el_before_av_one_full  avia-builder-el-first  '):                        
                    doc.asis("""  
                        <section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork">
                        <div class="avia_textblock  " itemprop="text">
                        <p style="text-align: center;"><span style="font-size: 36pt;">Liberaalipuolueen varjobudjetti 2024</span></p>
                        </div>
                        </section>
                    """)
                    doc.asis(generate_tulot(data))
                    doc.asis(generate_menot(data))

    doc.asis(generate_naamat())
    doc.asis(generate_outro())

    doc.asis(generate_2023())
    doc.asis(generate_mediassa_2023())
        
    doc.asis(generate_js())
    doc.asis("""<div style="height:50px" class="hr hr-invisible   avia-builder-el-115  el_after_av_hr  avia-builder-el-last "><span class="hr-inner "><span class="hr-inner-style"></span></span></div></div>""")

    # Generate release version
    current_datetime = datetime.datetime.now()
    timestamp = current_datetime.timestamp()
    formatted_time = current_datetime.strftime('%c')
    with tag('h6'):
        text("Versio %s" % formatted_time)

    return doc.getvalue()

def generate_intro() -> str:
    """
    Intro block
    """
    return """    
    <div class="flex_column av_one_full  flex_column_div av-zero-column-padding first  avia-builder-el-0  el_before_av_one_full  avia-builder-el-first  " style="border-radius:0px; "><section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p><img decoding="async" fetchpriority="high" class="wp-image-8978  aligncenter" src="https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-300x179.png" alt="" width="593" height="354" srcset="https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-300x179.png 300w, https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-1030x616.png 1030w, https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-768x459.png 768w, https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-1536x919.png 1536w, https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-2048x1225.png 2048w, https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-1500x897.png 1500w, https://liberaalipuolue.fi/wp-content/uploads/2022/09/Leikkauslogo_isokasi-705x422.png 705w" sizes="(max-width: 593px) 100vw, 593px"></p>
    </div></section></div>
    <div class="flex_column av_one_full  flex_column_div av-zero-column-padding first  avia-builder-el-2  el_after_av_one_full  el_before_av_one_half  column-top-margin" style="border-radius:0px; "><div class="hr hr-default   avia-builder-el-3  el_before_av_textblock  avia-builder-el-first "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><h4 style="text-align: center;"></h4>
<h4 style="text-align: center;"></h4>
<p style="text-align: center;"><span style="font-size: 24pt;">#LeikataanReilusti on Liberaalipuolueen varjobudjetti, jolla haluamme osoittaa, että nykyiselle tuhlauspolitiikalle ja valtion holtittomalle velanotolle on olemassa vaihtoehto.</span></p>
<p style="text-align: center;"><span style="font-size: 18pt;">Varjobudjetissa ei käytetä juustohöylää, vaan karsitaan kokonaan pois tehtäviä, jotka näkemyksemme mukaan eivät kuulu valtiolle ensinkään. Menokohteet tärkeysjärjestykseen laittamalla voidaan taata riittävä rahoitus koulutuksen, terveydenhuollon ja sosiaaliturvan kaltaisille ydintoiminnoille. Veronalennuksiinkin on varaa ilman alijäämiä ja lisävelkaa.</span></p>
<p style="text-align: center;"><span style="font-size: 18pt;">Tulevien sukupolvien kustannuksella eläminen ei ole välttämätöntä, vaan vastuuton poliittinen valinta. Me haluamme valita toisin, Suomen tulevaisuuden tähden.</span></p>
</div></section>
<div style="height:50px" class="hr hr-invisible   avia-builder-el-5  el_after_av_textblock  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    """

def generate_2023() -> str:
    """ 
    Linkit 2023 leikattavaa löytyy budjettiin
    """
    return """
    <div class="flex_column av_one_full  flex_column_div av-zero-column-padding first  avia-builder-el-96  el_after_av_one_third  el_before_av_one_full  column-top-margin" style="border-radius:0px; "><div style="height:50px" class="hr hr-invisible   avia-builder-el-97  el_before_av_hr  avia-builder-el-first "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <div class="hr hr-default   avia-builder-el-98  el_after_av_hr  el_before_av_hr "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
    <span style="font-size: 24pt;"><br>
    <a href="https://liberaalipuolue.fi/leikattavaaloytyy/">
    Katso myös Liberaalipuolueen #LeikattavaaLöytyy 2023 varjobudjetti</a></span>
    </div></section></div>
    """

    #    <div style="height:50px" class="hr hr-invisible   avia-builder-el-115  el_after_av_hr  avia-builder-el-last "><span class="hr-inner "><span class="hr-inner-style"></span></span></div></div>

def generate_mediassa_2023() -> str:
    """ 
    Linkit 2023 media esiintymisiin
    """

    # <div class="hr hr-default   avia-builder-el-9  el_after_av_hr  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
#<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><span style="font-size: 24pt;">#LeikattavaaLöytyy mediassa</span></p>
#</div></section></div>


    return """
<div class="flex_column av_one_half  flex_column_div av-zero-column-padding first  avia-builder-el-11  el_after_av_one_full  el_before_av_one_half  column-top-margin" style="border-radius:0px; "><section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">Aarne Leinonen | Heikelä&amp;Koskelo 23 minuuttia -podcastissa</p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><iframe title="YouTube video player" src="//www.youtube.com/embed/1nTK69pd6io?wmode=opaque&amp;rel=0" width="560" height="315" frameborder="0" allowfullscreen="allowfullscreen"></iframe></p>
</div></section></div>


<div class="flex_column av_one_half  flex_column_div av-zero-column-padding   avia-builder-el-14  el_after_av_one_half  el_before_av_one_half  column-top-margin" style="border-radius:0px; "><section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">Aarne Leinonen | Puheenaihe -podcastissa</p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><iframe loading="lazy" title="YouTube video player" src="//www.youtube.com/embed/MHwC4YUPThs?wmode=opaque&amp;rel=0" width="560" height="315" frameborder="0" allowfullscreen="allowfullscreen"></iframe></p>
</div></section></div>


<div class="flex_column av_one_half  flex_column_div av-zero-column-padding first  avia-builder-el-17  el_after_av_one_half  el_before_av_one_half  column-top-margin" style="border-radius:0px; "><section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">Lassi Kivinen | Rahapodin Vaalipodissa</p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><iframe loading="lazy" title="YouTube video player" src="//www.youtube.com/embed/IpV46VM23aY?wmode=opaque&amp;rel=0" width="560" height="315" frameborder="0" allowfullscreen="allowfullscreen"></iframe></p>
</div></section></div>


<div class="flex_column av_one_half  flex_column_div av-zero-column-padding   avia-builder-el-20  el_after_av_one_half  el_before_av_one_full  column-top-margin" style="border-radius:0px; "><section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">Lassi Kivinen | Neuvottelija -podcastissä</p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><iframe loading="lazy" title="YouTube video player" src="//www.youtube.com/embed/Lyd94PaRmxo?wmode=opaque&amp;rel=0" width="560" height="315" frameborder="0" allowfullscreen="allowfullscreen"></iframe></p>
</div></section></div>
    """

def generate_outro() -> str:
    """
    Contact and call to action -buttons
    """
    return """
    <div class="flex_column av_one_full  flex_column_div av-zero-column-padding first  avia-builder-el-96  el_after_av_one_third  el_before_av_one_full  column-top-margin" style="border-radius:0px; "><div style="height:50px" class="hr hr-invisible   avia-builder-el-97  el_before_av_hr  avia-builder-el-first "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <div class="hr hr-default   avia-builder-el-98  el_after_av_hr  el_before_av_hr "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <div style="height:50px" class="hr hr-invisible   avia-builder-el-99  el_after_av_hr  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><span style="font-size: 24pt;">Lisätietoja:<br>
    <a href="mailto:hallitus@liberaalipuolue.fi">hallitus@liberaalipuolue.fi</a></span></p>
    </div></section></div>
    <div class="flex_column av_one_full  flex_column_div av-zero-column-padding first  avia-builder-el-101  el_after_av_one_full  el_before_av_one_third  column-top-margin" style="border-radius:0px; ">
    <div class="hr hr-default   avia-builder-el-103  el_after_av_hr  el_before_av_hr "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>    

<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><span style="font-size: 32px;">Vapaus kaipaa puolustajansa – tule mukaan!</span></p>
</div></section>
    
    <div class="flex_column av_one_third  flex_column_div av-zero-column-padding first  avia-builder-el-108  el_after_av_one_third  el_before_av_one_third  column-top-margin" style="border-radius:0px; "><div class="avia-button-wrap avia-button-center  avia-builder-el-109  avia-builder-el-no-sibling "><a href="http://liberaalipuolue.fi/jaseneksi/" class="avia-button avia-button-fullwidth  avia-font-color-black avia-icon_select-yes-left-icon avia-color-custom " style="background-color:#ffd900; "><span class="avia_button_icon avia_button_icon_left" aria-hidden="true" data-av_icon="" data-av_iconfont="entypo-fontello"></span><span class="avia_iconbox_title">Liity jäseneksi!</span><span class="avia_button_background avia-button avia-button-fullwidth avia-color-theme-color-subtle"></span></a></div></div>
    <div class="flex_column av_one_third  flex_column_div av-zero-column-padding   avia-builder-el-110  el_after_av_one_third  el_before_av_one_full  column-top-margin" style="border-radius:0px; "><div class="avia-button-wrap avia-button-center  avia-builder-el-111  avia-builder-el-no-sibling "><a href="https://puoluerekisteri.fi/puolue/50" class="avia-button avia-button-fullwidth  avia-font-color-black avia-icon_select-yes-left-icon avia-color-custom " style="background-color:#ffd900; "><span class="avia_button_icon avia_button_icon_left" aria-hidden="true" data-av_icon="" data-av_iconfont="entypo-fontello"></span><span class="avia_iconbox_title">Täytä kannattajakortti</span><span class="avia_button_background avia-button avia-button-fullwidth avia-color-theme-color-subtle"></span></a></div></div>
    <div class="flex_column av_one_third  flex_column_div av-zero-column-padding  avia-builder-el-106  el_after_av_one_full  el_before_av_one_third  column-top-margin" style="border-radius:0px; "><div class="avia-button-wrap avia-button-center  avia-builder-el-107  avia-builder-el-no-sibling "><a href="https://liberaalipuolue.fi/leikattavaaloytyy/" class="avia-button avia-button-fullwidth  avia-font-color-black avia-icon_select-yes-left-icon avia-color-custom " style="background-color:#ffd900; "><span class="avia_button_icon avia_button_icon_left" aria-hidden="true" data-av_icon="" data-av_iconfont="entypo-fontello"></span><span class="avia_iconbox_title">#LeikattavaaLöytyy</span><span class="avia_button_background avia-button avia-button-fullwidth avia-color-theme-color-subtle"></span></a></div></div>
    """

    # Ei vaaleja nyt menossa:
    # 

def generate_naamat() -> str:
    """
    #LeikataanReilusti -työryhmä
    """
    return """

    <div class="flex_column av_one_full  flex_column_div av-zero-column-padding first  avia-builder-el-76  el_after_av_one_fourth  el_before_av_one_third  column-top-margin" style="border-radius:0px; " id="tyoryhma"><div class="hr hr-default   avia-builder-el-77  el_before_av_hr  avia-builder-el-first "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
<div style="height:50px" class="hr hr-invisible   avia-builder-el-78  el_after_av_hr  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><span style="font-size: 24pt;">#LeikataanReilusti -työryhmä<br>
</span></p>
</div></section></div>


<div class="flex_column av_one_third  flex_column_div av-zero-column-padding first  avia-builder-el-80  el_after_av_one_full  el_before_av_one_third  column-top-margin" style="border-radius:0px; "><section class="avia-team-member   avia-builder-el-81  el_before_av_button  avia-builder-el-first " itemscope="itemscope" itemtype="https://schema.org/Person"><div class="team-img-container"><img decoding="async" width="300" height="300" class="wp-image-11180 avia-img-lazy-loading-not-11180 avia_image avia_image_team" src="https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen-300x300.jpg" alt="Lassi Kivinen" itemprop="image" srcset="https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen-300x300.jpg 300w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen-80x80.jpg 80w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen-768x768.jpg 768w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen-36x36.jpg 36w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen-180x180.jpg 180w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen-705x705.jpg 705w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Lassi_Kivinen.jpg 800w" sizes="(max-width: 300px) 100vw, 300px"></div><h3 class="team-member-name" itemprop="name"><span class="ez-toc-section" id="lassi_kivinen"></span>Lassi Kivinen<span class="ez-toc-section-end"></span></h3><div class="team-member-description " itemprop="description"><p>Liberaalipuolueen puheenjohtaja<br>
Myyntipäällikkö<br>
</div><span class="hidden team-member-affiliation" itemprop="affiliation">Liberaalipuolue</span></section>
</div>


<div class="flex_column av_one_third  flex_column_div av-zero-column-padding   avia-builder-el-83  el_after_av_one_third  el_before_av_one_third  column-top-margin" style="border-radius:0px; "><section class="avia-team-member   avia-builder-el-84  el_before_av_button  avia-builder-el-first " itemscope="itemscope" itemtype="https://schema.org/Person"><div class="team-img-container"><img decoding="async" width="300" height="300" class="wp-image-10678 avia-img-lazy-loading-not-10678 avia_image avia_image_team" src="https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen-300x300.jpg" alt="Aarne Leinonen" itemprop="image" srcset="https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen-300x300.jpg 300w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen-80x80.jpg 80w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen-768x768.jpg 768w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen-36x36.jpg 36w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen-180x180.jpg 180w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen-705x705.jpg 705w, https://liberaalipuolue.fi/wp-content/uploads/2023/02/Aarne_Leinonen.jpg 974w" sizes="(max-width: 300px) 100vw, 300px"></div><h3 class="team-member-name" itemprop="name"><span class="ez-toc-section" id="aarne_leinonen"></span>Aarne Leinonen<span class="ez-toc-section-end"></span></h3><div class="team-member-description " itemprop="description"><p>Liberaalipuolueen puoluesihteeri<br>
Palvelumuotoilija, tohtorikoulutettava<br>
</div><span class="hidden team-member-affiliation" itemprop="affiliation">Liberaalipuolue</span></section>
</div>


<div class="flex_column av_one_third  flex_column_div av-zero-column-padding   avia-builder-el-86  el_after_av_one_third  el_before_av_one_third  column-top-margin" style="border-radius:0px; "><section class="avia-team-member   avia-builder-el-87  el_before_av_button  avia-builder-el-first " itemscope="itemscope" itemtype="https://schema.org/Person"><div class="team-img-container"><img decoding="async" width="300" height="300" class="wp-image-11375 avia-img-lazy-loading-not-11375 avia_image avia_image_team" src="https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-300x300.jpg" alt="Jussi Mäkipelto" itemprop="image" srcset="https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-300x300.jpg 300w, https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-1030x1030.jpg 1030w, https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-80x80.jpg 80w, https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-768x768.jpg 768w, https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-36x36.jpg 36w, https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-180x180.jpg 180w, https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM-705x705.jpg 705w, https://liberaalipuolue.fi/wp-content/uploads/2023/03/crop-3C3A9362-Jussi-Makipelto-022023-MEDIUM.jpg 1353w" sizes="(max-width: 300px) 100vw, 300px"></div><h3 class="team-member-name" itemprop="name"><span class="ez-toc-section" id="jussi_makipelto"></span>Jussi Mäkipelto<span class="ez-toc-section-end"></span></h3><div class="team-member-description " itemprop="description"><p>Vaasan piirijärjestön puheenjohtaja<br>
Tietotekniikan diplomi-insinööri<br>
</div><span class="hidden team-member-affiliation" itemprop="affiliation">Liberaalipuolue</span></section>
</div>

    """

def generate_summary(data, summary) -> str:
    doc, tag, text = Doc().tagtext()

    # Splitter and title

# I think this is redundant, the intro already briefs reader in
#    doc.asis("""
#    <div class="hr hr-default   avia-builder-el-24  el_before_av_textblock  avia-builder-el-first "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>  
#<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text">
#<p style="text-align: center;">
#<span style="font-size: 24pt;">#LeikataanReilusti -työryhmän tulokset</span></p>
#</div></section>
#    """)
    
    # Valtion tehtäviä vähennetty    
    doc.asis("""<div style="height:50px" class="hr hr-invisible   avia-builder-el-31  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>""")
    doc.asis("""
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
<span style="font-size: 24pt;">Valtion tehtäviä vähennetty</span></p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
<span style="font-size: 36pt;">
""")
    doc.asis(f'{euros(summary.valtion_tehtavia_vahennetty)}</span></p></div></section>')

    # valtion budjetista leikattu
    # % title
    doc.asis(f'<div style="height:50px" class="hr hr-invisible   avia-builder-el-28  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div><section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  av_inherit_color " itemprop="text"><p style="text-align: center;"><span style="font-size: 24pt;">Valtionbudjetista leikattu {round(summary.budjetista_leikattu_percent,2)} %</span></p></div></section>')
    # % progressbar
    doc.asis(f'<div class="avia-progress-bar-container avia_animate_when_almost_visible avia-builder-el-30 el_after_av_textblock el_before_av_hr av-flat-bar av-animated-bar av-small-bar avia_start_animation"><div class="avia-progress-bar theme-color-bar icon-bar-no"><div class="progress avia_start_animation" style="height:46px;"><div class="bar-outer"><div class="bar" style="width: {summary.budjetista_leikattu_percent_abs}%" data-progress="{summary.budjetista_leikattu_percent_abs}"></div></div></div></div></div>')
    doc.asis('<div style="height:50px" class="hr hr-invisible   avia-builder-el-31  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>')

    # Veronmaksajien rahaa säästetty
    # <div style="height:50px" class="hr hr-invisible   avia-builder-el-31  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    doc.asis("""
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><span style="font-size: 24pt;">Veronmaksajien rahaa säästetty</span></p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
<span style="font-size: 36pt;">
""")
    doc.asis(f'{euros(summary.veronmaksajien_rahaa_saastetty)}</span></p></div></section>')

    # Tehtaviä siirretty aluehallinnolle
    doc.asis("""<div style="height:50px" class="hr hr-invisible   avia-builder-el-31  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>""")
    doc.asis("""
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
<span style="font-size: 24pt;">Tehtäviä siirretty aluehallinnolle</span></p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
<span style="font-size: 36pt;">
""")
    doc.asis(f'{euros(summary.tehtavia_siirretty_aluehallinnolle)}</span></p></div></section>')

    # Alijäämää
    doc.asis("""<div style="height:50px" class="hr hr-invisible   avia-builder-el-31  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>""")
    doc.asis("""
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
<span style="font-size: 24pt;">Alijäämää</span></p>
</div></section>
<section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
<span style="font-size: 36pt;">
""")
    doc.asis(f'{euros(summary.alijaamaa)}</span></p></div></section>')

    # Leikkausten osuus
    # % title
    doc.asis(f'<div style="height:50px" class="hr hr-invisible   avia-builder-el-28  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div><section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  av_inherit_color " itemprop="text"><p style="text-align: center;"><span style="font-size: 24pt;">Leikkausten osuus {summary.leikkausten_osuus}%</span></p></div></section>')
    # % progressbar
    doc.asis(f'<div class="avia-progress-bar-container avia_animate_when_almost_visible avia-builder-el-30 el_after_av_textblock el_before_av_hr av-flat-bar av-animated-bar av-small-bar avia_start_animation"><div class="avia-progress-bar theme-color-bar icon-bar-no"><div class="progress avia_start_animation" style="height:46px;"><div class="bar-outer"><div class="bar" style="width: {summary.leikkausten_osuus}%" data-progress="{summary.leikkausten_osuus}"></div></div></div></div></div>')
    doc.asis('<div style="height:50px" class="hr hr-invisible   avia-builder-el-31  el_after_av_progress  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>')



    return doc.getvalue()

# "Säästöjä löydetty ministeriöittän"
def generate_menot_summary(data) -> str:
    doc, tag, text = Doc().tagtext()

    doc.asis("""
    <div class="hr hr-default   avia-builder-el-37  el_before_av_textblock  avia-builder-el-first "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;"><span style="font-size: 18pt;">Säästöjä löydetty ministeriöittäin.</span></p>
</div></section>    
    """)

    # Generate "Säästöjä löydetty ministeriöittäin" progress bar for each ministeriö
    for row in data.values():
        # Include only menot
        if row.tulo:
            continue
        if row.hallitus == 0:
            print("Skipping ministeriö with zero value at hallituksen esitys: %s" % title)
            continue
        title = row.osoite + " " + row.paaluokka_selite
        try:
            # Calculate
            #cut_percent = str(calc_saastoja_percent(row.hallitus, row.lib))
            # Use values from sheet
            percent = round(row.eroPercent*100, 0)
            lisays = percent > 0
            lisaysStr = ''
            if lisays:
                lisaysStr = ' KOROTUS'
            cut_percent = str(abs(percent))            
        except ZeroDivisionError:
            print("Unable to calculate cut percent for %s due hallitus value zero. Skipping" % title)
            continue
        doc.asis("""<div class="avia-progress-bar-container avia_animate_when_almost_visible avia-builder-el-39 el_after_av_textblock el_before_av_progress av-flat-bar av-animated-bar av-small-bar avia_start_animation"><div class="avia-progress-bar theme-color-bar icon-bar-yes"><div class="progressbar-title-wrap"><div class="progressbar-icon"><span class="progressbar-char" aria-hidden="true" data-av_icon="" data-av_iconfont="entypo-fontello"></span></div>""")
        with tag('div', klass='progressbar-title'):
            text(title)
        doc.asis("""</div><div class="progressbar-percent avia_sc_animated_number_active number_prepared avia_animation_done" data-timer="2200">""")
        doc.asis(f'<span class="av-bar-counter __av-single-number" data-number="{cut_percent}">{cut_percent}</span>%{lisaysStr}</div><div class="progress avia_start_animation" style="height:12px;"><div class="bar-outer">')
        doc.asis(f'<div class="bar" style="width: {cut_percent}%" data-progress="{cut_percent}"></div></div></div></div></div>')
                
    return doc.getvalue()

# Generated progress bars do not make much sense for tulot top level. Not current used due this.
def generate_tulot_summary(data) -> str:
    doc, tag, text = Doc().tagtext()

    doc.asis("""
    <div class="hr hr-default   avia-builder-el-37  el_before_av_textblock  avia-builder-el-first "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
    <span style="font-size: 18pt;">Veroleikkaukset</span></p>
</div></section>    
    """)

    for row in data.values():
        # Include only tulot
        if not row.tulo:
            continue
        if row.hallitus == 0:
            print("Skipping ministeriö with zero value at hallituksen esitys: %s" % title)
            continue
        title = row.osoite + " " + row.paaluokka_selite
        try:
            # Calculate
            #cut_percent = str(calc_saastoja_percent(row.hallitus, row.lib))
            # Use values from sheet
            percent = round(row.eroPercent*100, 0)
            cut_percent = str(percent)
        except ZeroDivisionError:
            print("Unable to calculate cut percent for %s due hallitus value zero. Skipping" % title)
            continue
        doc.asis("""<div class="avia-progress-bar-container avia_animate_when_almost_visible avia-builder-el-39 el_after_av_textblock el_before_av_progress av-flat-bar av-animated-bar av-small-bar avia_start_animation"><div class="avia-progress-bar theme-color-bar icon-bar-yes"><div class="progressbar-title-wrap"><div class="progressbar-icon"><span class="progressbar-char" aria-hidden="true" data-av_icon="" data-av_iconfont="entypo-fontello"></span></div>""")
        with tag('div', klass='progressbar-title'):
            text(title)
        doc.asis("""</div><div class="progressbar-percent avia_sc_animated_number_active number_prepared avia_animation_done" data-timer="2200">""")
        doc.asis(f'<span class="av-bar-counter __av-single-number" data-number="{cut_percent}">{cut_percent}</span>%</div><div class="progress avia_start_animation" style="height:12px;"><div class="bar-outer">')
        doc.asis(f'<div class="bar" style="width: {cut_percent}%" data-progress="{cut_percent}"></div></div></div></div></div>')
                
    return doc.getvalue()


def generate_tulot(data):
    doc, tag, text = Doc().tagtext()

    # Header
    doc.asis("""
    <div id="tulot" style="height:50px" class="hr hr-invisible   avia-builder-el-58  el_after_av_textblock  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
    <span style="font-size: 24pt;">Tulot</span></p>
</div></section>"""
    )

    doc.asis(generate_tables(data, include_tulot=True, include_menot=False))

    return doc.getvalue()

def generate_menot(data):
    doc, tag, text = Doc().tagtext()

    # Header
    doc.asis("""
    <div id="menot" style="height:50px" class="hr hr-invisible   avia-builder-el-58  el_after_av_textblock  el_before_av_textblock "><span class="hr-inner "><span class="hr-inner-style"></span></span></div>
    <section class="av_textblock_section " itemscope="itemscope" itemtype="https://schema.org/CreativeWork"><div class="avia_textblock  " itemprop="text"><p style="text-align: center;">
    <span style="font-size: 24pt;">Menot</span></p>
</div></section>"""
    )

    doc.asis(generate_tables(data, include_tulot=False, include_menot=True))

    return doc.getvalue()

def generate_tables(data, include_tulot=True, include_menot=True) -> str:
    """        
    """
    doc, tag, text = Doc().tagtext()

    for row in data.values():
        if row.tulo and not include_tulot:
            continue
        if not row.tulo and not include_menot:
            continue
        with tag('div', klass='toggle-section', style='border: none;'):
            with tag('h2', klass='toggle-button av-elegant-toggle toggler', style='padding: 35px 10px 30px 35px; border-left-width: 0; border-right-width: 0;'):
                text(row.osoite + " " + row.paaluokka_selite)
                doc.asis('<span class="toggle_icon"><span class="vert_icon"></span><span class="hor_icon"></span></span>')
            with tag('div', klass='section-content'):

                with tag('br'):
                    pass
                with tag('h4'):
                    text(f'Hallituksen esitys: {euros(row.hallitus)}')
                with tag('h4'):
                    text(f'Liberaalipuolueen esitys: {euros(row.lib)}')
                with tag('h4'):
                    text(f'Reilumpi leikkaus: {euros(row.ero)}')
                with tag('p', style="font-size: 14pt;"):
                    text(row.perustelu)

                # TODO: Search

                for subrow in row.subrows.values():
                    doc.asis(generate_level_2(subrow))
    return doc.getvalue()

def generate_level_2(subrow) -> str:
    """
    <section class="av_toggle_section"  itemscope="itemscope" itemtype="https://schema.org/CreativeWork"  >
        <div role="tablist" class="single_toggle" data-tags="{All} "  >        
        <p data-fake-id="#25_oikeusministerion_hallinnonala" class="toggler "  itemprop="headline"    role="tab" tabindex="0" aria-controls="25_oikeusministerion_hallinnonala">
        25. Oikeusministeriön hallinnonala
        <span class="toggle_icon" >
        <span class="vert_icon"></span>
        <span class="hor_icon"></span>
        </span><
        /p>        
        <div id="25_oikeusministerion_hallinnonala" class="toggle_wrap "   >
        <div class="toggle_content invers-color "  itemprop="text"   >
        <p>
        <a href="https://budjetti.vm.fi/indox/sisalto.jsp?year=2023&#038;lang=fi&#038;maindoc=/2023/tae/hallituksenEsitys/hallituksenEsitys.xml&#038;id=/2023/tae/hallituksenEsitys/YksityiskohtaisetPerustelut/25/25.html" target="_blank" rel="noopener">Linkki</a>
        </p>
    <h4>Hallituksen esitys: 1 076 795 000€</h4>
    <h4>Liberaalipuolueen esitys: 998 883 761€</h4>
    <h4>Leikattavaa löytyy: −77 911 239€</h4>
    <p><span style="font-size: 14pt;" data-sheets-value="{" data-sheets-userformat="{">
    Oikeusvaltion ylläpito tulee turvata riittävällä rahoituksella. IT-hankkeiden resurssitehokkuutta tulee parantaa.</span>
    </p>
    """
    doc, tag, text = Doc().tagtext()

    with tag('section', klass='inner-toggle-section'):
#        with tag('p', klass="inner-toggle-button"):
#            with tag('span', style="font-size: 16pt;"):
#                text(subrow.osoite + " " + subrow.menoluokka_selite)
#        with tag('div',klass='inner-section-content'):
#            with tag('p'):
#                pass           
#            with tag('h5'):
#                text(f'Hallituksen esitys: {euros(subrow.hallitus)}')
#            with tag('h5'):
#                text(f'Liberaalipuolueen esitys: {euros(subrow.lib)}')
#            with tag('h5'):
#                text(f'Leikattavaa löytyy: {euros(subrow.ero)}')
#            with tag('p', style="font-size: 14pt;"):
#                text(subrow.perustelu)
        doc.asis(generate_level_2_table(subrow))

    return doc.getvalue()

def generate_level_2_table(subrow) -> str:
    """
    Returns table as yattag doc
    

    <table id="tablepress-11_verot" class="tablepress tablepress-id-11_verot tablepress-responsive tablepress-responsive-stack-tablet">
    <caption style="caption-side:bottom;text-align:left;border:none;background:none;margin:0;padding:0;"><a href="https://liberaalipuolue.fi/wp-admin/admin.php?page=tablepress&#038;action=edit&#038;table_id=11_verot" rel="nofollow">Muokkaa</a></caption>
    <thead>
    <tr class="row-1 odd">
	<th class="column-1">Momentti</th><th class="column-2">Hallituksen esitys</th><th class="column-3">Liberaalien esitys</th><th class="column-4">Leikattavaa löytyy</th><th class="column-5">Selite</th>
    </tr>
    </thead>
    <tbody>
    <tr class="row-2 even">
	    <td class="column-1"><h4 class="table_header">11.01. Tulon ja varallisuuden perusteella kannettavat verot</h4><a href="https://budjetti.vm.fi/indox/sisalto.jsp?year=2023&amp;lang=fi&amp;maindoc=/2023/tae/hallituksenEsitys/hallituksenEsitys.xml&amp;id=/2023/tae/hallituksenEsitys/YksityiskohtaisetPerustelut/11/01/01.html"target="_blank">Linkki</a></td><td class="column-2"><h4 class="table_header"><span class="mobileview">Hallituksen esitys: </span>30 857 000 000</h4></td><td class="column-3"><h4 class="table_header"><span class="mobileview">Liberaalipuolueen esitys: </span>27 791 335 988</h4></td><td class="column-4"><h4 class="table_header"><span class="mobileview">Leikattavaa löytyy: </span>−3 065 664 012</h4></td><td class="column-5"></td>
    </tr>
    <tr class="row-3 odd">
    	<td class="column-1"><p>11.01.01. Ansio- ja pääomatuloverot</p><a href="https://budjetti.vm.fi/indox/sisalto.jsp?year=2023&amp;lang=fi&amp;maindoc=/2023/tae/hallituksenEsitys/hallituksenEsitys.xml&amp;id=/2023/tae/hallituksenEsitys/YksityiskohtaisetPerustelut/11/01/01/01.html"target="_blank">Linkki</a></td><td class="column-2"><p><span class="mobileview">Hallituksen esitys: </span>23 876 000 000</p></td><td class="column-3"><p><span class="mobileview">Liberaalipuolueen esitys: </span>21 506 335 988</p></td><td class="column-4"><p><span class="mobileview">Leikattavaa löytyy: </span>−2 369 664 012</p></td><td class="column-5"><p>Työn verotusta tulee laskea merkittävästi. Liberaalipuolue ehdottaa palkkatulojen verotukseen 4,3 miljardin kevennystä. Työn verotusta ovat kaikki palkkasidonnaiset maksut, esimerkiksi eläkemaksut, sosiaalivakuutusmaksut, kunnallisvero ja valtion tulovero. Markkinoita vääristävistä ja verojärjestelmää monimutkaistavista verovähennyksistä tulee luopua samalla kun työn verotusta lasketaan merkittävästi. Tuloverotuksen kevennys katetaan karsimalla valtion toissijaisista tehtävistä 2,4 mrd € eriteltynä muissa momenteissa, sekä poistamalla verotukia 1,9 mrd €. Poistettavia verotukia ovat oman asunnon myyntivoiton verottomuus 1,5 mrd €, työmarkkinajärjestöjen jäsenmaksujen vähennys 0,21 mrd €. Kansalaisilla on oltava varaa ostaa palveluita ilman verovähennyksiä; nykyinen verokiila tekee sen mahdottomaksi. Verotuksen yksinkertaistamiseksi myös erillinen Yleisradiovero poistetaan. Lisäksi luovutusvoittoveron kertymä nousee 90 M€ perintöveron poistamisen myötä. Näiden ansio- ja pääomatuloverojen sisällä tapahtuvien painopistemuutosten avulla työhön kohdistuvaa verotusta voidaan laskea 4,3 mrd €/v, eli 21 % nykyisestä 2023 vuodelle suunnitellusta 20,5 mrd kertymästä.</p></td>
    </tr>
    </tbody>
    </table>
    """

    # XXX: tablepress-id-11_verot applies some styling, so each table gets it

    doc, tag, text = Doc().tagtext()
    odd = True
    with tag('table', klass='datatable tablepress tablepress-responsive tablepress-responsive-stack-tablet tablepress-id-11_verot'):
        with tag('thead'):
            with tag('tr'):
                with tag('th'):
                    text('Momentti')
                with tag('th'):
                    text('Hallituksen esitys')
                with tag('th'):
                    text('Liberaalipuolueen esitys')
                with tag('th'):
                    text('Reilumpi leikkaus')
                with tag('th'):
                    text('Perustelu')

        with tag('tbody'):

            # Draw menoluokka as special row
            # #ffd90 Bright yellow
            with tag('tr', klass='menoluokka_row', style='background-color: rgb(255, 217, 0) !important;'):
                with tag('td'):
                    with tag('h4', klass='table_header'):
                        text(subrow.osoite + " " + subrow.menoluokka_selite)
                with tag('td'):
                    with tag('h4', klass='table_header'):
                        text(euros(subrow.hallitus))
                with tag('td'):
                    with tag('h4', klass='table_header'):
                        text(euros(subrow.lib))
                with tag('td'):
                    with tag('h4', klass='table_header'):
                        text(euros(subrow.ero))
                with tag('td'):
                    with tag('h4', klass='table_header'):
                        text(subrow.perustelu)

            for subsubrow in subrow.subrows.values():
                odd = not odd
                class_text = 'even'
                if odd:
                    class_text = 'odd'
                with tag('tr', klass=class_text):
                    with tag('td'):
                        text(subsubrow.osoite + " " + subsubrow.momentti_selite)
                        text(" ")
                        if subsubrow.linkki:
                            with tag('a', href=subsubrow.linkki, target='_blank'):
                                text("Linkki")
                    with tag('td'):
                        text(euros(subsubrow.hallitus))
                    with tag('td'):
                        text(euros(subsubrow.lib))
                    with tag('td'):
                        text(euros(subsubrow.ero))
                    with tag('td'):
                        text(subsubrow.perustelu)
            
    return doc.getvalue()

def generate_js() -> str:
    """
    Add js for:
    * Collapsing tables
    * Datatables for search
    """
    return """    
     <script>
        jQuery(document).ready(function(){
            jQuery(".toggle-button").click(function(){
                var section = jQuery(this).closest(".toggle-section");              
                section.find(".section-content").slideToggle();
                section.find(".vert_icon").slideToggle();
            });
            jQuery(".section-content").slideToggle(0);
        });
    </script>

    
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.js"></script>

    <script>
        jQuery(document).ready(function(){
            jQuery("table.datatable").DataTable({
                paging: false,
                searching: true,
                ordering: false,
                language: {
                  url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/fi.json',
                },
            });
       });
    </script>
 
    """

    # Not needed
    # <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.css" />

    
    


if __name__ == '__main__':
    main()
