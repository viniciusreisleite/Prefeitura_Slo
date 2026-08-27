import os
import json
from bs4 import BeautifulSoup
from curl_cffi import requests
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

# 2. Acessar perfil mascarando TLS como Chrome real
username = "prefeituraslmg"
profile_url = f"https://imginn.com/{username}/"
print(f"Buscando publicações em {profile_url} com impersonação de navegador...")

session = requests.Session(impersonate="chrome120")
response = session.get(profile_url, timeout=25)

if response.status_code != 200:
    raise Exception(f"Erro ao acessar perfil: status {response.status_code}")

soup = BeautifulSoup(response.text, 'html.parser')
items = soup.find_all('div', class_='item')

video_url = None
post_id = None

for item in items:
    link_tag = item.find('a', href=True)
    if link_tag and ('/p/' in link_tag['href']):
        post_path = link_tag['href']
        post_page_url = f"https://imginn.com{post_path}"
        print(f"Verificando publicação: {post_page_url}")
        
        post_resp = session.get(post_page_url, timeout=25)
        post_soup = BeautifulSoup(post_resp.text, 'html.parser')
        
        video_tag = post_soup.find('video')
        download_btn = post_soup.find('a', class_='download')
        
        if video_tag and video_tag.get('src'):
            video_url = video_tag['src']
        elif download_btn and download_btn.get('href') and '.mp4' in download_btn['href']:
            video_url = download_btn['href']
        
        if video_url:
            post_id = post_path.strip('/').split('/')[-1]
            break

# 3. Fazer download do arquivo de vídeo
if video_url:
    print(f"Vídeo encontrado! Baixando arquivo mp4...")
    video_file = f"video_{post_id}.mp4"
    
    vid_data = session.get(video_url, timeout=60)
    with open(video_file, 'wb') as f:
        f.write(vid_data.content)
                
    # 4. Enviar para a pasta do Google Drive
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
    print("Nenhum vídeo recente foi encontrado entre as primeiras postagens.")
