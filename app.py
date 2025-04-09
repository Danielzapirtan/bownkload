import gradio as gr
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os
import tempfile
from pytube import YouTube
import re

def is_youtube_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    return re.match(youtube_regex, url) is not None

def download_youtube_video(url):
    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not stream:
            return None, "No suitable video stream found"
        
        temp_dir = tempfile.mkdtemp()
        file_path = stream.download(output_path=temp_dir)
        return file_path, f"Successfully downloaded YouTube video: {yt.title}"
    
    except Exception as e:
        return None, f"YouTube download error: {str(e)}"

def download_file(url):
    # First check if it's a YouTube URL
    if is_youtube_url(url):
        return download_youtube_video(url)
    
    try:
        # Regular file download logic
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Check if HTML content (might be a shared page)
        content_type = response.headers.get('content-type', '')
        if 'text/html' in content_type:
            soup = BeautifulSoup(response.text, 'html.parser')
            file_links = []
            
            # Look for common file download links
            for tag in soup.find_all(['a', 'link']):
                href = tag.get('href', '')
                if any(href.lower().endswith(ext) for ext in ['.pdf', '.mp4', '.mp3', '.zip', '.rar', '.exe', '.dmg', '.png', '.jpg', '.jpeg', '.gif']):
                    file_links.append(href)
            
            if file_links:
                base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                file_url = file_links[0] if file_links[0].startswith('http') else base_url + file_links[0]
                response = requests.get(file_url, stream=True)
                response.raise_for_status()
            else:
                return None, "No downloadable files found in the HTML page"
        
        # Get filename
        filename = os.path.basename(urlparse(url).path)
        if not filename:
            if 'content-disposition' in response.headers:
                content_disposition = response.headers['content-disposition']
                filename = content_disposition.split('filename=')[1].strip('"\'')
            else:
                filename = 'downloaded_file'
        
        # Save to temporary file
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        return file_path, f"Successfully downloaded: {filename}"
    
    except requests.exceptions.RequestException as e:
        return None, f"Error downloading file: {str(e)}"
    except Exception as e:
        return None, f"An error occurred: {str(e)}"

def download_and_display(url):
    file_path, message = download_file(url)
    if file_path:
        return file_path, message
    else:
        return None, message

with gr.Blocks() as app:
    gr.Markdown("## Universal File Downloader")
    gr.Markdown("Enter a URL to download files or YouTube videos")
    
    with gr.Row():
        url_input = gr.Textbox(label="URL", placeholder="https://example.com/file.pdf or YouTube URL")
        download_btn = gr.Button("Download")
    
    with gr.Row():
        message_output = gr.Textbox(label="Status")
        file_output = gr.File(label="Downloaded Content")
    
    download_btn.click(
        fn=download_and_display,
        inputs=url_input,
        outputs=[file_output, message_output]
    )

if __name__ == "__main__":
    app.launch(debug=True)