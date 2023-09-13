from bs4 import BeautifulSoup
import requests
import re
import sqlite3

def RipPromosHTM(input_string):
    #Beginning of Promo Rip
    url = input_string
    page = requests.get(url)
    soup = BeautifulSoup(page.text,'html.parser')
    #Get just the Promos
    promos = soup.find_all('p', attrs={'align' : 'left'})
    #Print Promo and Handle Bad Characters
    try:
        for promo in promos:
            rawPromo = promo.encode('utf-8', errors='ignore').decode('utf-8')
            formattedPromo = re.sub(r'<.*?>', '', rawPromo)
            insertPromo(rawPromo, input_string, formattedPromo)
    except UnicodeEncodeError as e:
        problematic_string = promo.get_text()
        print(f"UnicodeEncodeError occurred. Problematic string: {problematic_string.encode('utf-8', errors='ignore').decode('utf-8')}")

def find_href_links(base_Url):
    url = base_Url
    page = requests.get(url)
    soup = BeautifulSoup(page.text,'html.parser')
    rawTags = soup.find_all('a')
    aTags = str(rawTags)

    href_links = []
    start_index = 0

    while True:
        # Find the next occurrence of 'href="'
        start_index = aTags.find('href="', start_index)
        if start_index == -1:
            break

        # Find the end of the link (double quote after href=")
        end_index = aTags.find('"', start_index + 6)  # Add 6 to skip 'href="'

        if end_index != -1:
            # Extract the link and add it to the list
            href_link = aTags[start_index + 6:end_index]
            href_links.append(href_link)

        # Move the start_index to continue searching
        start_index = end_index + 1

    try:
        return href_links
    except UnicodeEncodeError as e:
        return href_links.encode('utf-8', errors='ignore').decode('utf-8')


def getPageLinks(base_url):
    showlinks = find_href_links(base_url)
    pattern = r"^\d+\.htm$"
    matching_numbers = set()
    for string in showlinks:
        match = re.match(pattern, string)
        if match:
            matching_numbers.add(int(match.group()[:-4]))

    ordered_numbers = sorted(matching_numbers)
    base_url_without_index = base_url.rstrip("/index.htm")  # Remove "/index.htm" from the end of the base URL, if present
    ordered_links = [f"{base_url_without_index}/{num}.htm" for num in ordered_numbers]
    return ordered_links

def findShowLink(input_list):
    for string in input_list:
        if 'recapshow' in string:
            return string
        elif 'bit.ly' in string:
            try:
                with requests.Session() as session:
                    response = session.head(string, allow_redirects=True)
                    final_url = response.url
                return final_url
            except requests.exceptions.RequestException as e:
                print(f"Error: {e}")
                return None
    return None

def findShows(base_url):
    result_list = []
    for link in find_href_links(base_url):
        if "showthread" in link and "Card" not in link and "post" not in link:
            result_list.append(link)
    return result_list

def ripPromosFromShow(base_url):
    indexLink = findShowLink(find_href_links(base_url))
    if indexLink is not None:
        print(RipPromosHTM(indexLink))
        for link in getPageLinks(indexLink):
            RipPromosHTM(link)
    else:
        print(f"No show link found for: {base_url}")

def nextPage(base_url, page_number):
    result = f"{base_url}/page{page_number}&order=desc"
    return result

def check_webpage_exists(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception if the response status code is not 2xx
        return True
    except requests.exceptions.RequestException as e:
        return False
    
def scrapePromos(base_url):
    isRunning = True
    page_number =  15 # Initialize the page number
    while isRunning:
        currentPage = nextPage(base_url, page_number)  # Pass the page number to nextPage
        if check_webpage_exists(currentPage):
            print(currentPage)
            for link in findShows(currentPage):
                print("http://www.ocwfed.com/forum/" + link)
                ripPromosFromShow("http://www.ocwfed.com/forum/" + link)
            page_number += 1  # Increment the page number for the next iteration
        else:
            isRunning = False

def create_table():
    conn = sqlite3.connect('Promos.db')
    cursor = conn.cursor()
    
    create_table_query = '''
        CREATE TABLE IF NOT EXISTS Promos (
            ID INTEGER PRIMARY KEY,
            RawPromo TEXT,
            ShowLink TEXT,
            FormattedPromo TEXT
        )
    '''
    
    cursor.execute(create_table_query)
    
    conn.commit()
    conn.close()

def insertPromo(promo, show, unformattedPromo):
    # Connect to the SQLite database (create a new one if it doesn't exist  )
    conn = sqlite3.connect('Promos.db')
    cursor = conn.cursor()
    
    # Define the SQL query to insert data
    insert_query = "INSERT OR REPLACE INTO Promos (RawPromo, ShowLink, FormattedPromo) VALUES (?, ?, ?)"
    
    # Execute the query with the provided variables
    cursor.execute(insert_query, (promo, show, unformattedPromo))
    
    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    
create_table()
scrapePromos(input("Type in the Home Link: ")        
