"""Engine de automação de navegador (Playwright) usada pelas fontes públicas.

Os sites consultados montam a tabela de resultados via JavaScript, então não
basta enviar o formulário por HTTP: é preciso um navegador de verdade, que
preencha o campo, clique no botão de pesquisa e leia a tabela já renderizada.

Os elementos são localizados pelo texto visível (rótulo, placeholder, texto do
botão) em vez de por atributos internos de HTML, que mudam com frequência.
Quando algo falha, salva print da tela e HTML renderizado para diagnóstico.
"""
import os

from bs4 import BeautifulSoup

from . import comum
from .comum import FonteError

TIMEOUT_NAVEGACAO_MS = 45000
TIMEOUT_ELEMENTO_MS = 8000
TIMEOUT_RESULTADO_MS = 20000

MENSAGEM_SEM_PLAYWRIGHT = (
    "O componente de navegador (Playwright) não está instalado. "
    "Feche o programa e rode o iniciar.bat novamente para instalá-lo."
)


def _importar_playwright():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise FonteError(MENSAGEM_SEM_PLAYWRIGHT) from exc
    return sync_playwright


def _primeiro_visivel(candidatos, timeout_ms=TIMEOUT_ELEMENTO_MS):
    """Tenta cada estratégia de localização e devolve a primeira que aparecer."""
    for construir in candidatos:
        try:
            alvo = construir().first
            alvo.wait_for(state="visible", timeout=timeout_ms)
            return alvo
        except Exception:
            continue
    return None


def _localizar_campo(pagina, palavras_chave):
    import re

    padrao = re.compile("|".join(palavras_chave), re.IGNORECASE)
    seletor_atributos = ", ".join(
        f"input[{atributo}*='{palavra}' i]"
        for palavra in palavras_chave
        for atributo in ("id", "name", "aria-label", "title")
    )

    return _primeiro_visivel(
        [
            lambda: pagina.get_by_label(padrao),
            lambda: pagina.get_by_placeholder(padrao),
            lambda: pagina.locator(seletor_atributos),
        ]
    )


def _localizar_botao(pagina, palavras_botao):
    import re

    padrao = re.compile("|".join(palavras_botao), re.IGNORECASE)
    seletor_atributos = ", ".join(
        f"input[type=submit][value*='{palavra}' i], button[title*='{palavra}' i]"
        for palavra in palavras_botao
    )

    return _primeiro_visivel(
        [
            lambda: pagina.get_by_role("button", name=padrao),
            lambda: pagina.get_by_role("link", name=padrao),
            lambda: pagina.locator(seletor_atributos),
            lambda: pagina.get_by_text(padrao),
        ]
    )


def _aguardar_resultados(pagina):
    """Espera até a tabela aparecer ou o site dizer que não há resultados."""
    frases = [frase.lower() for frase in comum.FRASES_SEM_RESULTADO]
    try:
        pagina.wait_for_load_state("networkidle", timeout=TIMEOUT_RESULTADO_MS)
    except Exception:
        pass
    try:
        pagina.wait_for_function(
            """(frases) => {
                if (document.querySelector('table tr td')) return true;
                const texto = (document.body.innerText || '').toLowerCase();
                return frases.some((frase) => texto.includes(frase));
            }""",
            arg=frases,
            timeout=TIMEOUT_RESULTADO_MS,
        )
    except Exception:
        pass


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


def buscar(config, cnpj, visivel=False):
    """Executa a busca por CNPJ na fonte descrita por `config`.

    Retorna (cabecalhos, resultados, url_da_consulta).
    Lança FonteError com mensagem amigável em caso de falha esperada.
    """
    sync_playwright = _importar_playwright()

    with sync_playwright() as playwright:
        try:
            navegador = playwright.chromium.launch(headless=not visivel)
        except Exception as exc:
            raise FonteError(MENSAGEM_SEM_PLAYWRIGHT) from exc

        contexto = navegador.new_context(
            locale="pt-BR",
            user_agent=comum.USER_AGENT,
            viewport={"width": 1440, "height": 900},
        )
        pagina = contexto.new_page()

        try:
            try:
                pagina.goto(
                    config["url"],
                    wait_until="domcontentloaded",
                    timeout=TIMEOUT_NAVEGACAO_MS,
                )
            except Exception as exc:
                raise FonteError(
                    f"Não foi possível abrir o site de {config['nome']}. "
                    "Verifique sua conexão com a internet e tente novamente."
                ) from exc

            campo = _localizar_campo(pagina, config["palavras_campo"])
            if campo is None:
                _salvar_diagnostico(pagina, config)
                raise FonteError(
                    f"Não foi possível localizar o campo de CNPJ em {config['nome']} "
                    "(o site pode ter mudado de layout ou exigir outro caminho de "
                    "consulta)." + _dica_diagnostico(config)
                )

            campo.fill(cnpj)

            botao = _localizar_botao(pagina, config["palavras_botao"])
            if botao is None:
                _salvar_diagnostico(pagina, config)
                raise FonteError(
                    f"Não foi possível localizar o botão de pesquisa em "
                    f"{config['nome']}." + _dica_diagnostico(config)
                )

            botao.click()
            _aguardar_resultados(pagina)

            html_renderizado = pagina.content()
            comum.salvar_debug(config["arquivo_html"], html_renderizado)

            texto_pagina = html_renderizado.lower()
            if "captcha" in texto_pagina:
                _salvar_diagnostico(pagina, config)
                raise FonteError(
                    f"{config['nome']} exigiu verificação adicional (captcha). "
                    "Use a busca manual pelo link abaixo."
                )

            soup = BeautifulSoup(html_renderizado, "html.parser")
            tabela = comum.selecionar_tabela_resultados(soup)
            sem_resultado = any(
                frase in texto_pagina for frase in comum.FRASES_SEM_RESULTADO
            )

            if tabela is None:
                if sem_resultado:
                    return [], [], pagina.url
                _salvar_diagnostico(pagina, config)
                raise FonteError(
                    f"A página de resultados de {config['nome']} não veio no formato "
                    "esperado." + _dica_diagnostico(config)
                )

            cabecalhos, resultados = comum.extrair_resultados(
                tabela, pagina.url, config["palavras_link_detalhe"]
            )

            if not resultados and not sem_resultado:
                _salvar_diagnostico(pagina, config)
                raise FonteError(
                    f"Não foi possível interpretar a tabela de resultados de "
                    f"{config['nome']}." + _dica_diagnostico(config)
                )

            return cabecalhos, resultados, pagina.url
        finally:
            contexto.close()
            navegador.close()
