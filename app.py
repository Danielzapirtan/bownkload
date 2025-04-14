import gradio as gr
import os
import yt_dlp
from whisper import load_model
import tempfile
import traceback

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
        'extract_flat': True,  # Bypass extractor errors
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First validate the URL
            info = ydl.extract_info(video_url, download=False)
            if not info:
                raise gr.Error("Invalid URL or unsupported video source")
            
            # Then download
            ydl.download([video_url])
        
        # Find the downloaded file
        for file in os.listdir(temp_dir):
            if file.startswith("audio.") and file != "audio.mp3":
                os.rename(os.path.join(temp_dir, file), output_path)
                break
        
        if not os.path.exists(output_path):
            raise gr.Error("Failed to convert video to audio")
        
        return output_path
    except yt_dlp.utils.DownloadError as e:
        raise gr.Error(f"Download error: {str(e)}")
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Error processing video: {str(e)}")

def transcribe_audio(audio_file_path):
    if not audio_file_path or not os.path.exists(audio_file_path):
        raise gr.Error("No valid audio file found for transcription")
    
    try:
        # Transcribe using Whisper
        result = whisper_model.transcribe(audio_file_path)
        return result["text"]
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(f"Error during transcription: {str(e)}")
    finally:
        # Clean up the temporary file
        if audio_file_path and os.path.exists(audio_file_path):
            os.remove(audio_file_path)

def process_video_url(video_url):
    try:
        # Step 1: Download and convert to MP3
        audio_file = download_and_convert_to_mp3(video_url)
        
        # Step 2: Transcribe the audio
        transcription = transcribe_audio(audio_file)
        
        return transcription
    except Exception as e:
        raise gr.Error(str(e))

# Create Gradio interface
with gr.Blocks(title="Video to Transcription") as app:
    gr.Markdown("""
    # Video to Transcription
    1. Paste a video URL (YouTube or direct video file link)
    2. The app will download the audio as MP3
    3. Then transcribe it using OpenAI's Whisper
    """)
    
    with gr.Row():
        video_url = gr.Textbox(
            label="Video URL",
            placeholder="https://www.youtube.com/watch?v=... or https://example.com/video.mp4",
            scale=4
        )
        submit_btn = gr.Button("Process", variant="primary", scale=1)
    
    with gr.Row():
        error_box = gr.Textbox(label="Error", visible=False)
    
    with gr.Row():
        output_text = gr.Textbox(
            label="Transcription",
            interactive=True,
            lines=10,
            max_lines=20,
            show_copy_button=True
        )
    
    # Progress bar
    progress_bar = gr.Progress()
    
    def wrapper_process(video_url, progress=gr.Progress()):
        progress(0, desc="Starting...")
        progress(0.3, desc="Downloading audio...")
        audio_file = download_and_convert_to_mp3(video_url)
        progress(0.7, desc="Transcribing audio...")
        transcription = transcribe_audio(audio_file)
        progress(1.0, desc="Complete!")
        return transcription
    
    submit_btn.click(
        fn=wrapper_process,
        inputs=video_url,
        outputs=output_text,
    )

if __name__ == "__main__":
    app.launch()