"""Cliente de consulta ao Sistema Mediador (Ministério do Trabalho e Emprego).

Fonte oficial: todo instrumento coletivo (convenção, acordo ou termo
aditivo) só é válido se estiver registrado aqui.
"""
from . import comum, navegador
from .comum import FonteError

NOME_FONTE = "Sistema Mediador (Ministério do Trabalho e Emprego)"
BASE_URL = "https://mediador.trabalho.gov.br"
# A página inicial de "ConsultarInstColetivo" é só uma landing page; o
# formulário de filtros (CNPJ, tipo, vigência, UF) fica em "ConsultaBasica".
CAMINHO_BUSCA = "/sistemas/mediador/ConsultarInstColetivo/ConsultaBasica"
URL_BUSCA_MANUAL = BASE_URL + CAMINHO_BUSCA

CONFIG = {
    "nome": NOME_FONTE,
    "url": URL_BUSCA_MANUAL,
    "palavras_campo": ["cnpj", "participante", "razao social", "razão social"],
    "palavras_botao": ["pesquisar", "consultar", "buscar"],
    "palavras_link_detalhe": ["visualiz", "detalh", "extrato", "consultar"],
    "arquivo_html": "debug_mediador.html",
    "arquivo_print": "debug_mediador.png",
}


def buscar_por_cnpj(cnpj_bruto, visivel=False):
    cnpj = comum.apenas_digitos(cnpj_bruto)
    if not comum.cnpj_valido(cnpj):
        raise FonteError("CNPJ inválido. Confira o número informado.")
    return navegador.buscar(CONFIG, cnpj, visivel=visivel)
