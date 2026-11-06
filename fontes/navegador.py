"""Automação de navegador (Playwright) em modo assistido.

O site do Mediador fica atrás da proteção anti-robô da Cloudflare. O app não
tenta enganar essa proteção: abre uma janela de navegador visível e, se a
verificação aparecer, espera a própria pessoa resolvê-la. Depois disso,
marca o critério de CNPJ, digita o número, pesquisa e lê a tabela.

O perfil do navegador fica salvo em perfil_navegador/, como num navegador
comum, então a verificação tende a não reaparecer a cada busca.
"""
import os
import re
import threading
import time

from bs4 import BeautifulSoup

from . import comum
from .comum import FonteError

PASTA_PERFIL = os.path.join(comum.PASTA_PROJETO, "perfil_navegador")

TIMEOUT_NAVEGACAO_MS = 60000
TIMEOUT_ELEMENTO_MS = 8000
TIMEOUT_RESULTADO_MS = 30000
TEMPO_MAXIMO_VERIFICACAO_S = 180

SELETOR_CAMPO_TEXTO = (
    "input:not([type]), input[type=text], input[type=search], "
    "input[type=tel], input[type=number], textarea"
)
TITULOS_VERIFICACAO = ["just a moment", "um momento", "attention required"]
TEXTOS_VERIFICACAO = [
    "verify you are human",
    "verifique se você é humano",
    "confirme que você é humano",
    "enable javascript and cookies",
    "checking your browser",
]

_trava_busca = threading.Lock()


def _importar_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise FonteError(
            "O componente de navegador (Playwright) não está instalado. "
            "Feche o programa e rode o iniciar.bat novamente para instalá-lo."
        ) from exc
    return sync_playwright


def _primeiro_visivel(candidatos, timeout_ms=TIMEOUT_ELEMENTO_MS):
    """Testa todas as estratégias de localização em rodízio até uma achar um
    elemento visível, sem gastar o tempo inteiro esperando em cada uma."""
    limite = time.monotonic() + timeout_ms / 1000
    while True:
        for construir in candidatos:
            try:
                alvo = construir().first
                if alvo.count() and alvo.is_visible():
                    return alvo
            except Exception:
                continue
        if time.monotonic() > limite:
            return None
        time.sleep(0.25)


def _salvar_diagnostico(pagina, config):
    try:
        comum.salvar_debug(config["arquivo_html"], pagina.content())
    except Exception:
        pass
    try:
        pagina.screenshot(
            path=os.path.join(comum.PASTA_PROJETO, config["arquivo_print"]),
            full_page=True,
        )
    except Exception:
        pass


def _dica_diagnostico(config):
    return (
        f" Para diagnóstico, o programa salvou {config['arquivo_print']} e "
        f"{config['arquivo_html']} na pasta do aplicativo."
    )


def _falhar(pagina, config, mensagem):
    _salvar_diagnostico(pagina, config)
    raise FonteError(mensagem + _dica_diagnostico(config))


def _em_verificacao(pagina):
    try:
        titulo = (pagina.title() or "").lower()
        if any(sinal in titulo for sinal in TITULOS_VERIFICACAO):
            return True
        if pagina.locator("iframe[src*='challenges.cloudflare.com']").count():
            return True
        texto = pagina.locator("body").inner_text(timeout=2000).lower()
    except Exception:
        # A página está no meio de um redirecionamento da própria verificação.
        return True
    return any(sinal in texto for sinal in TEXTOS_VERIFICACAO)


def _aguardar_verificacao_humana(pagina, config):
    limite = time.monotonic() + TEMPO_MAXIMO_VERIFICACAO_S
    while True:
        if pagina.is_closed():
            raise FonteError(
                "A janela do navegador foi fechada antes de a busca terminar."
            )
        if not _em_verificacao(pagina):
            return
        if time.monotonic() > limite:
            _falhar(
                pagina,
                config,
                f"A verificação de segurança de {config['nome']} não foi concluída "
                "(ou o site não aceitou o navegador do aplicativo). Use a busca no "
                "site oficial pelo botão abaixo.",
            )
        pagina.wait_for_timeout(1000)


def _marcar_criterio(pagina, padrao):
    """Em formulários de "critérios", o campo só vale com a caixa marcada."""
    caixa = _primeiro_visivel(
        [lambda: pagina.get_by_role("checkbox", name=padrao)], timeout_ms=2000
    )
    if caixa is None:
        return
    try:
        if not caixa.is_checked():
            caixa.check()
    except Exception:
        pass


def _localizar_campo(pagina, palavras_chave, padrao):
    campos_texto = pagina.locator(SELETOR_CAMPO_TEXTO)
    palavras_simples = [p for p in palavras_chave if " " not in p]
    seletor_atributos = ", ".join(
        f"[{atributo}*='{palavra}' i]"
        for palavra in palavras_simples
        for atributo in ("id", "name", "aria-label", "title", "placeholder")
    )
    texto_proximo = (
        "xpath=//*[text()[contains(translate(., 'cnpj', 'CNPJ'), 'CNPJ')]]"
        "/following::input[not(@type) or @type='text' or @type='search' or @type='tel'][1]"
    )

    return _primeiro_visivel(
        [
            lambda: pagina.get_by_label(padrao).and_(campos_texto),
            lambda: pagina.get_by_placeholder(padrao).and_(campos_texto),
            lambda: pagina.locator(seletor_atributos).and_(campos_texto),
            lambda: pagina.locator(texto_proximo),
        ]
    )


def _localizar_botao(pagina, palavras_botao):
    padrao = re.compile("|".join(palavras_botao), re.IGNORECASE)
    seletor_atributos = ", ".join(
        f"input[type=submit][value*='{palavra}' i], input[type=button][value*='{palavra}' i]"
        for palavra in palavras_botao
    )

    return _primeiro_visivel(
        [
            lambda: pagina.get_by_role("button", name=padrao),
            lambda: pagina.locator(seletor_atributos),
            lambda: pagina.get_by_role("link", name=padrao),
        ]
    )


