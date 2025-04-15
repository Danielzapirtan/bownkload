import gradio as gr
import os
from pytube import YouTube
from pytube.exceptions import PytubeError, VideoUnavailable
import yt_dlp
import whisper
import tempfile
import traceback

# Legal disclaimer and ToS notice
LEGAL_NOTICE = """
**Legal Notice:**  
This tool is for **personal, non-commercial use only**.  
By using this service, you agree to:
1. Only process content you own or have permission to transcribe.
2. Comply with YouTube's Terms of Service (Section 5.2: No unauthorized downloading).
3. Accept that automated access to YouTube may be blocked without notice.
"""

def validate_youtube_url(url):
    """Check if URL is a valid YouTube link we're allowed to process"""
    allowed_domains = [
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com"
    ]
    return any(domain in url for domain in allowed_domains)

def download_audio(video_url, temp_dir):
    try:
        # Legal check - only proceed if valid YouTube URL
        if not validate_youtube_url(video_url):
            raise gr.Error("Only YouTube links are supported for URL processing")

        # Check for problematic URL patterns
        if "playlist" in video_url:
            raise gr.Error("Playlists are not supported - use single video URLs")

        # Use yt-dlp with strict user-agent and rate limiting
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
            'quiet': True,
            'extract_flat': True,
            'sleep_interval': 2,  # Add delay between requests
            'max_downloads': 1,   # Limit to single video processing
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First check if download is allowed
            info = ydl.extract_info(video_url, download=False)
            if info.get('is_live'):
                raise gr.Error("Live streams are not supported")
            if info.get('duration', 0) > 3600:  # 1 hour max
                raise gr.Error("Videos longer than 1 hour are not supported")
            
            # Proceed with download if checks pass
            ydl.download([video_url])
            filename = ydl.prepare_filename(info)
        
        return filename.replace('.webm', '.mp3').replace('.m4a', '.mp3')
    
    except yt_dlp.utils.DownloadError as e:
        if "Private video" in str(e):
            raise gr.Error("Private videos are not supported")
        if "Copyright" in str(e):
            raise gr.Error("This content is copyright protected")
        raise gr.Error(f"Download error: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Processing error: {str(e)}")

def transcribe_audio(audio_path, model_size):
    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Transcription failed: {str(e)}")

def process_input(video_url, video_file, model_size, agree_to_terms):
    if not agree_to_terms:
        raise gr.Error("You must agree to the terms of service")
    
    temp_dir = tempfile.mkdtemp()
    try:
        audio_path = None
        
        if video_url:  # URL case
            audio_path = download_audio(video_url.strip(), temp_dir)
        elif video_file:  # Uploaded file case
            audio_path = os.path.join(temp_dir, "uploaded_audio.mp3")
            with open(video_file.name, 'rb') as src, open(audio_path, 'wb') as dst:
                dst.write(src.read())
        
        if not audio_path or not os.path.exists(audio_path):
            raise gr.Error("Failed to process audio input")
        
        return transcribe_audio(audio_path, model_size)
    
    finally:
        # Clean up temporary files
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                try:
                    os.remove(os.path.join(temp_dir, f))
                except:
                    pass
            try:
                os.rmdir(temp_dir)
            except:
                pass

with gr.Blocks(title="Video Transcription Tool") as app:
    gr.Markdown("# 🎥 Video to Transcription")
    gr.Markdown(LEGAL_NOTICE)
    
    with gr.Row():
        with gr.Column():
            video_url = gr.Textbox(
                label="YouTube URL (single video only)", 
                placeholder="https://www.youtube.com/watch?v=...",
                max_lines=1
            )
            video_file = gr.File(
                label="Or upload your own video/audio file", 
                file_types=["video", "audio"],
                type="filepath"
            )
            model_size = gr.Dropdown(
                ["tiny", "base", "small", "medium", "large"], 
                value="base", 
                label="Model Size (larger = more accurate)"
            )
            agree_to_terms = gr.Checkbox(
                label="I confirm I have rights to process this content",
                value=False
            )
    
    transcribe_btn = gr.Button("Transcribe", variant="primary")
    output_text = gr.Textbox(label="Transcription", lines=10, interactive=False)
    
    transcribe_btn.click(
        fn=process_input,
        inputs=[video_url, video_file, model_size, agree_to_terms],
        outputs=output_text,
    )

if __name__ == "__main__":
    app.launch(
        share=False,  # Disable public sharing for legal compliance
        debug=True,
        server_name="0.0.0.0",
        server_port=7860
    )
