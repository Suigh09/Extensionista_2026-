# Tarefas — Plataforma Extensionista

## Concluídas

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

- Nenhuma tarefa em andamento.

## Próximas

- Commit das mudanças pendentes desta sessão (aguardando confirmação do usuário).
- Execução dos testes E2E Playwright no CI (requer backend rodando e E2E_TEST_PASSWORD)
- Tela pública anônima do acervo no frontend (hoje só existe o endpoint `/projects/acervo-publico/`)

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
- **Download público do PDF do documento**:
  - `publicationDocumentDownloadPublicUrl` no `api.ts` — URL pública para download do documento
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

- Bug pré-existente: `App > cria o projeto antes de formar o grupo` falha no frontend — verificado falhar também no HEAD sem alterações (stash).
- Cobertura backend: 92% (mínimo 85%).
- Branch: `main`, **9 commits à frente de `origin/main`** (não empurrados).
- Último commit: `c5321ab6` feat: formulário de documento publicável com conteúdo editável até aprovação do orientador
- Ver `DESAFIOS.md` antes de retomar (PowerShell, como rodar pytest local, bugs já corrigidos).
