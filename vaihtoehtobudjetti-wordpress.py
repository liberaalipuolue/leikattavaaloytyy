from __future__ import print_function
from collections import defaultdict

import sys
import os.path
import configparser

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

from decimal import Decimal, InvalidOperation
from dataclasses import dataclass

@dataclass
class DataObject:
    tulo: bool          # Tulo vai meno
    syvyys: int         # 1, 2 vai 3 tason rivi
    paaluokka: int      # Ensimmäinen nro
    paaluokkaSelite: str # Ensimmäinen selite
    menoluokka: int       # Toinen nro
    menoluokkaSelite: str # Toinen selite
    momentti: int       # Kolmas nro
    momenttiSelite: str # Kolman selite
    osoite: str         # Ensimmainen nro.Toinen nro.Kolmas nro
    libLisays: bool     # Jos rivi on Liberaalipuolueen lisäys
    hallitus: Decimal   # Hallituksen esitys
    lib: Decimal # Liberaalipuolueen esitys
    perustelu: str      # Leikkauksen perustelu
    linkki: str         # Budjettikirjan linkki
    subrows: dict        # Sorttausta varten, alemman tason rivit



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

    sys.exit(0)

    dataDict = sort_data(data)

    print("Got dataDict")

    print_sorted_data(dataDict)
    
    

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



def get_data() -> list[DataObject]:
    """
    Acquires Vaihtoehtobudjetti data over Sheets API.
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
    try:
        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID,
                                    range=SHEET_NAME).execute()
        values = result.get('values', [])
    except HttpError as err:
        raise err
    
    data = []
    if not values:
        print('No data found.')
        return
    else:
        for row in values:
            # Skip empty rows
            if not row:                
                continue

            try:
                tuloStr = row[COL_IDX_TULO]
                tuloBool = tuloStr == 'tulo'

                syvyysInt = 0
                syvyysStr = row[COL_IDX_SYVYYS]
                try:
                    syvyysInt = int(syvyysStr)
                except ValueError:
                    pass

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
                (paaluokkaInt, menoLuokkaInt, momenttiInt, libLisays) = extract_osoite(row[COL_IDX_OSOITE])


                momenttiSelite = row[COL_IDX_MOMENTTI_SELITE]
                libLisays = 'lib.' in momenttiSelite

                hallitusDecimal = Decimal('0.0')
                hallitusStr = row[COL_IDX_HALLITUS]
                if (len(hallitusStr) > 0):
                    # Remove non-breaking spaces
                    hallitusStr = hallitusStr.replace('\xa0', '')
                    try:
                        hallitusDecimal = Decimal(hallitusStr)
                    except InvalidOperation:
                        print("Failed to convert hallitusStr %r to Decimal" % hallitusStr)
                        continue

                libDecimal = Decimal('0.0')
                libStr = row[COL_IDX_LIB]
                if (len(libStr) > 0):
                    # Remove non-breaking spaces
                    libStr = libStr.replace('\xa0', '')
                    try:
                        libDecimal = Decimal(libStr)
                    except InvalidOperation:
                        print("Failed to convert libStr %r to Decimal" % hallitusStr)
                        continue

                # TODO: build full url
                linkki = "https://budjetti.vm.fi"

                dataObj = DataObject(
                    tulo=tuloBool,
                    syvyys=syvyysInt,
                    paaluokka=paaluokkaInt,
                    paaluokkaSelite=row[COL_IDX_PAALUOKKA_SELITE],
                    menoluokka=menoLuokkaInt,
                    menoluokkaSelite=row[COL_IDX_MENOLUOKKA_SELITE],
                    momentti=momenttiInt,
                    momenttiSelite=momenttiSelite,
                    osoite=row[COL_IDX_OSOITE],
                    libLisays=libLisays,
                    hallitus=hallitusDecimal,
                    lib=libDecimal,
                    perustelu=row[COL_IDX_PERUSTELU],
                    linkki=linkki,
                    subrows={}
                )
                data.append(dataObj)
            except Exception as e:
                print("Failed to process row %r due %r" % (row, e))
    return data

def extract_osoite(osoite: str) -> (int, int, int, bool):
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

def sort_data_tree(data: list[DataObject]) -> defaultdict:
    """
    Groups dataRows based on their common paaluokka and menoluokka numbers

    FIXME
    
    tree['root'] Top level rows
    tree[paaluokka_nro] 
    tree[paaluokka_nro][menoluokka_nro]
    """
    initial_sort = sorted(data, key=lambda x:(x.syvyys))
    tree = defaultdict(lambda: defaultdict(list))
    tree['root'] = list # XXX Generate special position to hold top level rows
    for row in initial_sort:
        if row.syvyys == 3:
            tree[row.paaluokka][row.menoluokka].append(row)
        elif row.syvyys == 2:
            tree[row.paaluokka].append(row)
        elif row.syvyys == 1:
            tree['root'].append(row)
        else:
            print("Unexpected syvyys value %r, don't know what to do!" % row.syvyys)
    return tree 

def sort_data(data: list[DataObject]) -> dict:
    """
    Groups dataRows based on their common paaluokka and menoluokka numbers
    
    Returns
        dict of top level rows, other rows inserted into subrows dicts inside each row object
    """
    # XXX Initial sort required, as we want to first assign top level rows to dict, then second level and finally third level
    initial_sort = sorted(data, key=lambda row:(row.syvyys, row.paaluokka, row.menoluokka, row.momentti))

    for item in initial_sort[:50]:  # inspect the first 10 items
        print(item.syvyys, item.paaluokka, item.menoluokka, item.momentti, item.osoite)


    tempDict = {}    
    for row in initial_sort:
        # Skip suspicious rows
        if not validate_syvyys(row):
            continue

        print("Sorted a row %s" % row.osoite)

        if row.syvyys == 3:
            if row.paaluokka not in tempDict:
                print("Unknown paaluokka in row with syvyys 3. Implementation error")
                print("%r" % row)
                sys.exit(2)
            else:  
                if row.menoluokka not in tempDict[row.paaluokka].subrows:
                    print("Unknown menoluokka %d in paaluokka %d in row with syvyys 3. Implementation error" % (row.menoluokka, row.paaluokka))
                    print("%r" % row)
                    print("%r" % tempDict[row.paaluokka].subrows)
                    sys.exit(2)
                else:
                    tempDict[row.paaluokka].subrows[row.menoluokka].subrows[row.momentti] = row
        elif row.syvyys == 2:
            if row.paaluokka not in tempDict:
                print("Unknown paaluokka in row with syvyys 2. Unable to find paaluokka %d. Implementation error?" % row.paaluokka)
                print("%r" % row)
                sys.exit(2)
            else:
                tempDict[row.paaluokka].subrows[row.menoluokka] = row
        elif row.syvyys == 1:
            tempDict[row.paaluokka] = row
        else:
            print("Unexpected syvyys value %r, don't know what to do!" % row.syvyys)
    return tempDict

def validate_syvyys(row) -> bool:
    """
    Expecting syvyys = 1 row to have integer value in paaluokka
    Expecting syvyys = 2 row to have integer value in paaluokka and menoluokka
    Expecting syvyys = 3 row to have integer value in paaluokka and menoluokka and momentti
    Any other value for syvyys, assume invalid row
    Return True if syvyys validates OK
    """
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

def print_data(data: list[DataObject]) -> None:
    for d in data:
        print('%r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r, %r' % (d.tulo, d.syvyys, d.paaluokka, d.paaluokkaSelite, d.menoluokka, d.menoluokkaSelite, 
                        d.momentti, d.momenttiSelite, d.osoite, d.libLisays, d.hallitus, d.lib, d.perustelu, d.linkki))

def print_data2(data: list[DataObject]) -> None:
    for d in data:
        print('%r, %r, %r, %r, %r' % (d.syvyys, d.paaluokka, d.menoluokka, d.momentti, d.osoite))

def print_sorted_tree(tree) -> None:
    for row in tree['root']:
        print("%r %r" % (row.osoite, row.paaluokkaSelite))
        for subrow in tree[row.paaluokka]:
            print("%r %r" % (subrow.osoite, subrow.menoluokkaSelite))
            for subsubrow in tree[row.paaluokka][subrow.menoluokka]:
                print("%r %r" % (subsubrow.osoite, subsubrow.momenttiSelite))

def print_sorted_data(dataDict) -> None:
    for row in dataDict.values():
        print('%r %r' % (row.osoite, row.paaluokkaSelite))
        for subrow in row.subrows.values():
            print("%r %r" % (subrow.osoite, subrow.menoluokkaSelite))
            for subsubrow in subrow.subrows.values():
                print("%r %r" % (subsubrow.osoite, subsubrow.momenttiSelite))



def update_wordpress_page(page_id, content):
    """
    Update Vaihtoehtobudjetti page at Wordpress site

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



