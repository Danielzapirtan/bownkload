import gradio as gr
import requests
from bs4 import BeautifulSoup

def search_and_download_book(phrase):
    # Search Project Gutenberg for books containing the phrase
    search_url = f"https://www.gutenberg.org/ebooks/search/?query={phrase}&submit_search=Go!"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the first book link
    book_link = soup.find('a', class_='link', href=True)
    if not book_link:
        return "No books found containing the phrase."

    book_url = "https://www.gutenberg.org" + book_link['href']

    # Fetch the book page to get the download link
    book_page = requests.get(book_url)
    book_soup = BeautifulSoup(book_page.text, 'html.parser')

    # Find the download link (assuming plain text format)
    download_link = book_soup.find('a', href=True, string='Plain Text UTF-8')
    if not download_link:
        return "Download link not found."

    download_url = "https://www.gutenberg.org" + download_link['href']

    # Download the book
    book_response = requests.get(download_url)
    if book_response.status_code != 200:
        return "Failed to download the book."

    # Save the book to a file
    book_filename = f"{phrase.replace(' ', '_')}.txt"
    with open(book_filename, 'wb') as f:
        f.write(book_response.content)

    return f"Book downloaded successfully: {book_filename}"

# Gradio interface
iface = gr.Interface(
    fn=search_and_download_book,
    inputs="text",
    outputs="text",
    title="Public Domain Book Downloader",
    description="Enter a phrase to search for a book in the public domain and download it."
)

iface.launch()
