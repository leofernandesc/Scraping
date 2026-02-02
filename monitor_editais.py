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

        links = driver.find_elements(By.CSS_SELECTOR, "#editais-abertos_content h2 a")

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
    novos_itens_total = set()

    novos_capes = buscar_capes_cnpq({
        "nome": "CAPES",
        "url": "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes",
        "seletor": "a.external-link, a.internal-link"
    })
    
    diff_capes = novos_capes - historico
    if diff_capes:
        qtd = len(diff_capes)
        print(f" -> {qtd} novos na CAPES.")
        enviar_whatsapp(f"*ATENCAO: {qtd} Novo(s) na CAPES*\n\nConfira: https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes")
        novos_itens_total.update(diff_capes)
    else:
        print(" -> Sem novidades na CAPES.")

    novos_cnpq = buscar_capes_cnpq({
        "nome": "CNPq",
        "url": "http://memoria2.cnpq.br/web/guest/chamadas-publicas?p_p_id=resultadosportlet_WAR_resultadoscnpqportlet_INSTANCE_0ZaM&filtro=abertas/#void",
        "seletor": ".content h4"
    })

    diff_cnpq = novos_cnpq - historico
    if diff_cnpq:
        qtd = len(diff_cnpq)
        print(f" -> {qtd} novos no CNPq.")
        enviar_whatsapp(f"*ATENCAO: {qtd} Novo(s) no CNPq*\n\nConfira: http://memoria2.cnpq.br/web/guest/chamadas-publicas")
        novos_itens_total.update(diff_cnpq)
    else:
        print(" -> Sem novidades no CNPq.")

    novos_fapeam = buscar_fapeam_selenium()
    
    diff_fapeam = novos_fapeam - historico
    if diff_fapeam:
        qtd = len(diff_fapeam)
        print(f" -> {qtd} novos na FAPEAM.")
        enviar_whatsapp(f"*ATENCAO: {qtd} Novo(s) na FAPEAM*\n\nConfira: https://www.fapeam.am.gov.br/editais/?aba=editais-abertos")
        novos_itens_total.update(diff_fapeam)
    else:
        print(" -> Sem novidades na FAPEAM.")

    if novos_itens_total:
        historico_atualizado = historico.union(novos_itens_total)
        salvar_historico(historico_atualizado)
        print("\nHistórico atualizado.")

if __name__ == "__main__":
    verificar_novos_editais()