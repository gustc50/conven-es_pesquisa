"""Cliente de consulta ao SACC-DIEESE (Sistema de Acompanhamento de
Contratações Coletivas), base mantida pelo DIEESE como complemento de
pesquisa. Não substitui o Mediador — que é a fonte oficial —, mas pode
trazer resultados adicionais.

Diferente do Mediador, o SACC não anuncia publicamente suporte a busca por
CNPJ (costuma ser organizado por sindicato/categoria e UF), então essa
fonte pode legitimamente não encontrar o campo de CNPJ — nesse caso o erro
retornado já explica isso, em vez de indicar uma falha de verdade.
"""
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from . import comum
from .comum import FonteError

NOME_FONTE = "SACC-DIEESE"
BASE_URL = "https://www.dieese.org.br"
CAMINHO_BUSCA = "/sacc/pesquisa.do?method=setup"
URL_BUSCA_MANUAL = BASE_URL + CAMINHO_BUSCA

PALAVRAS_CHAVE_CAMPO_CNPJ = ["cnpj", "participante", "documento", "razaosocial", "empresa"]
PALAVRAS_CHAVE_LINK_DETALHE = ["visualiz", "detalh", "consultar", "exibir"]
ARQUIVO_DEBUG = "debug_ultima_consulta_dieese.html"


def buscar_por_cnpj(cnpj_bruto, timeout=25):
    """Busca instrumentos coletivos pelo CNPJ no SACC-DIEESE.

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
            "Não foi possível acessar o SACC-DIEESE. "
            "Verifique sua conexão com a internet e tente novamente."
        ) from exc

    soup_form = BeautifulSoup(resposta_form.text, "html.parser")
    form = comum.selecionar_formulario_busca(soup_form, PALAVRAS_CHAVE_CAMPO_CNPJ)
    if form is None:
        raise FonteError(
            "O formulário de busca do SACC-DIEESE não foi encontrado. "
            "Use a busca manual abaixo."
        )

    dados = comum.montar_dados_formulario(
        form,
        cnpj,
        PALAVRAS_CHAVE_CAMPO_CNPJ,
        "O SACC-DIEESE não parece ter um campo de busca por CNPJ nesta página "
        "(essa base costuma ser organizada por sindicato/categoria e UF, não "
        "por CNPJ). Use a busca manual abaixo.",
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
        raise FonteError("Não foi possível concluir a consulta no SACC-DIEESE.") from exc

    comum.salvar_debug(ARQUIVO_DEBUG, resposta.text)

    texto_resposta = resposta.text.lower()
    if "captcha" in texto_resposta:
        raise FonteError(
            "O SACC-DIEESE exigiu verificação adicional (captcha) para esta "
            "consulta. Faça a busca manualmente pelo link abaixo."
        )
    if "senha" in texto_resposta and ("login" in texto_resposta or "usuário" in texto_resposta):
        raise FonteError(
            "O SACC-DIEESE pediu login para esta consulta "
            "(parte do conteúdo pode exigir cadastro). Use a busca manual abaixo."
        )

    soup_resultado = BeautifulSoup(resposta.text, "html.parser")
    tabela = comum.selecionar_tabela_resultados(soup_resultado)
    if tabela is None:
        if any(frase in texto_resposta for frase in comum.FRASES_SEM_RESULTADO):
            return [], [], resposta.url
        raise FonteError(
            "A página de resultados do SACC-DIEESE não veio no formato esperado. "
            "Use a busca manual abaixo — o arquivo "
            f"{ARQUIVO_DEBUG}, salvo na pasta do programa, ajuda a diagnosticar "
            "o que aconteceu."
        )

    cabecalhos, resultados = comum.extrair_resultados(
        tabela, resposta.url, PALAVRAS_CHAVE_LINK_DETALHE
    )
    if not resultados and not any(frase in texto_resposta for frase in comum.FRASES_SEM_RESULTADO):
        raise FonteError(
            "Não foi possível interpretar a tabela de resultados do SACC-DIEESE. "
            "Use a busca manual abaixo — o arquivo "
            f"{ARQUIVO_DEBUG}, salvo na pasta do programa, ajuda a diagnosticar "
            "o que aconteceu."
        )

    return cabecalhos, resultados, resposta.url
