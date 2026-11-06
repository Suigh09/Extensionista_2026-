# Tarefas — Plataforma Extensionista

## Concluídas

- 05/11/2026: commit de implementação 0a6733b enviado ao GitHub origin/main após
  autorização do usuário para scope workflow. Push normal confirmado, sem force,
  sem bancos/credenciais/script local inseguro. CI remoto não declarado aprovado.

- 05/11/2026: usuário autorizou consolidar o projeto atual em commit e enviar ao
  origin/main. Revisão de segredos, diff --check e Ruff backend aprovados; script
  inseguro create_test_data.py preservado somente local, sem bancos/credenciais.
  Hash e estado do envio devem ser conferidos no Git, não presumidos pelo CI.

- 05/11/2026: #6 Projeto Homologação Alocação Automática preparado com aluno3
  líder/aluno4 integrante, orientador fluxo.orientador, proposta/entrega aprovadas
  e encaminhamento concluído. Sem agenda/avaliador; três candidatos compatíveis
  prof.orientador1/2/3 via competência nova de homologação. Novos logins e API da
  Secretaria validados; dump/reversão/inventário preservador em docs/HANDOFF.md.

- 05/11/2026: integrantes (somente nomes) e resumo também no card público, por
  autorização explícita. Snapshot publicado compartilhado com autenticado, PDF
  ainda privado. 16 testes backend/86 frontend/Ruff/lint/build e UI/API anônimas
  desktop/mobile aprovados. Sem alterar publicação; backend atualizado.

- 05/11/2026: acesso ao acervo público na mesma aba após logoff/login corrigido
  com observação de hash no App anônimo. 85 testes frontend/lint/build e três
  cenários reais de navegação sem sessão aprovados (desktop/mobile/link direto).

- 05/11/2026: card do acervo autenticado inclui nomes e resumo do snapshot da
  versão publicada, sem RA/IDs. Anônimo continua com metadados mínimos. 16 testes
  backend/82 frontend/Ruff/build aprovados e card/PDF reais desktop/mobile
  validados sem alterar publicação. Backend atualizado com imagem de reversão.

- 05/11/2026: acervo autenticado com título clicável e "Ler PDF" em nova aba,
  somente versão publicada vigente; anônimo/retirada/IDs de documentos bloqueados.
  16 testes backend da Mostra, 81 frontend, Ruff/lint/build aprovados. Leitura
  real da versão 3 do #5 validada desktop/mobile e SHA-256 conferido, sem mudanças
  na publicação. Backend Docker atualizado com backup e imagem de reversão.

- 05/11/2026: documento do acervo em duas colunas (edição à esquerda,
  versões/PDFs à direita), formulário sem sticky. Empilhado até 1100px.
  81 testes frontend/build e geometria real desktop/mobile aprovados;
  versões existentes preservadas, sem enviar documento.

- 05/11/2026: consentimento do acervo com checkbox 16×16 e texto adjacente,
  sem transbordar formulário. Geometria real desktop/mobile e 7 testes do acervo
  aprovados, build OK; nenhum documento enviado na validação.

- 05/11/2026: botão renomeado para "Publicar no Acervo" e navegação lista/detalhe
  corrigida mantendo hash completo no estado, não só tipo de página. 80 testes,
  lint/build e navegação real do líder do #5 desktop/mobile aprovados, inclusive
  voltar/avançar/recarga; sem enviar documento ou confirmar publicação.

- 05/11/2026: corrigida rota `#/group-evaluation/<projeto>` que caía no Início.
  Avaliações → Avaliar grupo abre presença/nota direta somente do projeto
  selecionado. 79 testes frontend, lint e build aprovados; clique e recarga reais
  do #5 validados como fluxo.avaliador em desktop/mobile sem enviar formulários.

- 05/11/2026: formulário por rubrica removido da avaliação do projeto e gestão
  retirada do perfil. Lançamento centralizado no fluxo já existente de presença,
  nota única 0–10 e observações; histórico/modelos antigos preservados. Frontend
  77 testes e build aprovados; detalhes em docs/HANDOFF.md.

