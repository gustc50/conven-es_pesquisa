# Buscador de Convenção Coletiva

Aplicativo local (Windows) para buscar convenções coletivas, acordos coletivos
e termos aditivos pelo **CNPJ do sindicato**, consultando múltiplas fontes
públicas de uma vez, com opção de baixar o PDF do instrumento encontrado.

Fontes consultadas automaticamente:

- **[Sistema Mediador](https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo/ConsultaBasica)**
  (Ministério do Trabalho e Emprego) — fonte oficial: todo instrumento
  coletivo só é válido se estiver registrado aqui.
- **[SACC-DIEESE](https://www.dieese.org.br/sacc/pesquisa.do?method=setup)**
  — base complementar de pesquisa mantida pelo DIEESE. Não é organizada
  necessariamente por CNPJ, então pode não trazer resultado mesmo quando o
  Mediador traz.

Fontes citadas mas **não** automatizadas (aparecem como links no app, seção
"Outras fontes de consulta"):

- Sites de sindicatos e federações (ex.: FIESP/CIESP, Fecomércio) — cada um
  tem seu próprio formato, sem busca unificada por CNPJ.
- Bases pagas por assinatura (ex.: LegisWeb, Convenia, IOB) — exigem login e
  os termos de uso normalmente não autorizam automação/raspagem; por isso o
  app só linka para elas, sem tentar buscar automaticamente.

Não é um site oficial — é uma automação da consulta pública que qualquer
pessoa já pode fazer diretamente nesses sites.

## Como usar

1. Instale o [Python](https://www.python.org/downloads/) (versão 3.10 ou
   superior), marcando a opção **"Add python.exe to PATH"** durante a
   instalação.
2. Dê dois cliques em **`iniciar.bat`**.
3. Na primeira execução, o script cria um ambiente virtual e instala as
   dependências automaticamente (pode levar cerca de um minuto).
4. O navegador abrirá sozinho em `http://127.0.0.1:5000`.
5. Digite o CNPJ do sindicato e clique em **Buscar**. O app mostra um bloco
   de resultados para cada fonte. Use o botão **Baixar / abrir** para salvar
   o PDF (quando disponível direto) ou visualizar a página oficial.
6. Para encerrar, feche a janela preta que ficou aberta (o servidor local).

## Como a busca funciona

Os sites consultados montam a tabela de resultados via JavaScript, então não
adianta enviar o formulário por HTTP puro — os resultados simplesmente não
apareceriam. Por isso o aplicativo usa um **navegador de verdade**
(Chromium, via Playwright) rodando em segundo plano: ele abre a página,
preenche o CNPJ, clica no botão de pesquisa e lê a tabela já renderizada.

Os campos são localizados pelo **texto visível** (rótulo, placeholder, texto
do botão) em vez de por nomes internos de HTML, que nesses sistemas são
gerados automaticamente e mudam com frequência.

## Estrutura do projeto

- `iniciar.bat` — instala dependências (incluindo o navegador) e inicia o app.
- `app.py` — servidor web local (Flask): página inicial, endpoint de busca
  (consulta todas as fontes), download do PDF e download dos arquivos de
  diagnóstico.
- `fontes/navegador.py` — automação do navegador (abrir página, achar campo,
  clicar, esperar resultado, salvar diagnóstico).
- `fontes/comum.py` — validação de CNPJ, leitura da tabela de resultados e
  download do arquivo original.
- `fontes/mediador.py`, `fontes/dieese.py` — configuração de cada fonte (URL,
  palavras-chave de campo e de botão).
- `templates/`, `static/` — interface web (HTML/CSS/JS).

## Se a busca falhar

1. Marque a opção **"Mostrar o navegador durante a busca"** e busque de novo:
   uma janela do navegador abre e você vê exatamente onde o processo trava.
2. Quando uma fonte dá erro, o app salva automaticamente um **print da tela**
   (`debug_mediador.png` / `debug_dieese.png`) e o **HTML da página**
   (`debug_mediador.html` / `debug_dieese.html`) na pasta do programa, e
   oferece os dois para download logo abaixo da mensagem de erro. Esses
   arquivos mostram o que o site realmente respondeu e são o suficiente para
   ajustar o programa.
3. Em qualquer caso, o link de busca manual naquela fonte continua disponível.

## Limitações e observações

- É necessária conexão com a internet: o aplicativo consulta os sites
  oficiais em tempo real, sem armazenar nenhum dado.
- Na primeira execução, o `iniciar.bat` baixa o Chromium usado na automação
  (algumas centenas de MB). Isso acontece uma única vez.
- Se um site exigir verificação adicional (captcha/login), a busca automática
  naquela fonte falha — mas as outras fontes continuam funcionando.
- Roda apenas em `127.0.0.1` (acesso local à sua máquina).
