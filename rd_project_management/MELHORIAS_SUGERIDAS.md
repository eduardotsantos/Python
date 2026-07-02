# Sugestões de Melhoria — Orion P&D

> Revisão técnica do sistema com foco em aderência à gestão de projetos de inovação (P&D), módulo de IA e captura de recursos.

---

## 1. MELHORIAS PRIORITÁRIAS — EXPERIÊNCIA GERAL

### 1.1 Dashboard Executivo com KPIs de Inovação
- Adicionar painel com **Índice de Maturidade do Portfolio** (TRL médio ponderado)
- Mostrar **Heatmap de risco** por projeto na visão de portfolio
- Gráfico **Burn Rate projetado × planejado** por projeto e consolidado
- **Alertas inteligentes** com link direto para ação: *"3 marcos vencem em 7 dias. [Ver cronograma]"*

### 1.2 Gestão de Marcos (Cronograma)
- Adicionar **dependências entre projetos** no portfolio (não só dentro de um projeto)
- Implementar **Critical Path Method (CPM)** visual — destacar o caminho crítico em vermelho
- Suporte a **Kanban integrado ao cronograma** — ao mover tarefa para "Concluído" no Kanban, o marco é atualizado
- Baseline de cronograma: salvar baseline original e comparar com execução (SV no EVM)
- **Notificação automática** por email quando um marco atrasa (já tem scheduler, só falta o trigger)

### 1.3 Controle Financeiro
- **Curva S de desembolso** — planejado × realizado por período
- Categorização de despesas por **Natureza Contábil** (alinhado à prestação de contas FINEP: custeio, capital, bolsas, RH)
- **Aprovação em dois níveis**: gerente aprova → admin confirma pagamento
- Exportar planilha de prestação de contas no formato FINEP/FAPESC (campo obrigatório: NF, CNPJ fornecedor, categoria, período)
- **Alertas de vencimento de boleto** (enviar email X dias antes)

### 1.4 Gestão de Recursos Humanos
- Controle de **carga horária máxima** por colaborador (ex: 160h/mês)
- Alerta de **superalocação**: quando colaborador ultrapassa 100% em algum projeto
- Relatório de **produtividade por colaborador** (horas planejadas × realizadas)
- Integração com **espelho de ponto** (importação CSV)

### 1.5 Módulo de Prestação de Contas
- Criar módulo dedicado de **Prestação de Contas** (por chamada vinculada)
- Checklists automáticos de documentos obrigatórios por fonte (FINEP, FAPESC, BNDES)
- Status de cada item documental: pendente / entregue / aprovado / reprovado
- Geração de **relatório de conformidade documental** em PDF

---

## 2. MELHORIAS NO MÓDULO DE IA

### 2.1 Chat Assistente (PMO Autônomo)
**Problema atual**: o chat envia todo o contexto a cada mensagem, sem memória eficiente.

**Sugestões**:
- Implementar **memória de contexto resumida** (sumarizar histórico longo antes de enviar)
- Adicionar **modo de briefing ativo**: o assistente inicia a conversa com o resumo do dia sem o usuário perguntar
- **Comandos rápidos** (/relatorio, /riscos, /cronograma, /despesas) que ativam análises específicas
- **Contexto por projeto**: filtrar dados apenas do projeto ativo no chat
- Salvar **favoritos de perguntas** — usuário pode reutilizar perguntas frequentes

### 2.2 Análise de Risco por IA
**Problema atual**: análise é pontual (on-demand), não proativa.

**Sugestões**:
- Análise **automática diária** de risco (já existe o scheduler às 7h — aproveitar)
- **Score de risco histórico**: mostrar evolução do risco ao longo do tempo (gráfico)
- Detecção de **padrões cross-projeto**: "4 de 6 projetos com atraso >10% têm o mesmo recurso alocado"
- Integrar risco financeiro com **câmbio** (para projetos com componente internacional)
- Alertas de risco por **email automático** quando score ultrapassa threshold configurável