- 05/11/2026: projeto #5 de homologação preparado por solicitação do usuário,
  proposta/entrega aprovadas e encaminhadas à Secretaria, avaliador designado,
  ainda sem agendamento. Cinco contas `fluxo.*` exclusivas com acessos HTTP
  validados; dados anteriores preservados. Backup/reversão em
  `.runtime/showcase-homologation-20261105-185449/`.

- 05/11/2026: liderança do projeto #2 definida como RA4001 após autorização
  explícita para escolher um integrante. Backup pontual e auditoria; permissões
  reais da API verificadas (RA4001 líder, RA4002 não). Demais registros preservados.

- 05/11/2026: fluxo completo do acervo implementado e aplicado no PostgreSQL Docker
  com backup. Nota do grupo/presenças ao orientador; formulário/PDF do líder;
  revisão com versões e aceite; publicação/retirada pela Secretaria. Backend final
  **165 passed em lotes**, cobertura consolidada **93,14%**, frontend **76 passed**,
  **4 E2E reais PostgreSQL** e **6 E2E de contrato**, concorrência real aprovada.
  Inventários anteriores preservados, sem atos acadêmicos no #2 nem commit/push.
  Guia docs/ACERVO_WORKFLOW_GUIDE.md e resultados em docs/HANDOFF.md.

- 05/11/2026: presença individual por checkbox e avaliação integrada do grupo
  (nota 0–10/observações) implementadas, compatíveis com rubricas e acervo. Migração
  0024 aplicada no PostgreSQL Docker com backup e inventário preservado. 150 testes
  backend (92,88%), 69 frontend e 2 Playwright aprovados; concorrência em PostgreSQL
  descartável e UI real do avaliador validadas. Projeto #2 ainda sem presença
  individual/nota, aguardando atos do usuário. Detalhes atuais em docs/HANDOFF.md.

