import os
import time
import requests
from playwright.sync_api import sync_playwright

def main():
    # 1. Carregar cookies salvos no Secret
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
    captured_video_url = None
    post_id = f"video_{int(time.time())}"

    # 2. Navegar com Chromium diretamente no Instagram
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

        # Interceptar tráfego de rede buscando a URL real do CDN (.mp4 / video/mp4)
        def handle_response(response):
            nonlocal captured_video_url
            url = response.url
            # Evita capturar links blob ou URLs de áudio isoladas
            if url.startswith("http") and not captured_video_url:
                ct = response.headers.get("content-type", "")
                if ("video/mp4" in ct or ".mp4" in url) and ("cdninstagram.com" in url or "fbcdn.net" in url):
                    print(f"Fluxo de mídia detectado na rede!")
                    captured_video_url = url

        page.on("response", handle_response)

        print(f"Acessando Reels de @{username} no Instagram...")
        try:
            page.goto(f"https://www.instagram.com/{username}/reels/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(5)

            # Clica no primeiro Reel
            first_reel = page.locator("a[href*='/reel/']").first
            if first_reel.count() > 0:
                print("Abrindo o Reel mais recente...")
                first_reel.click()
                time.sleep(7)
            else:
                first_post = page.locator("a[href*='/p/']").first
                if first_post.count() > 0:
                    print("Abrindo publicação do feed...")
                    first_post.click()
                    time.sleep(7)

            # Se a resposta de rede direta não foi capturada, busca no elemento JS
            if not captured_video_url:
                video_src = page.evaluate("""() => {
                    const v = document.querySelector('video');
                    return v ? (v.currentSrc || v.src) : null;
                }""")
                if video_src and video_src.startswith("http"):
                    captured_video_url = video_src

        except Exception as e:
            print(f"Aviso durante a navegação: {e}")

        browser.close()

    # 3. Baixar o arquivo .mp4 para o GitHub Runner
    if captured_video_url and captured_video_url.startswith("http"):
        print(f"Baixando vídeo capturado...")
        video_file = f"{post_id}.mp4"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        vid_data = requests.get(captured_video_url, headers=headers, stream=True, timeout=90)
        with open(video_file, 'wb') as f:
            for chunk in vid_data.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    
        print(f"Sucesso! Arquivo {video_file} baixado com êxito.")
    else:
        print("Nenhum link HTTP direto de vídeo foi capturado nesta tentativa.")

if __name__ == "__main__":
    main()
