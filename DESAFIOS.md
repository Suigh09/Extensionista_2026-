# Desafios — Plataforma Extensionista

## Windows / PowerShell

- GitHub pode permitir WRITE no repo, mas recusar push que altera workflow se o
  token OAuth não tiver scope workflow. Não retirar o CI nem forçar push para
  contornar: renovar com gh auth refresh --hostname github.com --scopes workflow
  e aguardar autorização do usuário no device flow. Não persistir código/token.

- Entrega de senha de homologação nesta sessão: Set-Clipboard/Clipboard.SetDataObject
  falharam e clip.exe retornou acesso negado. Não afirmar cópia bem-sucedida sem
  comparar a leitura. Alternativa iniciada: janela WinForms local lendo DPAPI,
  sem arquivo com senha em texto claro; marcador de Shown confirma exibição,
  mas não substitui confirmação de que o usuário conseguiu visualizar a janela.

- PowerShell 5.1 não aceita `&&` nem comandos Unix como `head`/`sed`.
- Ler texto sem encoding explícito e regravar como UTF-8 pode produzir mojibake.
  Em `App.tsx`, a inversão de sequências UTF-8 mal interpretadas como CP1252
  reparou os textos sem restaurar o arquivo inteiro ou perder mudanças de lógica.
- `.env` pode ter LF ou CRLF. `ReadAllLines`/`splitlines()` aceitam ambos;
  separar apenas por CRLF tratou todo o arquivo como uma única variável.
- Usar caminhos baseados em `$PSScriptRoot`; não imprimir variáveis de ambiente.
- Nunca encerrar todos os `node.exe`/`python.exe`; preservar outros processos.

## Backend local

- Para testar alocação automática entre três perfis sintéticos existentes, não
  basta criar contas: auto_allocate só usa candidatos com aderência >0, exclui o
  orientador e confere horário/carga. No #6 foram adicionadas competências novas
  de homologação aos três perfis e exigidas no encaminhamento; opções verificadas
  sem executar alocação. Guardar IDs adicionados para reversão localizada.

- Dados sintéticos do #2 estavam APPROVED com leader nulo; assign_student regular
  só aceita preparação da proposta e pressupõe group.leader em algumas validações.
  Não reabrir projeto nem tentar adicionar aluno já integrante para contornar isso.
  Após autorização explícita, corrigido somente leader para RA4001 sob transação,
  com backup/auditoria e checagem da API. Isso não autoriza reparos em outros grupos
  nem amplia a regra normal de alteração de composição.

- E2E real PostgreSQL encontrou group.name sendo passado para new_status varchar(20)
  de ProjectStateEvent na conclusão das notas. SQLite não valida esse tamanho.
  Corrigido em grading.py: status anterior/novo do projeto permanecem project.status,
  nome do grupo vai no motivo. Teste com nome longo evita regressão.
- Servidor de teste abortado pode deixar base temporária mesmo com finally interno.
  validate_acervo_live gera o UUID do banco no host e faz limpeza externa idempotente
  do nome exato após parar só seu container. Não remover bases por prefixo amplo.
- Nesta execução final, pytest integral encerrou com código nativo -1, sem relatório
  ou traceback, em testes diferentes. Causa não determinada. Rodar arquivos em lotes
  via scripts/validate_backend.py e acumular coverage (--append), avaliando o limite
  original somente no relatório consolidado. Não alterar hashers nem excluir testes.
  Arquivo .runtime/.coverage-acervo-final separado dos relatórios anteriores.
- Labels que envolvem textarea pré-preenchida dificultaram getByLabel exact no
  navegador real. Novo formulário usa useId e label htmlFor separado do controle;
  preserva acessibilidade e seletores estáveis mesmo após carregar texto da versão.

- Presença legada PRESENTED/ABSENT não identifica os alunos presentes. No #2 isso
  impedia usar o novo fluxo: permitir complemento explícito antes da conclusão,
  preservando o resultado agregado e sem inferir checkboxes. Teste de regressão
  em test_member_attendance.py. Notas diretas pertencem a GradeSubmission, não ao
  registro individual nem a IndividualGrade (reservado ao orientador).
- Para pytest local, executar Python da .venv da raiz, sys.path com raiz do projeto
  e load_environment; isso evita conflito de import scripts.local_environment.
  Passar argumentos a pytest.main efetivamente; nunca desabilitar testes para
  contornar descoberta/ambiente. Suíte completa atual inclui esse teste.
