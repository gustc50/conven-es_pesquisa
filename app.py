"""Buscador de Convenção Coletiva — aplicação web local (Flask).

Interface para consultar, pelo CNPJ do sindicato, instrumentos coletivos
registrados no Sistema Mediador (Ministério do Trabalho e Emprego). Cada
resultado abre o extrato oficial no navegador, de onde a convenção é baixada.
"""
import os
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template, request, send_file

import fontes
from fontes.comum import PASTA_PROJETO, FonteError, cnpj_valido

app = Flask(__name__)

ARQUIVOS_DIAGNOSTICO = [
    nome
    for modulo in fontes.FONTES
    for nome in (modulo.CONFIG["arquivo_html"], modulo.CONFIG["arquivo_print"])
]


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
            item["diagnostico"] = [
                nome
                for nome in (
                    modulo.CONFIG["arquivo_print"],
                    modulo.CONFIG["arquivo_html"],
                )
                if os.path.exists(os.path.join(PASTA_PROJETO, nome))
            ]
        resultado_fontes.append(item)

    return jsonify(ok=True, fontes=resultado_fontes)


@app.route("/diagnostico/<nome>")
def diagnostico(nome):
    if nome not in ARQUIVOS_DIAGNOSTICO:
        return "Arquivo de diagnóstico desconhecido.", 404

    caminho = os.path.join(PASTA_PROJETO, nome)
    if not os.path.exists(caminho):
        return "Arquivo de diagnóstico ainda não foi gerado.", 404

    return send_file(caminho, as_attachment=True)


def _abrir_navegador(url):
    time.sleep(1.2)
    webbrowser.open(url)


if __name__ == "__main__":
    porta = 5000
    url_local = f"http://127.0.0.1:{porta}"
    threading.Thread(target=_abrir_navegador, args=(url_local,), daemon=True).start()
    app.run(host="127.0.0.1", port=porta, debug=False)
