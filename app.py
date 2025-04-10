import gradio as gr
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled, NoTranscriptFound,
    VideoUnavailable, TooManyRequests
)
import re

# Supported languages (with Romanian added)
LANGUAGES = {
    "Auto (Detect)": "auto",
    "English": "en",
    "Romanian": "ro",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Italian": "it",
    "Portuguese": "pt",
    "Russian": "ru",
    "Hindi": "hi",
    "Arabic": "ar"
}

def extract_video_id(url: str) -> str:
    """Extracts video ID from various YouTube URL formats."""
    patterns = [
        r"v=([^&]+)",         # Standard ?v=ID
        r"youtu\.be/([^?]+)",  # Short URL
        r"embed/([^/?]+)",     # Embed URL
        r"/([^/?]+)$"          # Vanity URL
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""

def get_transcript(video_url: str, language_code: str) -> str:
    """
    Fetches transcript with support for Romanian and auto-detection.
    Returns formatted text or error message.
    """
    try:
        video_id = extract_video_id(video_url)
        if not video_id:
            return "❌ Error: Invalid YouTube URL."

        # Handle 'auto' language (fetch first available transcript)
        if language_code == "auto":
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
        else:
            transcript = YouTubeTranscriptApi.get_transcript(
                video_id,
                languages=[language_code]
            )

        # Format with timestamps
        return "\n".join(
            f"[{round(entry['start'], 1)}s] {entry['text']}"
            for entry in transcript
        )

    except TranscriptsDisabled:
        return "❌ Error: Transcripts disabled for this video."
    except NoTranscriptFound:
        return f"❌ Error: No {LANGUAGES.get(language_code, language_code)} transcript found."
    except VideoUnavailable:
        return "❌ Error: Video unavailable or private."
    except TooManyRequests:
        return "❌ Error: Too many requests. Wait and try again."
    except Exception as e:
        return f"❌ Unexpected error: {str(e)}"

# Gradio UI
with gr.Blocks(theme=gr.themes.Soft(), title="YouTube Transcript Extractor") as app:
    gr.Markdown("""
    # 🇷🇴 YouTube Transcript Extractor  
    *Supports **Romanian** and 10+ other languages*  
    *For educational/fair use only*  
    """)

    with gr.Row():
        video_url = gr.Textbox(
            label="YouTube URL",
            placeholder="Paste any YouTube video link...",
            max_lines=1
        )
        language = gr.Dropdown(
            label="Language",
            choices=list(LANGUAGES.keys()),
            value="Auto (Detect)"
        )

    btn = gr.Button("Get Transcript", variant="primary")
    output = gr.Textbox(
        label="Transcript",
        interactive=True,
        lines=15,
        show_copy_button=True
    )

    gr.Markdown("""
    ### ⚠️ Legal Notice  
    - This tool **does not store** transcripts.  
    - Only use for **personal, educational, or accessibility purposes**.  
    - Respect [YouTube's Terms of Service](https://www.youtube.com/t/terms).  
    """)

    btn.click(
        fn=get_transcript,
        inputs=[video_url, language],
        outputs=output
    )

if __name__ == "__main__":
    app.launch()