import gradio as gr
import os
from pytube import YouTube
from pytube.exceptions import PytubeError, VideoUnavailable, RegexMatchError
import yt_dlp
import whisper
import tempfile
import traceback
from pathlib import Path
import re

current_model = None

def load_whisper_model(model_size):
    global current_model
    if current_model is None or current_model.model_size != model_size:
        print(f"Loading Whisper model: {model_size}")
        current_model = whisper.load_model(model_size)
    return current_model

def is_valid_url(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        '(youtube|youtu|youtube-nocookie)\.(com|be)/'
        '(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')
    generic_url_regex = (
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|'
        r'[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    return bool(re.match(youtube_regex, url) or re.match(generic_url_regex, url))

def is_youtube_url(url):
    return "youtube.com" in url or "youtu.be" in url

def download_yt_with_pytube(video_url, temp_dir):
    try:
        yt = YouTube(video_url)
        if yt.vid_info.get('playabilityStatus', {}).get('status', '').lower() == 'error':
            reason = yt.vid_info['playabilityStatus'].get('reason', 'Video unavailable')
            raise VideoUnavailable(reason)
        if yt.vid_info.get('videoDetails', {}).get('isLive', False):
            raise PytubeError("Live streams are not supported")
        
        audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
        if not audio_stream:
            raise PytubeError("No audio stream available")
        
        output_file = "audio.mp3"
        audio_file_path = audio_stream.download(output_path=temp_dir, filename=output_file)
        
        if not os.path.exists(audio_file_path):
            for ext in ['.mp4', '.webm', '.m4a']:
                alt_path = os.path.join(temp_dir, f"audio{ext}")
                if os.path.exists(alt_path):
                    mp3_path = os.path.join(temp_dir, "audio.mp3")
                    os.rename(alt_path, mp3_path)
                    return mp3_path
            raise PytubeError("Downloaded file not found")
        
        return audio_file_path
    except RegexMatchError:
        raise gr.Error("Invalid YouTube URL format")
    except VideoUnavailable as e:
        raise gr.Error(f"YouTube video unavailable: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Pytube error: {str(e)}")

def download_with_ytdlp(video_url, temp_dir):
    try:
        output_template = os.path.join(temp_dir, 'audio')
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'quiet': True,
            'ignoreerrors': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 10,
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            if not info:
                raise gr.Error("Could not extract video info")
            if info.get('is_live', False):
                raise gr.Error("Live streams are not supported")
            if info.get('_type', 'video') != 'video':
                raise gr.Error("Only single videos are supported")
            
            ydl.download([video_url])
        
        expected_file = output_template + '.mp3'
        if os.path.exists(expected_file):
            return expected_file
            
        for file in os.listdir(temp_dir):
            if file.startswith("audio"):
                return os.path.join(temp_dir, file)
        
        raise gr.Error("Failed to download audio")
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"YT-DLP error: {str(e)}")

def download_and_convert_to_mp3(video_url):
    temp_dir = tempfile.mkdtemp()
    try:
        if not is_valid_url(video_url):
            raise gr.Error("Invalid URL format")
        
        if is_youtube_url(video_url):
            try:
                return download_yt_with_pytube(video_url, temp_dir)
            except Exception:
                return download_with_ytdlp(video_url, temp_dir)
        else:
            return download_with_ytdlp(video_url, temp_dir)
    except Exception as e:
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                try: os.remove(os.path.join(temp_dir, file))
                except: pass
            try: os.rmdir(temp_dir)
            except: pass
        raise

def transcribe_audio(audio_file_path, model_size):
    if not audio_file_path or not os.path.exists(audio_file_path):
        raise gr.Error("No valid audio file found")
    
    try:
        model = load_whisper_model(model_size)
        result = model.transcribe(audio_file_path)
        return result["text"]
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Transcription failed: {str(e)}")
    finally:
        if audio_file_path and os.path.exists(audio_file_path):
            temp_dir = os.path.dirname(audio_file_path)
            try:
                os.remove(audio_file_path)
                if not os.listdir(temp_dir):
                    os.rmdir(temp_dir)
            except:
                pass

def process_video_url(video_url, model_size, progress=gr.Progress()):
    try:
        progress(0.1, desc="Validating URL...")
        audio_file = download_and_convert_to_mp3(video_url)
        progress(0.6, desc=f"Loading {model_size} model...")
        progress(0.7, desc="Transcribing audio...")
        transcription = transcribe_audio(audio_file, model_size)
        progress(1.0, desc="Complete!")
        return transcription
    except gr.Error:
        raise
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(str(e))

with gr.Blocks(title="Video Transcription", theme="soft") as app:
    gr.Markdown("""# 🎥 Video to Transcription""")
    
    with gr.Row():
        video_url = gr.Textbox(label="Video URL", placeholder="Enter video URL")
        submit_btn = gr.Button("Transcribe", variant="primary")
    
    with gr.Row():
        model_dropdown = gr.Dropdown(
            ["tiny", "base", "small", "medium", "large"],
            value="base",
            label="Model Size"
        )
    
    output_text = gr.Textbox(label="Transcription", interactive=True)
    
    submit_btn.click(
        fn=process_video_url,
        inputs=[video_url, model_dropdown],
        outputs=output_text
    )

if __name__ == "__main__":
    try:
        with yt_dlp.YoutubeDL() as ydl:
            ydl.update()
    except:
        print("Could not update yt-dlp")
    
    try:
        load_whisper_model("base")
    except Exception as e:
        print(f"Warning: {e}")
    
    app.launch()