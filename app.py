import gradio as gr
import openai
import whisper
import re
import os
import time
from urllib.request import urlretrieve
from typing import Optional
from pathlib import Path

# Predefined clickable URL examples
EXAMPLE_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://soundcloud.com/lifeat40/sets/electronic-dreams",
    "https://www.ted.com/talks/sir_ken_robinson_do_schools_kill_creativity"
]

# Supported Whisper models
WHISPER_MODELS = ["tiny", "base", "small", "medium", "large"]

def is_valid_url(text: str) -> bool:
    """Check if text is a valid URL using regex"""
    url_pattern = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(url_pattern, text) is not None

def download_from_url(url: str, temp_dir: str = "temp") -> str:
    """Download media from URL to temporary file"""
    os.makedirs(temp_dir, exist_ok=True)
    filename = os.path.join(temp_dir, os.path.basename(url).split("?")[0] + ".mp4")
    try:
        urlretrieve(url, filename)
        return filename
    except Exception as e:
        raise gr.Error(f"Failed to download from URL: {str(e)}")

def transcribe(
    input_source: str,
    model_size: str,
    progress: gr.Progress
) -> str:
    """Transcribe audio/video from file path or URL"""
    try:
        start_time = time.time()
        
        # Show loading spinner while model loads
        with gr.Spinner(text=f"Loading Whisper {model_size} model..."):
            model = whisper.load_model(model_size)
        
        # Determine if input is URL or file
        if is_valid_url(input_source):
            with gr.Spinner(text="Downloading media from URL..."):
                media_path = download_from_url(input_source)
        else:
            media_path = input_source
        
        # Transcribe with progress updates
        progress(0, desc="Starting transcription...")
        result = model.transcribe(media_path)
        
        # Clean up downloaded file if it was from URL
        if input_source != media_path and os.path.exists(media_path):
            os.remove(media_path)
        
        elapsed = time.time() - start_time
        return f"Transcription completed in {elapsed:.2f} seconds:\n\n{result['text']}"
    except Exception as e:
        raise gr.Error(f"Transcription failed: {str(e)}")

def create_demo() -> gr.Blocks:
    """Create Gradio interface"""
    with gr.Blocks(title="Whisper Transcription App") as demo:
        gr.Markdown("# 🎤 OpenAI Whisper Transcription")
        gr.Markdown("Upload audio/video files or paste URLs to transcribe")
        
        with gr.Row():
            with gr.Column():
                input_source = gr.Textbox(
                    label="Media URL or File Path",
                    placeholder="Paste URL or click examples below..."
                )
                
                # Clickable URL examples
                gr.Examples(
                    examples=EXAMPLE_URLS,
                    inputs=input_source,
                    label="Try these examples:"
                )
                
                # File upload component
                file_upload = gr.File(
                    label="Or upload file",
                    file_types=["audio", "video"],
                    type="file"
                )
                
                # Model selection
                model_size = gr.Dropdown(
                    choices=WHISPER_MODELS,
                    value="base",
                    label="Whisper Model Size",
                    info="Larger models are more accurate but slower"
                )
                
                submit_btn = gr.Button("Transcribe", variant="primary")
                
            with gr.Column():
                output_text = gr.Textbox(
                    label="Transcription Result",
                    interactive=True,
                    lines=10
                )
                with gr.Row():
                    copy_btn = gr.Button("Copy to Clipboard")
                    download_btn = gr.Button("Download Result")
                
                # Timer and progress bar
                timer = gr.Textbox(label="Processing Time", interactive=False)
                progress_bar = gr.State(0)
        
        # Event handlers
        submit_btn.click(
            transcribe,
            inputs=[input_source, model_size, progress_bar],
            outputs=[output_text],
            api_name="transcribe"
        )
        
        # Update timer on any change
        demo.load(
            None,
            None,
            timer,
            _js="() => {const start = new Date(); return () => Math.round((new Date() - start)/1000) + ' seconds'}"
        )
        
        # Connect file upload to input source
        file_upload.change(
            lambda file: file.name,
            inputs=file_upload,
            outputs=input_source
        )
        
        # Copy button functionality
        copy_btn.click(
            lambda text: gr.Clipboard().copy(text),
            inputs=output_text,
            outputs=None,
            api_name="copy_result"
        )
        
        # Download button functionality
        download_btn.click(
            lambda text: {
                "name": "transcription.txt",
                "data": text,
                "mime_type": "text/plain"
            },
            inputs=output_text,
            outputs=gr.File(label="Download Transcription"),
            api_name="download_result"
        )
    
    return demo

if __name__ == "__main__":
    demo = create_demo()
    demo.launch(share=True, debug=True)