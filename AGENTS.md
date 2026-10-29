# AGENTS.md — Plataforma Extensionista

## Stack e convenções observadas

- **Backend:** Django (Python 3.11), PostgreSQL 17 via Docker Compose. Apps: `accounts`, `academic`, `core`, `projects`. Lint: `ruff` (target py311, line-length 100, select E F I B S UP, ignore S101). Testes: `pytest` com `DJANGO_SETTINGS_MODULE=config.settings`, coverage mínima 85%.
- **Frontend:** Vite + React + TypeScript. Lint: ESLint. Testes: Vitest + Playwright (E2E). Build: `npm run build`.
- **Infra:** `compose.yaml` com serviços `db`, `backend`, `frontend`. Scripts locais: `Iniciar Plataforma.bat`, `Parar Plataforma.bat`, `scripts/start_platform.ps1`, `scripts/stop_platform.ps1`.
- **CI:** `.github/workflows/ci.yml` — backend: ruff, `manage.py check`, `makemigrations --check --dry-run`, pytest com cobertura, pip-audit. Frontend: npm ci, lint, test, build, playwright install + test:e2e.

## Estrutura do repositório

```
backend/            # Django (apps: accounts, academic, core, projects)
frontend/           # Vite + React + TypeScript
docs/               # Especificações de sprint (ex: SPRINT_07_SPEC.md)
documentos/         # Análise e modelagem da Entrega 1 (Mermaid)
scripts/            # Scripts de iniciar/parar plataforma
.github/workflows/  # CI
```

## Execução e testes

- Backend: `cd backend && python manage.py check`, `ruff check backend`, `pytest --cov` (coverage 85%).
- Frontend: `cd frontend && npm ci && npm run lint && npm test && npm run build && npm run test:e2e`.
- Docker: `docker compose up --build`.

## Segurança e restrições

- Autorização no backend e por objeto; ocultar botão não concede segurança.
- Negação por padrão, menor privilégio, UUIDs externos, uploads privados, validação de tipo/tamanho.
- CPF integral, senhas, tokens e segredos não aparecem em diagramas nem artefatos.
- Registros acadêmicos e históricos não expiram automaticamente; `PROTECT` em chaves críticas.
- Nunca commite credenciais, chaves ou dados pessoais sensíveis.

## Regras de trabalho para agentes

- Não crie funcionalidades novas fora do escopo da tarefa solicitada.
- Respeite decisões documentadas em `docs/sprints/SPRINT_07_SPEC.md` e `documentos/`.
- Antes de implementar, confirme que a especificação tem aceite (cabeçalho da Sprint 7 diz "Não autoriza implementação antes do aceite").
- Mantenha compatibilidade; evite refatorações alheias à tarefa.
- Não exponha segredos, senhas, CPFs integrais ou dados fiscais.

## Matriz de rastreabilidade (UCs)

- `IMP` = implementado; `PLN` = planejado/não implementado.
- UC-001 a UC-016: IMP (autenticação, salas, projetos, grupos, follow-ups, marcos, parcerias).
- UC-017 a UC-023: implementados (Sprint 7); consulte `docs/HANDOFF.md` para validação e pendências, sem presumir CI verde.