- Docker pode ter container rodando imagem que já não aparece em docker image ls;
  validar tag/ID antes de prometer rollback exato. Na tarefa de presença foi
  preservado o código projects em execução e latest anterior, com ressalva explícita.
- Neste harness, Vite iniciado por Start-Process em shell foreground encerrou ao
  terminar a árvore da chamada. Usar shell background com node e caminho absoluto
  de vite/bin/vite.js; registrar PID/data em .runtime/processes.json somente após
  Test-PlatformFrontend. npm usa caminho .bin/../vite, que não casa com a validação
  estrita de identidade. Não enfraquecer verificação nem encerrar processos alheios.
- Em PowerShell 5.1, conteúdo UTF-8 encaminhado via pipeline nativo pode virar `?`.
  Usar OutputEncoding UTF-8 explícito ou ler arquivo UTF-8 dentro do processo;
  regex ASCII em smoke test evita falso negativo de seletor. Não regravar dados
  acadêmicos por conveniência de encoding.

- Perfis Secretaria e Admin unificados no perfil **Administrador** (`ADMIN`). Todas as verificações de permissão agora usam `role == "ADMIN"`. Usuários previamente cadastrados como `SECRETARIAT` foram convertidos via migração `0008_convert_secretariat_to_admin`.
- Desde 05/11/2026, uso normal é PostgreSQL Docker + Vite local, não Django local. Não forçar SQLite nos atalhos nem tratar `health` 200 isoladamente como prova do banco correto. O helper verifica `connection.vendor` e abre conexão real no container.
- A senha de `.env.e2e` inicialmente não correspondia à conta sintética `ra3001` no PostgreSQL (05/11/2026). Resolvido após autorização explícita: cinco contas sintéticas redefinidas para a credencial local existente, com backup DPAPI dos hashes e cinco logins HTTP validados. Não supor sincronização de senhas entre bancos nem rotacionar sem autorização; entregar credenciais sem publicá-las no chat/logs.
- PIDs antigos em `.runtime/processes.json` podem ter sido reutilizados: só parar o Node registrado se PID, instante de criação e caminho do Vite corresponderem. Registros antigos não autorizam matar processos.
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

- Rotas anônimas também precisam escutar hashchange: após logoff, colar URL com
  outro fragmento na mesma aba não recarrega o documento. Apenas ler window.hash
  no render deixava login parado. Cobrir login→público, logoff→público e acesso
  direto, incluindo retorno ao login; abrir URL em contexto novo não basta.

- Acervo público herda a listagem autenticada. Nomes/resumo inicialmente restritos
  ao autenticado foram liberados também ao público por pedido explícito posterior.
  Manter contrato limitado a nomes/resumo publicados, sem RA/contatos/notas.
  Usar snapshot da versão publicada; teste altera perfil depois e confirma autoria
  histórica inalterada. Publicação legada sem snapshot não deve inventar nomes.

- Leitura do acervo não deve reutilizar download privado de PublicationDocument:
  leitor autenticado sem vínculo pode consultar publicação, mas não suas versões
  internas. Endpoint por Publication serve só o PDF vinculado enquanto não retirado;
  conferir inline (leitura) versus attachment (download), sessão e hash da versão.

- project-form global usa position:sticky: no documento longo, encobria histórico
  abaixo. Layout do acervo agora tem editor/histórico em grid e position:static
  local. Contar links de versões antigas com includeHidden:true quando details
  estiver fechado; link fora da árvore acessível não significa versão ausente.

- Inputs checkbox em project-form herdam width:100% e min-height:46px globais.
  Para consentimento, definir dimensões/padding/flex explicitamente e texto em
  span para quebra correta. Validar geometria no navegador, não apenas no JSDOM.

- Dashboard não pode guardar apenas Page como estado de navegação: lista e detalhe
  de publication têm o mesmo tipo, então React ignora setState idêntico e o clique
  muda URL sem mudar conteúdo. Guardar hash completo e derivar Page. Regressão deve
  clicar na lista, não só abrir URL direta; validar formulário/painel, pois o título
  do projeto também existe na lista. Validado voltar/avançar/recarga reais.

- Rotas hash dinâmicas devem ser reconhecidas tanto em pageFromHash como no
  extrator de ID. O botão Avaliar grupo gerava group-evaluation/UUID, mas ambos
  ignoravam esse formato, levando ao Início. Regressão cobre clique e link direto;
  navegação real desktop/mobile cobre recarga sem gravar atos acadêmicos.
- Após mudança de rota com GSAP, findByRole no checkbox não garante que o heading
  já está visível: esperar o próprio heading com findByRole, não getByRole imediato.

