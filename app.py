import gradio as gr
import requests

def search_books(query):
    url = f"https://openlibrary.org/search.json?q={query}&limit=5"
    response = requests.get(url)
    data = response.json()
    
    results = []
    for book in data.get("docs", []):
        title = book.get("title", "Unknown Title")
        author = ", ".join(book.get("author_name", ["Unknown Author"]))
        olid = book.get("cover_edition_key") or book.get("edition_key", [None])[0]
        
        if olid:
            book_url = f"https://openlibrary.org/books/{olid}"
            borrow_url = f"https://openlibrary.org/borrow/ia/{olid}" if book.get("ia") else None
            
            if "public_scan" in book and book["public_scan"]:
                download_url = f"https://archive.org/download/{book['ia'][0]}"
                results.append(f"📖 [{title}]({book_url}) by {author} - [Download]({download_url})")
            else:
                results.append(f"📖 [{title}]({book_url}) by {author} - [Borrow]({borrow_url})" if borrow_url else f"📖 [{title}]({book_url}) by {author}")
    
    return "\n".join(results) if results else "No books found."

iface = gr.Interface(
    fn=search_books,
    inputs=gr.Textbox(label="Search for a book"),
    outputs=gr.Markdown(),
    title="Book Finder",
    description="Search for books from Open Library. Click links to read, borrow, or download legally."
)

iface.launch()
