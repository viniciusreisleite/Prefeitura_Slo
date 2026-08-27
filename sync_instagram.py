import os
import json
import yt_dlp
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 1. Configurar credenciais do Google Drive
creds_json = os.environ.get("GDRIVE_CREDENTIALS")
folder_id = os.environ.get("GDRIVE_FOLDER_ID")

creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(
    creds_dict, 
    scopes=['https://www.googleapis.com/auth/drive']
)
drive_service = build('drive', 'v3', credentials=creds)

# 2. Baixar o vídeo mais recente do perfil usando yt-dlp
username = "prefeituraslmg"
ydl_opts = {
    'outtmpl': 'video_instagram.%(ext)s',
    'format': 'mp4/best',
    'playlist_items': '1',  # Baixa apenas o post mais recente
    'quiet': False
}

print(f"Buscando publicações de @{username}...")
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([f"https://www.instagram.com/{username}/"])

# 3. Localizar o arquivo baixado e enviar para o Google Drive
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
