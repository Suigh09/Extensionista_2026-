# Handoff — Plataforma Extensionista

## Objetivo e tarefa atual

Implementação da Sprint 7 — Mostra, publicação e acervo (UC-017 a UC-023). Especificação formalmente aceita. Implementação backend e frontend concluída. Pendentes: testes Vitest (frontend), testes E2E Playwright (GF-09/GF-10), commit do CI alterado, e criação deste handoff.

## Estado

Sprint 7 implementada e validada. Funcionalidades entregues:
- `ShowcaseEntry`: agenda da Mostra (PENDING→SCHEDULED), registro de presença (PRESENTED/ABSENT) pelo avaliador, cancelamento pela secretaria
- `PublicationDocument`: geração de PDF server-side versionado pelo aluno, consentimento explícito, aprovação/reprovação pelo orientador com parecer
- `Publication`: publicação no acervo (GF-09) e bloqueio de publicação inválida (GF-10), retirada pela secretaria com histórico preservado (sem republicação)
- Notificações: documento aprovado/reprovado, publicação criada, publicação retirada
- Auditoria: agenda, presença, gerações, aprovações, publicações, retiradas

## O que parece funcionar

- `ruff check backend`: OK (0 erros)
- `python manage.py check`: OK (0 issues)
- `makemigrations --check --dry-run`: OK (sem mudanças pendentes)
- pytest backend: 78 passed, 1 falha pré-existente não relacionada (`App > cria o projeto antes de formar o grupo` no frontend, e anteriormente `IndividualGrade.id` já corrigido)
- Coverage backend: 91.32% (mínimo 85%)
- `npm run lint` frontend: OK (0 erros, 3 warnings pré-existentes)
- `npm run build` frontend: OK
- `npm test` frontend: 38 passed, 1 falha pré-existente (`App > cria o projeto antes de formar o grupo`)
- 15 testes específicos da Sprint 7 passando (`backend/tests/test_showcase.py`)

## Trabalho feito

### Sprint 7 backend (arquivos novos/modificados)
- `backend/projects/models.py`: modelos `ShowcaseEntry`, `PublicationDocument`, `Publication`
- `backend/projects/showcase.py`: serviços transacionais (agenda, presença, cancelamento, geração de documento, revisão, publicação, retirada)
- `backend/projects/showcase_views.py`: 8 views da Sprint 7
- `backend/projects/serializers.py`: serializers dos modelos da Sprint 7
- `backend/projects/urls.py`: URLs da Sprint 7
- `backend/accounts/models.py`: novos `Notification.Kind` (DOCUMENT_PENDING, DOCUMENT_APPROVED, DOCUMENT_REJECTED, PUBLICATION_CREATED, PUBLICATION_WITHDRAWN)
- `backend/tests/test_showcase.py`: 15 testes de unidade/integração da Sprint 7
- Migrations: `projects/0013`, `projects/0014`, `projects/0015`, `accounts/0005`

### Bug pré-existente corrigido
- `backend/projects/models.py`: `IndividualGrade.id` — `primary_key=uuid.uuid4` → `primary_key=True, default=uuid.uuid4` (migration `projects/0015`)

### Documentação
- `AGENTS.md` (novo), `AI_CONTEXT.md` (novo), `README.md` (atualizado)
- `docs/sprints/SPRINT_07_SPEC.md`: cabeçalho alterado de "Especificação para aprovação. Não autoriza implementação antes do aceite." para "Especificação aceita. Implementação autorizada."; decisões Q1 a Q7 registradas
- `TASKS.md` atualizado

### Sprint 7 frontend (arquivos novos/modificados)
- `frontend/src/showcase.tsx` (novo): componentes ShowcasePanel, ShowcasePresencePanel, PublicationDocumentPanel, PublicationPanel, AcervoPanel
- `frontend/src/api.ts`: tipos e funções da API da Sprint 7
- `frontend/src/App.tsx`: rotas e navegação da Sprint 7 integradas

## Problemas / hipóteses

- 1 falha pré-existente no frontend (`App > cria o projeto antes de formar o grupo`) não relacionada à Sprint 7. Não investigada nesta sessão.
- Decisões Q1 a Q7 foram tomadas com base nas respostas do usuário. Q7 (sem republicação) está implementada conforme decisão.

## Arquivos relevantes / modificados

- `docs/sprints/SPRINT_07_SPEC.md` (modificado)
- `AGENTS.md` (novo)
- `AI_CONTEXT.md` (novo)
- `README.md` (modificado)
- `TASKS.md` (modificado)
- `backend/projects/models.py` (modificado)
- `backend/projects/showcase.py` (novo)
- `backend/projects/showcase_views.py` (novo)
- `backend/projects/serializers.py` (modificado)
- `backend/projects/urls.py` (modificado)
- `backend/accounts/models.py` (modificado)
- `backend/tests/test_showcase.py` (novo)
- `backend/projects/migrations/0013_*.py` (novo)
- `backend/projects/migrations/0014_*.py` (novo)
- `backend/projects/migrations/0015_*.py` (novo)
- `backend/accounts/migrations/0005_*.py` (novo)
- `frontend/src/showcase.tsx` (novo)
- `frontend/src/api.ts` (modificado)
- `frontend/src/App.tsx` (modificado)

## Mudanças não commitadas

- `.github/workflows/ci.yml` (alterado: CI placeholder → pipeline real ruff/pytest/pip-audit + npm lint/test/build/e2e)
- Todo o código da Sprint 7 acima (arquivos novos e modificados)

## Branch e commits recentes

- Branch: `main`, atualizada com `origin/main` (https://github.com/Suigh09/Extensionista_2026-)
- Commit recente: `4a396bc feat: adiciona todo o código do projeto (backend, frontend, scripts, infra)`

## Testes

- Testes encontrados: 79 no backend (incluindo 15 novos em `test_showcase.py`), 39 no frontend
- Testes realmente executados nesta sessão: 15 (`test_showcase.py`), 3 (`test_grading.py` após correção), 61 (demais do backend), 38/39 (frontend)
- Todos os testes da Sprint 7 passam. 1 falha pré-existente no frontend não relacionada.

## Próxima ação

1. Commit da alteração em `.github/workflows/ci.yml` e de todo o código da Sprint 7.
2. Criar testes Vitest para componentes frontend da Sprint 7.
3. Executar testes E2E desktop+mobile (GF-09/GF-10) com Playwright.
4. Executar `npm ci && npm run lint && npm test && npm run build` e `npm run test:e2e` no frontend para CI completa.
