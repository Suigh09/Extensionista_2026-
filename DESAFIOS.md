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
