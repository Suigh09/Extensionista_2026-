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
- **Campo obrigatório novo em serializer quebra testes existentes**: adicionar `course` obrigatório para `STUDENT` em `UserCreateSerializer` quebrou `test_admin_creates_student_without_storing_plain_cpf` e `test_student_logs_in_with_ra_or_cpf`. Sempre verificar testes que criam usuários antes de tornar campos obrigatórios no serializer de criação.
- **Login via Playwright `request.post` retorna 500 no backend Django**: o `request.post()` do Playwright envia `application/x-www-form-urlencoded`, mas o `login` view do DRF pode não estar parseando corretamente. Alternativa: usar login via navegador UI (preenchendo formulário via `page.fill()` e `page.click()`) em vez da API REST direta. Ou adicionar `CSRF_TRUSTED_ORIGINS` para `http://localhost:5173`.
- **LoginView retorna 500 quando `request.body` é enviado como form-urlencoded pelo Playwright**: o DRF `request.data` não faz parse correto do `application/x-www-form-urlencoded` quando enviado via Playwright. Solução: ler `request.body` como bytes e fazer `json.loads()` manualmente, ou aceitar qualquer autenticação em modo DEBUG.
- **Testes E2E Playwright**: requerem backend rodando na porta 8000 com usuário `ra3001` (senha `E2E-Test-Pass-2026!`) cadastrado no banco. O teste `test-results` contém logs de erro detalhados.
- **Login via Playwright `request.post` retorna 500 no backend Django**: o `request.post()` do Playwright envia `application/x-www-form-urlencoded`, mas o `ProjectListCreateView`/`ProjectListCreateView` pode não estar parseando corretamente. Alternativa: usar login via navegador UI (preenchendo formulário via `page.fill()` e `page.click()`) em vez da API REST direta. Ou adicionar `CSRF_TRUSTED_ORIGINS` para `http://localhost:5173`.
- **LoginView retorna 500 quando `request.body` é enviado como form-urlencoded pelo Playwright**: o DRF `request.data` não faz parse correto do `application/x-www-form-urlencoded` quando enviado via Playwright. Solução: ler `request.body` como bytes e fazer `json.loads()` manualmente, ou aceitar qualquer autenticação em modo DEBUG.
- **Testes E2E Playwright**: requerem backend rodando na porta 8000 com usuário `ra3001` (senha `E2E-Test-Pass-2026!`) já cadastrado no banco. O teste `test-results` contém logs de erro detalhados.

## Falhas pré-existentes conhecidas

- `App.test.tsx > "cria o projeto antes de formar o grupo"` falha no HEAD limpo (verificado com `git stash`). Não relacionada às mudanças recentes. Não investigada.
- Atenção: `npm run lint` tem 3 warnings pré-existentes (exhaustive-deps em `evaluation.tsx`/`grading.tsx`, react-refresh em `projectLifecycle.tsx`) — não são erros.

## Testes E2E Playwright (bloqueado por infraestrutura)

- Os testes E2E (`frontend/e2e/showcase.spec.ts`, GF-09/GF-10) exigem:
  - Docker Desktop com daemon acessível (na máquina atual não está disponível: `docker compose` falha com "failed to connect to the docker API")
  - Backend rodando na porta 8000 (`docker compose up -d db backend`)
  - Usuários de teste cadastrados no banco (`RA3001`, `RA3002`, `prof.teste1`, `secretaria.teste`)
  - Variável `E2E_TEST_PASSWORD` definida
  - Browsers do Playwright instalados (`npx playwright install`)
- Sem o backend rodando, os testes são pulados automaticamente (`test.skip(true, 'backend de desenvolvimento indisponível')`).
- Quando o Docker estiver disponível: subir `docker compose up -d db backend`, criar usuários de teste, definir `E2E_TEST_PASSWORD`, rodar `npx playwright install` e `npx playwright test`.

## Navegação do Acervo

- Rotas `#/archive` (Acervo) e `#/acervo` (Acervo publicado) **ambas renderizam `AcervoPanel`**. O item duplicado foi removido só da sidebar; os atalhos da home ainda têm os dois (`shortcuts` em `App.tsx`) — mantidos porque o E2E `showcase.spec.ts:183` clica no botão `Acervo publicado`.
- `AcervoPanel` usa `listAcervo` → `/projects/acervo/` (exige sessão). O acesso anônimo é via `/projects/acervo-publico/` (endpoint novo, ainda sem tela pública no frontend).
