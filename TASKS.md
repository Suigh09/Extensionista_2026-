# Tarefas — Plataforma Extensionista

## Concluídas

- Backend Django com apps `accounts`, `academic`, `core`, `projects` (autenticação, salas, projetos, grupos, follow-ups, marcos, parcerias)
- Frontend Vite/React com telas de projeto, grupo, follow-up, marcos, parcerias
- Docker Compose (Postgres 17, backend, frontend)
- CI placeholder substituído por pipeline real (`.github/workflows/ci.yml`, alteração não commitada)
- Documentação de análise/modelagem da Entrega 1 (`documentos/`)
- Especificação da Sprint 7 com decisões Q1 a Q7 definidas e aceitas (`docs/sprints/SPRINT_07_SPEC.md`)
- AGENTS.md, AI_CONTEXT.md e README.md criados/atualizados
- **Sprint 7 backend concluído:**
  - Modelos `ShowcaseEntry`, `PublicationDocument`, `Publication` (backend/projects/models.py)
  - Novos Notification.Kind (DOCUMENT_PENDING, DOCUMENT_APPROVED, DOCUMENT_REJECTED, PUBLICATION_CREATED, PUBLICATION_WITHDRAWN)
  - Migrations 0013/0014/0015 (projects) e 0005 (accounts) geradas e validadas
  - Serviços: agenda da Mostra, registro de presença, cancelamento, geração de documento, revisão do documento, publicação, retirada (backend/projects/showcase.py)
  - Views: ShowcaseEntryListCreateView, ShowcaseEntryDetailView, PublicationDocumentListCreateView, PublicationDocumentReviewView, PublicationDocumentDownloadView, PublicationListCreateView, PublicationWithdrawView, AcervoListView (backend/projects/showcase_views.py)
  - Serializers para todos os modelos da Sprint 7 (backend/projects/serializers.py)
  - URLs da Sprint 7 (backend/projects/urls.py)
  - 15 testes de backend da Sprint 7 passando (`backend/tests/test_showcase.py`)
- **Sprint 7 frontend concluído:**
  - Componentes: ShowcasePanel, ShowcasePresencePanel, PublicationDocumentPanel, PublicationPanel, AcervoPanel (frontend/src/showcase.tsx)
  - Tipos e funções da API (frontend/src/api.ts)
  - Rotas integradas no App.tsx
  - `npm run lint` OK (0 erros); `npm run build` OK; `npm test` 38/39 (1 falha pré-existente no App.test.tsx)
- Bug pré-existente corrigido: `IndividualGrade.id` (primary_key inválido) — `makemigrations 0015`
- Validação CI: `ruff check backend` OK; `manage.py check` OK; `makemigrations --check --dry-run` OK; pytest coverage 91% (mínimo 85%)

## Em andamento

- Nenhuma tarefa em andamento no momento.

## Próximas (Sprint 7)

### Testes pendentes

- [ ] Testes Vitest para componentes frontend da Sprint 7
- [ ] Testes E2E desktop+mobile (GF-09/GF-10) com Playwright

### Operacionais

- [ ] Commit da alteração em `.github/workflows/ci.yml` (pipeline real de CI)
- [ ] Criar `docs/HANDOFF.md` (fotografia operacional para próximo agente)

### Observações

- Bug pré-existente: `App > cria o projeto antes de formar o grupo` falha no frontend — não relacionado à Sprint 7.
- Cobertura backend: 91.32% (mínimo 85%).
- Branch: `main`, atualizada com `origin/main` (https://github.com/Suigh09/Extensionista_2026-)
- Alteração não commitada: `.github/workflows/ci.yml`