def generate_html(data):

    doc, tag, text = Doc().tagtext()
    with tag('h1'):
        text("Hello world")
    doc.asis(generate_level_2(data))

    return doc.getvalue()


def generate_level_2(data):
    """
    Returns table as yattag doc

    Kakkostason momentti, otsikko osio taulukolle

    Data:
    1. tason momenttinumero
    2. tason momentin nimi
    -> esim 25. Oikeusministeriön hallinnonala
    Linkki budjettikirjaan

    Hallituksen esitys €
    Liberaalipuolueen esitys €
    Erotus €
    Liberaalipuolueen leikkausten kuvaus

    Lista 3. tason momenteista


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
    with tag('section', klass='av_toggle_section', itemscope='itemscope', itemtype='https://schema.org/CreativeWork'):
        with tag('div', role='tablist', klass='single_toggle', data_tags="{All}"):
            with tag('p', data_fake_id="#25_oikeusministerion_hallinnonala", klass="toggler ",  itemprop="headline", role="tab", tabindex="0", aria_controls="25_oikeusministerion_hallinnonala"):
                text("1. Hello")
            #<span class="toggle_icon" >
            #<span class="vert_icon"></span>
            #<span class="hor_icon"></span>
            #</span>
            with tag('h4'):
                text("Hallituksen esitys: 1 076 795 000€")
            with tag('h4'):
                text("Liberaalipuolueen esitys: 998 883 761€")
            with tag('h4'):
                text("Leikattavaa löytyy: −77 911 239€")
            with tag('p', style="font-size: 14pt;"):
                text('Oikeusvaltion ylläpito tulee turvata riittävällä rahoituksella. IT-hankkeiden resurssitehokkuutta tulee parantaa.')

    doc.asis(generate_level_3(data))

    return doc


def generate_level_3(data):
    """
    Returns table as yattag doc

    Kolmostason momentit

    

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

    doc, tag, text = Doc().tagtext()
    with tag('table'):
        for i in range(1, 3):
            with tag('tr'):
                for j in range(1, 3):
                    with tag('td'):
                        text(f"Row{i} Col{j}")
    return doc

if __name__ == '__main__':
    main()
