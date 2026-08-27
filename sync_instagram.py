import os
import subprocess
import time
from playwright.sync_api import sync_playwright

def main():
    # 1. Salvar os cookies no formato Netscape
    cookies_raw = os.environ.get("INSTAGRAM_COOKIES", "")
    cookie_file = "cookies.txt"
    with open(cookie_file, "w", encoding="utf-8") as f:
        f.write(cookies_raw)

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
    reel_url = None

    # 2. Abrir Instagram e localizar o Reel mais recente
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

        print(f"Acessando perfil de @{username}...")
        try:
            page.goto(f"https://www.instagram.com/{username}/reels/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(5)

            first_reel = page.locator("a[href*='/reel/']").first
            if first_reel.count() > 0:
                href = first_reel.get_attribute("href")
                reel_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                print(f"Reel mais recente encontrado: {reel_url}")
            else:
                first_post = page.locator("a[href*='/p/']").first
                if first_post.count() > 0:
                    href = first_post.get_attribute("href")
                    reel_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                    print(f"Post com vídeo encontrado: {reel_url}")

        except Exception as e:
            print(f"Erro durante a navegação: {e}")

        browser.close()

    if not reel_url:
        print("Nenhum post/reel foi identificado.")
        return

    # 3. Verificar se o vídeo já foi baixado anteriormente
    last_video_file = "last_video.txt"
    last_saved_url = ""
    if os.path.exists(last_video_file):
        with open(last_video_file, "r", encoding="utf-8") as f:
            last_saved_url = f.read().strip()

    if reel_url == last_saved_url:
        print(f"O vídeo {reel_url} já foi baixado anteriormente. Nada a fazer.")
        return

    # 4. Fazer o download do vídeo inédito
    output_filename = f"video_{int(time.time())}.mp4"
    print(f"Novo vídeo detectado! Baixando com yt-dlp...")

    cmd = [
        "yt-dlp",
        "--cookies", cookie_file,
        "--no-check-certificates",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "-o", output_filename,
        reel_url
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)

    if os.path.exists(output_filename) and os.path.getsize(output_filename) > 0:
        size_mb = os.path.getsize(output_filename) / (1024 * 1024)
        print(f"Sucesso! Vídeo salvo: {output_filename} ({size_mb:.2f} MB)")
        
        # Salva o link no arquivo de controle para a próxima checagem
        with open(last_video_file, "w", encoding="utf-8") as f:
            f.write(reel_url)
    else:
        print("Erro: O yt-dlp não conseguiu gerar o arquivo final.")
        print(result.stderr)

if __name__ == "__main__":
    main()
