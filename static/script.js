function apenasDigitos(valor) {
  return (valor || "").replace(/\D/g, "");
}

function mascararCnpj(valor) {
  valor = apenasDigitos(valor).slice(0, 14);
  valor = valor.replace(/^(\d{2})(\d)/, "$1.$2");
  valor = valor.replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3");
  valor = valor.replace(/\.(\d{3})(\d)/, ".$1/$2");
  valor = valor.replace(/(\d{4})(\d)/, "$1-$2");
  return valor;
}

function cnpjValido(valor) {
  const cnpj = apenasDigitos(valor);
  if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) {
    return false;
  }

  const calcularDigito = (base, pesos) => {
    const soma = base
      .split("")
      .reduce((acumulado, digito, indice) => acumulado + Number(digito) * pesos[indice], 0);
    const resto = soma % 11;
    return resto < 2 ? 0 : 11 - resto;
  };

  const pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
  const digito1 = calcularDigito(cnpj.slice(0, 12), pesos1);
  const digito2 = calcularDigito(cnpj.slice(0, 12) + digito1, pesos2);

  return cnpj.slice(-2) === `${digito1}${digito2}`;
}

const inputCnpj = document.getElementById("cnpj");
const form = document.getElementById("form-busca");
const erroCnpj = document.getElementById("erro-cnpj");
const status = document.getElementById("status");
const divResultados = document.getElementById("resultados");
const linhaCabecalho = document.getElementById("linha-cabecalho");
const corpoTabela = document.getElementById("corpo-tabela");
const avisoManual = document.getElementById("aviso-manual");
const linkManual = document.getElementById("link-manual");
const botaoBuscar = document.getElementById("botao-buscar");

inputCnpj.addEventListener("input", () => {
  inputCnpj.value = mascararCnpj(inputCnpj.value);
});

function mostrarStatus(mensagem, tipo) {
  status.textContent = mensagem || "";
  status.className = `status ${tipo || ""}`.trim();
  status.hidden = !mensagem;
}

function renderizarResultados(cabecalhos, resultados) {
  linhaCabecalho.innerHTML = "";
  const titulos =
    cabecalhos && cabecalhos.length
      ? cabecalhos
      : resultados[0].colunas.map((_, indice) => `Coluna ${indice + 1}`);

  titulos.forEach((titulo) => {
    const th = document.createElement("th");
    th.textContent = titulo;
    linhaCabecalho.appendChild(th);
  });

  const thAcao = document.createElement("th");
  thAcao.textContent = "Convenção";
  linhaCabecalho.appendChild(thAcao);

  corpoTabela.innerHTML = "";
  resultados.forEach((resultado) => {
    const tr = document.createElement("tr");

    resultado.colunas.forEach((coluna) => {
      const td = document.createElement("td");
      td.textContent = coluna;
      tr.appendChild(td);
    });

    const tdAcao = document.createElement("td");
    if (resultado.pdf_url) {
      const link = document.createElement("a");
      link.href = `/download?url=${encodeURIComponent(resultado.pdf_url)}`;
      link.textContent = "Baixar PDF";
      link.className = "botao-download";
      tdAcao.appendChild(link);
    } else {
      tdAcao.textContent = "—";
    }
    tr.appendChild(tdAcao);

    corpoTabela.appendChild(tr);
  });

  divResultados.hidden = false;
}

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  divResultados.hidden = true;
  avisoManual.hidden = true;
  erroCnpj.hidden = true;
  mostrarStatus("", "");

  const cnpj = inputCnpj.value;
  if (!cnpjValido(cnpj)) {
    erroCnpj.textContent = "CNPJ inválido. Confira os números digitados.";
    erroCnpj.hidden = false;
    return;
  }

  botaoBuscar.disabled = true;
  mostrarStatus("Buscando no Sistema Mediador...", "carregando");

  try {
    const resposta = await fetch("/buscar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cnpj }),
    });
    const dados = await resposta.json();

    if (!dados.ok) {
      mostrarStatus(dados.erro || "Não foi possível concluir a busca.", "erro");
      if (dados.url_manual) {
        linkManual.href = dados.url_manual;
        avisoManual.hidden = false;
      }
      return;
    }

    if (!dados.resultados.length) {
      mostrarStatus(dados.aviso || "Nenhum resultado encontrado para este CNPJ.", "vazio");
      return;
    }

    mostrarStatus(`${dados.resultados.length} resultado(s) encontrado(s).`, "sucesso");
    renderizarResultados(dados.cabecalhos, dados.resultados);
  } catch (erro) {
    mostrarStatus("Erro de conexão com o servidor local. Tente novamente.", "erro");
  } finally {
    botaoBuscar.disabled = false;
  }
});
