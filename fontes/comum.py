"""Utilitários compartilhados pelos clientes de consulta a fontes externas:
validação de CNPJ, leitura da tabela de resultados e download do arquivo
original. A navegação em si fica em navegador.py.
"""
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

PALAVRAS_CHAVE_ARQUIVO_ORIGINAL = ["pdf", "download", "baixar", "original", "imprimir"]
FRASES_SEM_RESULTADO = [
    "nenhum resultado",
    "nenhum registro",
    "nao foram encontrados",
    "não foram encontrados",
    "nenhuma informa",
]

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class FonteError(Exception):
    """Erro esperado ao consultar uma fonte externa (mensagem já amigável para o usuário)."""


def apenas_digitos(texto):
    return re.sub(r"\D", "", texto or "")


def cnpj_valido(cnpj):
    cnpj = apenas_digitos(cnpj)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False

    def digito_verificador(base, pesos):
        soma = sum(int(d) * p for d, p in zip(base, pesos))
        resto = soma % 11
        return "0" if resto < 2 else str(11 - resto)

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = digito_verificador(cnpj[:12], pesos1)
    d2 = digito_verificador(cnpj[:12] + d1, pesos2)
    return cnpj[-2:] == d1 + d2


def formatar_cnpj(cnpj):
    cnpj = apenas_digitos(cnpj)
    if len(cnpj) != 14:
        return cnpj
    return f"{cnpj[0:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"


def sessao_http():
    sessao = requests.Session()
    sessao.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
    )
    return sessao


def salvar_debug(nome_arquivo, texto):
    try:
        caminho = os.path.join(PASTA_PROJETO, nome_arquivo)
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto)
    except OSError:
        pass


def selecionar_tabela_resultados(soup):
    melhor_tabela = None
    melhor_pontuacao = 0
    for tabela in soup.find_all("table"):
        linhas = tabela.find_all("tr")
        if len(linhas) < 2:
            continue
        pontuacao = len(linhas)
        if tabela.find("a", href=True):
            pontuacao += 5
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_tabela = tabela
    return melhor_tabela


def extrair_resultados(tabela, url_base, palavras_chave_link_detalhe):
    cabecalhos = [th.get_text(strip=True) for th in tabela.select("thead th")]

    corpo = tabela.find("tbody")
    linhas = corpo.find_all("tr") if corpo else tabela.find_all("tr")

    if not cabecalhos and linhas:
        primeira_linha = linhas[0]
        celulas_th = primeira_linha.find_all("th")
        if celulas_th:
            cabecalhos = [c.get_text(strip=True) for c in celulas_th]
            linhas = linhas[1:]

    resultados = []
    for linha in linhas:
        celulas = linha.find_all("td")
        if not celulas:
            continue
        textos = [c.get_text(" ", strip=True) for c in celulas]

        link_detalhe = None
        for link in linha.find_all("a", href=True):
            texto_link = link.get_text(" ", strip=True).lower()
            href = link["href"]
            if href.lower().endswith(".pdf") or any(
                p in texto_link for p in palavras_chave_link_detalhe
            ):
                link_detalhe = urljoin(url_base, href)
                break
        if link_detalhe is None:
            primeiro_link = linha.find("a", href=True)
            if primeiro_link is not None:
                link_detalhe = urljoin(url_base, primeiro_link["href"])

        resultados.append({"colunas": textos, "detalhe_url": link_detalhe})

    return cabecalhos, resultados


def resolver_arquivo_original(url_detalhe, timeout=25):
    """A partir do link de um resultado, localiza e baixa o arquivo (PDF).

    Alguns links de resultado já apontam direto para o PDF; outros levam a
    uma página de detalhe/extrato do item, de onde é preciso seguir o link
    de download do arquivo original. Retorna (url_final, conteudo_bytes,
    content_type) ou (None, None, None) se não for possível localizar o PDF.
    """
    sessao = sessao_http()

    try:
        resposta = sessao.get(url_detalhe, timeout=timeout, allow_redirects=True)
        resposta.raise_for_status()
    except requests.RequestException:
        return None, None, None

    tipo = (resposta.headers.get("Content-Type") or "").lower()
    if "pdf" in tipo:
        return resposta.url, resposta.content, resposta.headers.get("Content-Type")

    soup = BeautifulSoup(resposta.text, "html.parser")
    candidato = None
    for link in soup.find_all("a", href=True):
        texto_link = link.get_text(" ", strip=True).lower()
        href = link["href"]
        if href.lower().endswith(".pdf") or any(
            p in texto_link for p in PALAVRAS_CHAVE_ARQUIVO_ORIGINAL
        ):
            candidato = urljoin(resposta.url, href)
            break

    if candidato is None:
        return None, None, None

    try:
        resposta_arquivo = sessao.get(candidato, timeout=timeout, allow_redirects=True)
        resposta_arquivo.raise_for_status()
    except requests.RequestException:
        return None, None, None

    tipo_arquivo = (resposta_arquivo.headers.get("Content-Type") or "").lower()
    if "pdf" not in tipo_arquivo and not candidato.lower().endswith(".pdf"):
        return None, None, None

    return (
        resposta_arquivo.url,
        resposta_arquivo.content,
        resposta_arquivo.headers.get("Content-Type"),
    )
