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
- Validação CI: `ruff check backend` OK; `manage.py check` OK; `makemigrations --check --dry-run` OK; pytest coverage 91% (mínimo 85%); `npm run lint` OK (0 erros); `npm run build` OK

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

## Observações

- Bug pré-existente: `App > cria o projeto antes de formar o grupo` falha no frontend — verificado falhar também no HEAD sem alterações (stash).
- Cobertura backend: 91% (mínimo 85%).
- Branch: `main`, **7 commits à frente de `origin/main`** (não empurrados).
- Último commit: `6fe9a23` Move account section to top of sidebar and make notification panel a fixed popup with scroll
- Ver `DESAFIOS.md` antes de retomar (PowerShell, como rodar pytest local, bugs já corrigidos).
