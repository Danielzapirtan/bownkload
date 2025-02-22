from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Directory to save downloaded files
DOWNLOAD_DIR = "/tmp/downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

@app.route('/')
def index():
    # Render the index.html template
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download_file():
    # Get the URL from the request
    data = request.json
    url = data.get('url')

    if not url:
        return jsonify({"error": "URL is required"}), 400

    try:
        # Send a GET request to the URL
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for bad status codes

        # Extract the filename from the URL
        filename = os.path.join(DOWNLOAD_DIR, url.split('/')[-1])

        # Save the file
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)

        return jsonify({"message": f"File downloaded successfully: {filename}"}), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to download the file: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='localhost', port=5045, debug=True)