- 05/11/2026: perfis Secretaria e Admin unificados no perfil **Administrador** (`ADMIN`). Usuário `secretaria.teste` passou a ter role `ADMIN`. Conta `admin.teste` com credencial de homologação existente, sem is_staff/is_superuser Django. Validação: 16 testes backend de planejamento, 7 frontend, Ruff/lint/build e logins/API reais aprovados.
- Validação da agenda em 05/11/2026: backend 119 testes/cobertura 92,29%; frontend 61 testes/cobertura configurada 91,64%; Playwright novo 4 cenários desktop/mobile; concorrência em PostgreSQL descartável e navegação real de secretaria.teste validadas. CI remoto/E2E legado completo não executados.
- Protótipo `ShowcaseSession` retirado do fluxo em 05/11/2026; dados preservados e rotas com resposta 410. Agenda usa `ShowcaseEntry` para integração real com presença/publicação. Não retomar o protótipo paralelo.
- 05/11/2026: agenda visual unificada, locais físicos/datas Secretaria/Admin, passos de 30 min, drag-and-drop/resize e alternativa sem arrastar, busca por integrantes/projeto/número. IDs curtos aditivos e links de notificações corrigidos; migrações preservadoras 0022/0023. Guia: `docs/SHOWCASE_PLANNING_GUIDE.md`.
- 05/11/2026: senha simplificada definida pelo usuário aplicada exclusivamente às cinco contas sintéticas de homologação; credencial E2E local sincronizada, backup DPAPI e cinco logins/sessões/logouts HTTP aprovados. Validação global de senhas preservada.
- 05/11/2026: redefinição autorizada de senhas das cinco contas sintéticas no PostgreSQL, com backup DPAPI dos hashes anteriores. Login/perfil/logout das cinco contas validados por HTTP via proxy, CSRF obrigatório e projeto preservado; divergência de credencial resolvida, sem alteração de contas reais ou SQLite.
- Padronização PostgreSQL Docker concluída em 05/11/2026: atalhos sem backend SQLite, conexão PostgreSQL verificada, iniciar/reutilizar/parar/reiniciar validados. SQLite preservado (hash idêntico), sem mesclar dados. Divergência inicial de credencial resolvida pela redefinição autorizada acima.
- 05/11/2026: melhorias de UX da agenda visual — `rowHeight` aumentado de 112 para 160 (maior espaço entre horários); cards de grupos não agendados reduzidos (padding 0.6rem, margin 0.5rem); múltiplos grupos podem ser agendados na mesma sala e mesmo horário (validação de conflito de sala removida; apenas o avaliador tem restrição de conflito). Frontend empilha múltiplos bookings no mesmo slot com offset de 42px. Testes: 127 backend passando, 66 frontend passando, build/lint OK.
- Backend Django com apps `accounts`, `academic`, `core`, `projects` (autenticação, salas, projetos, grupos, follow-ups, marcos, parcerias)
- Frontend Vite/React com telas de projeto, grupo, follow-up, marcos, parcerias
- Docker Compose (Postgres 17, backend, frontend)
- CI placeholder substituído por pipeline real (`.github/workflows/ci.yml`)
- Documentação de análise/modelagem da Entrega 1 (`documentos/`)
- Especificação da Sprint 7 com decisões Q1 a Q7 definidas e aceitas (`docs/sprints/SPRINT_07_SPEC.md`)
- AGENTS.md, AI_CONTEXT.md, README.md, HANDOFF.md, TASKS.md criados/atualizados
- **Sprint 7 backend concluído:**
  - Modelos `ShowcaseEntry`, `PublicationDocument`, `Publication` (backend/projects/models.py)
  - Novos Notification.Kind (DOCUMENT_PENDING, DOCUMENT_APPROVED, DOCUMENT_REJECTED, PUBLICATION_CREATED, PUBLICATION_WITHDRAWN)
  - Migrations 0013/0014/0015 (projects) e 0005 (accounts)
  - Serviços: agenda da Mostra, registro de presença, cancelamento, geração de documento, revisão do documento, publicação, retirada (backend/projects/showcase.py)
  - Views: ShowcaseEntryListCreateView, ShowcaseEntryDetailView, PublicationDocumentListCreateView, PublicationDocumentReviewView, PublicationDocumentDownloadView, PublicationListCreateView, PublicationWithdrawView, AcervoListView (backend/projects/showcase_views.py)
  - Serializers para todos os modelos da Sprint 7 (backend/projects/serializers.py)
  - URLs da Sprint 7 (backend/projects/urls.py)
  - 15 testes de backend da Sprint 7 passando (`backend/tests/test_showcase.py`)
- **Sprint 7 frontend concluído:**
  - Componentes: ShowcasePanel, ShowcasePresencePanel, PublicationDocumentPanel, PublicationPanel, AcervoPanel (frontend/src/showcase.tsx)
  - Tipos e funções da API (frontend/src/api.ts)
  - Rotas integradas no App.tsx
  - 11 testes Vitest da Sprint 7 passando (frontend/src/showcase.test.tsx)
  - 2 testes E2E Playwright da Sprint 7 (GF-09/GF-10) (frontend/e2e/showcase.spec.ts)
- Bug pré-existente corrigido: `IndividualGrade.id` (primary_key inválido) — migration `0015`
- Validação CI: `ruff check backend` OK; `manage.py check` OK; `makemigrations --check --dry-run` OK; pytest backend **92% coverage** (mínimo 85%); `npm run lint` OK (0 erros); `npm run build` OK

## Em andamento











- 05/11/2026: alocação automática/manual de um avaliador por grupo integrada à agenda; plano em `docs/EVALUATOR_ALLOCATION_PLAN.md`.
- Continuação autorizada em 29/10/2026: resolver gates globais e segurança dos
  utilitários locais, preservando banco/uploads e sem commit/push.
  1. Atualizar contrato de convites conforme decisão do commit `542f8f2` e testar
     autorização de consulta de alunos (erro `PermissionDenied`).
  2. Consolidar preparação E2E e arquivar cópias sanitizadas dos scripts obsoletos.
  3. Validar Ruff/pytest/cobertura sem reduzir limites ou excluir código ativo.
  4. Coordenar rotação e atualização do backend Docker identificado no projeto;
     confirmar saúde e autenticação sem expor credenciais.

