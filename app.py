"""Buscador de Convenção Coletiva — aplicação web local (Flask).

Interface para consultar, pelo CNPJ do sindicato, instrumentos coletivos
registrados no Sistema Mediador (Ministério do Trabalho e Emprego) e
baixar o PDF correspondente.
"""
import re
import threading
import time
import webbrowser
from urllib.parse import urlparse

import requests
from flask import Flask, Response, jsonify, render_template, request

from mediador import (
    MediadorError,
    URL_BUSCA_MANUAL,
    USER_AGENT,
    buscar_por_cnpj,
    cnpj_valido,
)

app = Flask(__name__)

HOSTS_PERMITIDOS_DOWNLOAD = ("trabalho.gov.br",)


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

    try:
        cabecalhos, resultados, url_consulta = buscar_por_cnpj(cnpj)
    except MediadorError as exc:
        return jsonify(ok=False, erro=str(exc), url_manual=URL_BUSCA_MANUAL), 502

    if not resultados:
        return jsonify(
            ok=True,
            cabecalhos=cabecalhos,
            resultados=[],
            aviso="Nenhuma convenção, acordo ou termo aditivo foi encontrado para este CNPJ.",
            url_manual=URL_BUSCA_MANUAL,
        )

    return jsonify(
        ok=True,
        cabecalhos=cabecalhos,
        resultados=resultados,
        url_consulta=url_consulta,
    )


@app.route("/download")
def download():
    url = request.args.get("url", "")
    host = urlparse(url).hostname or ""

    if not url.startswith("https://") or not _host_permitido(host):
        return "Download não permitido para esta URL.", 400

    try:
        resposta = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
        resposta.raise_for_status()
    except requests.RequestException:
        return "Não foi possível baixar o arquivo no site oficial.", 502

    nome_arquivo = url.rstrip("/").split("/")[-1] or "convencao.pdf"
    nome_arquivo = re.sub(r"[^A-Za-z0-9._-]", "_", nome_arquivo)
    if not nome_arquivo.lower().endswith(".pdf"):
        nome_arquivo += ".pdf"

    return Response(
        resposta.content,
        mimetype=resposta.headers.get("Content-Type", "application/pdf"),
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
