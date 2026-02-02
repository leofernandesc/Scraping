import requests
from bs4 import BeautifulSoup
import json
import os
import time

# --- CONFIGURAÇÕES ---
URL = "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes"  # Coloque a URL do site aqui
ARQUIVO_HISTORICO = "editais_vistos.json"

# IMPORTANTE: Você deve inspecionar o site para descobrir o seletor correto.
# Exemplo: 'div.edital-item h3' ou 'a.link-edital'
SELETOR_CSS_EDITAL = "a.external-link"

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
        # Convertemos para lista para poder salvar em JSON
        json.dump(list(novos_dados), f, ensure_ascii=False, indent=4)

def verificar_novos_editais():
    print(f"Verificando: {URL}...")
    
    try:
        response = requests.get(URL, headers=headers)
        response.raise_for_status() # Para o script se der erro 404 ou 500
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar o site: {e}")
        return

    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Busca todos os elementos que correspondem ao seletor
    elementos_encontrados = soup.select(SELETOR_CSS_EDITAL)
    
    if not elementos_encontrados:
        print("Nenhum elemento encontrado. Verifique o SELETOR_CSS.")
        return

    # Extrai o texto (ou link) para identificar o edital
    editais_atuais = set()
    for item in elementos_encontrados:
        # Aqui pegamos o texto limpo. Se preferir o link, use item['href']
        titulo = item.get_text(strip=True)
        if titulo:
            editais_atuais.add(titulo)

    # Compara com o histórico
    historico = carregar_historico()
    novos_editais = editais_atuais - historico

    if novos_editais:
        print(f"\n🚨 {len(novos_editais)} NOVO(S) EDITAL(IS) ENCONTRADO(S)!\n")
        for edital in novos_editais:
            print(f" - {edital}")
        
        # Atualiza o histórico com tudo o que foi visto hoje
        historico_atualizado = historico.union(novos_editais)
        salvar_historico(historico_atualizado)
    else:
        print("Nenhum edital novo encontrado neste momento.")

if __name__ == "__main__":
    verificar_novos_editais()