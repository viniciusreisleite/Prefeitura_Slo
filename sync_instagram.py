import os
import json
import yt_dlp
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Carregar cookies do Instagram salvos no Secret
cookies_content = os.environ.get("INSTAGRAM_COOKIES")
cookies_file = "cookies.txt"
if cookies_content:
    with open(cookies_file, "w", encoding="utf-8") as f:
        f.write(cookies_content)

# 2. Configurar credenciais do Google Drive
creds_json = os.environ.get("GDRIVE_CREDENTIALS")
folder_id = os.environ.get("GDRIVE_FOLDER_ID")

creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(
    creds_dict, 
    scopes=['https://www.googleapis.com/auth/drive']
)
drive_service = build('drive', 'v3', credentials=creds)

# 3. Baixar o vídeo mais recente com yt-dlp usando cookies
username = "prefeituraslmg"
ydl_opts = {
    'outtmpl': 'video_instagram.%(ext)s',
    'format': 'mp4/best',
    'playlist_items': '1',
    'cookiefile': cookies_file if cookies_content else None,
    'quiet': False
}

print(f"Buscando publicações de @{username} com autenticação...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([f"https://www.instagram.com/{username}/"])

# 4. Enviar o vídeo para o Google Drive
for file_name in os.listdir('.'):
    if file_name.startswith('video_instagram') and file_name.endswith('.mp4'):
        print(f"Enviando {file_name} para o Google Drive...")
        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_name, mimetype='video/mp4', resumable=True)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"Sucesso! Arquivo enviado com ID: {uploaded_file.get('id')}")
        break
