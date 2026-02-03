import requests
from bs4 import BeautifulSoup
import json
import os
import urllib.parse
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

load_dotenv()

ARQUIVO_HISTORICO = "editais_vistos.json"
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
            try:
                dados = json.load(f)
                if isinstance(dados, dict):
                    return {k: set(v) for k, v in dados.items()}
            except json.JSONDecodeError:
                pass
    return {}

def salvar_historico(historico_sets):
    historico_listas = {k: list(v) for k, v in historico_sets.items()}
    with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as f:
        json.dump(historico_listas, f, ensure_ascii=False, indent=4)

def enviar_whatsapp(mensagem):
    msg_codificada = urllib.parse.quote(mensagem)
    url_callmebot = f"https://api.callmebot.com/whatsapp.php?phone={SEU_TELEFONE}&text={msg_codificada}&apikey={SUA_API_KEY}"
    try:
        requests.get(url_callmebot, timeout=10)
    except Exception:
        pass

def buscar_capes_cnpq(site):
    editais_encontrados = set()
    try:
        response = requests.get(site["url"], headers=headers, timeout=20)
        soup = BeautifulSoup(response.content, 'html.parser')
        elementos = soup.select(site["seletor"])
        
        for item in elementos:
            titulo = item.get_text(strip=True)
            if titulo and len(titulo) > 2:
                editais_encontrados.add(titulo)
    except Exception as e:
        print(f"Erro em {site['nome']}: {e}")
    
    return editais_encontrados

def buscar_fapeam_selenium():
    editais_encontrados = set()
    
    chrome_options = Options()
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--log-level=3")
    
    driver = None
    try:
        servico = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        
        url = "https://www.fapeam.am.gov.br/editais/?aba=editais-abertos"
        driver.get(url)

        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "editais-abertos_content")))

        links = driver.find_elements(By.CSS_SELECTOR, ".editais-abertos h2 a")

        for link in links:
            titulo = link.text.strip()
            if titulo and "{{post_title}}" not in titulo:
                editais_encontrados.add(titulo)

    except Exception as e:
        print(f"Erro no Selenium FAPEAM: {e}")
    finally:
        if driver:
            driver.quit()

    return editais_encontrados

def verificar_novos_editais():
    print("Iniciando verificação...")
    historico = carregar_historico()
    houve_alteracao = False

    sites_config = [
        {
            "nome": "CAPES",
            "url": "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes",
            "seletor": "a.external-link, a.internal-link",
            "metodo": "requests"
        },
        {
            "nome": "CNPq",
            "url": "http://memoria2.cnpq.br/web/guest/chamadas-publicas?p_p_id=resultadosportlet_WAR_resultadoscnpqportlet_INSTANCE_0ZaM&filtro=abertas/#void",
            "seletor": ".content h4",
            "metodo": "requests"
        },
        {
            "nome": "FAPEAM",
            "url": "https://www.fapeam.am.gov.br/editais/?aba=editais-abertos",
            "metodo": "selenium"
        }
    ]

    for site in sites_config:
        nome_site = site["nome"]
        
        if nome_site not in historico:
            historico[nome_site] = set()

        if site["metodo"] == "requests":
            editais_atuais = buscar_capes_cnpq(site)
        else:
            editais_atuais = buscar_fapeam_selenium()

        novos_deste_site = editais_atuais - historico[nome_site]

        if novos_deste_site:
            qtd = len(novos_deste_site)
            print(f" -> {qtd} novos em {nome_site}.")
            
            mensagem = f"*ATENCAO: {qtd} Novo(s) em {nome_site}*\n\nConfira: {site['url']}"
            enviar_whatsapp(mensagem)
            
            historico[nome_site].update(novos_deste_site)
            houve_alteracao = True
        else:
            print(f" -> Sem novidades em {nome_site}.")

    if houve_alteracao:
        salvar_historico(historico)
        print("\nHistórico atualizado.")

if __name__ == "__main__":
    verificar_novos_editais()