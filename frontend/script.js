// Replace with your actual backend URL after deployment
const BACKEND_URL = 'https://y2-downloader-1.onrender.com'; // Change this to your deployed backend URL

let selectedFormat = null;
let currentVideoUrl = null;

async function getVideoInfo() {
    const urlInput = document.getElementById('urlInput');
    const url = urlInput.value.trim();
    
    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }
    
    showLoading(true);
    hideError();
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/info`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch video information');
        }
        
        displayVideoInfo(data, url);
        currentVideoUrl = url;
        showLoading(false);
        
    } catch (error) {
        showLoading(false);
        showError(error.message);
    }
}

function displayVideoInfo(info, url) {
    document.getElementById('thumbnail').src = info.thumbnail;
    document.getElementById('videoTitle').textContent = info.title;
    
    const duration = formatDuration(info.duration);
    document.getElementById('videoDuration').textContent = `Duration: ${duration}`;
    
    const formatsList = document.getElementById('formatsList');
    formatsList.innerHTML = '';
    
    info.formats.forEach(format => {
        const formatElement = createFormatElement(format);
        formatsList.appendChild(formatElement);
    });
    
    // Add download button
    const downloadBtn = document.createElement('button');
    downloadBtn.textContent = 'Download Selected Format';
    downloadBtn.className = 'download-btn';
    downloadBtn.onclick = () => downloadVideo(url);
    formatsList.appendChild(downloadBtn);
    
    document.getElementById('videoInfo').classList.remove('hidden');
}

function createFormatElement(format) {
    const div = document.createElement('div');
    div.className = 'format-item';
    
    let formatName = '';
    if (format.vcodec !== 'none' && format.acodec !== 'none') {
        formatName = 'Video + Audio';
    } else if (format.vcodec !== 'none') {
        formatName = 'Video Only';
    } else if (format.acodec !== 'none') {
        formatName = 'Audio Only';
    }
    
    const fileSize = format.filesize ? formatFileSize(format.filesize) : 'Unknown size';
    
    div.innerHTML = `
        <div class="format-name">${formatName} (${format.ext})</div>
        <div class="format-details">
            Resolution: ${format.resolution}<br>
            Size: ${fileSize}
        </div>
    `;
    
    div.onclick = () => {
        document.querySelectorAll('.format-item').forEach(item => {
            item.classList.remove('selected');
        });
        div.classList.add('selected');
        selectedFormat = format.format_id;
    };
    
    return div;
}

async function downloadVideo(url) {
    if (!selectedFormat) {
        showError('Please select a format first');
        return;
    }
    
    try {
        const response = await fetch(`${BACKEND_URL}/api/download`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                url: url,
                format_id: selectedFormat
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Download failed');
        }
        
        // Get the blob from response
        const blob = await response.blob();
        
        // Create download link
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        
        // Get filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'video.mp4';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (match && match[1]) {
                filename = match[1].replace(/['"]/g, '');
            }
        }
        
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
        
    } catch (error) {
        showError(error.message);
    }
}

function formatDuration(seconds) {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function formatFileSize(bytes) {
    if (!bytes) return 'Unknown';
    const units = ['B', 'KB', 'MB', 'GB'];
    let size = bytes;
    let unitIndex = 0;
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }
    
    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

function showLoading(show) {
    const loading = document.getElementById('loading');
    const fetchBtn = document.getElementById('fetchBtn');
    
    if (show) {
        loading.classList.remove('hidden');
        fetchBtn.disabled = true;
    } else {
        loading.classList.add('hidden');
        fetchBtn.disabled = false;
    }
}

function showError(message) {
    const error = document.getElementById('error');
    error.textContent = message;
    error.classList.remove('hidden');
}

function hideError() {
    document.getElementById('error').classList.add('hidden');
}
