# Manual do Usuário — Sistema de Gestão de Projetos de P&D

**Versão 1.0**

---

## Sumário

1. [Introdução](#1-introdução)
2. [Requisitos e Instalação](#2-requisitos-e-instalação)
3. [Primeiro Acesso](#3-primeiro-acesso)
4. [Autenticação](#4-autenticação)
   - 4.1 Login
   - 4.2 Registro de Novo Usuário
   - 4.3 Logout
5. [Painel de Projetos](#5-painel-de-projetos)
   - 5.1 Visão Geral
   - 5.2 Filtros e Busca
   - 5.3 Criar Novo Projeto
   - 5.4 Visualizar Projeto
   - 5.5 Editar Projeto
   - 5.6 Excluir Projeto
6. [Controle de Despesas](#6-controle-de-despesas)
   - 6.1 Listar Despesas
   - 6.2 Registrar Nova Despesa
   - 6.3 Editar e Excluir Despesas
7. [Gestão de Recursos](#7-gestão-de-recursos)
   - 7.1 Pessoas e Máquinas
   - 7.2 Adicionar Recurso
   - 7.3 Editar e Excluir Recursos
8. [Cronograma](#8-cronograma)
   - 8.1 Gráfico de Gantt
   - 8.2 Criar Marcos/Etapas
   - 8.3 Progresso Interativo
9. [Timesheet (Registro de Horas)](#9-timesheet-registro-de-horas)
   - 9.1 Listar Registros
   - 9.2 Registrar Horas
   - 9.3 Filtros por Mês e Colaborador
10. [Chamadas Públicas (FINEP/BNDES)](#10-chamadas-públicas-finepbndes)
    - 10.1 Visão Geral
    - 10.2 Atualizar Chamadas Automaticamente
    - 10.3 Filtrar e Buscar
    - 10.4 Detalhes da Chamada
11. [Referência de Campos](#11-referência-de-campos)
12. [Perguntas Frequentes](#12-perguntas-frequentes)

---

## 1. Introdução

O **Sistema de Gestão de Projetos de P&D** é uma aplicação web completa para gerenciar projetos de Pesquisa e Desenvolvimento. Ele oferece:

- **Cadastro de projetos** com orçamento, status e categorização
- **Controle de despesas** com aprovação e rastreamento por categoria
- **Gestão de recursos** humanos (pesquisadores, técnicos, bolsistas) e materiais (máquinas e equipamentos)
- **Cronograma** com gráfico de Gantt visual e progresso interativo
- **Timesheet** para registro de horas trabalhadas por colaborador
- **Chamadas públicas** com busca automática nos portais da FINEP e do BNDES

O sistema roda em um navegador web e pode ser acessado por qualquer dispositivo (computador, tablet ou celular).

---

## 2. Requisitos e Instalação

### Requisitos do sistema

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)
- Navegador web moderno (Chrome, Firefox, Edge, Safari)

### Instalação

Abra o terminal e execute os seguintes comandos:

```bash
cd rd_project_management
pip install -r requirements.txt
python app.py
```

O servidor será iniciado e exibirá a mensagem:

```
 * Running on http://0.0.0.0:5000
```

Abra o navegador e acesse **http://localhost:5000**.

### Variáveis de ambiente (opcional)

| Variável       | Descrição                          | Valor Padrão                        |
|----------------|------------------------------------|-------------------------------------|
| `SECRET_KEY`   | Chave secreta do Flask             | *(valor interno de desenvolvimento)* |
| `DATABASE_URL` | URI do banco de dados              | `sqlite:///rd_projects.db`          |
| `PORT`         | Porta do servidor                  | `5000`                              |

Para produção, defina a `SECRET_KEY` com um valor aleatório e seguro.

---

## 3. Primeiro Acesso

Na primeira execução, o sistema cria automaticamente um usuário administrador:

| Campo    | Valor                  |
|----------|------------------------|
| Usuário  | `admin`                |
| Senha    | `admin123`             |
| Email    | `admin@gestaopdp.com`  |
| Nome     | Administrador          |

> **Importante:** Altere a senha padrão após o primeiro login. Para isso, registre um novo usuário com seus dados reais.

---

## 4. Autenticação

### 4.1 Login

1. Acesse **http://localhost:5000** no navegador.
2. Você será redirecionado para a tela de login.
3. Preencha o campo **Usuário** e **Senha**.
4. Clique em **Entrar**.

Se as credenciais estiverem corretas, você será direcionado para a lista de projetos.

Caso tente acessar qualquer página sem estar logado, o sistema exibirá a mensagem *"Por favor, faça login para acessar esta página"* e redirecionará para o login.

### 4.2 Registro de Novo Usuário

1. Na tela de login, clique no link **Cadastre-se aqui**.
2. Preencha os campos:
   - **Nome Completo** — seu nome para exibição no sistema
   - **Email** — endereço de email válido
   - **Usuário** — nome de login (deve ser único)
   - **Senha** — mínimo de 6 caracteres
   - **Confirmar Senha** — repita a mesma senha
3. Clique em **Registrar**.

Após o registro, você será redirecionado para a tela de login e poderá entrar com as credenciais criadas.

### 4.3 Logout

1. No canto superior direito da barra de navegação, clique no seu nome.
2. No menu que aparece, clique em **Sair**.

Você será desconectado e redirecionado para a tela de login.

---

## 5. Painel de Projetos

### 5.1 Visão Geral

Ao fazer login, você verá a **Lista de Projetos**. No topo da página são exibidos quatro cartões de resumo:

| Cartão            | Descrição                                      |
|-------------------|-------------------------------------------------|
| **Total Projetos** | Quantidade total de projetos cadastrados        |
| **Em Andamento**   | Projetos com status "Em Andamento"              |
| **Concluídos**     | Projetos com status "Concluído"                 |
| **Orçamento Total**| Soma dos orçamentos de todos os projetos (R$)   |

Abaixo dos cartões está a tabela de projetos com as colunas:
- **Código** — identificador único do projeto (ex.: PD-2024-001)
- **Título** — nome do projeto
- **Categoria** — tipo de pesquisa/inovação
- **Status** — estado atual do projeto (indicado por etiqueta colorida)
- **Orçamento** — valor em Reais
- **Período** — data de início e fim

### 5.2 Filtros e Busca

Acima da tabela de projetos existem dois filtros:

- **Campo de busca** — digite parte do título, código ou descrição do projeto e clique em **Filtrar**
- **Status** — selecione um status específico no menu suspenso (Planejamento, Em Andamento, Concluído, Cancelado)

Para limpar os filtros, clique no botão **Limpar**.

### 5.3 Criar Novo Projeto

1. Na lista de projetos, clique no botão **Novo Projeto** (canto superior direito).
2. Preencha o formulário:

| Campo               | Obrigatório | Descrição                                                |
|---------------------|-------------|----------------------------------------------------------|
| Código do Projeto   | Sim         | Identificador único (ex.: PD-2024-001)                   |
| Título              | Sim         | Nome descritivo do projeto                               |
| Descrição           | Não         | Detalhamento do projeto                                  |
| Categoria           | Não         | Pesquisa Básica, Pesquisa Aplicada, Desenvolvimento Experimental, Inovação Tecnológica ou Inovação de Processo |
| Status              | Não         | Planejamento (padrão), Em Andamento, Concluído, Cancelado|
| Data Início         | Não         | Data de início do projeto                                |
| Data Término        | Não         | Data prevista de conclusão                               |
| Orçamento (R$)      | Não         | Valor total do orçamento                                 |
| Fonte de Recursos   | Não         | Recursos Próprios, FINEP, BNDES, CNPq, CAPES, FAPESP, Embrapii, Lei do Bem, Lei de Informática ou Misto |
| Responsável         | Não         | Usuário responsável pelo projeto (lista de usuários cadastrados) |

3. Clique em **Criar Projeto**.

Após a criação, você será redirecionado para a lista de projetos com uma mensagem de confirmação.

### 5.4 Visualizar Projeto

1. Na lista de projetos, clique no botão de visualização (ícone de olho) ou no título do projeto.
2. A página de detalhes exibe:
   - **Cartões de resumo**: Orçamento, Despesas totais, Horas registradas e Progresso geral
   - **Informações do projeto**: descrição, status, categoria, período, fonte de recursos e responsável
   - **Acesso rápido**: links para Despesas, Recursos, Cronograma e Timesheet, cada um com a quantidade de registros

### 5.5 Editar Projeto

1. Na página de detalhes do projeto, clique em **Editar** (ícone de lápis).
2. Modifique os campos desejados.
3. Clique em **Salvar Alterações**.

### 5.6 Excluir Projeto

1. Na página de detalhes do projeto, clique em **Excluir** (ícone de lixeira).
2. Uma janela de confirmação será exibida: *"Tem certeza que deseja excluir este projeto e todos os dados associados?"*
3. Confirme para excluir.

> **Atenção:** A exclusão de um projeto remove permanentemente todas as despesas, recursos, marcos do cronograma e registros de horas associados.

---

## 6. Controle de Despesas

### 6.1 Listar Despesas

1. Acesse a página de um projeto e clique em **Despesas** no menu de acesso rápido.
2. A página exibe cartões de resumo:

| Cartão            | Descrição                                            |
|-------------------|------------------------------------------------------|
| **Orçamento**      | Orçamento total do projeto                           |
| **Total Despesas** | Soma de todas as despesas registradas                |
| **Aprovadas**      | Total de despesas com status "Aprovada"              |
| **Pendentes**      | Total de despesas com status "Pendente"              |

3. A tabela lista todas as despesas com: Data, Descrição, Categoria, Fornecedor, Valor e Status.

**Filtros disponíveis:**
- **Categoria**: Pessoal, Equipamento, Material, Viagem, Serviço Terceiro, Outros
- **Status**: Pendente, Aprovada, Rejeitada, Paga

### 6.2 Registrar Nova Despesa

1. Na lista de despesas, clique em **Nova Despesa**.
2. Preencha o formulário:

| Campo            | Obrigatório | Descrição                                     |
|------------------|-------------|------------------------------------------------|
| Descrição        | Sim         | O que foi comprado/contratado                  |
| Categoria        | Sim         | Tipo da despesa (veja categorias acima)        |
| Valor (R$)       | Sim         | Valor da despesa                               |
| Data             | Sim         | Data da despesa (padrão: hoje)                 |
| Status           | Não         | Pendente (padrão), Aprovada, Rejeitada, Paga  |
| Fornecedor       | Não         | Nome do fornecedor                             |
| Nº Nota Fiscal   | Não         | Número do documento fiscal                     |
| Observações      | Não         | Informações adicionais                         |

3. Clique em **Registrar**.

O valor é formatado automaticamente com duas casas decimais ao sair do campo.

### 6.3 Editar e Excluir Despesas

- **Editar:** Clique no ícone de lápis na linha da despesa, modifique os dados e salve.
- **Excluir:** Clique no ícone de lixeira na linha da despesa e confirme a exclusão.

#### Cores das etiquetas de status

| Status      | Cor       |
|-------------|-----------|
| Pendente    | Amarelo   |
| Aprovada    | Verde     |
| Rejeitada   | Vermelho  |
| Paga        | Azul      |

---

## 7. Gestão de Recursos

### 7.1 Pessoas e Máquinas

O módulo de Recursos permite cadastrar dois tipos:

- **Pessoa** — pesquisadores, técnicos, bolsistas, gestores e demais colaboradores do projeto
- **Máquina** — equipamentos, instrumentos de laboratório e demais recursos materiais

Acesse a página de um projeto e clique em **Recursos** no menu de acesso rápido.

A página exibe cartões de resumo:
- **Pessoas** — quantidade de pessoas alocadas
- **Máquinas/Equipamentos** — quantidade de máquinas cadastradas
- **Custo Estimado Total** — soma de (horas alocadas × custo/hora) de todos os recursos

Os recursos são exibidos em formato de cartões visuais, com ícone diferente para pessoa (silhueta) e máquina (engrenagem).

Você pode filtrar por tipo clicando nos botões: **Todos**, **Pessoas** ou **Máquinas**.

### 7.2 Adicionar Recurso

1. Clique em **Novo Recurso**.
2. Preencha o formulário:

| Campo           | Obrigatório | Descrição                                        |
|-----------------|-------------|--------------------------------------------------|
| Tipo            | Sim         | Pessoa ou Máquina                                |
| Nome            | Sim         | Nome do colaborador ou do equipamento            |
| Função/Papel    | Não         | Ex.: Pesquisador, Técnico, Bolsista              |
| Status          | Não         | Ativo (padrão) ou Inativo                        |
| Horas Alocadas  | Não         | Total de horas previstas para o recurso (em incrementos de 0,5h) |
| Custo/Hora (R$) | Não         | Custo por hora de utilização                     |
| Data Início     | Não         | Início da alocação do recurso no projeto         |
| Data Fim        | Não         | Fim da alocação do recurso no projeto            |
| Observações     | Não         | Notas adicionais                                 |

3. Clique em **Salvar**.

### 7.3 Editar e Excluir Recursos

Cada cartão de recurso possui botões de **Editar** (lápis) e **Excluir** (lixeira) no canto inferior direito.

---

## 8. Cronograma

### 8.1 Gráfico de Gantt

Acesse a página de um projeto e clique em **Cronograma** no menu de acesso rápido.

A página exibe:

1. **Barra de progresso geral** — média do progresso de todos os marcos
2. **Gráfico de Gantt** — visualização gráfica dos marcos com:
   - Barras horizontais proporcionais ao período de cada marco
   - Preenchimento interno indicando o progresso percentual
   - Cores por status:

| Status        | Cor       |
|---------------|-----------|
| Pendente      | Azul claro|
| Em Andamento  | Amarelo   |
| Concluído     | Verde     |
| Atrasado      | Vermelho  |

3. **Tabela de marcos** — lista detalhada com número, título, datas de início e término, barra de progresso com controle deslizante, status e ações

### 8.2 Criar Marcos/Etapas

1. Clique em **Novo Marco**.
2. Preencha o formulário:

| Campo       | Obrigatório | Descrição                                                 |
|-------------|-------------|-----------------------------------------------------------|
| Título      | Sim         | Nome do marco ou etapa (ex.: "Fase 1 - Revisão Bibliográfica") |
| Ordem       | Não         | Número de sequência para ordenação no cronograma          |
| Descrição   | Não         | Detalhamento da etapa                                     |
| Data Início | Sim         | Data de início da etapa                                   |
| Data Término| Sim         | Data prevista de conclusão da etapa                       |
| Progresso   | Não         | Percentual de conclusão (0% a 100%, controle deslizante)  |
| Status      | Não         | Pendente, Em Andamento, Concluído, Atrasado               |

3. Clique em **Salvar**.

### 8.3 Progresso Interativo

Na tabela de marcos, cada linha possui um **controle deslizante de progresso** (slider). Ao arrastar o controle:

- O percentual é atualizado em tempo real na tela
- O valor é salvo automaticamente no banco de dados via AJAX (sem recarregar a página)
- O status é atualizado automaticamente:
  - **0%** → Pendente
  - **1% a 99%** → Em Andamento
  - **100%** → Concluído

O controle avança em incrementos de 5%.

---

## 9. Timesheet (Registro de Horas)

### 9.1 Listar Registros

Acesse a página de um projeto e clique em **Timesheet** no menu de acesso rápido.

A página exibe:

1. **Cartões de resumo**:
   - **Total de Horas** — soma de todas as horas registradas
   - **Registros** — quantidade de lançamentos
   - **Colaboradores** — quantidade de pessoas que registraram horas

2. **Horas por Colaborador** — barras de progresso mostrando a proporção de horas de cada colaborador em relação ao total, com o nome e a quantidade de horas

3. **Tabela de registros**: Data, Colaborador, Atividade, Marco relacionado (se houver), Horas e ações

### 9.2 Registrar Horas

1. Clique em **Registrar Horas**.
2. Preencha o formulário:

| Campo                   | Obrigatório | Descrição                                         |
|-------------------------|-------------|----------------------------------------------------|
| Data                    | Sim         | Data do registro                                   |
| Horas                   | Sim         | Quantidade de horas (0,5 a 24, em incrementos de 0,5) |
| Atividade               | Sim         | Descrição da atividade realizada                   |
| Marco/Etapa Relacionada | Não         | Selecione o marco do cronograma associado          |
| Observações             | Não         | Notas adicionais sobre o trabalho                  |

3. Clique em **Registrar**.

O registro é associado automaticamente ao usuário logado.

### 9.3 Filtros por Mês e Colaborador

- **Mês** — selecione um mês no formato AAAA-MM para ver apenas os registros daquele período
- **Colaborador** — filtre por um usuário específico (útil para gestores que precisam ver horas de cada membro da equipe)

---

## 10. Chamadas Públicas (FINEP/BNDES)

### 10.1 Visão Geral

Na barra de navegação superior, clique em **Chamadas Públicas**. Esta seção mantém um cadastro de editais e chamadas públicas de fomento provenientes da **FINEP** e do **BNDES**.

A página exibe:

1. **Cartões de resumo**:
   - **Total Chamadas** — quantidade total no banco de dados
   - **FINEP** — quantidade de chamadas da FINEP
   - **BNDES** — quantidade de chamadas do BNDES

2. **Lista de chamadas** — cada chamada é exibida como um cartão contendo:
   - **Fonte** — etiqueta FINEP (azul) ou BNDES (verde)
   - **Tema** — área temática da chamada
   - **Data de publicação**
   - **Título** — nome da chamada (clicável para ver detalhes)
   - **Descrição** — resumo com até 200 caracteres
   - **Fonte de Recursos** e **Público-Alvo** (quando disponíveis)
   - **Link** — botão para acessar o edital original no site da instituição

Os cartões possuem uma borda lateral colorida: **azul** para FINEP e **verde** para BNDES.

### 10.2 Atualizar Chamadas Automaticamente

Para buscar as chamadas mais recentes dos portais da FINEP e do BNDES:

1. Clique no botão **"Atualizar do FINEP/BNDES"** (ícone de seta circular) no topo da página.
2. O botão exibirá um indicador de carregamento (spinner) enquanto a busca é realizada.
3. Ao finalizar, uma notificação será exibida informando:
   - Quantidade de chamadas encontradas na FINEP
   - Quantidade de chamadas encontradas no BNDES
   - Eventuais erros de conexão
4. A página será recarregada automaticamente após 1,5 segundo.

**Como funciona internamente:**
- O sistema acessa o portal da **FINEP** em `www.finep.gov.br/chamadas-publicas` e extrai os dados das chamadas publicadas.
- O sistema acessa o portal do **BNDES** em `www.bndes.gov.br` nas seções de editais e chamadas públicas e extrai os dados.
- Os dados extraídos incluem: título, tema (classificado automaticamente), descrição, data de publicação, fonte de recursos e público-alvo.
- Chamadas já existentes no banco são atualizadas; novas chamadas são inseridas.
- A busca não duplica registros — se uma chamada com mesmo título e fonte já existir, ela é apenas atualizada.

**Temas classificados automaticamente:**
A partir do conteúdo da chamada, o sistema identifica e atribui temas como: Saúde, Energia, Agropecuária, Tecnologia da Informação, Transformação Digital, Sustentabilidade, Defesa, Biotecnologia, Nanotecnologia, Inovação, Infraestrutura, Desenvolvimento Social, Mudança Climática, entre outros.

### 10.3 Filtrar e Buscar

Acima da lista de chamadas, utilize:

- **Campo de busca** — pesquise por palavras no título, descrição ou tema
- **Fonte** — selecione "FINEP" ou "BNDES" para filtrar por instituição

Clique em **Filtrar** para aplicar ou **Limpar** para remover os filtros.

### 10.4 Detalhes da Chamada

Clique no título de uma chamada para ver a página de detalhes completa, que exibe:

- Fonte e Tema (etiquetas)
- Título completo
- Descrição completa
- Data de Publicação
- Prazo (quando disponível)
- Fonte de Recursos
- Público-Alvo
- Link para o edital oficial (abre em nova aba)
- Data da última atualização no sistema

---

## 11. Referência de Campos

### Status dos Projetos

| Status         | Descrição                                             |
|----------------|-------------------------------------------------------|
| Planejamento   | Projeto em fase de elaboração, ainda não iniciado     |
| Em Andamento   | Projeto em execução                                   |
| Concluído      | Projeto finalizado com sucesso                        |
| Cancelado      | Projeto cancelado ou descontinuado                    |

### Categorias de Projeto

| Categoria                      | Descrição                                                          |
|--------------------------------|--------------------------------------------------------------------|
| Pesquisa Básica                | Investigação original sem aplicação prática específica             |
| Pesquisa Aplicada              | Investigação dirigida a um objetivo prático determinado            |
| Desenvolvimento Experimental   | Trabalho sistemático baseado em conhecimento existente             |
| Inovação Tecnológica           | Implementação de produto ou processo novo ou melhorado             |
| Inovação de Processo           | Método de produção ou distribuição novo ou melhorado               |

### Categorias de Despesa

| Categoria          | Exemplos                                                     |
|--------------------|--------------------------------------------------------------|
| Pessoal            | Salários, bolsas, encargos trabalhistas                      |
| Equipamento        | Instrumentos de laboratório, computadores, servidores        |
| Material           | Reagentes, insumos, material de escritório                   |
| Viagem             | Passagens, hospedagem, diárias para eventos e congressos     |
| Serviço Terceiro   | Consultoria externa, análises laboratoriais, manutenção      |
| Outros             | Despesas que não se enquadram nas categorias anteriores       |

### Fontes de Recursos

| Fonte               | Descrição                                                    |
|----------------------|--------------------------------------------------------------|
| Recursos Próprios    | Financiamento com capital da própria instituição             |
| FINEP                | Financiadora de Estudos e Projetos                           |
| BNDES                | Banco Nacional de Desenvolvimento Econômico e Social         |
| CNPq                 | Conselho Nacional de Desenvolvimento Científico              |
| CAPES                | Coord. de Aperfeiçoamento de Pessoal de Nível Superior      |
| FAPESP               | Fundação de Amparo à Pesquisa do Estado de São Paulo         |
| Embrapii             | Empresa Brasileira de Pesquisa e Inovação Industrial         |
| Lei do Bem           | Incentivos fiscais para inovação tecnológica (Lei 11.196/05)|
| Lei de Informática   | Incentivos para o setor de TIC (Lei 8.248/91)               |
| Misto                | Combinação de múltiplas fontes de financiamento              |

### Tipos de Recurso

| Tipo     | Descrição                                                         |
|----------|-------------------------------------------------------------------|
| Pessoa   | Colaboradores humanos do projeto (pesquisadores, técnicos, etc.)  |
| Máquina  | Equipamentos e instrumentos utilizados no projeto                 |

---

## 12. Perguntas Frequentes

**P: Esqueci minha senha, como recuperar?**
R: Na versão atual, solicite ao administrador do sistema para criar um novo usuário. A funcionalidade de recuperação de senha será incluída em versões futuras.

**P: Posso usar o sistema em um celular ou tablet?**
R: Sim. A interface é responsiva e se adapta a diferentes tamanhos de tela. Todos os menus e tabelas se ajustam automaticamente.

**P: O que acontece ao excluir um projeto?**
R: Todas as despesas, recursos, marcos do cronograma e registros de timesheet associados ao projeto são excluídos permanentemente. Esta ação não pode ser desfeita.

**P: As chamadas públicas são atualizadas sozinhas?**
R: Não automaticamente. Você deve clicar no botão **"Atualizar do FINEP/BNDES"** para buscar as chamadas mais recentes. Recomenda-se fazer essa atualização periodicamente (ex.: semanalmente).

**P: Por que a atualização de chamadas retornou erros?**
R: Isso pode ocorrer se os portais da FINEP ou BNDES estiverem fora do ar, se a estrutura das páginas tiver sido alterada, ou se houver problemas de conectividade com a internet. Tente novamente mais tarde.

**P: Como altero a porta do servidor?**
R: Defina a variável de ambiente `PORT` antes de executar o sistema. Exemplo: `PORT=8080 python app.py`

**P: Como uso um banco de dados PostgreSQL em vez do SQLite?**
R: Defina a variável de ambiente `DATABASE_URL` com a URI de conexão. Exemplo: `DATABASE_URL=postgresql://usuario:senha@servidor:5432/nome_do_banco python app.py`. Será necessário instalar o pacote `psycopg2-binary` adicionalmente.

**P: Vários usuários podem acessar ao mesmo tempo?**
R: Sim. Cada usuário faz login com suas próprias credenciais e o sistema suporta acesso concorrente. Os registros de timesheet são vinculados ao usuário logado.

**P: Os valores monetários suportam centavos?**
R: Sim. Todos os campos de valor aceitam até duas casas decimais e são formatados automaticamente no padrão brasileiro (R$ 1.234,56).

**P: Como imprimir um relatório?**
R: Use a função de impressão do navegador (Ctrl+P ou Cmd+P). O sistema oculta automaticamente a barra de navegação e os botões de ação na versão impressa, mantendo apenas o conteúdo relevante.

---

*Sistema de Gestão de Projetos de P&D — Versão 1.0*
