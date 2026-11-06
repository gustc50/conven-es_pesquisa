"""Utilitários compartilhados: validação de CNPJ e leitura da tabela de
resultados. A navegação em si fica em navegador.py.
"""
import os
import re
from urllib.parse import urljoin, urlparse

FRASES_SEM_RESULTADO = [
    "nenhum resultado",
    "nenhum registro",
    "nao foram encontrados",
    "não foram encontrados",
    "nenhuma informa",
]

PASTA_PROJETO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_SELETOR_CAMPOS_FORMULARIO = "input[type=text], input:not([type]), select, textarea"


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


def salvar_debug(nome_arquivo, texto):
    try:
        caminho = os.path.join(PASTA_PROJETO, nome_arquivo)
        with open(caminho, "w", encoding="utf-8") as arquivo:
            arquivo.write(texto)
    except OSError:
        pass


def _texto_do_link(link):
    return " ".join(
        [link.get_text(" ", strip=True), link.get("href", ""), link.get("onclick", "")]
    ).lower()


def _tem_link_de_detalhe(tabela, palavras_chave_link_detalhe):
    return any(
        any(p in _texto_do_link(link) for p in palavras_chave_link_detalhe)
        for link in tabela.find_all("a")
    )


def _tem_evidencia_de_resultado(tabela, palavras_chave_link_detalhe, padrao_registro):
    if _tem_link_de_detalhe(tabela, palavras_chave_link_detalhe):
        return True
    return bool(
        padrao_registro
        and re.search(padrao_registro, tabela.get_text(" "), re.IGNORECASE)
    )


def selecionar_tabela_resultados(soup, palavras_chave_link_detalhe, padrao_registro=None):
    """Escolhe a tabela que mais parece a lista de resultados.

    Retorna (tabela, com_evidencia). Sites antigos usam tabelas também para
    diagramar o formulário de critérios e o rodapé, então a busca vai do
    critério mais exigente ao mais tolerante:
    1. tabela "folha", sem campos de formulário, com link de detalhe ou nº de registro;
    2. tabela "folha", sem campos de formulário;
    3. qualquer tabela.
    """
    def eh_folha_sem_formulario(tabela):
        return (
            tabela.find("table") is None
            and tabela.select_one(_SELETOR_CAMPOS_FORMULARIO) is None
        )

    passadas = [
        lambda t: eh_folha_sem_formulario(t)
        and _tem_evidencia_de_resultado(t, palavras_chave_link_detalhe, padrao_registro),
        eh_folha_sem_formulario,
        lambda t: True,
    ]
    for indice, aceita in enumerate(passadas):
        melhor_tabela = None
        melhor_pontuacao = 0
        for tabela in soup.find_all("table"):
            if not aceita(tabela):
                continue
            pontuacao = len([tr for tr in tabela.find_all("tr") if tr.find("td")])
            if pontuacao > melhor_pontuacao:
                melhor_pontuacao = pontuacao
                melhor_tabela = tabela
        if melhor_tabela is not None:
            return melhor_tabela, indice == 0
    return None, False


def _url_do_link(link, url_base):
    """Extrai a URL de destino de um link, inclusive de href/onclick em JavaScript."""
    href = (link.get("href") or "").strip()
    if href and not href.lower().startswith(("javascript:", "#")):
        candidato = urljoin(url_base, href)
    else:
        trecho = re.search(r"['\"]([^'\"]*[/?][^'\"]*)['\"]", href + " " + (link.get("onclick") or ""))
        if trecho is None:
            return None
        candidato = urljoin(url_base, trecho.group(1))

    if urlparse(candidato).scheme not in ("http", "https"):
        return None
    return candidato


def _eh_celula_de_acao(celula, palavras_chave_link_detalhe):
    if celula.find("a") is None:
        return False
    texto = celula.get_text(" ", strip=True)
    texto_links = " ".join(a.get_text(" ", strip=True) for a in celula.find_all("a")).strip()
    if texto != texto_links:
        return False
    return not texto or any(p in texto.lower() for p in palavras_chave_link_detalhe)


def _colunas_de_acao(linhas, palavras_chave_link_detalhe):
    """Índices das colunas que só têm links de ação (ex.: "Visualizar"). No
    app elas viram o botão de abrir o extrato, então não aparecem como texto."""
    if not linhas:
        return set()
    total_colunas = max(len(linha.find_all("td")) for linha in linhas)
    colunas = set()
    for indice in range(total_colunas):
        celulas = [
            linha.find_all("td")[indice]
            for linha in linhas
            if len(linha.find_all("td")) > indice
        ]
        if celulas and all(
            _eh_celula_de_acao(celula, palavras_chave_link_detalhe) for celula in celulas
        ):
            colunas.add(indice)
    return colunas


def extrair_resultados(tabela, url_base, palavras_chave_link_detalhe):
    cabecalhos = [th.get_text(strip=True) for th in tabela.select("thead th")]

    corpo = tabela.find("tbody")
    linhas = corpo.find_all("tr") if corpo else tabela.find_all("tr")

    if not cabecalhos and linhas:
        celulas_th = linhas[0].find_all("th")
        if celulas_th:
            cabecalhos = [c.get_text(strip=True) for c in celulas_th]
            linhas = linhas[1:]

    linhas = [linha for linha in linhas if linha.find_all("td")]
    colunas_de_acao = _colunas_de_acao(linhas, palavras_chave_link_detalhe)
    if cabecalhos:
        cabecalhos = [c for i, c in enumerate(cabecalhos) if i not in colunas_de_acao]

    resultados = []
    for linha in linhas:
        celulas = linha.find_all("td")
        textos = [
            c.get_text(" ", strip=True)
            for i, c in enumerate(celulas)
            if i not in colunas_de_acao
        ]

        links = linha.find_all("a")
        links_detalhe = [
            link
            for link in links
            if any(p in _texto_do_link(link) for p in palavras_chave_link_detalhe)
        ]
        link_detalhe = None
        for link in links_detalhe + links:
            link_detalhe = _url_do_link(link, url_base)
            if link_detalhe:
                break

        resultados.append({"colunas": textos, "detalhe_url": link_detalhe})

    return cabecalhos, resultados
