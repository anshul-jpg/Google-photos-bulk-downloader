import os
import json
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import requests
import tkinter as tk
from tkinter import filedialog
import sys

# Set up OAuth 2.0 credentials
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']
creds = None

# Load or create credentials
try:
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if not os.path.exists('credentials.json'):
            print("Error: 'credentials.json' file not found. Please ensure it's in the same directory as this script.")
            sys.exit(1)
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    print("Credentials loaded successfully.")
except Exception as e:
    print(f"Error during authentication: {str(e)}")
    sys.exit(1)

# Create a custom service object for Google Photos API
class GooglePhotosService:
    def __init__(self, credentials):
        self.base_url = "https://photoslibrary.googleapis.com/v1"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {credentials.token}"})
    
    def list_media_items(self, pageSize=100, pageToken=None):
        url = f"{self.base_url}/mediaItems"
        params = {"pageSize": pageSize}
        if pageToken:
            params["pageToken"] = pageToken
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching media items: {str(e)}")
            return {}

def sanitize_filename(filename):
    # Remove invalid characters (including '|') and replace spaces
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.replace(' ', '_')
    # Remove or replace any other potentially problematic characters
    filename = re.sub(r'[^\w\-_\. ]', '', filename)
    # Trim the filename if it's too long (Windows has a 255 character limit)
    if len(filename) > 240:
        name, ext = os.path.splitext(filename)
        filename = name[:240-len(ext)] + ext
    # Ensure the filename is not empty after sanitization
    if not filename:
        filename = "untitled"
    return filename

def download_photos(service, download_folder):
    print("Starting to count and download photos...")
    
    total_photos = 0
    downloaded = 0
    skipped = 0
    nextPageToken = None
    
    while True:
        print(f"Fetching next batch of photos (Current total: {total_photos})...")
        results = service.list_media_items(pageSize=100, pageToken=nextPageToken)
        items = results.get('mediaItems', [])
        
        if not items:
            print("No items found in this batch.")
            break
        
        total_photos += len(items)
        print(f"Total photos found so far: {total_photos}")
        
        for item in items:
            original_filename = item['filename']
            filename = sanitize_filename(original_filename)
            download_url = item['baseUrl'] + '=d'  # '=d' parameter for original quality
            
            file_path = os.path.join(download_folder, filename)
            
            if os.path.exists(file_path):
                print(f"Skipped (already exists): {filename}")
                skipped += 1
            else:
                try:
                    response = requests.get(download_url)
                    response.raise_for_status()
                    
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    downloaded += 1
                    print(f"Downloaded: {filename}")
                except requests.exceptions.RequestException as e:
                    print(f"Failed to download: {filename}. Error: {str(e)}")
                except OSError as e:
                    print(f"Failed to save: {filename}. Error: {str(e)}")
                    print(f"Original filename: {original_filename}")
                    print(f"Sanitized filename: {filename}")
                    print(f"Full file path: {file_path}")
                    continue
            
            print(f"Progress: {downloaded + skipped}/{total_photos} "
                  f"(Downloaded: {downloaded}, Skipped: {skipped})")
        
        nextPageToken = results.get('nextPageToken')
        if not nextPageToken:
            break
    
    print(f"\nProcess complete. "
          f"Total photos found: {total_photos}, Downloaded: {downloaded}, Skipped: {skipped}")

# Ask the user to choose the download folder
root = tk.Tk()
root.withdraw()  # Hide the root window
download_folder = filedialog.askdirectory(title="Select Download Folder")

# Ensure the download folder exists
if download_folder:
    os.makedirs(download_folder, exist_ok=True)
    print(f"Download folder: {download_folder}")
    # Instantiate the GooglePhotosService
    service = GooglePhotosService(creds)
    # Start downloading photos
    download_photos(service, download_folder)
else:
    print("No folder selected. Exiting.")