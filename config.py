# Configuration file for Scholar Citation Tracker

# Google Scholar Configuration
GOOGLE_SCHOLAR_URL = "https://scholar.google.com/citations?user=RkspD6IAAAAJ"

# Web Application Configuration
HOST = "0.0.0.0"
PORT = 8080
DEBUG = True

# Data Update Configuration
AUTO_UPDATE_INTERVAL = 300  # seconds (5 minutes)
STATUS_CHECK_INTERVAL = 60  # seconds (1 minute)

# Request Headers for Google Scholar
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# File Paths
DATA_DIRECTORIES = {
    'history': 'history',
    'difference': 'difference'
}