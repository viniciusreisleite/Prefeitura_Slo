import os
import json
import subprocess
import time
from playwright.sync_api import sync_playwright

def main():
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
    post_caption = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        
        if playwright_cookies:
            context.add_cookies(playwright_cookies)

        page = context.new_page()
        print(f"Acessando perfil de @{username}...")

        try:
            page.goto(f"https://www.instagram.com/{username}/reels/", wait_until="domcontentloaded", timeout=45000)
            time.sleep(5)

            first_reel = page.locator("a[href*='/reel/']").first
            if first_reel.count() > 0:
                href = first_reel.get_attribute("href")
                reel_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                first_reel.click()
                time.sleep(4)
                
                # Extrai a legenda do post
                caption_elem = page.locator("h1, div[role='dialog'] span, article span").first
                if caption_elem.count() > 0:
                    post_caption = caption_elem.inner_text()
            else:
                first_post = page.locator("a[href*='/p/']").first
                if first_post.count() > 0:
                    href = first_post.get_attribute("href")
                    reel_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                    first_post.click()
                    time.sleep(4)
                    caption_elem = page.locator("h1, article span").first
                    if caption_elem.count() > 0:
                        post_caption = caption_elem.inner_text()

        except Exception as e:
            print(f"Erro na navegação: {e}")

        browser.close()

    if not reel_url:
        print("Nenhum post encontrado.")
        return

    # Baixa o vídeo e gera o arquivo latest.mp4 fixo para o player web
    output_filename = "latest.mp4"
    print("Baixando vídeo e mesclando com ffmpeg...")

    cmd = [
        "yt-dlp",
        "--cookies", cookie_file,
        "--no-check-certificates",
        "--merge-output-format", "mp4",
        "-f", "bestvideo+bestaudio/best",
        "-o", output_filename,
        "--force-overwrites",
        reel_url
    ]
    subprocess.run(cmd, capture_output=True, text=True)

    # Salva os dados do post para o painel de TV
    post_data = {
        "url": reel_url,
        "username": username,
        "caption": post_caption if post_caption else "Confira as últimas novidades da Prefeitura Municipal de São Lourenço.",
        "updated_at": time.strftime("%d/%m/%Y às %H:%M")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)

    with open("last_video.txt", "w", encoding="utf-8") as f:
        f.write(reel_url)

    print("Vídeo e dados preparados para a TV!")

if __name__ == "__main__":
    main()