def _aguardar_resultados(pagina, config):
    """Espera um sinal de resultado (link de detalhe, nº de registro ou "nenhum
    registro"). Se nada disso aparecer, segue mesmo assim e a leitura decide."""
    try:
        pagina.wait_for_load_state("networkidle", timeout=TIMEOUT_RESULTADO_MS)
    except Exception:
        pass
    try:
        pagina.wait_for_function(
            """(args) => {
                const texto = document.body.innerText || '';
                const minusculo = texto.toLowerCase();
                if (args.frases.some((f) => minusculo.includes(f))) return true;
                if (args.registro && new RegExp(args.registro, 'i').test(texto)) return true;
                return Array.from(document.querySelectorAll('table a')).some((a) => {
                    const alvo = [a.innerText, a.getAttribute('href'), a.getAttribute('onclick')]
                        .join(' ').toLowerCase();
                    return args.palavras.some((p) => alvo.includes(p));
                });
            }""",
            arg={
                "frases": [f.lower() for f in comum.FRASES_SEM_RESULTADO],
                "registro": config.get("padrao_registro"),
                "palavras": config["palavras_link_detalhe"],
            },
            timeout=TIMEOUT_RESULTADO_MS,
        )
    except Exception:
        pass


def _ler_resultados(pagina, config):
    html_renderizado = pagina.content()
    comum.salvar_debug(config["arquivo_html"], html_renderizado)

    texto_pagina = html_renderizado.lower()
    sem_resultado = any(frase in texto_pagina for frase in comum.FRASES_SEM_RESULTADO)

    soup = BeautifulSoup(html_renderizado, "html.parser")
    tabela, com_evidencia = comum.selecionar_tabela_resultados(
        soup, config["palavras_link_detalhe"], config.get("padrao_registro")
    )
    if sem_resultado and not com_evidencia:
        # O site disse que não há resultados e nenhuma tabela parece uma
        # lista de convenções (só layout ou rodapé).
        return [], []
    if tabela is None:
        _falhar(
            pagina,
            config,
            f"A página de resultados de {config['nome']} não veio no formato esperado.",
        )

    cabecalhos, resultados = comum.extrair_resultados(
        tabela, pagina.url, config["palavras_link_detalhe"]
    )
    if not resultados and not sem_resultado:
        _falhar(
            pagina,
            config,
            f"Não foi possível interpretar a tabela de resultados de {config['nome']}.",
        )

    montar_link = config.get("montar_link")
    if montar_link:
        for resultado in resultados:
            if not resultado["detalhe_url"]:
                resultado["detalhe_url"] = montar_link(resultado["colunas"])

    return cabecalhos, resultados


def _executar_busca(pagina, config, cnpj):
    pagina.set_default_timeout(15000)
    try:
        pagina.goto(config["url"], wait_until="domcontentloaded", timeout=TIMEOUT_NAVEGACAO_MS)
    except Exception as exc:
        raise FonteError(
            f"Não foi possível abrir o site de {config['nome']}. "
            "Verifique sua conexão com a internet e tente novamente."
        ) from exc

    pagina.bring_to_front()
    _aguardar_verificacao_humana(pagina, config)

    padrao = re.compile("|".join(config["palavras_campo"]), re.IGNORECASE)
    _marcar_criterio(pagina, padrao)

    campo = _localizar_campo(pagina, config["palavras_campo"], padrao)
    if campo is None:
        _falhar(
            pagina,
            config,
            f"Não foi possível localizar o campo de CNPJ em {config['nome']} "
            "(o site pode ter mudado de layout).",
        )

    try:
        campo.click()
        campo.fill("")
        # Digita tecla a tecla para que máscaras de CNPJ do site funcionem.
        campo.press_sequentially(cnpj, delay=40)
    except Exception:
        _falhar(pagina, config, f"Não foi possível preencher o CNPJ em {config['nome']}.")

    botao = _localizar_botao(pagina, config["palavras_botao"])
    if botao is None:
        _falhar(pagina, config, f"Não foi possível localizar o botão de pesquisa em {config['nome']}.")

    botao.click()
    _aguardar_resultados(pagina, config)

    if _em_verificacao(pagina):
        _aguardar_verificacao_humana(pagina, config)
        _aguardar_resultados(pagina, config)

    cabecalhos, resultados = _ler_resultados(pagina, config)
    return cabecalhos, resultados, pagina.url


def buscar(config, cnpj):
    """Executa a busca por CNPJ na fonte descrita por `config`.

    Retorna (cabecalhos, resultados, url_da_consulta).
    Lança FonteError com mensagem amigável em caso de falha esperada.
    """
    sync_playwright = _importar_playwright()

    if not _trava_busca.acquire(blocking=False):
        raise FonteError("Já existe uma busca em andamento. Aguarde ela terminar.")

    try:
        with sync_playwright() as playwright:
            try:
                contexto = playwright.chromium.launch_persistent_context(
                    PASTA_PERFIL,
                    headless=False,
                    locale="pt-BR",
                    no_viewport=True,
                )
            except Exception as exc:
                raise FonteError(
                    "Não foi possível abrir o navegador do aplicativo. Se já houver "
                    "uma janela dele aberta, feche-a; se for a primeira execução, "
                    "rode o iniciar.bat novamente para instalá-lo."
                ) from exc

            try:
                pagina = contexto.pages[0] if contexto.pages else contexto.new_page()
                return _executar_busca(pagina, config, cnpj)
            finally:
                contexto.close()
    finally:
        _trava_busca.release()
