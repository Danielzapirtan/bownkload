import gradio as gr
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

def get_transcript(video_url, language_code='en'):
    """
    Fetches transcript using youtube-transcript-api (no scraping, uses YouTube's system).
    Handles errors gracefully and respects fair use.
    """
    try:
        # Extract video ID from URL
        video_id = video_url.split("v=")[-1].split("&")[0]
        
        # Fetch available transcripts
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        transcript = transcript_list.find_transcript([language_code])
        
        # Fetch the actual transcript
        transcript_text = "\n".join([t['text'] for t in transcript.fetch()])
        
        # Metadata for attribution
        metadata = f"Video: {video_url}\nLanguage: {transcript.language_code}\n\n"
        return metadata + transcript_text
        
    except TranscriptsDisabled:
        return "Error: Transcripts are disabled for this video."
    except NoTranscriptFound:
        return "Error: No transcript found for the selected language."
    except Exception as e:
        return f"Error: {str(e)}"

# Gradio UI
with gr.Blocks(title="YouTube Transcript Extractor") as app:
    gr.Markdown("""
    ## 📜 YouTube Transcript Extractor  
    **Fair Use Notice**: This tool extracts *publicly available* transcripts for **personal/educational use**.  
    Do not redistribute content without permission.  
    """)
    
    with gr.Row():
        video_url = gr.Textbox(label="YouTube Video URL", placeholder="Paste a YouTube link...")
        language = gr.Dropdown(
            label="Language", 
            choices=["en", "es", "fr", "de", "ja"],  # Add more as needed
            value="en"
        )
    
    btn = gr.Button("Get Transcript")
    output = gr.Textbox(label="Transcript", interactive=False)
    
    # Warning footer
    gr.Markdown("""
    ⚠️ **Disclaimer**:  
    - This tool does not store transcripts.  
    - Only use transcripts for **fair use purposes** (research, education, accessibility).  
    - Respect copyright laws.  
    """)
    
    btn.click(
        fn=get_transcript,
        inputs=[video_url, language],
        outputs=output
    )

if __name__ == "__main__":
    app.launch()