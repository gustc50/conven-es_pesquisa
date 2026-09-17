"""Utilitários compartilhados pelos clientes de consulta a fontes externas.

Cada fonte (Mediador, SACC-DIEESE, etc.) tem seu próprio módulo com as
constantes específicas (URL, palavras-chave de campo), mas todas usam esta
mesma engine genérica: ela descobre os campos do formulário e a tabela de
resultados em tempo de execução, em vez de fixar nomes, para se adaptar
melhor a pequenas mudanças de layout dos sites públicos.
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


def _localizar_campo_por_palavras(form, palavras_chave):
    for palavra in palavras_chave:
        padrao = re.compile(palavra, re.IGNORECASE)
        campo = form.find(["input", "select", "textarea"], attrs={"name": padrao})
        if campo is not None:
            return campo
    for palavra in palavras_chave:
        padrao = re.compile(palavra, re.IGNORECASE)
        campo = form.find(["input", "select", "textarea"], attrs={"id": padrao})
        if campo is not None:
            return campo
    for label in form.find_all("label"):
        texto_label = label.get_text(" ", strip=True).lower()
        if any(palavra in texto_label for palavra in palavras_chave):
            id_destino = label.get("for")
            if id_destino:
                campo = form.find(["input", "select", "textarea"], id=id_destino)
                if campo is not None:
                    return campo
    return None


def selecionar_formulario_busca(soup, palavras_chave_campo):
    formularios = soup.find_all("form")
    for form in formularios:
        if _localizar_campo_por_palavras(form, palavras_chave_campo) is not None:
            return form
    return formularios[0] if formularios else None


def montar_dados_formulario(form, valor_cnpj, palavras_chave_campo, mensagem_campo_nao_encontrado):
    dados = {}
    for campo in form.find_all(["input", "select", "textarea"]):
        nome = campo.get("name")
        if not nome:
            continue
        if campo.name == "select":
            opcao = campo.find("option", selected=True) or campo.find("option")
            dados[nome] = opcao.get("value", "") if opcao else ""
        elif (campo.get("type") or "text").lower() in ("checkbox", "radio"):
            if campo.has_attr("checked"):
                dados[nome] = campo.get("value", "on")
        else:
            dados[nome] = campo.get("value", "")

    campo_cnpj = _localizar_campo_por_palavras(form, palavras_chave_campo)
    if campo_cnpj is None or not campo_cnpj.get("name"):
        raise FonteError(mensagem_campo_nao_encontrado)
    dados[campo_cnpj["name"]] = valor_cnpj
    return dados


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
