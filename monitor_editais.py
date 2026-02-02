import requests
from bs4 import BeautifulSoup
import json
import os
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

URL = "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes"
ARQUIVO_HISTORICO = "editais_vistos.json"
SELETOR_CSS_EDITAL = "a.external-link"

SEU_TELEFONE = os.getenv("TELEFONE")
SUA_API_KEY = os.getenv("API_KEY")

if not SEU_TELEFONE or not SUA_API_KEY:
    print("ERRO: Configure o arquivo .env com TELEFONE e API_KEY")
    exit()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def carregar_historico():
    if os.path.exists(ARQUIVO_HISTORICO):
        with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def salvar_historico(novos_dados):
    with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
        json.dump(list(novos_dados), f, ensure_ascii=False, indent=4)

def enviar_whatsapp(mensagem):
    msg_codificada = urllib.parse.quote(mensagem)
    url_callmebot = f"https://api.callmebot.com/whatsapp.php?phone={SEU_TELEFONE}&text={msg_codificada}&apikey={SUA_API_KEY}"
    
    try:
        requests.get(url_callmebot, timeout=10)
    except Exception:
        pass

def verificar_novos_editais():
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    elementos_encontrados = soup.select(SELETOR_CSS_EDITAL)
    
    if not elementos_encontrados:
        return

    editais_atuais = set()
    for item in elementos_encontrados:
        titulo = item.get_text(strip=True)
        if titulo:
            editais_atuais.add(titulo)

    historico = carregar_historico()
    novos_editais = editais_atuais - historico

    if novos_editais:
        qtd = len(novos_editais)
        
        mensagem_zap = f"*ATENCAO: {qtd} Novo(s) Edital(is) Encontrado(s)*\n\n"
        mensagem_zap += f"Confira no site: {URL}"
        
        enviar_whatsapp(mensagem_zap)
        
        historico_atualizado = historico.union(novos_editais)
        salvar_historico(historico_atualizado)

if __name__ == "__main__":
    verificar_novos_editais()