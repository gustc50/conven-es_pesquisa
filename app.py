"""Buscador de Convenção Coletiva — aplicação web local (Flask).

Interface para consultar, pelo CNPJ do sindicato, instrumentos coletivos
em múltiplas fontes públicas (Sistema Mediador, SACC-DIEESE) e baixar o
PDF correspondente.
"""
import re
import threading
import time
import webbrowser
from urllib.parse import urlparse

from flask import Flask, Response, jsonify, redirect, render_template, request

import fontes
from fontes.comum import FonteError, cnpj_valido, resolver_arquivo_original

app = Flask(__name__)

HOSTS_PERMITIDOS_DOWNLOAD = ("trabalho.gov.br", "dieese.org.br")


def _host_permitido(host):
    return any(host == h or host.endswith("." + h) for h in HOSTS_PERMITIDOS_DOWNLOAD)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/buscar", methods=["POST"])
def buscar():
    dados = request.get_json(silent=True) or {}
    cnpj = dados.get("cnpj", "")

    if not cnpj_valido(cnpj):
        return jsonify(ok=False, erro="CNPJ inválido. Confira o número informado."), 400

    resultado_fontes = []
    for modulo in fontes.FONTES:
        item = {"nome": modulo.NOME_FONTE, "url_manual": modulo.URL_BUSCA_MANUAL}
        try:
            cabecalhos, resultados, url_consulta = modulo.buscar_por_cnpj(cnpj)
            item["ok"] = True
            item["cabecalhos"] = cabecalhos
            item["resultados"] = resultados
            item["url_consulta"] = url_consulta
            if not resultados:
                item["aviso"] = (
                    "Nenhuma convenção, acordo ou termo aditivo foi encontrado "
                    "para este CNPJ."
                )
        except FonteError as exc:
            item["ok"] = False
            item["erro"] = str(exc)
        resultado_fontes.append(item)

    return jsonify(ok=True, fontes=resultado_fontes)


@app.route("/download")
def download():
    url = request.args.get("url", "")
    host = urlparse(url).hostname or ""

    if not url.startswith("https://") or not _host_permitido(host):
        return "Download não permitido para esta URL.", 400

    url_final, conteudo, content_type = resolver_arquivo_original(url)

    if conteudo is None:
        # Não foi possível localizar o PDF diretamente: manda o usuário para
        # a página oficial do instrumento, onde ele pode visualizar/baixar.
        return redirect(url, code=302)

    nome_arquivo = url_final.rstrip("/").split("/")[-1] or "convencao.pdf"
    nome_arquivo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_arquivo)
    if not nome_arquivo.lower().endswith(".pdf"):
        nome_arquivo += ".pdf"

    return Response(
        conteudo,
        mimetype=content_type or "application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


def _abrir_navegador(url):
    time.sleep(1.2)
    webbrowser.open(url)


if __name__ == "__main__":
    porta = 5000
    url_local = f"http://127.0.0.1:{porta}"
    threading.Thread(target=_abrir_navegador, args=(url_local,), daemon=True).start()
    app.run(host="127.0.0.1", port=porta, debug=False)
