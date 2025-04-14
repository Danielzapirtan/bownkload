import gradio as gr
import os
import tempfile
from urllib.parse import urlparse
import requests
from pytube import YouTube
import whisper

# Initialize the Whisper model (load only once)
model = whisper.load_model("base")  # You can change to "small", "medium", etc. based on your needs

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def download_video_from_url(url):
    """Download video from URL (supports YouTube and direct video links)"""
    try:
        # Handle YouTube URLs
        if "youtube.com" in url or "youtu.be" in url:
            yt = YouTube(url)
            stream = yt.streams.filter(only_audio=True).first()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            stream.download(filename=temp_file.name)
            return temp_file.name
        
        # Handle direct video URLs
        else:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_file.close()
                return temp_file.name
            else:
                raise Exception(f"Failed to download video. HTTP status: {response.status_code}")
    except Exception as e:
        raise Exception(f"Error downloading video: {str(e)}")

def transcribe_video(video_file, url):
    """Transcribe video from either file or URL"""
    try:
        # Determine input source
        if video_file is not None:
            video_path = video_file
        elif url and is_valid_url(url):
            video_path = download_video_from_url(url)
        else:
            return "Please provide either a video file or a valid URL"
        
        # Transcribe the audio
        result = model.transcribe(video_path)
        
        # Clean up temporary files
        if url and is_valid_url(url) and os.path.exists(video_path):
            os.unlink(video_path)
            
        return result["text"]
    
    except Exception as e:
        return f"Error during transcription: {str(e)}"

# Gradio interface
with gr.Blocks(title="Video Transcription App") as app:
    gr.Markdown("""
    # Video Transcription App
    Upload a video file or paste a video URL to get a transcription.
    """)
    
    with gr.Row():
        with gr.Column():
            video_input = gr.Video(label="Upload Video File", sources=["upload"])
            url_input = gr.Textbox(label="OR Paste Video URL", placeholder="https://www.youtube.com/watch?v=...")
            submit_btn = gr.Button("Transcribe")
        
        with gr.Column():
            output_text = gr.Textbox(label="Transcription", lines=20, interactive=True)
            clear_btn = gr.Button("Clear")
    
    # Define button actions
    submit_btn.click(
        fn=transcribe_video,
        inputs=[video_input, url_input],
        outputs=output_text
    )
    
    clear_btn.click(
        fn=lambda: [None, "", ""],
        inputs=[],
        outputs=[video_input, url_input, output_text]
    )

if __name__ == "__main__":
    app.launch()