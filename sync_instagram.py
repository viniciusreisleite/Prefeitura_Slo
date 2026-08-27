import os
import json
import glob
from http.cookiejar import MozillaCookieJar
from itertools import islice
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

# 2. Configurar Instaloader com Cookies
L = instaloader.Instaloader(
    download_pictures=False,
    download_videos=True,
    download_video_thumbnails=False,
    download_geotags=False,
    download_comments=False,
    save_metadata=False
)

cookies_content = os.environ.get("INSTAGRAM_COOKIES")
if cookies_content:
    cookie_file = "cookies.txt"
    with open(cookie_file, "w", encoding="utf-8") as f:
        f.write(cookies_content)
    
    # Carrega os cookies no formato Netscape/Mozilla
    cj = MozillaCookieJar(cookie_file)
    cj.load(ignore_discard=True, ignore_expires=True)
    L.context._session.cookies = cj
    print("Sessão autenticada via cookies com sucesso!")

username = "prefeituraslmg"
print(f"Buscando publicações de @{username}...")

profile = instaloader.Profile.from_username(L.context, username)

# 3. Localizar e baixar o vídeo mais recente
video_encontrado = False
for post in islice(profile.get_posts(), 5):
    if post.is_video:
        print(f"Baixando vídeo: {post.shortcode}")
        L.download_post(post, target="downloads")
        video_encontrado = True
        break

# 4. Enviar para o Google Drive
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
        print(f"Concluído! ID no Drive: {uploaded_file.get('id')}")
