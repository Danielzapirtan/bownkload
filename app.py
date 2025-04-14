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
            'outtmpl': os.path.join(temp_dir, 'audio.%(ext)s'),
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            filename = ydl.prepare_filename(info)
        
        # Convert to mp3 if needed
        base, ext = os.path.splitext(filename)
        if ext != '.mp3':
            new_filename = base + '.mp3'
            if os.path.exists(new_filename):
                return new_filename
            raise Exception("Audio conversion failed")
        
        return filename
    except Exception as e:
        traceback.print_exc()
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

def process_input(video_url, video_file, model_size):
    temp_dir = tempfile.mkdtemp()
    try:
        audio_path = None
        
        if video_url:  # URL case
            if not video_url.strip():
                raise gr.Error("Please provide either a URL or upload a video file")
            
            # Download audio
            audio_path = download_audio(video_url.strip(), temp_dir)
        elif video_file:  # Uploaded file case
            audio_path = os.path.join(temp_dir, os.path.basename(video_file.name))
            # Copy the file instead of rename to avoid permission issues
            with open(video_file.name, 'rb') as src, open(audio_path, 'wb') as dst:
                dst.write(src.read())
        
        if not audio_path or not os.path.exists(audio_path):
            raise gr.Error("Failed to process audio file")
        
        # Transcribe
        transcription = transcribe_audio(audio_path, model_size)
        
        return transcription
    except Exception as e:
        traceback.print_exc()
        raise gr.Error(str(e))
    finally:
        # Clean up
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

with gr.Blocks(title="Video Transcription") as app:
    gr.Markdown("# 🎥 Video to Transcription")
    
    with gr.Row():
        with gr.Column():
            video_url = gr.Textbox(label="Video URL", 
                                 placeholder="https://www.youtube.com/watch?v=...")
            video_file = gr.File(label="Or upload a video file", 
                              file_types=["video", "audio"])
            model_size = gr.Dropdown(["tiny", "base", "small", "medium", "large"], 
                                   value="base", label="Model Size")
    
    transcribe_btn = gr.Button("Transcribe")
    output_text = gr.Textbox(label="Transcription", lines=10, interactive=False)
    
    transcribe_btn.click(
        fn=process_input,
        inputs=[video_url, video_file, model_size],
        outputs=output_text,
    )

if __name__ == "__main__":
    app.launch(share=True, debug=True)
