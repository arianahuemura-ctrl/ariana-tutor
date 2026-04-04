import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive.file']
CREDENTIALS_FILE = 'credentials.json'

def autenticar():
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f'\nAcesse esse link no navegador:\n{auth_url}\n')
            code = input('Cole o codigo que apareceu aqui: ')
            flow.fetch_token(code=code)
            creds = flow.credentials
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def buscar_ou_criar_pasta(service, nome, pasta_pai=None):
    query = f"name='{nome}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if pasta_pai:
        query += f" and '{pasta_pai}' in parents"
    resultado = service.files().list(q=query, fields='files(id, name)').execute()
    arquivos = resultado.get('files', [])
    if arquivos:
        return arquivos[0]['id']
    metadata = {'name': nome, 'mimeType': 'application/vnd.google-apps.folder'}
    if pasta_pai:
        metadata['parents'] = [pasta_pai]
    pasta = service.files().create(body=metadata, fields='id').execute()
    return pasta.get('id')

def salvar_texto_drive(conteudo, nome_arquivo, subpasta):
    service = autenticar()
    pasta_raiz_id = buscar_ou_criar_pasta(service, 'Ariana Tutor')
    pasta_id = buscar_ou_criar_pasta(service, subpasta, pasta_raiz_id)
    caminho_temp = f'/tmp/{nome_arquivo}'
    with open(caminho_temp, 'w', encoding='utf-8') as f:
        f.write(conteudo)
    metadata = {'name': nome_arquivo, 'parents': [pasta_id]}
    media = MediaFileUpload(caminho_temp, mimetype='text/plain')
    arquivo = service.files().create(
        body=metadata, media_body=media, fields='id, webViewLink'
    ).execute()
    link = arquivo.get('webViewLink')
    print(f"Salvo no Drive: {link}")
    return link

if __name__ == "__main__":
    print("Testando conexao com Google Drive...")
    link = salvar_texto_drive("Teste de conexao!", "teste.txt", "Testes")
    print(f"Funcionou! Link: {link}")