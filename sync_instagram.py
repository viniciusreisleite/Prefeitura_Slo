import os
import json
import glob
import instaloader
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

# 2. Configurar o Instaloader para baixar apenas vídeos
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False,
    compress_history=False
)

username = "prefeituraslmg"
print(f"Buscando publicações de @{username} via Instaloader...")

profile = instaloader.Profile.from_username(L.context, username)

# 3. Baixar o vídeo mais recente do perfil
video_encontrado = False
for post in profile.get_posts():
    if post.is_video:
        print(f"Baixando vídeo mais recente: {post.shortcode}")
        L.download_post(post, target="downloads")
        video_encontrado = True
        break

# 4. Localizar o arquivo .mp4 e enviar para o Google Drive
if video_encontrado:
    arquivos_mp4 = glob.glob("downloads/*.mp4")
    if arquivos_mp4:
        caminho_video = arquivos_mp4[0]
        nome_arquivo = os.path.basename(caminho_video)
        print(f"Enviando {nome_arquivo} para o Google Drive...")
        
        file_metadata = {
            'name': nome_arquivo,
            'parents': [folder_id]
        }
        media = MediaFileUpload(caminho_video, mimetype='video/mp4', resumable=True)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        print(f"Sucesso! Arquivo enviado com ID: {uploaded_file.get('id')}")
    else:
        print("Aviso: O post foi processado, mas nenhum arquivo .mp4 foi gerado localmente.")
else:
    print("Nenhum post em formato de vídeo foi encontrado recentemente.")
