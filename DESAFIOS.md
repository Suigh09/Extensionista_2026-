# Desafios — Plataforma Extensionista

Problemas recorrentes e aprendizados para não repetir. Atualizar ao final de cada sessão.

## Ambiente Windows / PowerShell 5.1

- `&&`, `head`, `tail`, `sed` **não funcionam**. Encadear com `; if ($?) { ... }` e `Select-Object -Last/-Skip`.
- Comandos inline com `$Matches`/regex no PowerShell quebram o parsing do shell — gravar script `.ps1` temporário e rodar com `-ExecutionPolicy Bypass -File` (ex.: `C:\Users\gustavo.alves\AppData\Local\Temp\opencode\run-pytest.ps1`).
- `git stash push -- <paths>` com paths relativos falha se o `workdir` não for a raiz do repositório (prefixo duplicado).

## Rodar testes backend localmente

- `pytest`/`manage.py` exigem env vars (`DJANGO_SECRET_KEY` etc.); sem elas falha com `ImproperlyConfigured`.
- Solução: carregar as variáveis do `.env` (raiz, não commitado) e forçar `DATABASE_ENGINE=sqlite` (usa `backend/test.sqlite3`). Script auxiliar: `C:\Users\gustavo.alves\AppData\Local\Temp\opencode\run-pytest.ps1`.
- `.venv` local não tem `pytest.exe`/`django-admin` em Scripts — usar `python.exe -m pytest` e `python.exe manage.py`.

## Bugs já corrigidos (não reintroduzir)

- **Renomear classe Django exige atualizar todos os imports**: sessão anterior renomeou `AcervoListView` → `AcervoPublicListView` sem atualizar `backend/projects/urls.py` (ImportError) e deixou `from rest_framework.permissions import AllowIsAuthenticatedOrReadOnly` (inexistente no DRF). Corrigido: `AcervoListView` restaurada (autenticada) + `AcervoPublicListView` como subclass pública.
- **Fixture de teste incompleto quebra `npm run build`**: `frontend/src/showcase.test.tsx` usava `as Project` sem `class_offering`, `submitted_at`, `reviewed_at`, `review_feedback`, `reviewed_by`, e membros com `is_active` (campo inexistente em `Member`). Corrigido.
- **Variável não usada quebra lint**: `safe` em `frontend/e2e/showcase.spec.ts` (`openProject`). Corrigido.
- **Reescrever arquivo `.tsx` inteiro via `write` quebra JSX**: `frontend/src/notifications.tsx` teve erros `TS1005: ',' expected` / `TS17008: button has no corresponding closing tag` em toda reescrita. Causa provável: perda de detalhes estruturais ao reconstruir expressões JSX longas numa linha. Solução: `git checkout -- <arquivo>` para restaurar + **edições pontuais via `edit`**. Arquivo `.tsx` não testado não deve ser reescrito por inteiro.

## Falhas pré-existentes conhecidas

- `App.test.tsx > "cria o projeto antes de formar o grupo"` falha no HEAD limpo (verificado com `git stash`). Não relacionada às mudanças recentes. Não investigada.
- Atenção: `npm run lint` tem 3 warnings pré-existentes (exhaustive-deps em `evaluation.tsx`/`grading.tsx`, react-refresh em `projectLifecycle.tsx`) — não são erros.

## Navegação do Acervo

- Rotas `#/archive` (Acervo) e `#/acervo` (Acervo publicado) **ambas renderizam `AcervoPanel`**. O item duplicado foi removido só da sidebar; os atalhos da home ainda têm os dois (`shortcuts` em `App.tsx`) — mantidos porque o E2E `showcase.spec.ts:183` clica no botão `Acervo publicado`.
- `AcervoPanel` usa `listAcervo` → `/projects/acervo/` (exige sessão). O acesso anônimo é via `/projects/acervo-publico/` (endpoint novo, ainda sem tela pública no frontend).
