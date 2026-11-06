# Buscador de Convenção Coletiva

Aplicativo local (Windows) para buscar convenções coletivas, acordos
coletivos e termos aditivos pelo **CNPJ do sindicato** no
[Sistema Mediador](https://mediador.trabalho.gov.br/sistemas/mediador/ConsultarInstColetivo/ConsultaBasica)
do Ministério do Trabalho e Emprego, a fonte oficial (todo instrumento
coletivo só é válido se estiver registrado lá). Cada resultado abre o
extrato oficial no navegador, de onde a convenção pode ser baixada ou
impressa em PDF.

Não é um site oficial: é uma automação da consulta pública que qualquer
pessoa já pode fazer diretamente no Mediador.

## Como usar

1. Instale o [Python](https://www.python.org/downloads/) (versão 3.10 ou
   superior), marcando a opção **"Add python.exe to PATH"** durante a
   instalação.
2. Dê dois cliques em **`iniciar.bat`**.
3. Na primeira execução, o script cria um ambiente virtual, instala as
   dependências e baixa o navegador usado na busca (algumas centenas de MB,
   só uma vez).
4. O app abre sozinho em `http://127.0.0.1:5000`.
5. Digite o CNPJ do sindicato e clique em **Buscar**.
6. **Uma janela do navegador abre no site do Ministério.** Se aparecer a
   verificação de segurança ("Confirme que você é humano"), clique nela. O
   resto da busca continua sozinho: o app marca o critério de CNPJ, digita o
   número, pesquisa e traz a lista para a tela do app. Não feche essa janela
   durante a busca.
7. Na lista, **Abrir / baixar** abre o extrato oficial daquela convenção.
8. Para encerrar, feche a janela preta do servidor local.

## Por que existe a janela do navegador

O site do Mediador usa a proteção anti-robô da Cloudflare: qualquer acesso
automatizado recebe uma tela de verificação ("Just a moment...") no lugar do
site. O app **não tenta enganar essa proteção**. Em vez disso, abre um
navegador visível e espera você mesmo passar pela verificação, como faria
normalmente. O perfil desse navegador fica salvo em `perfil_navegador/`
(como num navegador comum), então a verificação tende a não reaparecer a
cada busca.

Se a Cloudflare não aceitar o navegador do app mesmo depois do clique, o app
avisa e oferece o plano B: **Abrir a busca no site oficial** (no seu navegador
de sempre) e **Copiar CNPJ** para colar lá.

## Outras fontes

Aparecem como atalhos na seção "Outras fontes de consulta" do app, sem busca
automática:

- **SACC-DIEESE**: exige login de entidade cadastrada no DIEESE.
- **Sites de sindicatos e federações** (FIESP/CIESP, Fecomércio etc.): cada
  um tem um formato, sem busca unificada por CNPJ.
- **Bases pagas** (LegisWeb, Convenia, IOB): exigem assinatura e login.

## Se a busca falhar

Quando algo dá errado, o app salva um **print da tela** (`debug_mediador.png`)
e o **HTML da página** (`debug_mediador.html`) na pasta do programa, e mostra
links para baixar os dois logo abaixo da mensagem de erro. Esses arquivos
mostram o que o site realmente exibiu e bastam para ajustar o programa.

## Estrutura do projeto

- `iniciar.bat`: instala dependências (incluindo o navegador) e inicia o app.
- `app.py`: servidor web local (Flask) com a página, a busca e o download
  dos arquivos de diagnóstico.
- `fontes/navegador.py`: automação do navegador (esperar a verificação,
  marcar o critério, digitar o CNPJ, pesquisar, ler o resultado).
- `fontes/comum.py`: validação de CNPJ e leitura da tabela de resultados.
- `fontes/mediador.py`: configuração do Mediador (endereço, textos dos campos,
  formato do número da solicitação e link do extrato).
- `templates/`, `static/`: interface web (HTML/CSS/JS).

## Observações

- É necessária conexão com a internet: a consulta é feita em tempo real, sem
  armazenar dados.
- Roda apenas em `127.0.0.1` (acesso local à sua máquina).
