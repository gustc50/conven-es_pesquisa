"""Cliente de consulta ao SACC-DIEESE (Sistema de Acompanhamento de
Contratações Coletivas), base mantida pelo DIEESE como complemento de
pesquisa. Não substitui o Mediador, que é a fonte oficial.

Diferente do Mediador, o SACC não anuncia publicamente busca por CNPJ
(costuma ser organizado por sindicato/categoria e UF), então essa fonte pode
legitimamente não encontrar o campo de CNPJ.
"""
from . import comum, navegador
from .comum import FonteError

NOME_FONTE = "SACC-DIEESE"
BASE_URL = "https://www.dieese.org.br"
CAMINHO_BUSCA = "/sacc/pesquisa.do?method=setup"
URL_BUSCA_MANUAL = BASE_URL + CAMINHO_BUSCA

CONFIG = {
    "nome": NOME_FONTE,
    "url": URL_BUSCA_MANUAL,
    "palavras_campo": ["cnpj", "participante", "empresa", "razao social", "razão social"],
    "palavras_botao": ["pesquisar", "consultar", "buscar"],
    "palavras_link_detalhe": ["visualiz", "detalh", "consultar", "exibir"],
    "arquivo_html": "debug_dieese.html",
    "arquivo_print": "debug_dieese.png",
}


def buscar_por_cnpj(cnpj_bruto, visivel=False):
    cnpj = comum.apenas_digitos(cnpj_bruto)
    if not comum.cnpj_valido(cnpj):
        raise FonteError("CNPJ inválido. Confira o número informado.")
    return navegador.buscar(CONFIG, cnpj, visivel=visivel)