### 2.3 Geração de Relatórios IA
**Sugestão**:
- Adicionar templates de relatório específicos por agência:
  - **FINEP**: Relatório Técnico de Acompanhamento (RTA) e Relatório Final (RF)
  - **FAPESC**: Relatório de Atividades e Prestação de Contas
  - **EMBRAPII**: Relatório de Progresso Técnico-Científico
- **Versionamento de relatórios** — histórico de versões geradas
- **Assinatura digital** no PDF (integração com Adobe Sign / DocuSign)
- Exportar em **formato Word** editável (.docx) além de PDF

### 2.4 Matching Projeto-Edital
**Problema atual**: matching usa apenas texto livre, sem estrutura semântica.

**Sugestões**:
- Classificar projetos e editais por **taxonomia TRL** — só sugerir editais compatíveis com o TRL do projeto
- **Score de compatibilidade** (0-100%) com justificativa detalhada
- **Alertas automáticos** quando novo edital compatível é encontrado (email ao PM responsável)
- Histórico de matchings anteriores — saber quais editais foram considerados e por quê
- Integrar com **Google Scholar / CAPES** para verificar publicações do time (reforça elegibilidade)

### 2.5 Geração de Proposta
**Sugestão**:
- Adicionar **seções configuráveis** por template de chamada (objetivo, metodologia, cronograma, orçamento, equipe)
- Gerar **memorial descritivo de equipe** automaticamente baseado nos recursos cadastrados
- **Revisão colaborativa**: PM edita a proposta gerada, com controle de versão
- Exportar proposta em formato **SISGF (FINEP)** quando aplicável

---

## 3. ROBÔS DE CAPTURA DE RECURSOS (SCRAPERS)

### 3.1 Problemas Identificados nos Scrapers Atuais

#### FINEP (`finep_scraper.py`)
```
Problema: Tentativa de múltiplas URLs em sequência — site do governo com Joomla/CDN
muda layout com frequência. Falha silenciosa sem dados.
```
**Melhorias**:
- **FINEP possui API REST**: usar `https://www.finep.gov.br/api/chamadas` (verificar disponibilidade)
- Implementar **FINEP RSS Feed** como alternativa: `https://www.finep.gov.br/chamadas-publicas/rss`
- Adicionar **scraping do Portal de Dados Abertos do Governo** (`dados.gov.br`) — FINEP publica datasets de chamadas
- Usar **Selenium/Playwright** como fallback para páginas com JavaScript pesado
- Cache com TTL de 6 horas para evitar bloqueio por excesso de requisições
- **Retry com exponential backoff** (atualmente falha sem retry)

#### FAPESC (`fapesc_scraper.py`)
```
Problema: TLS verification desabilitada (verify=False) — risco de segurança.
```
**Melhorias**:
- Instalar certificado correto ou usar `certifi` com atualização automática
- FAPESC usa WordPress — aproveitar **WP REST API**: `https://fapesc.sc.gov.br/wp-json/wp/v2/posts?categories=chamadas`
- Capturar **deadline** da chamada (data de encerramento) — crítico para alertas
- Extrair **valor máximo financiável** de cada chamada

#### BNDES (`bndes_scraper.py`)
```
Problema: BNDES usa portal IBM WebSphere — difícil de scraping direto.
```
**Melhorias**:
- BNDES tem **API de dados abertos**: `https://dadosabertos.bndes.gov.br/`
- Usar endpoint `https://dadosabertos.bndes.gov.br/api/3/action/datastore_search?resource_id=...`
- Monitorar também **BNDES Finem, BNDES BK** (inovação tecnológica) e **BNDES Finame** (equipamentos P&D)

### 3.2 Nova Arquitetura de Captura Sugerida

