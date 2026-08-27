import os
import json
import time
import requests
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

def main():
    # 1. Configurar credenciais do Google Drive
    creds_json = os.environ.get("GDRIVE_CREDENTIALS")
    folder_id = os.environ.get("GDRIVE_FOLDER_ID")

    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict, 
        scopes=['https://www.googleapis.com/auth/drive']
    )
    drive_service = build('drive', 'v3', credentials=creds)

    # 2. Carregar cookies salvos no Secret
    cookies_raw = os.environ.get("INSTAGRAM_COOKIES", "")
    playwright_cookies = []

    for line in cookies_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            domain, _, path, secure, expires, name, value = parts[:7]
            playwright_cookies.append({
                "name": name,
                "value": value,
                "domain": domain,
                "path": path,
                "secure": secure.lower() == "true",
                "expires": float(expires) if expires.isdigit() else -1
            })

    username = "prefeituraslmg"
    video_url = None
    post_id = f"video_{int(time.time())}"

    # 3. Navegar com Chromium diretamente no Instagram
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        
        if playwright_cookies:
            context.add_cookies(playwright_cookies)
            print(f"Injetados {len(playwright_cookies)} cookies de autenticação.")

        page = context.new_page()

        # Interceptar URLs de arquivos de vídeo MP4 transferidos pela rede
        def intercept_response(response):
            nonlocal video_url
            if ".mp4" in response.url or "video" in response.headers.get("content-type", ""):
                if "blob:" not in response.url and not video_url:
                    video_url = response.url

        page.on("response", intercept_response)

        print(f"Acessando Reels de @{username} no Instagram...")
        try:
            page.goto(f"https://www.instagram.com/{username}/reels/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(5)

            # Clica no primeiro Reel disponível
            first_reel = page.locator("a[href*='/reel/']").first
            if first_reel.count() > 0:
                print("Abrindo o Reel mais recente...")
                first_reel.click()
                time.sleep(6)
                
                if not video_url:
                    video_elem = page.locator("video").first
                    if video_elem.count() > 0:
                        video_url = video_elem.get_attribute("src")
            else:
                first_post = page.locator("a[href*='/p/']").first
                if first_post.count() > 0:
                    print("Abrindo publicação do feed...")
                    first_post.click()
                    time.sleep(6)
                    video_elem = page.locator("video").first
                    if video_elem.count() > 0:
                        video_url = video_elem.get_attribute("src")
                        
        except Exception as e:
            print(f"Erro durante a navegação: {e}")

        browser.close()

    # 4. Baixar o vídeo e enviar para o Google Drive
    if video_url:
        print("Vídeo capturado com sucesso! Baixando mídia...")
        video_file = f"{post_id}.mp4"
        
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
        
        print(f"Sucesso total! Arquivo enviado com ID: {uploaded_file.get('id')}")
    else:
        print("Nenhum vídeo pôde ser capturado nesta execução.")

if __name__ == "__main__":
    main()
