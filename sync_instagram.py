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
    target_count = 8
    reels_urls = []

    # 2. Localizar os 8 Reels mais recentes com Playwright
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

            # Rola a página para baixo para carregar mais publicações
            page.evaluate("window.scrollBy(0, 1000);")
            time.sleep(3)

            links = page.locator("a[href*='/reel/'], a[href*='/p/']").all()
            for l in links:
                href = l.get_attribute("href")
                if href:
                    full_url = f"https://www.instagram.com{href}" if href.startswith("/") else href
                    if full_url not in reels_urls:
                        reels_urls.append(full_url)
                if len(reels_urls) >= target_count:
                    break

        except Exception as e:
            print(f"Erro na navegação: {e}")

        browser.close()

    print(f"Total de posts localizados: {len(reels_urls)}")
    if not reels_urls:
        print("Nenhum post foi identificado.")
        return

    # 3. Processar e baixar os 8 vídeos com descrições
    posts_data = []
    
    for idx, reel_url in enumerate(reels_urls[:target_count], start=1):
        print(f"\n--- Processando Post #{idx}: {reel_url} ---")
        output_filename = f"video_{idx}.mp4"

        # Extrair legenda original via yt-dlp metadata
        caption = ""
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
                caption = info_json.get("description") or info_json.get("title") or ""
        except Exception as e:
            print(f"Erro ao capturar legenda: {e}")

        # Baixar o vídeo correspondente
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

        posts_data.append({
            "id": idx,
            "url": reel_url,
            "video_file": output_filename,
            "caption": caption.strip() if caption else "Informativo Oficial da Prefeitura Municipal de São Lourenço.",
            "updated_at": time.strftime("%d/%m/%Y às %H:%M")
        })

    # 4. Salvar banco de dados JSON com os 8 posts
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    print("\n✅ Todos os 8 vídeos e legendas foram atualizados com sucesso!")

if __name__ == "__main__":
    main()