```
Fontes a Adicionar:
├── CNPq (Plataforma Sucupira + site)
│   └── https://www.gov.br/cnpq/pt-br/acesso-a-informacao/acoes-e-programas/programas/chamadas
├── EMBRAPII
│   └── https://embrapii.org.br/chamadas/
├── FAPERGS, FAPESP, FAPEMIG, FAPERJ (FAPs estaduais)
├── Portal de Convênios (SICONV/TRANSFEREGOV)
│   └── API REST disponível em transferegov.sistema.gov.br
├── Diário Oficial da União (DOU) — editais publicados
│   └── https://www.in.gov.br/servicos/buscar-no-dou
└── MCTI — chamadas de programas como Sibratec, Rhae
```

**Implementação recomendada**:
```python
# Scheduler mais robusto com controle de saúde
class ScraperJob:
    def __init__(self, name, scraper_fn, interval_hours=6):
        self.name = name
        self.scraper_fn = scraper_fn
        self.interval_hours = interval_hours
        self.last_run = None
        self.last_count = 0
        self.error_count = 0
    
    def run_with_retry(self, max_retries=3):
        for attempt in range(max_retries):
            try:
                result = self.scraper_fn()
                self.error_count = 0
                return result
            except Exception as e:
                self.error_count += 1
                wait = 2 ** attempt * 30  # 30s, 60s, 120s
                time.sleep(wait)
        return []
```

### 3.3 Dashboard de Saúde dos Scrapers
Criar painel admin mostrando:
- Data/hora da última execução de cada scraper
- Quantidade de chamadas capturadas
- Status (OK / Erro / Sem dados)
- Botão para forçar re-sincronização manual

---

## 4. MELHORIAS DE ADERÊNCIA AO PMBOK 8 / INOVAÇÃO

### 4.1 Gestão de Valor (PMBOK 8 — Entrega de Valor)
- Adicionar **Business Case** por projeto: problema, solução, impacto esperado, KPIs de sucesso
- **OKRs de Inovação** por projeto/programa: Objetivo + Key Results mensuráveis
- **Roadmap de inovação** visual do portfolio por linha do tempo
- **Indicador de Impacto Social** e **Impacto Ambiental** (ESG) por projeto
- Módulo de **Lições Aprendidas** estruturado (categorizado por fase, tipo de lição, projeto)

### 4.2 Gestão de Conhecimento (P&D)
- **Repositório de PI (Propriedade Intelectual)**: registrar patentes, pedidos, publicações por projeto
- **Publicações Científicas**: vincular papers ao projeto (DOI, periódico, fator de impacto)
- **Know-how técnico**: base de conhecimento interna por tecnologia/processo desenvolvido
- Rastreabilidade **P&D → Produto**: mostrar quais projetos geraram produtos/serviços

### 4.3 Gestão de Parceiros e Ecossistema
- Módulo de **Parceiros de P&D**: universidades, institutos, empresas parceiras
- **Mapa de relacionamentos**: visualizar conexões entre projetos e parceiros
- **Acordos de parceria** (contratos, cartas de intenção) vinculados ao projeto

### 4.4 TRL e Inovação
- **TRL Automático sugerido por IA**: baseado na descrição do projeto e documentos anexados
- Comparativo **TRL início vs. TRL fim** por projeto concluído (impacto de maturação)
- **Mapa de calor TRL × investimento** — portfolio view identificando onde concentrar recursos

### 4.5 Indicadores de Desempenho Inovação (Innovation KPIs)
Adicionar no dashboard:
| KPI | Cálculo |
|---|---|
| Taxa de conversão edital → projeto | Projetos aprovados / editais submetidos |
| ROI P&D | Valor Realizado / Investimento Total |
| Tempo médio de ciclo de inovação | Data início → TRL 7+ |
| Índice de reuso de tecnologia | Projetos que usam tecnologia de projetos anteriores |
| NPS de inovação interno | Survey trimestral com equipe |

---

## 5. MELHORIAS TÉCNICAS E DE SEGURANÇA

