import gradio as gr
import os
import yt_dlp
from whisper import load_model
import tempfile

# Load Whisper model (load once at startup)
whisper_model = load_model("base")  # You can change to "small", "medium", etc.

def download_and_convert_to_mp3(video_url):
    # Create a temporary directory to store the audio file
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, "audio.mp3")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(temp_dir, 'audio'),  # Output template
        'quiet': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Rename the file to have consistent output
        downloaded_file = os.path.join(temp_dir, "audio.mp3")
        if not os.path.exists(downloaded_file):
            # Sometimes the extension might be different
            for file in os.listdir(temp_dir):
                if file.startswith("audio."):
                    downloaded_file = os.path.join(temp_dir, file)
                    break
        
        return downloaded_file
    except Exception as e:
        raise gr.Error(f"Error downloading video: {str(e)}")

def transcribe_audio(audio_file_path):
    if not audio_file_path:
        raise gr.Error("No audio file provided")
    
    try:
        # Transcribe using Whisper
        result = whisper_model.transcribe(audio_file_path)
        return result["text"]
    except Exception as e:
        raise gr.Error(f"Error during transcription: {str(e)}")
    finally:
        # Clean up the temporary file
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)

def process_video_url(video_url):
    # Step 1: Download and convert to MP3
    audio_file = download_and_convert_to_mp3(video_url)
    
    # Step 2: Transcribe the audio
    transcription = transcribe_audio(audio_file)
    
    return transcription

# Create Gradio interface
with gr.Blocks() as app:
    gr.Markdown("""
    # Video to Transcription
    1. Paste a video URL (YouTube or direct video file link)
    2. The app will download the audio as MP3
    3. Then transcribe it using OpenAI's Whisper
    """)
    
    with gr.Row():
        video_url = gr.Textbox(label="Video URL", placeholder="https://www.youtube.com/watch?v=... or https://example.com/video.mp4")
    
    with gr.Row():
        submit_btn = gr.Button("Process")
    
    with gr.Row():
        output_text = gr.Textbox(label="Transcription", interactive=False)
    
    submit_btn.click(
        fn=process_video_url,
        inputs=video_url,
        outputs=output_text
    )

if __name__ == "__main__":
    app.launch()