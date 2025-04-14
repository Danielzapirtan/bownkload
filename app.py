import gradio as gr
import os
from pytube import YouTube
from pytube.exceptions import PytubeError, VideoUnavailable
import yt_dlp
from whisper import load_model
import tempfile
import traceback
from pathlib import Path

# Load Whisper model
whisper_model = load_model("base")  # Can change to "small", "medium", etc.

def is_youtube_url(url):
    return "youtube.com" in url or "youtu.be" in url

def download_yt_with_pytube(video_url, temp_dir):
    try:
        yt = YouTube(video_url)
        
        # Check if video is available
        if yt.vid_info.get('playabilityStatus', {}).get('status', '').lower() == 'error':
            raise VideoUnavailable(yt.vid_info['playabilityStatus']['reason'])
        
        # Skip live streams
        if yt.vid_info.get('videoDetails', {}).get('isLive', False):
            raise PytubeError("Live streams are not supported")
        
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        if not audio_stream:
            raise PytubeError("No audio stream available")
        
        output_path = os.path.join(temp_dir, "audio.mp3")
        audio_stream.download(output_path=temp_dir, filename="audio.mp3")
        
        if not os.path.exists(output_path):
            # Sometimes pytube downloads as mp4
            temp_path = os.path.join(temp_dir, "audio.mp4")
            if os.path.exists(temp_path):
                os.rename(temp_path, output_path)
            else:
                raise PytubeError("Downloaded file not found")
        
        return output_path
    except VideoUnavailable as e:
        raise gr.Error(f"YouTube video unavailable: {str(e)}")
    except Exception as e:
        raise gr.Error(f"Pytube error: {str(e)}")

def download_with_ytdlp(video_url, temp_dir):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(temp_dir, 'audio'),
            'quiet': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if not info:
                raise gr.Error("Could not extract video info")
            
            # Skip live streams
            if info.get('is_live', False):
                raise gr.Error("Live streams are not supported")
            
            if info.get('_type', 'video') != 'video':
                raise gr.Error("Only single videos are supported (not playlists)")
            
            ydl.download([video_url])
        
        # Find the downloaded file
        for file in os.listdir(temp_dir):
            if file.startswith("audio."):
                return os.path.join(temp_dir, file)
        
        raise gr.Error("Failed to download audio")
    except Exception as e:
        raise gr.Error(f"YT-DLP error: {str(e)}")

def download_and_convert_to_mp3(video_url):
    temp_dir = tempfile.mkdtemp()
    
    try:
        if is_youtube_url(video_url):
            try:
                return download_yt_with_pytube(video_url, temp_dir)
            except Exception as pytube_error:
                print(f"Pytube failed, falling back to yt-dlp: {pytube_error}")
                return download_with_ytdlp(video_url, temp_dir)
        else:
            return download_with_ytdlp(video_url, temp_dir)
    except Exception as e:
        # Clean up temp dir if error occurs
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
        raise

def transcribe_audio(audio_file_path):
    if not audio_file_path or not os.path.exists(audio_file_path):
        raise gr.Error("No valid audio file found")
    
    try:
        result = whisper_model.transcribe(audio_file_path)
        return result["text"]
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Transcription failed: {str(e)}")
    finally:
        # Clean up the audio file and its directory
        if audio_file_path and os.path.exists(audio_file_path):
            temp_dir = os.path.dirname(audio_file_path)
            os.remove(audio_file_path)
            try:
                os.rmdir(temp_dir)
            except OSError:
                pass  # Directory not empty or already deleted

def process_video_url(video_url, progress=gr.Progress()):
    try:
        if not video_url.strip():
            raise gr.Error("Please enter a video URL")
        
        progress(0.1, desc="Validating URL...")
        
        # Download audio
        progress(0.3, desc="Downloading audio...")
        audio_file = download_and_convert_to_mp3(video_url)
        
        # Transcribe
        progress(0.7, desc="Transcribing audio...")
        transcription = transcribe_audio(audio_file)
        
        progress(1.0, desc="Complete!")
        return transcription
    except Exception as e:
        raise gr.Error(str(e))

# Create Gradio interface
with gr.Blocks(title="Video Transcription", theme="soft") as app:
    gr.Markdown("""
    # 🎥 Video to Transcription
    Convert YouTube or other video URLs to text using Whisper AI
    
    **Note**: Live streams and age-restricted videos may not work
    """)
    
    with gr.Row():
        with gr.Column(scale=4):
            video_url = gr.Textbox(
                label="Video URL",
                placeholder="https://www.youtube.com/watch?v=... or any video URL",
                max_lines=1
            )
        with gr.Column(scale=1):
            submit_btn = gr.Button("Transcribe", variant="primary")
    
    error_box = gr.Textbox(label="Error", visible=False)
    
    with gr.Row():
        output_text = gr.Textbox(
            label="Transcription",
            interactive=True,
            lines=10,
            show_copy_button=True,
            autoscroll=True
        )
    
    with gr.Row():
        gr.Examples(
            examples=[
                ["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
                ["https://www.youtube.com/watch?v=YQHsXMglC9A"],
                ["https://www.youtube.com/watch?v=JGwWNGJdvx8"]
            ],
            inputs=video_url,
            label="Try these examples"
        )
    
    submit_btn.click(
        fn=process_video_url,
        inputs=video_url,
        outputs=[output_text, error_box],
    )

if __name__ == "__main__":
    app.launch()