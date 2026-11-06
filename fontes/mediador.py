"""Cliente de consulta ao Sistema Mediador (Ministério do Trabalho e Emprego).

Fonte oficial: todo instrumento coletivo (convenção, acordo ou termo
aditivo) só é válido se estiver registrado aqui.
"""
import re
from urllib.parse import quote

from . import comum, navegador
from .comum import FonteError

NOME_FONTE = "Sistema Mediador (Ministério do Trabalho e Emprego)"
BASE_URL = "https://mediador.trabalho.gov.br"
# A página inicial de "ConsultarInstColetivo" é só uma landing page; o
# formulário de critérios (CNPJ, tipo, vigência, UF) fica em "ConsultaBasica".
URL_BUSCA_MANUAL = BASE_URL + "/sistemas/mediador/ConsultarInstColetivo/ConsultaBasica"
URL_EXTRATO = BASE_URL + "/sistemas/mediador/Resumo/ResumoVisualizar?NrSolicitacao={}"

# Número da solicitação no Mediador, ex.: MR031221/2024.
PADRAO_SOLICITACAO = r"MR\d{6}/\d{4}"


def _montar_link_extrato(colunas):
    achado = re.search(PADRAO_SOLICITACAO, " ".join(colunas), re.IGNORECASE)
    if achado is None:
        return None
    return URL_EXTRATO.format(quote(achado.group(0).upper(), safe=""))


CONFIG = {
    "nome": NOME_FONTE,
    "url": URL_BUSCA_MANUAL,
    "palavras_campo": ["cnpj", "participante", "razão social", "razao social"],
    "palavras_botao": ["pesquisar", "consultar", "buscar"],
    "palavras_link_detalhe": ["visualiz", "detalh", "extrato", "resumo"],
    "padrao_registro": PADRAO_SOLICITACAO,
    "montar_link": _montar_link_extrato,
    "arquivo_html": "debug_mediador.html",
    "arquivo_print": "debug_mediador.png",
}


def buscar_por_cnpj(cnpj_bruto):
    cnpj = comum.apenas_digitos(cnpj_bruto)
    if not comum.cnpj_valido(cnpj):
        raise FonteError("CNPJ inválido. Confira o número informado.")
    return navegador.buscar(CONFIG, cnpj)