### 5.1 Segurança
- ✅ **Redefinição de senha por email** (implementado nesta sessão)
- Adicionar **2FA (Autenticação de Dois Fatores)** via TOTP (Google Authenticator)
- **Rate limiting** nas rotas de login e forgot-password (evitar brute force)
- Adicionar **CSRF protection** explícita com Flask-WTF (verificar se está ativo em todos os forms)
- **Log de tentativas de login falhas** com bloqueio temporário após N tentativas
- **Validação de força de senha** na criação/alteração (mínimo: 8 chars, maiúscula, número, especial)
- Implementar **HTTPS enforcement** com `flask-talisman`

### 5.2 Performance
- Adicionar **paginação** em todas as listagens (projetos, despesas, marcos, timesheets)
- **Cache Redis** para dados do dashboard (evitar recalcular EVM, status report a cada request)
- **Lazy loading** de dados pesados (KPIs) via AJAX após carregamento inicial da página
- **Compressão gzip** das respostas (Flask-Compress)
- Otimizar queries N+1 com `joinedload`/`selectinload` no SQLAlchemy

### 5.3 API REST
- Expor **API REST** para integração com sistemas externos (ERP, SIGA, etc.)
- Documentação automática com **Flask-RESTX + Swagger UI**
- **Webhooks** para notificar sistemas externos de eventos (novo projeto, marco concluído, etc.)

### 5.4 Notificações
- Implementar **notificações in-app** (sino na navbar) além de email
- **Canais de notificação configuráveis** por usuário: email / WhatsApp (via API) / Slack
- **Resumo semanal** automático além do briefing diário

---

## 6. UX/UI

- **Modo escuro nativo** (o login já é escuro — estender ao sistema interno)
- **Tour guiado** de onboarding para novos usuários (Shepherd.js)
- **Atalhos de teclado** para ações frequentes (Ctrl+N = novo projeto, etc.)
- **Busca global** (Ctrl+K) — encontrar projetos, marcos, despesas, usuários rapidamente
- **Favoritos**: usuário pode fixar projetos frequentes no dashboard
- **Modos de visualização** nas listagens: tabela, cards, kanban, timeline
- **Responsividade móvel** melhorada — gestores precisam acessar pelo celular em visitas técnicas

---

## 7. INTEGRAÇÕES EXTERNAS

| Sistema | Benefício |
|---|---|
| **SIAFI / SIAGRO** | Conciliação com execução orçamentária federal |
| **SIGEF (FINEP)** | Sincronização de dados de projetos aprovados |
| **Plataforma Lattes (CNPq)** | Importar currículo de pesquisadores |
| **INPI** | Status de patentes e pedidos de PI |
| **Google Drive / OneDrive** | Armazenar documentos diretamente na nuvem |
| **Jira / Trello** | Sincronizar tarefas com ferramentas ágeis |
| **Power BI / Looker Studio** | Exportar dados para BI externo via API |
| **DocuSign / ClickSign** | Assinatura digital de relatórios e contratos |

---

## PRIORIDADE DE IMPLEMENTAÇÃO

| # | Melhoria | Esforço | Impacto |
|---|---|---|---|
| 1 | Prestação de contas estruturada (FINEP/FAPESC) | Médio | Muito Alto |
| 2 | Scrapers via API (FINEP, BNDES dados abertos) | Baixo | Alto |
| 3 | Alertas automáticos (marcos, editais, riscos) | Baixo | Alto |
| 4 | 2FA + rate limiting login | Baixo | Alto |
| 5 | Paginação + cache dashboard | Médio | Alto |
| 6 | Curva S de desembolso | Baixo | Médio |
| 7 | Templates de relatório por agência | Médio | Alto |
| 8 | Dashboard saúde dos scrapers | Baixo | Médio |
| 9 | Módulo de PI e publicações científicas | Médio | Médio |
| 10 | API REST + Swagger | Alto | Alto |

---

*Documento gerado em revisão técnica do sistema Orion P&D — 2026-07-02*
