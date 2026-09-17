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
const resultadosFontes = document.getElementById("resultados-fontes");
const botaoBuscar = document.getElementById("botao-buscar");

inputCnpj.addEventListener("input", () => {
  inputCnpj.value = mascararCnpj(inputCnpj.value);
});

function mostrarStatus(mensagem, tipo) {
  status.textContent = mensagem || "";
  status.className = `status ${tipo || ""}`.trim();
  status.hidden = !mensagem;
}

function criarTabelaResultados(fonte) {
  const tabela = document.createElement("table");
  const thead = document.createElement("thead");
  const linhaCabecalho = document.createElement("tr");

  const titulos =
    fonte.cabecalhos && fonte.cabecalhos.length
      ? fonte.cabecalhos
      : fonte.resultados[0].colunas.map((_, indice) => `Coluna ${indice + 1}`);

  titulos.forEach((titulo) => {
    const th = document.createElement("th");
    th.textContent = titulo;
    linhaCabecalho.appendChild(th);
  });
  const thAcao = document.createElement("th");
  thAcao.textContent = "Documento";
  linhaCabecalho.appendChild(thAcao);
  thead.appendChild(linhaCabecalho);
  tabela.appendChild(thead);

  const corpoTabela = document.createElement("tbody");
  fonte.resultados.forEach((resultado) => {
    const tr = document.createElement("tr");

    resultado.colunas.forEach((coluna) => {
      const td = document.createElement("td");
      td.textContent = coluna;
      tr.appendChild(td);
    });

    const tdAcao = document.createElement("td");
    if (resultado.detalhe_url) {
      const link = document.createElement("a");
      link.href = `/download?url=${encodeURIComponent(resultado.detalhe_url)}`;
      link.textContent = "Baixar / abrir";
      link.className = "botao-download";
      link.target = "_blank";
      link.rel = "noopener";
      tdAcao.appendChild(link);
    } else {
      tdAcao.textContent = "—";
    }
    tr.appendChild(tdAcao);

    corpoTabela.appendChild(tr);
  });
  tabela.appendChild(corpoTabela);

  return tabela;
}

function renderizarFonte(fonte) {
  const secao = document.createElement("section");
  secao.className = "fonte";

  const titulo = document.createElement("h2");
  titulo.textContent = fonte.nome;
  secao.appendChild(titulo);

  if (!fonte.ok) {
    const mensagem = document.createElement("p");
    mensagem.className = "status erro";
    mensagem.textContent = fonte.erro || "Não foi possível concluir a busca nesta fonte.";
    secao.appendChild(mensagem);
  } else if (!fonte.resultados.length) {
    const mensagem = document.createElement("p");
    mensagem.className = "status vazio";
    mensagem.textContent = fonte.aviso || "Nenhum resultado encontrado para este CNPJ.";
    secao.appendChild(mensagem);
  } else {
    const mensagem = document.createElement("p");
    mensagem.className = "status sucesso";
    mensagem.textContent = `${fonte.resultados.length} resultado(s) encontrado(s).`;
    secao.appendChild(mensagem);
    secao.appendChild(criarTabelaResultados(fonte));
  }

  if ((!fonte.ok || !fonte.resultados.length) && fonte.url_manual) {
    const aviso = document.createElement("p");
    aviso.className = "aviso-manual-fonte";
    const link = document.createElement("a");
    link.href = fonte.url_manual;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = `Abrir busca manual em ${fonte.nome}`;
    aviso.appendChild(link);
    secao.appendChild(aviso);
  }

  return secao;
}

form.addEventListener("submit", async (evento) => {
  evento.preventDefault();

  resultadosFontes.innerHTML = "";
  erroCnpj.hidden = true;
  mostrarStatus("", "");

  const cnpj = inputCnpj.value;
  if (!cnpjValido(cnpj)) {
    erroCnpj.textContent = "CNPJ inválido. Confira os números digitados.";
    erroCnpj.hidden = false;
    return;
  }

  botaoBuscar.disabled = true;
  mostrarStatus("Buscando nas fontes disponíveis...", "carregando");

  try {
    const resposta = await fetch("/buscar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cnpj }),
    });
    const dados = await resposta.json();

    if (!dados.ok) {
      mostrarStatus(dados.erro || "Não foi possível concluir a busca.", "erro");
      return;
    }

    mostrarStatus("", "");
    dados.fontes.forEach((fonte) => {
      resultadosFontes.appendChild(renderizarFonte(fonte));
    });
  } catch (erro) {
    mostrarStatus("Erro de conexão com o servidor local. Tente novamente.", "erro");
  } finally {
    botaoBuscar.disabled = false;
  }
});
