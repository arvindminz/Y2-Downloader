from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time

app = Flask(__name__)
CORS(app)

# Create downloads directory if it doesn't exist
DOWNLOADS_DIR = "downloads"
if not os.path.exists(DOWNLOADS_DIR):
    os.makedirs(DOWNLOADS_DIR)

# Clean up old files periodically
def cleanup_old_files():
    while True:
        time.sleep(3600)  # Run every hour
        current_time = time.time()
        for filename in os.listdir(DOWNLOADS_DIR):
            filepath = os.path.join(DOWNLOADS_DIR, filename)
            if os.path.getctime(filepath) < current_time - 3600:  # Older than 1 hour
                try:
                    os.remove(filepath)
                except:
                    pass

# Start cleanup thread
cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()

@app.route('/api/info', methods=['POST'])
def get_video_info():
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Get available formats
            formats = []
            for f in info.get('formats', []):
                if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                    format_info = {
                        'format_id': f.get('format_id'),
                        'ext': f.get('ext'),
                        'resolution': f.get('resolution') or f.get('format_note') or 'N/A',
                        'filesize': f.get('filesize') or f.get('filesize_approx'),
                        'vcodec': f.get('vcodec'),
                        'acodec': f.get('acodec')
                    }
                    formats.append(format_info)
            
            return jsonify({
                'title': info.get('title'),
                'thumbnail': info.get('thumbnail'),
                'duration': info.get('duration'),
                'formats': formats
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_video():
    try:
        data = request.json
        url = data.get('url')
        format_id = data.get('format_id')
        
        if not url or not format_id:
            return jsonify({'error': 'URL and format are required'}), 400
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}.%(ext)s"
        output_path = os.path.join(DOWNLOADS_DIR, filename)
        
        ydl_opts = {
            'format': format_id,
            'outtmpl': output_path,
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            actual_filename = ydl.prepare_filename(info)
            
            # Get the actual file extension
            if not os.path.exists(actual_filename):
                # Try to find the file with different extension
                for file in os.listdir(DOWNLOADS_DIR):
                    if file.startswith(os.path.basename(actual_filename).split('.')[0]):
                        actual_filename = os.path.join(DOWNLOADS_DIR, file)
                        break
            
            return send_file(
                actual_filename,
                as_attachment=True,
                download_name=f"{info['title']}.{actual_filename.split('.')[-1]}"
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)