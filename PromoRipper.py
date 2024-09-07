from datetime import datetime
from bs4 import BeautifulSoup
import requests
import re
import sqlite3
import json
import os
from pytz import timezone, utc

promo_count = 0
date = ""
def RipPromosHTM(input_string, showName):
    #Beginning of Promo Rip
    url = input_string
    if "http" not in url:
        url = "https://" + url
    page = requests.get(url)
    page.encoding = "utf-8"
    soup = BeautifulSoup(page.text,'html.parser')
    #Extract Show Name and Format it
    #Get just the Promos
    promos = [p for p in soup.find_all('p') if p.get('align') != 'center']
    #promos.extend(soup.find_all('p', attrs={'text-align' : 'left'}))
    try:
        for promo in promos:
            rawPromo = promo.encode('utf-8', errors='ignore').decode('utf-8')
            formattedPromo = BeautifulSoup(rawPromo, 'html.parser').get_text()
            # Split the string into lines
            lines = formattedPromo.split('\n')

            # Remove leading and trailing whitespace from each line
            stripped_lines = [re.sub(r'\s+', ' ', line).strip() for line in lines]
            if stripped_lines[0] == "":
                stripped_lines.pop(0)
            # Add <strong> tags appropriately
            processed_lines = []
            for line in stripped_lines:
                if line.strip() != "":
                    if ":" in line:
                        line = "<strong>" + line[:line.find(":")] + "</strong>" + line[line.find(":"):] 
                    else:
                        line = f'<strong>{line}</strong>'
                    processed_lines.append(line)
            # Join the lines back into a single string with a \n between them
            formattedPromo = '\n\n'.join(processed_lines)
            if len(processed_lines) > 5 and formattedPromo.strip():
                insertPromo(rawPromo, showName, input_string, formattedPromo)
                global promo_count
                promo_count += 1
    except UnicodeEncodeError as e:
        problematic_string = promo.get_text()
        print(f"UnicodeEncodeError occurred. Problematic string: {problematic_string.encode('utf-8', errors='ignore').decode('utf-8')}")

def find_href_links(base_Url):
    url = base_Url
    if "http" not in url:
        url = "https://" + url
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
        href_links = list(dict.fromkeys(href_links))
        return href_links
    except UnicodeEncodeError as e:
        return href_links.encode('utf-8', errors='ignore').decode('utf-8')


def getPageLinks(base_url):
    # Get all the links on the page that are in the format of a show
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

    # Add end.htm and index.htm
    ordered_links.append(f"{base_url_without_index}/end.htm")
    ordered_links.append(base_url)
    return ordered_links

def findShowLink(input_list):
    for string in input_list:
        if 'recapshow' in string:
            return string
        elif 'recappv' in string:
            return string
        elif 'recapppv' in string:
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

# Reads the page and looks for links that are for a show
def findShows(base_url):
    result_list = []
    for link in find_href_links(base_url):
        if "/forums/topic" in link and "page" not in link and "comments" not in link:
            result_list.append(link)
    return result_list


def ripPromosFromShow(base_url):
    global promo_count
    promo_count = 0
    indexLink = findShowLink(find_href_links(base_url))
    global date
    date = findDate(base_url)
    showTitle = base_url.split('/', 6)[5].replace("-", " ").title()
    showName = re.sub(r'^\d+', '', showTitle).lstrip()
    if indexLink is not None:
        for link in getPageLinks(indexLink):
            RipPromosHTM(link, showName)
    else:
           print(f"No show link found for: {base_url}")
    if promo_count > 0:
        print(base_url + " ||"   +str(promo_count))