## Próximas

- Homologação manual principal agora no **#6**, pronto e sem avaliador/agenda
  na preparação documentada: Secretaria agenda/aloca automaticamente entre os
  três professores e usuário repete o fluxo. #5 já publicado pelo usuário.

- Validação funcional do #2 pelo usuário: líder RA4001 já definido com autorização;
  obter entrega vigente aprovada, complementar presença legada e avaliar como
  avaliador.e2e.acervo; documento/revisão/aceite/publicação depois. Não preencher
  esses atos de negócio automaticamente para simular elegibilidade.
- Revisar scripts legados create_test_data.py (credencial embutida, não idempotente)
  e validate_planning_postgres.py (teste de sala exclusivo desatualizado/testes de
  concorrência de avaliadores ausentes). Ruff global scripts não aprovado.

- Pedido de 05/11/2026, adiado explicitamente: discutir e implementar futuramente janela de avaliação por data/hora do grupo. Definir tolerância para atrasos e exceção auditada antes de implementar; hoje `submit_grades` não exige agenda nem horário da Mostra.
- Execução no CI com fixtures e `E2E_TEST_PASSWORD`; revisar configurações legadas
  de serviço/imagem e contexto Docker. Commit/push autorizados em 05/11/2026.

## Bloqueadas


- Nenhuma nesta etapa: `admin.teste` criado após autorização; Secretaria também gerencia locais, conforme esclarecimento do usuário.

## Produção / Implantação (pendente)

