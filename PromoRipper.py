from bs4 import BeautifulSoup
import requests
import re
# import openai
# openai.api_key = "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"

def RipPromosHTM(input_string):
    #Beginning of Promo Rip
    url = input_string
    page = requests.get(url)
    soup = BeautifulSoup(page.text,'html.parser')
    #Get just the Promos
    promos = soup.find_all('p', attrs={'align' : 'left'},class_="style155")
    return promos

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

    return href_links


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

def ripPromosFromShow(base_url):
    indexLink = findShowLink(find_href_links(base_url))
    print(RipPromosHTM(indexLink))
    for link in getPageLinks(indexLink):
        print(RipPromosHTM(link))

ripPromosFromShow(input('Type in The URL Of The Show: '))


