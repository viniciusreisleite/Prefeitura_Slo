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

# 2. Navegar com Chromium real para extrair o vídeo
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 800}
    )
    page = context.new_page()

    print(f"Acessando perfil de @{username} via Picuki...")
    try:
        page.goto(f"https://www.picuki.com/profile/{username}", wait_until="domcontentloaded", timeout=45000)
        time.sleep(3)
        
        # Encontra o primeiro link de postagem
        posts = page.locator(".box-photos .box-photo a").all()
        post_link = None
        for post in posts:
            href = post.get_attribute("href")
            if href and "/media/" in href:
                post_link = href
                break
                
        if post_link:
            print(f"Abrindo publicação: {post_link}")
            page.goto(post_link, wait_until="domcontentloaded", timeout=45000)
            time.sleep(3)
            
            # Localiza a tag de vídeo ou botão de download
            video_element = page.locator("video source, video").first
            if video_element.count() > 0:
                video_url = video_element.get_attribute("src")
                
            if not video_url:
                download_btn = page.locator("a[href*='.mp4'], a.btn-download").first
                if download_btn.count() > 0:
                    video_url = download_btn.get_attribute("href")
                    
    except Exception as e:
        print(f"Aviso durante a extração: {e}")
        
    browser.close()

# 3. Fazer download do arquivo e enviar ao Google Drive
if video_url:
    print(f"Vídeo localizado! Baixando arquivo...")
    video_file = f"video_{post_id}.mp4"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    vid_data = requests.get(video_url, headers=headers, stream=True, timeout=60)
    with open(video_file, 'wb') as f:
        for chunk in vid_data.iter_content(chunk_size=1024*1024):
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
    
    print(f"Sucesso! Arquivo enviado com ID: {uploaded_file.get('id')}")
else:
    print("Nenhum vídeo em formato .mp4 pôde ser extraído na última publicação.")
