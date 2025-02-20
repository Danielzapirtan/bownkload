import gradio as gr
import requests

def download_file(url):
    try:
        # Extract the file name from the URL
        file_name = url.split("/")[-1]
        
        # Send a GET request to the URL
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Return the file content and the file name for download
            return response.content, file_name
        else:
            return f"Failed to download file. Status code: {response.status_code}", None
    except Exception as e:
        return f"An error occurred: {str(e)}", None

# Create a Gradio interface
iface = gr.Interface(
    fn=download_file,
    inputs="text",
    outputs=[gr.File(label="Downloaded File"), "text"],
    title="File Downloader",
    description="Enter the URL of a file to download it. The file will be saved to your default downloads folder."
)

# Launch the app
iface.launch()