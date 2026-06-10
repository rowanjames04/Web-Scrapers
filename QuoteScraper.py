from bs4 import BeautifulSoup
import requests

page_to_scrape = requests.get("http://quotes.toscrape.com")
soup = BeautifulSoup(page_to_scrape.text, "html.parser")

#quotes
quotes = soup.findAll("span", attrs = {"class": "text"})
for quote in quotes:
    print(quote.text)

#authors
authors = soup.findAll("small", attrs = {"class": "author"})
for author in authors:
    print(author.text)
