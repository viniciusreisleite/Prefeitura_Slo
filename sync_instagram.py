import os
import json
import time
import requests
from playwright.sync_api import sync_playwright
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

username = "prefeituraslmg"
video_url = None
post_id = f"post_{int(time.time())}"

# 2. Navegar com Playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()

    profile_url = f"https://www.picuki.com/profile/{username}"
    print(f"Acessando {profile_url}...")
    
    try:
        page.goto(profile_url, wait_until="networkidle", timeout=60000)
        time.sleep(3)

        # Busca links que contenham /media/ no perfil
        links = page.eval_on_selector_all(
            "a[href*='/media/']",
            "elements => elements.map(el => el.href)"
        )
        print(f"Total de publicações encontradas: {len(links)}")

        if links:
            # Testa os primeiros posts até achar um com vídeo
            for post_link in links[:5]:
                print(f"Verificando publicação: {post_link}")
                page.goto(post_link, wait_until="networkidle", timeout=45000)
                time.sleep(2)

                # 1ª Tentativa: Tag <video>
                video_src = page.eval_on_selector(
                    "video, video source",
                    "el => el ? (el.src || el.getAttribute('src')) : null"
                )

                # 2ª Tentativa: Botão ou link de download
                if not video_src:
                    video_src = page.eval_on_selector(
                        "a[href*='.mp4'], a.download-link, a.btn-download, a:has-text('Download')",
                        "el => el ? el.href : null"
                    )

                if video_src and "blob:" not in video_src:
                    print(f"Link de vídeo encontrado: {video_src[:60]}...")
                    video_url = video_src
                    break
        else:
            print("Nenhum link de postagem foi retornado na página do perfil.")

    except Exception as e:
        print(f"Erro durante a navegação: {e}")

    browser.close()

# 3. Baixar o arquivo e enviar ao Google Drive
if video_url:
    print("Iniciando download do vídeo...")
    video_file = f"video_{post_id}.mp4"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    vid_data = requests.get(video_url, headers=headers, stream=True, timeout=90)
    with open(video_file, 'wb') as f:
        for chunk in vid_data.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                
    print(f"Enviando {video_file} para o Google Drive...")
    file_metadata = {
        'name': video_file,
        'parents': [folder_id]
    }
    media = MediaFileUpload(video_file, mimetype='video/mp4', resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    print(f"Sucesso! Arquivo enviado ao Drive com ID: {uploaded_file.get('id')}")
else:
    print("Nenhum arquivo de vídeo foi identificado para download.")
