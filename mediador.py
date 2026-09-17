"""Cliente de consulta ao Sistema Mediador (Ministério do Trabalho e Emprego).

Busca instrumentos coletivos (convenções, acordos e termos aditivos) pelo
CNPJ do sindicato, descobrindo os campos do formulário oficial em tempo de
execução (em vez de fixar nomes de campos), já que o layout do site público
pode mudar.
"""
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://mediador.trabalho.gov.br"
CAMINHO_BUSCA = "/sistemas/mediador/ConsultarInstColetivo"
URL_BUSCA_MANUAL = BASE_URL + CAMINHO_BUSCA

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

PALAVRAS_CHAVE_CAMPO_CNPJ = ["cnpj", "participante", "documento", "razaosocial"]
PALAVRAS_CHAVE_LINK_PDF = ["pdf", "visualiz", "download", "baixar"]


class MediadorError(Exception):
    """Erro esperado ao consultar o site oficial (mensagem já amigável para o usuário)."""


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


def _sessao_http():
    sessao = requests.Session()
    sessao.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept-Language": "pt-BR,pt;q=0.9",
        }
    )
    return sessao


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


def _montar_dados_formulario(form, cnpj):
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

    campo_cnpj = _localizar_campo_por_palavras(form, PALAVRAS_CHAVE_CAMPO_CNPJ)
    if campo_cnpj is None or not campo_cnpj.get("name"):
        raise MediadorError(
            "Não foi possível localizar o campo de CNPJ no formulário do site oficial "
            "(o layout pode ter mudado). Use a busca manual abaixo."
        )
    dados[campo_cnpj["name"]] = cnpj
    return dados


def _selecionar_tabela_resultados(soup):
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


def _extrair_resultados(tabela, url_base):
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

        link_pdf = None
        for link in linha.find_all("a", href=True):
            texto_link = link.get_text(" ", strip=True).lower()
            href = link["href"]
            if href.lower().endswith(".pdf") or any(
                p in texto_link for p in PALAVRAS_CHAVE_LINK_PDF
            ):
                link_pdf = urljoin(url_base, href)
                break
        if link_pdf is None:
            primeiro_link = linha.find("a", href=True)
            if primeiro_link is not None:
                link_pdf = urljoin(url_base, primeiro_link["href"])

        resultados.append({"colunas": textos, "pdf_url": link_pdf})

    return cabecalhos, resultados


def buscar_por_cnpj(cnpj_bruto, timeout=25):
    """Busca instrumentos coletivos pelo CNPJ do sindicato.

    Retorna (cabecalhos, resultados, url_da_consulta).
    Lança MediadorError com mensagem amigável em caso de falha esperada.
    """
    cnpj = apenas_digitos(cnpj_bruto)
    if not cnpj_valido(cnpj):
        raise MediadorError("CNPJ inválido. Confira o número informado.")

    sessao = _sessao_http()

    try:
        resposta_form = sessao.get(URL_BUSCA_MANUAL, timeout=timeout)
        resposta_form.raise_for_status()
    except requests.RequestException as exc:
        raise MediadorError(
            "Não foi possível acessar o site oficial do Mediador. "
            "Verifique sua conexão com a internet e tente novamente."
        ) from exc

    soup_form = BeautifulSoup(resposta_form.text, "html.parser")
    form = soup_form.find("form")
    if form is None:
        raise MediadorError(
            "O formulário de busca do site oficial não foi encontrado "
            "(o site pode ter mudado de layout). Use a busca manual abaixo."
        )

    dados = _montar_dados_formulario(form, cnpj)
    acao = form.get("action") or CAMINHO_BUSCA
    url_acao = urljoin(resposta_form.url, acao)
    metodo = (form.get("method") or "post").lower()

    try:
        if metodo == "get":
            resposta = sessao.get(url_acao, params=dados, timeout=timeout)
        else:
            resposta = sessao.post(url_acao, data=dados, timeout=timeout)
        resposta.raise_for_status()
    except requests.RequestException as exc:
        raise MediadorError(
            "Não foi possível concluir a consulta no site oficial do Mediador."
        ) from exc

    texto_resposta = resposta.text.lower()
    if "captcha" in texto_resposta:
        raise MediadorError(
            "O site oficial exigiu verificação adicional (captcha) para esta consulta. "
            "Faça a busca manualmente pelo link abaixo."
        )

    soup_resultado = BeautifulSoup(resposta.text, "html.parser")
    tabela = _selecionar_tabela_resultados(soup_resultado)
    if tabela is None:
        return [], [], resposta.url

    cabecalhos, resultados = _extrair_resultados(tabela, resposta.url)
    return cabecalhos, resultados, resposta.url
