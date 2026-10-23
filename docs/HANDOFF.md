# Handoff — Plataforma Extensionista

## Objetivo e tarefa atual

Melhorias contínuas pós-Sprint 7: UI em blocos, acervo público anônimo e correções de gate. Nesta sessão: (1) redesenho da tela do aluno em blocos com "Ver todos" expansível, (2) endpoint público do acervo + correção de 3 bugs no diff anterior, (3) correções de lint/build pré-existentes. **Mudanças validadas mas NÃO commitadas — aguardando confirmação.**

## Estado

- **Sprint 7 entregue e commitada** (UC-017 a UC-023, 4 commits recentes).
- Branch `main` com **7 commits à frente de `origin/main`** (não fazer push sem pedir).
- Último commit: `6fe9a23` Move account section to top of sidebar and make notification panel a fixed popup with scroll.

### Trabalho feito em sessões recentes (commitado)

- `8b28666`: regex `projectIdFromHash` corrigida (`projects?`) — resolve 404 `GET /api/v1/projects//`.
- `6fe9a23`: sidebar com conta/notificações no topo, "Sair" embaixo; sino abre popup fixo 380px com scroll, fecha em ESC/clique-fora.
- `48f7242`, `37f133a`, `a057813`: arquivos e testes faltantes da Sprint 7.

### Trabalho feito nesta sessão (NÃO commitado)

**Backend (`ruff` OK, `manage.py check` OK, pytest 80 passed / coverage 91%):**
- `backend/projects/showcase_views.py`: restaurada `AcervoListView` (autenticada, `IsAuthenticated`) — o diff anterior a havia renomeado; adicionada `AcervoPublicListView(AcervoListView)` com `IsAuthenticatedOrReadOnly` (endpoint público LGPD); removido import inexistente `AllowIsAuthenticatedOrReadOnly`.
- `backend/projects/urls.py`: import de `AcervoPublicListView` (estava sendo usado sem importar → NameError).
- `backend/tests/test_showcase.py`: novo teste `test_acervo_publico_permite_acesso_anonimo` — 200 anônimo com exatamente `{id, project_name, document_version, published_at, created_at}`; `/acervo/` continua 401/403 anônimo.

**Frontend (lint 0 erros, 49/50 testes, build OK):**
- `frontend/src/App.tsx`: `ProjectsPanel` redesenhado em blocos — grid `.projects-blocos` (coluna principal + aside sticky de convites), headers `<header className="bloco-header">`, listas limitadas a 5 com toggle `showAllActive`/`showAllHistory` ("Ver todos os projetos (N)" / "Ver todos (N)"), badge de convites pendentes. Sidebar: item duplicado `['acervo','Acervo publicado']` removido da navegação; `#/archive` renderiza `AcervoPanel` (antes `FutureModule`).
- `frontend/src/styles.css`: `.projects-blocos` (2 colunas), `.bloco`, `.bloco-header`, `.projects-convites` (sticky); ≤900px coluna única com convites primeiro (`order:-1`).
- `frontend/src/showcase.tsx`: cabeçalho do `AcervoPanel` de `<div>` para `<header>`.
- `frontend/src/showcase.test.tsx`: fixture do `project` completa (`class_offering`, `submitted_at`, `reviewed_at`, `review_feedback`, `reviewed_by`; removido `is_active` dos membros) — corrigia `npm run build`.
- `frontend/e2e/showcase.spec.ts`: removida variável `safe` não usada — corrigia lint.

## O que parece funcionar (validado nesta sessão)

- `ruff check backend`: OK
- `manage.py check`: 0 issues; `makemigrations --check --dry-run`: sem mudanças
- pytest backend: **80 passed** (79 + 1 novo), coverage **91%**
- `npm run lint`: 0 erros, 3 warnings pré-existentes
- `npm test` (vitest): **49 passed, 1 failed** — a falha `App > cria o projeto antes de formar o grupo` **também falha no HEAD limpo** (verificado com stash)
- `npm run build`: OK

## Problemas / hipóteses

- 1 falha pré-existente no frontend (acima), não investigada.
- Atalhos da home ainda listam "Acervo" **e** "Acervo publicado" (ambos → `AcervoPanel`); mantidos porque `showcase.spec.ts:183` clica em `Acervo publicado`. Ver `DESAFIOS.md`.
- `AcervoPanel` autenticado usa `/projects/acervo/`; endpoint público `/projects/acervo-publico/` existe mas ainda não tem tela.
- E2E Playwright não rodou nesta sessão (requer backend + `E2E_TEST_PASSWORD`).
- 7 commits não empurrados para `origin/main`.

## Arquivos modificados (não commitados)

- `backend/projects/showcase_views.py`
- `backend/projects/urls.py`
- `backend/tests/test_showcase.py`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/showcase.tsx`
- `frontend/src/showcase.test.tsx`
- `frontend/e2e/showcase.spec.ts`
- `TASKS.md`, `DESAFIOS.md` (este `docs/HANDOFF.md`)

Não commitar: `.env`, `.venv/`, `__pycache__/`, `dist/`, `node_modules/`, `test.sqlite3`, `.runtime/`, `temp.txt` (untracked).

## Testes

- Backend: 80 (arquivos `backend/tests/test_*.py`); executados nesta sessão.
- Frontend: 50 vitest; executados. E2E Playwright: 4 specs, **não executados**.

## Próxima ação

1. **Commit** das mudanças acima (aguardando confirmação) — sugestão: `feat: UI da tela do aluno em blocos e acesso público ao acervo`.
2. Validar visualmente no navegador (blocos da tela de projetos) — requer plataforma rodando (`docker compose up` ou `Iniciar Plataforma.bat`).
3. Opcional: tela pública anônima do acervo consumindo `/projects/acervo-publico/`.
4. Opcional: unificar atalhos duplicados da home + ajustar E2E correspondente.