def findDate(base_url):
    #Fix Time to make it EST and fix date search again
    try:
        # Fetch the page content
        page = requests.get(base_url)
        page.encoding = "utf-8"
        soup = BeautifulSoup(page.text, 'html.parser')
        
        # Try to find the <time> tag
        timeTag = soup.find('time')
        if timeTag:
            # Try to get the datetime attribute
            dateTime_str = timeTag.get('datetime')
            dateTime_str = dateTime_str.rstrip('Z')  # Remove the trailing 'Z' if present
            if dateTime_str:
                try:
                    date = datetime.fromisoformat(dateTime_str)
                    date = date.replace(tzinfo=utc)
                    est = timezone('US/Eastern')
                    date_est = date.astimezone(est)
                    return date_est.strftime('%Y-%m-%d')
                except ValueError:
                    pass  # Continue to the next method if this fails
            
            # Fallback: Try to parse the text content of the <time> tag with multiple formats
            date_formats = ['%B %d, %Y', '%Y-%m-%d', '%d %B %Y']
            for fmt in date_formats:
                try:
                    date = datetime.strptime(timeTag.text.strip(), fmt)
                    est = timezone('US/Eastern')
                    date_est = est.localize(date)
                    return date_est.strftime('%Y-%m-%d')
                except ValueError:
                    continue  # Try the next format
        
        # Fallback: Use a regular expression to find the first date in the format [YYYY-MM-DD]
        date_pattern = re.compile(r'\[\d{4}-\d{2}-\d{2}\]')
        match = date_pattern.search(soup.text)
        if match:
            date = datetime.strptime(match.group(0).strip('[]'), '%Y-%m-%d')
            est = timezone('US/Eastern')
            date_est = est.localize(date)
            return date_est.strftime('%Y-%m-%d')
        
        return "No valid date found on the page."
    
    except requests.exceptions.RequestException as e:
        return f"Error fetching the page: {e}"


# Concatenates base url with next number to get to next page
def nextPage(base_url, page_number):
    result = f"{base_url}/page/{page_number}"
    return result

def check_webpage_exists(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception if the response status code is not 2xx
        return True
    except requests.exceptions.RequestException as e:
        return False
    
#Most Front Facing Method that takes web link from user
def scrapePromos(base_url):
    isRunning = True
    page_number =  1 # Initialize the page number
    endNumber = 150 # Set the end number of pages to scrape
    while page_number < endNumber and isRunning:
        currentPage = nextPage(base_url, page_number)  # Pass the page number to nextPage
        if check_webpage_exists(currentPage):
            print(currentPage)
            for link in findShows(currentPage):
                ripPromosFromShow(link)
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
                Show TEXT,
                Date TEXT,
                ShowLink TEXT,
                FormattedPromo TEXT
        )
    '''
    
    cursor.execute(create_table_query)
    
    conn.commit()
    conn.close()

def insertPromo(promo, show, showLink, formattedPromo):
    global date
    # Connect to the SQLite database
    conn = sqlite3.connect('C:\\Users\\4l101\\OneDrive\\Documents\\PromoRipper\\Promos.db')
    cursor = conn.cursor()

    #Connect to the json file
    if os.path.exists("data.json") and os.path.getsize("data.json") > 0:
        # Read existing data
        with open("data.json", 'r') as json_file:
            data = json.load(json_file)
    else:
        # If the file doesn't exist or is empty, initialize with an empty list
        data = {"data": []}

    # Define the SQL query to insert data
    insert_query = "INSERT OR IGNORE INTO Promos (RawPromo, Show, Date, ShowLink, FormattedPromo) VALUES (?, ?, ?, ?, ?)"
    sqlPromo = BeautifulSoup(formattedPromo, 'html.parser').get_text()
    sqlPromo = sqlPromo.lstrip()
    # Execute the query with the provided variables
    cursor.execute(insert_query, (promo, show, date, showLink, sqlPromo))
    
    #Add to JSON if not Present
    if cursor.rowcount > 0:
        # Wrap the promo in a div with a class for styling
        wrapped_promo = f'<div class="overflow-cell">{formattedPromo}</div>'

        # Append the new data to the existing data
        data["data"].append({
            "promo": wrapped_promo,
            "show": show,
            "date": date,
            "page_link": showLink
        })
        #Update The JsonFile
        with open("Data.json", 'w') as json_file:
            json.dump(data, json_file, indent=4)

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    
create_table()
scrapePromos(input("Type in the Home Link: ")        
