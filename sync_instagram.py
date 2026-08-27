import os
import json
import requests
from bs4 import BeautifulSoup
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

# 2. Buscar postagens públicas via Imginn
username = "prefeituraslmg"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

profile_url = f"https://imginn.com/{username}/"
print(f"Buscando publicações em {profile_url}...")

response = requests.get(profile_url, headers=headers, timeout=20)
if response.status_code != 200:
    raise Exception(f"Erro ao acessar perfil: status code {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')
items = soup.find_all('div', class_='item')

video_url = None
post_id = None

for item in items:
    # Verifica se o post é do tipo vídeo
    icon_video = item.find('i', class_='icon-video') or item.find('span', class_='video')
    link_tag = item.find('a', href=True)
    
    if link_tag and ('/p/' in link_tag['href']):
        post_path = link_tag['href']
        post_page_url = f"https://imginn.com{post_path}"
        print(f"Checando post: {post_page_url}")
        
        post_resp = requests.get(post_page_url, headers=headers, timeout=20)
        post_soup = BeautifulSoup(post_resp.text, 'html.parser')
        
        # Procura a tag <video> ou link de download direto do mp4
        video_tag = post_soup.find('video')
        download_btn = post_soup.find('a', class_='download')
        
        if video_tag and video_tag.get('src'):
            video_url = video_tag['src']
        elif download_btn and download_btn.get('href') and '.mp4' in download_btn['href']:
            video_url = download_btn['href']
        
        if video_url:
            post_id = post_path.strip('/').split('/')[-1]
            break

# 3. Baixar o arquivo de vídeo e enviar ao Drive
if video_url:
    print(f"Vídeo encontrado! Baixando mídia...")
    video_file = f"video_{post_id}.mp4"
    
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
    print("Nenhum vídeo recente encontrado no perfil.")
