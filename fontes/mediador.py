"""Cliente de consulta ao Sistema Mediador (Ministério do Trabalho e Emprego).

Fonte oficial: todo instrumento coletivo (convenção, acordo ou termo
aditivo) só é válido se estiver registrado aqui.
"""
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from . import comum
from .comum import FonteError

NOME_FONTE = "Sistema Mediador (Ministério do Trabalho e Emprego)"
BASE_URL = "https://mediador.trabalho.gov.br"
# A página inicial de "ConsultarInstColetivo" é só uma landing page; o
# formulário de filtros (CNPJ, tipo, vigência, UF) fica em "ConsultaBasica".
CAMINHO_BUSCA = "/sistemas/mediador/ConsultarInstColetivo/ConsultaBasica"
URL_BUSCA_MANUAL = BASE_URL + CAMINHO_BUSCA

PALAVRAS_CHAVE_CAMPO_CNPJ = ["cnpj", "participante", "documento", "razaosocial"]
PALAVRAS_CHAVE_LINK_DETALHE = ["visualiz", "detalh", "extrato", "consultar"]
ARQUIVO_DEBUG = "debug_ultima_consulta_mediador.html"


def buscar_por_cnpj(cnpj_bruto, timeout=25):
    """Busca instrumentos coletivos pelo CNPJ do sindicato no Mediador.

    Retorna (cabecalhos, resultados, url_da_consulta).
    Lança FonteError com mensagem amigável em caso de falha esperada.
    """
    cnpj = comum.apenas_digitos(cnpj_bruto)
    if not comum.cnpj_valido(cnpj):
        raise FonteError("CNPJ inválido. Confira o número informado.")

    sessao = comum.sessao_http()

    try:
        resposta_form = sessao.get(URL_BUSCA_MANUAL, timeout=timeout)
        resposta_form.raise_for_status()
    except requests.RequestException as exc:
        raise FonteError(
            "Não foi possível acessar o Sistema Mediador. "
            "Verifique sua conexão com a internet e tente novamente."
        ) from exc

    soup_form = BeautifulSoup(resposta_form.text, "html.parser")
    form = comum.selecionar_formulario_busca(soup_form, PALAVRAS_CHAVE_CAMPO_CNPJ)
    if form is None:
        raise FonteError(
            "O formulário de busca do Mediador não foi encontrado "
            "(o site pode ter mudado de layout). Use a busca manual abaixo."
        )

    dados = comum.montar_dados_formulario(
        form,
        cnpj,
        PALAVRAS_CHAVE_CAMPO_CNPJ,
        "Não foi possível localizar o campo de CNPJ no formulário do Mediador "
        "(o layout pode ter mudado). Use a busca manual abaixo.",
    )
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
        raise FonteError("Não foi possível concluir a consulta no Mediador.") from exc

    comum.salvar_debug(ARQUIVO_DEBUG, resposta.text)

    texto_resposta = resposta.text.lower()
    if "captcha" in texto_resposta:
        raise FonteError(
            "O Mediador exigiu verificação adicional (captcha) para esta consulta. "
            "Faça a busca manualmente pelo link abaixo."
        )

    soup_resultado = BeautifulSoup(resposta.text, "html.parser")
    tabela = comum.selecionar_tabela_resultados(soup_resultado)
    if tabela is None:
        if any(frase in texto_resposta for frase in comum.FRASES_SEM_RESULTADO):
            return [], [], resposta.url
        raise FonteError(
            "A página de resultados do Mediador não veio no formato esperado "
            "(o layout pode ter mudado). Use a busca manual abaixo — o arquivo "
            f"{ARQUIVO_DEBUG}, salvo na pasta do programa, ajuda a diagnosticar "
            "o que aconteceu."
        )

    cabecalhos, resultados = comum.extrair_resultados(
        tabela, resposta.url, PALAVRAS_CHAVE_LINK_DETALHE
    )
    if not resultados and not any(frase in texto_resposta for frase in comum.FRASES_SEM_RESULTADO):
        raise FonteError(
            "Não foi possível interpretar a tabela de resultados do Mediador "
            "(o layout pode ter mudado). Use a busca manual abaixo — o arquivo "
            f"{ARQUIVO_DEBUG}, salvo na pasta do programa, ajuda a diagnosticar "
            "o que aconteceu."
        )

    return cabecalhos, resultados, resposta.url