- [ ] CI/CD pipeline completo (`.github/workflows/ci.yml`): ruff, manage.py check, makemigrations --check, pytest backend, npm lint/test/build, Playwright E2E, pip-audit
- [ ] Certificado SSL/TLS (Let's Encrypt ou similar) para domínio de produção
- [ ] Proxy reverso (Nginx/Traefik) na frente do Django
- [ ] `ALLOWED_HOSTS` com domínio de produção
- [ ] `CORS_ALLOWED_ORIGINS` com domínio do frontend de produção
- [ ] `DJANGO_SECRET_KEY` de produção (não a de desenvolvimento)
- [ ] Senhas fortes do PostgreSQL injetadas via variáveis de ambiente
- [ ] Migrações aplicadas no banco de produção (`manage.py migrate --noinput`)
- [ ] Estratégia de backup do banco PostgreSQL
- [ ] Configuração de serving de arquivos protegidos (`protected-media`, somente autenticados)
- [ ] Rotação de logs e monitoramento
- [ ] Testes de carga (load testing)
- [ ] Documentação de procedimento de deploy e rollback

## Importação em massa via CSV (concluída)

- Endpoint `POST /api/v1/auth/users/import-csv/` (apenas Admin/Secretaria)
- Formato CSV: `username,role,first_name,last_name,email,password,ra,course_code,class_offering_code,registration`
- Validação por linha com transação atômica (nenhuma alteração se houver erro)
- Arquivo de exemplo: `backend/accounts/management/commands/example_users_import.csv`
- Testes: `backend/tests/test_bulk_import.py` (4 testes passando)

## Finalização GF-09/GF-10 — 29/10/2026

- Login inseguro herdado corrigido: senha e usuário ativo verificados, CSRF,
  resposta genérica e controle de tentativas restaurados. Oito variações de
  regressão (DEBUG ligado/desligado, JSON/multipart, senha errada/inativo).
- Encoding de `frontend/src/App.tsx` reparado preservando lógica; removidos logs
  de senha/cookies, callbacks experimentais do proxy, esperas fixas e cópia de cookies.
- GF-09/GF-10 usam nomes distintos e contextos anônimos isolados; aguardam resposta
  HTTP 200 e renderização do acervo. GF-10 valida o erro JSON exato e ausência
  da publicação; GF-09 verifica download autenticado e bloqueio anônimo do PDF.
- Adicionados `.gitignore`, runner `scripts/validate_showcase_e2e.py`, `scripts/prepare_e2e.py`,
  `scripts/local_environment.py` e `backend/projects/management/commands/seed_e2e_acervo.py`.
- Scripts experimentais locais com credenciais embutidas arquivados sanitizados em
  `.runtime/legacy-e2e-20261029/` e removidos do working tree. Logs locais sanitizados.
- Chaves de aplicação local, senha PostgreSQL e senhas das cinco contas sintéticas
  rotacionadas com backup criptografado (DPAPI) em `.runtime/rotation-20261029-141253/`.
- Validação final: E2E **4 passed** (`--repeat-each=2`); frontend **51 passed**,
  lint sem erros e build OK; backend completo **98 passed**, cobertura **92%**,
  check e migrações OK, Ruff OK.

## Concluídas nesta sessão (melhorias de UI/Sprint 7)

- **Redesenho da tela do aluno em blocos** (`ProjectsPanel` em `frontend/src/App.tsx` + `.projects-blocos`/`.bloco`/`.projects-convites` em `styles.css`):
  - Layout em 2 colunas: blocos "Projetos atuais" e "Histórico" à esquerda; bloco "Meus convites" (sticky) à direita, visível sem scroll.
  - Listas mostram os 5 itens mais recentes; botão "Ver todos os projetos (N)" / "Ver todos (N)" expande via estado local (`showAllActive`/`showAllHistory`).
  - Mobile (≤900px): convites primeiro (`order:-1`), coluna única.
- **Acesso público anônimo ao acervo (backend)**:
  - `AcervoPublicListView` (subclass de `AcervoListView`, `IsAuthenticatedOrReadOnly`) em `backend/projects/showcase_views.py`; URL `/api/v1/projects/acervo-publico/`.
  - Corrigidos 3 bugs do diff anterior: classe renomeada mas importada com nome antigo em `urls.py`, import inexistente `AllowIsAuthenticatedOrReadOnly`, e removida duplicata de queryset.
  - Novo teste `test_acervo_publico_permite_acesso_anonimo` (LGPD: conjunto exato de metadados + `/acervo/` continua exigindo sessão).
- **Acervo unificado na sidebar**: `#/archive` renderiza `AcervoPanel` (antes `FutureModule`); item "Acervo publicado" removido da navegação (atalhos da home mantidos por causa do E2E).
- **Correções de gate**: fixture `showcase.test.tsx` (faltavam campos de `Project`, `is_active` em `Member`) quebrava `npm run build`; variável `safe` não usada em `showcase.spec.ts` quebrava lint.
- **Validação**: `ruff check backend` OK; `manage.py check` OK; `makemigrations --check` OK; pytest backend **80 passed**, coverage **91%**; `npm run lint` 0 erros; `npm test` 49/50 (1 falha pré-existente confirmada no HEAD limpo); `npm run build` OK.

## Melhorias de notificações (esta sessão)

- **Notificações deletáveis + marcar como lida ao clicar** (`frontend/src/notifications.tsx`):
  - Função `deleteItem(id)`: marca como lida no backend (`markNotificationRead`) e remove do estado local
  - Botão `×` (`.button.danger-sm`) como irmão do botão principal dentro do `<li>`
  - Marcar como lida ao clicar já existia (`openItem` → `markNotificationRead`)
- **Professor criar projeto + puxar alunos** (extensões do fluxo existente):
  - Novo `Notification.Kind.PROJECT_MEMBER_ADDED` (`accounts/migrations/0006`)
  - `assign_student` em `lifecycle.py` chama `notify()` quando cria `GroupMember` novo
  - `create_from_theme` aceita `student_ids` (máx. 3 além do líder, sem duplicatas, sem o líder)
  - Serializer `ProjectCreateSerializer`: campo write-only `student_ids`
  - Frontend `ThemeProjectCreate`: seção "Outros participantes (opcional)" com `StudentSearch` multi-seleção (máx. 3, sem duplicatas, limpa ao trocar tema)
  - `api.ts`: `createProject` aceita `student_ids?: number[]`
- **Cadastro de aluno com curso obrigatório** (frontend + backend):
  - `UserCreateSerializer` aceita `course` (obrigatório para STUDENT, queryset ativo); cria `StudentProfile` com `course` preenchido
  - Frontend `UserManagement`: dropdown de cursos (`GET /academic/courses/?is_active=true`) só para role STUDENT; tipo `NewUser` aceita `course?: string`; tipo `AcademicItem` inclui `id`
  - `EligibleRoomStudentListView`: filtro por `?course=<uuid>` para professor pesquisar alunos de um curso específico
  - `pull_student` / `RoomsPage`: professor só puxa alunos para a sala que é responsável (já existente, mantido)
  - Turma (`class_offering`) removida do cadastro — não é mais campo obrigatório nem opcional
- **Formulário de documento publicável editável até aprovação do orientador** (frontend + backend):
  - Campo `content` (TextField) adicionado ao `PublicationDocument` (`migrations/0016_publicationdocument_content.py`)
  - `PublicationDocumentUpdateView` (PATCH `/projects/publication-documents/<id>/content/`) permite o aluno editar o conteúdo enquanto o documento está PENDING; bloqueia se já APPROVED/REJECTED ou se não for o autor
  - `PublicationDocumentSerializer` expõe `content` como editável; `PublicationDocumentUpdateSerializer` para PATCH parcial
  - Frontend: `PublicationFormPanel` — formulário com título do projeto (só leitura), integrantes (só leitura), textarea de conteúdo (editável), checkbox de consentimento, botão "Salvar rascunho" (PATCH) e botão "Publicar no acervo" (se APPROVED)
  - Rota `#/publication-form/<id>` adicionada; item na sidebar e atalho da home para STUDENT
  - O documento fica editável até o orientador aprovar (status APPROVED), momento em que é travado
- **Acervo público no frontend** (anônimo):
  - `PublicAcervoPanel` — tela pública consumindo `GET /projects/acervo-publico/` (sem login), com pesquisa por título
  - Rota `#/acervo-publico` adicionada; item na sidebar para SECRETARIAT/ADMIN; atalho na home para todos
  - `listAcervoPublico` no `api.ts` com tipo `AcervoPublicItem`
- **Download do PDF do documento (autenticado)**:
  - O helper `publicationDocumentDownloadPublicUrl` aponta ao mesmo endpoint privado;
    o nome não concede acesso anônimo. GF-09 verifica a restrição.
- **Select de documentos no PublicationPanel**:
  - `PublicationPanel` agora carrega `PublicationDocument` APPROVED do projeto e preenche o `<select>` de documentos para publicação
- **Tela de avaliações (#/evaluations)**:
  - `EvaluationsPage` — lista projetos aprovados do professor com botão "Avaliar grupo" (navega para `group-evaluation`) e "Notas individuais"
  - Substitui o `FutureModule`
  - Item na sidebar para PROFESSOR
- **Tela de designar avaliador (#/evaluator-designation/<id>)**:
  - `EvaluatorDesignation` já existente, agora ligado à rota `#/evaluator-designation/<projectId>`
  - Item na sidebar para SECRETARIAT/ADMIN
- **Páginas independentes de avaliação**:
  - `GroupEvaluationPanel` acessível via `#/group-evaluation/<projectId>` (renderiza `ProjectDetailPage` com painéis de avaliação)
  - `IndividualGradesPage` — página independente para orientador lançar notas individuais por aluno (0-10) com histórico
  - Rotas `#/group-evaluation/<id>` e `#/individual-grades` adicionadas

## Observações

- As validações nas seções históricas não substituem os resultados atuais do handoff.
- Branch atual: `main`, HEAD `fb956d1`; há alterações locais não commitadas.
- Não foi verificada sincronização remota nesta etapa.
- Ver `DESAFIOS.md` antes de retomar (PowerShell, como rodar pytest local, bugs já corrigidos).
