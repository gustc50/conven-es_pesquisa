# Buscador de Convenção Coletiva

Aplicativo local (Windows) para buscar convenções coletivas, acordos coletivos
e termos aditivos pelo **CNPJ do sindicato**, consultando o
[Sistema Mediador](https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo)
do Ministério do Trabalho e Emprego, com opção de baixar o PDF do instrumento
encontrado.

Não é um site oficial — é uma automação da consulta pública que qualquer
pessoa já pode fazer diretamente no site do Mediador.

## Como usar

1. Instale o [Python](https://www.python.org/downloads/) (versão 3.10 ou
   superior), marcando a opção **"Add python.exe to PATH"** durante a
   instalação.
2. Dê dois cliques em **`iniciar.bat`**.
3. Na primeira execução, o script cria um ambiente virtual e instala as
   dependências automaticamente (pode levar cerca de um minuto).
4. O navegador abrirá sozinho em `http://127.0.0.1:5000`.
5. Digite o CNPJ do sindicato e clique em **Buscar**. Nos resultados, use o
   botão **Baixar / abrir** para salvar o PDF (quando o site disponibiliza o
   arquivo direto) ou visualizar a página oficial da convenção.
6. Para encerrar, feche a janela preta que ficou aberta (o servidor local).

## Estrutura do projeto

- `iniciar.bat` — instala dependências e inicia o aplicativo.
- `app.py` — servidor web local (Flask): página inicial, endpoint de busca
  e endpoint de download do PDF.
- `mediador.py` — cliente que consulta o site do Sistema Mediador.
- `templates/`, `static/` — interface web (HTML/CSS/JS).

## Limitações e observações

- É necessária conexão com a internet: o aplicativo consulta o site oficial
  em tempo real, sem armazenar nenhum dado.
- O aplicativo lê o formulário de busca do site oficial a cada consulta, em
  vez de usar campos fixos, para se adaptar melhor a pequenas mudanças de
  layout. Ainda assim, se o site oficial mudar significativamente ou exigir
  verificação adicional (captcha), a busca automática pode falhar — nesse
  caso é exibido um link para a busca manual no site oficial.
- Se a busca não trouxer o resultado esperado, o aplicativo salva a última
  resposta recebida do site oficial em `debug_ultima_consulta.html`, na
  pasta do programa. Esse arquivo ajuda a entender o que o site retornou
  (ex.: se o layout mudou) e pode ser compartilhado para diagnóstico.
- Roda apenas em `127.0.0.1` (acesso local à sua máquina).