- A nota direta da Mostra já estava em Registro de presença, mas a página do
  projeto ainda exibia formulário antigo por rubrica, confundindo a homologação.
  Removido esse envio paralelo e a gestão no perfil; projeto agora encaminha ao
  fluxo único existente. Ao substituir um fluxo, conferir também seus pontos de
  entrada antigos, preservando a consulta de histórico.

- Notificações: listener de clique em captura deve ignorar eventos dentro do sino;
  fechar o painel antes do onClick impedia navegar. Notificação antiga de encaminhamento
  tinha project nulo: migração 0023 só recupera vínculo por título exato/único, sem
  supor que exista ProjectForwarding. O estágio real do projeto é independente do aviso.
- Não atualizar state de renderização no listener nativo de input em captura apenas
  para marcar dirty: isso apagava valores controlados antes do onChange React. O
  dirtyRef basta; formulários de filtro podem declarar data-filter-form.
- Testes de contagem de componentes no JSDOM devem contar DOM, não visibilidade
  instantânea durante GSAP: o teste de duplicata do Acervo foi estabilizado sem
  desabilitar animações na aplicação. No navegador real, verificar visibilidade.
- SQLite não valida select_for_update: `scripts/validate_planning_postgres.py`
  cria uma base PostgreSQL temporária única, verifica números e reservas concorrentes
  e descarta somente essa base, sem copiar dados da plataforma.
- Senha simplificada solicitada para homologação é uma exceção somente às cinco contas sintéticas identificadas; `set_password` não executa validadores de cadastro. Não reduzir validação global para acomodar essa exceção nem reproduzi-la em contas reais/produção. Credencial E2E local deve acompanhar a alteração autorizada.
- Múltiplos grupos podem ser agendados na mesma sala e mesmo horário (validação de conflito de sala removida em 05/11/2026). Apenas o avaliador tem restrição de conflito de horário. No frontend, múltiplos bookings no mesmo slot são empilhados verticalmente com offset de 42px.
- rowHeight do agendamento aumentado de 112 para 160 (maior espaço entre horários). Cards de grupos não agendados reduzidos (padding 0.6rem, margin 0.5rem).
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

- Endpoint `POST /api/v1/auth/users/import-csv/` (apenas Admin).
- Formato CSV: `username,role,first_name,last_name,email,password,ra,course_code,class_offering_code,registration`.
- Validação por linha com transação atômica (rollback se houver erro).
- Arquivo de exemplo: `backend/accounts/management/commands/example_users_import.csv`.
- Testes: `backend/tests/test_bulk_import.py` (4 testes passando).

## Agendamento da Mostra — protótipo ShowcaseSession (histórico)

- Modelo `ShowcaseSession` em `backend/projects/models.py` com `start_time`, `end_time`, `location`, `status`, `project_group` (FK opcional para `ProjectGroup`).
- Migração `0021_showcasesession` criada e aplicada.
- O protótipo expunha `can_edit` sem aplicar autorização nas views e tornava `project_group` read-only. Substituído pela agenda transacional em `planning.py`; endpoints antigos retornam 410 para staff e não gravam mais. A relação `leader` existe no modelo atual; o diagnóstico anterior que a chamou de inexistente estava incorreto.
- Views `ShowcaseSessionListCreateView` e `ShowcaseSessionDetailView` em `backend/projects/showcase_views.py` (listar, criar, atualizar parcialmente, deletar).
- URLs `projects/showcase-sessions/` e `projects/showcase-sessions/<uuid:session_id>/` em `backend/projects/urls.py`.
- Componente frontend `frontend/src/showcaseScheduler.tsx` com formulário de agendamento (data/hora início/fim, local), listagem em tabela e remoção de sessões.
- Funções de API em `frontend/src/api.ts`: `listShowcaseSessions`, `createShowcaseSession`, `updateShowcaseSession`, `deleteShowcaseSession`.
- Rota `showcase-schedule` adicionada ao `App.tsx` (apenas para role ADMIN na navegação).
- 38 testes passando (test_showcase.py + test_projects.py), build frontend OK, ruff OK, lint OK.

- Os 38 testes anteriores não comprovavam o protótipo. Agora existe uma única interface `ShowcaseScheduler` e fonte `ShowcaseEntry`, com dias/locais cadastrados, arrastar/redimensionar e testes específicos. Modelo antigo preservado sem uso; o inventário PostgreSQL tinha zero sessões de protótipo.
