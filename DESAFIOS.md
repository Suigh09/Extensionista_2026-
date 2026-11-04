# Desafios — Plataforma Extensionista

## Windows / PowerShell

- PowerShell 5.1 não aceita `&&` nem comandos Unix como `head`/`sed`.
- Ler texto sem encoding explícito e regravar como UTF-8 pode produzir mojibake.
  Em `App.tsx`, a inversão de sequências UTF-8 mal interpretadas como CP1252
  reparou os textos sem restaurar o arquivo inteiro ou perder mudanças de lógica.
- `.env` pode ter LF ou CRLF. `ReadAllLines`/`splitlines()` aceitam ambos;
  separar apenas por CRLF tratou todo o arquivo como uma única variável.
- Usar caminhos baseados em `$PSScriptRoot`; não imprimir variáveis de ambiente.
- Nunca encerrar todos os `node.exe`/`python.exe`; preservar outros processos.

## Backend local

- Há dois ambientes: `.venv` na raiz contém pytest/Ruff; `backend/.venv`
  executa Django, mas não tem esses módulos de qualidade. Usar o ambiente correto.
- `manage.py`/pytest exigem variáveis do `.env` da raiz; não há `backend/.env`.
  Forçar `DATABASE_ENGINE=sqlite` somente na execução de validação local.
- Quatro inicializadores Python do HEAD `fb956d1` continham bytes nulos.
  Devem estar vazios; reproduzir o HEAD sem esse reparo falha antes dos testes.
- Arquivos experimentais não rastreados em `backend/` entram na descoberta de
  cobertura e de Ruff. Não confundir gates locais com os de checkout limpo,
  não reduzir limites nem apagar arquivos desconhecidos para obter resultado verde.
- Ausência de `staticfiles/` gera warning no ambiente local de testes.

## Autenticação / Playwright

- Nunca aceitar qualquer senha, nem em DEBUG. O login inseguro herdado foi
  substituído pelo fluxo `authenticate()` + `login()`, CSRF e controle de tentativas.
- Playwright com `data: {…}` envia JSON; `multipart` é opção separada. O DRF
  já faz o parse; não ler simultaneamente `request.body`, `request.POST` e `request.data`.
- `page.request` compartilha cookies com o BrowserContext. Não copiar `sessionid`
  manualmente; para comprovar anonimato criar contexto novo sem storage state.
- Conferir `.env`: valores explícitos substituem defaults. A origem
  `http://127.0.0.1:5173` deve estar nas origens CSRF confiáveis da execução local.
  Não desabilitar CSRF nem abrir CORS indiscriminadamente.
- O proxy Vite já encaminha cookies; callbacks manuais/logs de Cookie/Set-Cookie
  eram redundantes, sensíveis e quebravam lint/build.
- O problema de associação na publicação era o Dashboard passar projeto fictício
  com `groups: []`, não cookies. As rotas devem carregar `getProject(id)`.
- Testes negativos precisam aguardar HTTP 200 e o fim do carregamento antes de
  verificar ausência. Cada cenário deve ter título de projeto distinto.
- `scripts/validate_showcase_e2e.py` sobe e encerra apenas seus servidores no mesmo
  processo de execução; evita depender de servidores background que podem encerrar.
- O runner requer fixtures SQLite existentes e `E2E_TEST_PASSWORD`; não armazena senha.

## Pendências verificadas em 29/10/2026 (resolvidas)

- Falha de convite em `test_lifecycle.py:121`: decision do commit `542f8f2` permite
  qualquer integrante ativo criar convites; teste atualizado para verificar autorização
  de consulta de alunos e limite de vagas. Regressão contra login antigo confirmada.
- Scripts experimentais locais com credenciais embutidas arquivados sanitizados em
  `.runtime/legacy-e2e-20261029/` e removidos do working tree. Logs locais sanitizados.
- Chaves de aplicação local, senha PostgreSQL e senhas das cinco contas sintéticas
  rotacionadas com backup criptografado (DPAPI) em `.runtime/rotation-20261029-141253/`.
- Veja `docs/HANDOFF.md` para resultados atuais; registros antigos de CI/coverage
  não são evidência de que o working tree atual está aprovado.

## Produção / Implantação (pendente)

- CI/CD: pipeline GitHub Actions não cobre build/testes completos. Substituir placeholder em `.github/workflows/ci.yml` por pipeline real (ruff, pytest, npm lint/test/build, E2E Playwright, pip-audit).
- SSL/TLS: não há certificado para domínio de produção; necessário Let's Encrypt ou similar.
- Proxy reverso: Django exposto diretamente; necessário Nginx/Traefik na frente.
- ALLOWED_HOSTS e CORS: configurados apenas para localhost; precisam do domínio de produção.
- SECRET_KEY: usar chave de produção, não a de desenvolvimento.
- Senhas PostgreSQL: injetar via variáveis de ambiente, não hardcoded.
- Migrações: aplicar `manage.py migrate --noinput` no banco de produção.
- Backup: definir estratégia de backup do PostgreSQL.
- Arquivos protegidos: configurar serving de `protected-media` somente para autenticados.
- Logs/monitoramento: definir rotação de logs e sistema de observabilidade.
- Testes de carga: executar load testing antes de produção.
- Documentação de deploy/rollback: criar procedimento passo a passo.

## Importação em massa via CSV (concluída)

- Endpoint `POST /api/v1/auth/users/import-csv/` (apenas Admin/Secretaria).
- Formato CSV: `username,role,first_name,last_name,email,password,ra,course_code,class_offering_code,registration`.
- Validação por linha com transação atômica (rollback se houver erro).
- Arquivo de exemplo: `backend/accounts/management/commands/example_users_import.csv`.
- Testes: `backend/tests/test_bulk_import.py` (4 testes passando).
