import gradio as gr
import os
from pytube import YouTube
from pytube.exceptions import PytubeError, VideoUnavailable
import yt_dlp
import whisper
import tempfile
import traceback

def download_audio(video_url, temp_dir):
    try:
        # Try pytube first for YouTube URLs
        if "youtube.com" in video_url or "youtu.be" in video_url:
            try:
                yt = YouTube(video_url)
                stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                if not stream:
                    raise Exception("No audio stream found")
                output_path = os.path.join(temp_dir, "audio.mp3")
                stream.download(output_path=temp_dir, filename="audio.mp3")
                return output_path
            except Exception as e:
                print(f"Pytube failed: {e}")

        # Fallback to yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': os.path.join(temp_dir, 'audio'),
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Find the downloaded file
        for file in os.listdir(temp_dir):
            if file.startswith("audio."):
                return os.path.join(temp_dir, file)
        
        raise Exception("Failed to download audio")
    except Exception as e:
        raise gr.Error(f"Download error: {str(e)}")

def transcribe_audio(audio_path, model_size):
    try:
        # Load the selected model
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Transcription failed: {str(e)}")

def process_video(video_url, model_size):
    temp_dir = tempfile.mkdtemp()
    try:
        # Download audio
        audio_path = download_audio(video_url, temp_dir)
        if not audio_path or not os.path.exists(audio_path):
            raise gr.Error("Failed to download audio file")
        
        # Transcribe
        transcription = transcribe_audio(audio_path, model_size)
        
        return transcription
    except Exception as e:
        raise gr.Error(str(e))
    finally:
        # Clean up
        if os.path.exists(temp_dir):
            for f in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, f))
            os.rmdir(temp_dir)

with gr.Blocks(title="Video Transcription") as app:
    gr.Markdown("# 🎥 Video to Transcription")
    
    with gr.Row():
        video_url = gr.Textbox(label="Video URL", 
                             placeholder="https://www.youtube.com/watch?v=...")
        model_size = gr.Dropdown(["tiny", "base", "small", "medium", "large"], 
                               value="base", label="Model Size")
    
    transcribe_btn = gr.Button("Transcribe")
    output_text = gr.Textbox(label="Transcription", lines=10)
    error_box = gr.Textbox(label="Error", visible=False)
    
    transcribe_btn.click(
        fn=process_video,
        inputs=[video_url, model_size],
        outputs=[output_text, error_box]
    )

if __name__ == "__main__":
    app.launch()