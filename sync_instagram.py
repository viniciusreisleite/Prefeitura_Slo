import os
import json
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

    # 2. Localizar o link do post mais recente
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
            else:
                first_post = page.locator("a[href*='/p/']").first
                if first_post.count() > 0:
                    href = first_post.get_attribute("href")
                    reel_url = f"https://www.instagram.com{href}" if href.startswith("/") else href

        except Exception as e:
            print(f"Erro na navegação: {e}")

        browser.close()

    if not reel_url:
        print("Nenhum post/reel foi identificado.")
        return

    print(f"Post detectado: {reel_url}")

    # 3. Obter a descrição/legenda original diretamente via yt-dlp
    post_caption = ""
    try:
        desc_cmd = [
            "yt-dlp",
            "--cookies", cookie_file,
            "--no-check-certificates",
            "--dump-json",
            reel_url
        ]
        info_res = subprocess.run(desc_cmd, capture_output=True, text=True)
        if info_res.stdout:
            info_json = json.loads(info_res.stdout)
            post_caption = info_json.get("description") or info_json.get("title") or ""
            print(f"Legenda extraída com sucesso! ({len(post_caption)} caracteres)")
    except Exception as e:
        print(f"Erro ao extrair legenda via metadata: {e}")

    # 4. Baixar o vídeo e mesclar no latest.mp4
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

    # 5. Salvar os dados para a TV
    post_data = {
        "url": reel_url,
        "username": username,
        "caption": post_caption.strip() if post_caption else "Confira as últimas novidades da Prefeitura Municipal de São Lourenço.",
        "updated_at": time.strftime("%d/%m/%Y às %H:%M")
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)

    with open("last_video.txt", "w", encoding="utf-8") as f:
        f.write(reel_url)

    print("Painel atualizado com vídeo e texto originais!")

if __name__ == "__main__":
    main()
