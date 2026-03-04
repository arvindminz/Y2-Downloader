from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import uuid
import threading
import time
import re

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

def extract_youtube_id(url):
    """Extract YouTube video ID from various URL formats"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'(?:youtube\.com\/v\/)([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.route('/api/info', methods=['POST'])
def get_video_info():
    try:
        data = request.json
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400

        # Extract video ID to validate it's a YouTube URL
        video_id = extract_youtube_id(url)
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400

        # Configure yt-dlp options to avoid the error
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': False,
            'ignoreerrors': True,
            'no_color': True,
            'geo_bypass': True,
            'nocheckcertificate': True,
            # Add these options to handle the urllib error
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # First try to extract info without downloading
                info = ydl.extract_info(url, download=False)
                
                if info is None:
                    return jsonify({'error': 'Could not fetch video information'}), 400
                
                # Get available formats
                formats = []
                if 'formats' in info:
                    for f in info.get('formats', []):
                        if f.get('vcodec') != 'none' or f.get('acodec') != 'none':
                            # Skip unwanted formats
                            if f.get('format_note') in ['storyboard', 'sb0', 'sb1', 'sb2']:
                                continue
                                
                            format_info = {
                                'format_id': f.get('format_id'),
                                'ext': f.get('ext'),
                                'resolution': f.get('resolution') or f.get('format_note') or 'N/A',
                                'filesize': f.get('filesize') or f.get('filesize_approx'),
                                'vcodec': f.get('vcodec'),
                                'acodec': f.get('acodec'),
                                'format_note': f.get('format_note', '')
                            }
                            formats.append(format_info)
                
                # If no formats found in 'formats', try 'requested_formats'
                if not formats and 'requested_formats' in info:
                    for f in info.get('requested_formats', []):
                        format_info = {
                            'format_id': f.get('format_id'),
                            'ext': f.get('ext'),
                            'resolution': f.get('resolution') or 'N/A',
                            'filesize': f.get('filesize'),
                            'vcodec': f.get('vcodec'),
                            'acodec': f.get('acodec'),
                            'format_note': ''
                        }
                        formats.append(format_info)
                
                return jsonify({
                    'title': info.get('title', 'Unknown Title'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'formats': formats
                })
                
        except Exception as ydl_error:
            print(f"yt-dlp error: {str(ydl_error)}")
            # Try alternative method with different options
            ydl_opts_alt = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': True,  # Only get basic info
                'force_generic_extractor': False,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts_alt) as ydl:
                info = ydl.extract_info(url, download=False)
                return jsonify({
                    'title': info.get('title', 'Unknown Title'),
                    'thumbnail': info.get('thumbnail', ''),
                    'duration': info.get('duration', 0),
                    'formats': []
                })
            
    except Exception as e:
        print(f"General error: {str(e)}")
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
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Find the downloaded file
            downloaded_file = None
            for file in os.listdir(DOWNLOADS_DIR):
                if file.startswith(os.path.basename(output_path).split('.')[0]):
                    downloaded_file = os.path.join(DOWNLOADS_DIR, file)
                    break
            
            if downloaded_file and os.path.exists(downloaded_file):
                return send_file(
                    downloaded_file,
                    as_attachment=True,
                    download_name=f"{info['title']}.{downloaded_file.split('.')[-1]}",
                    mimetype='application/octet-stream'
                )
            else:
                return jsonify({'error': 'File not found after download'}), 500
            
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'YouTube Downloader API is running'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
