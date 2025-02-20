import gradio as gr
import requests
import os

def download_file(url):
    try:
        # Extract the file name from the URL
        file_name = url.split("/")[-1]
        
        # Send a GET request to the URL
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:
            # Save the file to the current working directory
            with open(file_name, "wb") as file:
                file.write(response.content)
            return f"File '{file_name}' downloaded successfully!"
        else:
            return f"Failed to download file. Status code: {response.status_code}"
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Create a Gradio interface
iface = gr.Interface(
    fn=download_file,
    inputs="text",
    outputs="text",
    title="File Downloader",
    description="Enter the URL of a file to download it."
)

# Launch the app
iface.launch()