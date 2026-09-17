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

## Estrutura do projeto

- `iniciar.bat` — instala dependências e inicia o aplicativo.
- `app.py` — servidor web local (Flask): página inicial, endpoint de busca
  (consulta todas as fontes) e endpoint de download do PDF.
- `fontes/comum.py` — engine genérica de raspagem (descoberta de formulário,
  tabela de resultados e arquivo original), reaproveitada por todas as fontes.
- `fontes/mediador.py`, `fontes/dieese.py` — clientes específicos de cada fonte
  (URL, palavras-chave de campo).
- `templates/`, `static/` — interface web (HTML/CSS/JS).

## Limitações e observações

- É necessária conexão com a internet: o aplicativo consulta os sites
  oficiais em tempo real, sem armazenar nenhum dado.
- O aplicativo lê o formulário de busca de cada site a cada consulta, em vez
  de usar campos fixos, para se adaptar melhor a pequenas mudanças de
  layout. Ainda assim, se um site mudar significativamente ou exigir
  verificação adicional (captcha/login), a busca automática nessa fonte pode
  falhar — nesse caso é exibido, só para aquela fonte, um link para a busca
  manual, enquanto as outras fontes continuam funcionando normalmente.
- Se a busca não trouxer o resultado esperado em alguma fonte, o aplicativo
  salva a última resposta recebida em `debug_ultima_consulta_mediador.html`
  ou `debug_ultima_consulta_dieese.html`, na pasta do programa. Esses
  arquivos ajudam a entender o que o site retornou (ex.: se o layout mudou)
  e podem ser compartilhados para diagnóstico.
- Roda apenas em `127.0.0.1` (acesso local à sua máquina).
