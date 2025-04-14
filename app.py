Okay, let's modify the code to include error display in the Gradio interface, add a basic download progress indication, and provide three example video URLs.
import gradio as gr
import os
from pytube import YouTube
from pytube.exceptions import PytubeError, VideoUnavailable
import yt_dlp
from yt_dlp.utils import DownloadError
import whisper
import tempfile
import traceback
import time  # For simulating download progress

def download_audio(video_url, temp_dir, progress=gr.Progress()):
    try:
        progress(0, desc="Initializing download...")
        # Try pytube first for YouTube URLs
        if "youtube.com" in video_url or "youtu.be" in video_url:
            try:
                yt = YouTube(video_url, on_progress_callback=lambda stream, chunk, bytes_remaining: progress((stream.filesize - bytes_remaining) / stream.filesize, desc="Downloading audio (pytube)..."))
                stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
                if not stream:
                    raise Exception("No audio stream found")
                output_path = os.path.join(temp_dir, "audio.mp3")
                stream.download(output_path=temp_dir, filename="audio.mp3")
                return output_path, None
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
            'progress_hooks': [lambda d: progress(d['downloaded_bytes'] / d['total_bytes'] if 'total_bytes' in d and d['total_bytes'] else None, desc="Downloading audio (yt-dlp)...") if d['status'] == 'downloading' else None],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download([video_url])
            except DownloadError as e:
                raise Exception(str(e))

        # Find the downloaded file
        for file in os.listdir(temp_dir):
            if file.startswith("audio."):
                return os.path.join(temp_dir, file), None

        raise Exception("Failed to download audio")
    except Exception as e:
        return None, f"Download error: {str(e)}"

def transcribe_audio(audio_path, model_size, progress=gr.Progress()):
    try:
        progress(0, desc="Loading model...")
        model = whisper.load_model(model_size)
        progress(0.1, desc="Transcribing audio...")
        result = model.transcribe(audio_path)
        return result["text"], None
    except Exception as e:
        traceback.print_exc()
        return None, f"Transcription failed: {str(e)}"

def process_video(video_url, model_size, progress=gr.Progress()):
    temp_dir = tempfile.mkdtemp()
    try:
        # Download audio
        audio_path, download_error = download_audio(video_url, temp_dir, progress)
        if download_error:
            return "", download_error

        if not audio_path or not os.path.exists(audio_path):
            return "", "Failed to download audio file"

        # Transcribe
        transcription, transcribe_error = transcribe_audio(audio_path, model_size, progress)
        if transcribe_error:
            return "", transcribe_error

        return transcription, None
    except Exception as e:
        return "", str(e)
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
                             placeholder="Enter video URL here...")
        model_size = gr.Dropdown(["tiny", "base", "small", "medium", "large"],
                               value="base", label="Model Size")

    transcribe_btn = gr.Button("Transcribe")
    output_text = gr.Textbox(label="Transcription", lines=10)
    error_box = gr.Textbox(label="Error", visible=True)  # Make error box visible
    progress_bar = gr.Progress(label="Processing")

    gr.Markdown("### Example URLs:")
    gr.Markdown("- YouTube: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`")
    gr.Markdown("- Vimeo: `https://vimeo.com/170478648`")
    gr.Markdown("- Bilibili: `https://www.bilibili.com/video/BV1x7411V7YF`")

    transcribe_btn.click(
        fn=process_video,
        inputs=[video_url, model_size, progress_bar],
        outputs=[output_text, error_box]
    )

if __name__ == "__main__":
    app.launch()

Key Changes and Explanations:
 * Error Display:
   * The error_box in the Gradio interface is now set to visible=True by default.
   * The download_audio and transcribe_audio functions now return two values: the result (audio path or transcription) and an error message (or None if no error).
   * The process_video function now also returns two values: the transcription and the error message.
   * The click event's outputs are updated to [output_text, error_box] to display the returned error message in the error_box.
 * Download Progress:
   * The download_audio function now accepts a progress=gr.Progress() argument.
   * pytube Progress: For pytube, the on_progress_callback in the YouTube constructor is used to track the download progress and update the Gradio Progress component.
   * yt-dlp Progress: For yt-dlp, a progress_hooks list is added to the ydl_opts. This hook is a lambda function that gets called with download information (d). It calculates the progress and updates the Gradio Progress component when the status is 'downloading'.
   * The transcribe_audio function also accepts and uses a progress argument to show a basic "Loading model..." and "Transcribing audio..." step. Whisper itself doesn't provide granular progress updates during transcription.
   * The process_video function now also accepts and passes the progress component to the download and transcribe functions.
   * The click event's inputs now include progress_bar.
 * Example URLs:
   * A gr.Markdown section is added to the interface below the input elements to provide three example video URLs for different platforms: YouTube, Vimeo, and Bilibili.
How to Run:
 * Save the code as a Python file (e.g., app.py).
 * Make sure you have the necessary libraries installed:
   pip install gradio pytube yt-dlp whisper

 * Run the application from your terminal:
   python app.py

 * A local web server will start, and you can access the Gradio interface in your web browser (usually at http://localhost:7860).
Now, when you encounter an error during download or transcription, the error message should be displayed in the "Error" text box in the Gradio interface, and you'll see a basic progress indication during the download process.
