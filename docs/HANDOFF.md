# Handoff — Plataforma Extensionista

## Implementação atual — acervo completo, 05/11/2026

Esta seção substitui o diagnóstico pré-implementação abaixo.

### Entrega ao GitHub autorizada — 05/11/2026

- Usuário solicitou commit e envio do projeto atual. Destino configurado:
  `https://github.com/Suigh09/Extensionista_2026-.git`, branch main; fetch confirmou
  base local/remota alinhada antes da consolidação. Git é a fonte para o hash
  final e confirmação de sincronização após o push.
- Incluídos código, migrações, testes, scripts seguros e documentação das etapas
  anteriores. Fora do commit: `.runtime/`, `.env*`, bancos, uploads, credenciais,
  e o arquivo local não rastreado `scripts/create_test_data.py` (senha embutida e
  criação não idempotente). O arquivo foi preservado localmente, não executado.
- Revisão automatizada dos candidatos não encontrou tokens/chaves privadas nem
  correspondências com segredos locais. git diff --check e Ruff backend aprovados.
  Últimas validações funcionais: 86 testes frontend e 16 backend da Mostra,
  além da validação backend anterior de 165 testes em lotes (93,14%). Não confundir
  testes de rodadas anteriores com nova execução integral nesta etapa de Git.
- CI remoto não validado antes do envio. O workflow ainda contém configurações
  legadas (serviço com imagem local de CI e contexto Docker do job backend-docker)
  que exigem revisão própria; não declarar pipeline verde pelo push bem-sucedido.
- Dados e contas dos projetos #5/#6 permanecem somente no PostgreSQL local;
  commits não transportam esses registros nem suas senhas para outras instalações.

### Novo teste do fluxo — projeto #6, 05/11/2026

- Pedido autorizado: criadas somente contas novas `fluxo.aluno3` (líder HML5003)
  e `fluxo.aluno4` (HML5004), com a mesma senha das contas fluxo.* já entregue,
  sem redefinir contas anteriores e sem staff/superuser. HTTP login/perfil/vínculo/
  permissões/logout aprovados: aluno3 representa o grupo, aluno4 não.
- Criado **#6 — Projeto Homologação Alocação Automática** na sala de homologação
  existente, orientador fluxo.orientador. Convite aceito, proposta enviada e
  aprovada, entrega PDF enviada/aprovada e encaminhamento à Secretaria realizados
  pelos serviços/APIs existentes, com histórico/auditoria, não só troca de status.
- Sem avaliador, EvaluatorAssignment, agendamento, presença, nota, documento do
  acervo ou publicação. API da Secretaria confirma grupo elegível e não agendado.
- Três candidatos: prof.orientador1/2/3. Adicionados somente três novos itens de
  competência **Homologação Automática**, utilizada no encaminhamento; API confirma
  exatamente esses três disponíveis/com aderência antes de definir data/horário.
  Orientador do próprio #6 excluído normalmente. Disponibilidade de horário será
  reavaliada ao agendar/alocar. Nenhuma alocação automática foi executada pelo agente.
- Próximo passo: fluxo.secretaria agenda o #6, seleciona dia/sala e usa **Alocar
  avaliadores automaticamente**. Rotina considera competências/disponibilidade/
  carga, preserva designações anteriores e não sorteia aleatoriamente.
- Backup/dump validado, manifest, reversão localizada, fingerprints e validações:
  `.runtime/second-showcase-homologation-20261105-202018/`, também apontado por
  `.runtime/second-showcase-homologation-path.txt`. Credencial somente DPAPI.
  Todos os registros preexistentes inventariados permaneceram idênticos; contador
  de número avançou e novos registros foram adicionados. #5/publicação preservados.
  Runner de criação `.runtime/prepare_second_showcase_fixture.py`: não rerodar.

### Integrantes e resumo públicos — 05/11/2026

- Pedido explícito posterior autoriza nomes dos integrantes e resumo no card
  público. Substitui a decisão anterior de limitar esses campos ao autenticado.
  As duas listagens reutilizam nomes/abstract da versão publicada e componente
  AcervoCardDetails. Não expõem RA, IDs de aluno, contatos, notas ou presenças.
- PDF continua privado e rascunhos/versões internas não foram liberados. Teste
  anônimo agora exige exatamente sete campos (cinco anteriores + members/abstract).
  16 testes backend da Mostra/86 frontend/Ruff/lint/build aprovados; warnings
  preexistentes mantidos, sem cobertura backend global nesta rodada.
- UI/API reais totalmente anônimas: #5 com dois nomes e resumo visíveis em
  1440/390px; sessão/PDF retornam 403, lista antes/depois idêntica. Runner
  `.runtime/validate_public_acervo_details.cjs`, capturas acervo-publico-detalhes-*.
- Backend Docker atualizado sem schema/dados novos; imagem anterior/reversão
  na pasta apontada por `.runtime/public-acervo-details-path.txt`. Vite encerrou
  durante a tarefa e foi reiniciado em background; identidade validada e novo
  registro em `.runtime/processes.json`. Sem commit/push.

### Acervo público após logoff — 05/11/2026

- Reproduzido: App anônimo só lia window.location.hash durante render e não
  escutava hashchange; colar #/acervo-publico na aba de login não mudava conteúdo.
  Link direto com recarga funcionava. App agora observa hash também sem sessão.
- Três cenários de regressão (login → público, logoff → público e link direto)
  e retorno ao login cobertos; dois primeiros falharam antes da correção.
  **85 testes frontend aprovados**, cobertura configurada 95,16%, lint sem erros
  e build aprovado (warnings preexistentes). Alteração apenas frontend.
- UI/API reais: sair como fluxo.secretaria, navegar na mesma aba ao público,
  consultar #5 sem sessão, recarregar e voltar ao login; aprovados em 1440/390px.
  Contexto novo totalmente anônimo também aprovado. Nenhuma publicação alterada.
  Runner `.runtime/validate_public_acervo_navigation.cjs`, capturas
  `.runtime/acervo-publico-1440.png`/390.png. PDF continua exigindo autenticação.

### Integrantes e resumo no card — 05/11/2026

- Acervo autenticado inclui members (lista apenas de nomes) e abstract da versão
  vinculada à publicação. Não usa vínculos/perfis atuais para reescrever autoria.
  Publicações legadas sem esses dados mostram mensagem explícita na UI.
- AcervoPublicListView desabilita detalhes; contrato anônimo permanece exatamente
  id/project_name/document_version/published_at/created_at. Link público local:
  `http://127.0.0.1:5173/#/acervo-publico`, sem login. Não ampliado acesso ao PDF.
- 16 testes backend da Mostra aprovados, incluindo estabilidade do snapshot após
  alteração de nome do autor e contrato público; 82 frontend aprovados, Ruff/build
  OK. Runner real validou nomes/resumo do #5 e PDF versão 3 em 1440/390px, hash
  correto e workflow idêntico. Capturas `.runtime/acervo-card-1440.png`/390.png.
- Backend Docker reconstruído/recriado, check OK; imagem anterior e reversão na
  pasta indicada em `.runtime/acervo-card-path.txt`, sem alteração de registros/schema.

### Leitura do PDF no acervo — 05/11/2026

- Acervo autenticado agora tem título clicável e ação Ler PDF em nova aba.
  Endpoint `GET /api/v1/projects/acervo/<publication-id>/pdf/` exige autenticação,
  publicação efetiva não retirada e documento aprovado; serve somente o PDF
  vinculado à publicação com Content-Disposition inline, private/no-store/nosniff.
  Download privado antigo continua com autorização por vínculo. Acervo público
  anônimo permanece só metadados; não foram expostos rascunhos/versões anteriores.
- 16 testes de test_showcase.py aprovados (sem cobertura global nesta rodada),
  incluindo leitor autenticado sem vínculo, conteúdo exato, headers, bloqueio
  anônimo e retirada; 81 frontend aprovados, Ruff arquivos alterados/lint/build OK
  (warnings preexistentes). Falha transitória de criação de projeto reapareceu na
  primeira suíte frontend; execução completa seguinte aprovada sem alterar teste.
- Backend Docker reconstruído/recriado isoladamente, manage.py check OK. Backup
  `.runtime/acervo-pdf-20261105-200028/`, dump e tag da imagem anterior preservados,
  reversão registrada; sem nova migração de schema.
- UI/API/PostgreSQL reais como fluxo.secretaria: título abre PDF versão 3 do #5
  em 1440/390px, application/pdf e inline confirmados, bytes/SHA-256 conferem com
  versão publicada. Anônimo bloqueado; workflow antes/depois idêntico. Runner
  `.runtime/validate_published_pdf.cjs`. O #5 está PUBLISHED após atos do usuário.

### Edição e versões lado a lado — 05/11/2026

- Pedido do usuário: formulário à esquerda e todos os PDFs/versões à direita.
  acervo-document-layout usa grid 3fr/2fr, colunas minmax(0,...), aside nomeado;
  até 1100px empilha editor e histórico. Formulários locais com position:static
  para não herdar sticky de project-form e encobrir o histórico durante scroll.
- Todas as versões/links preservados; a mais recente aberta, anteriores expansíveis.
  Teste novo confirma painéis irmãos e PDFs das versões 1/2. **81 testes frontend**
  e build aprovados; runner real verificou geometria sem sobreposição, todas as
  versões (incluindo links em details fechados), navegação e recarga em 1440/390px.
  Captura desktop inspecionada. Nenhum formulário enviado; workflow idêntico.
- Na leitura real atual o #5 já tem duas versões e aguarda orientador, após atos
  do usuário; não confundir com fotografia inicial de preparação sem documento.

### Layout do consentimento — 05/11/2026

- Corrigida checkbox do documento que herdava width:100% e min-height:46px de
  inputs gerais, empurrando texto para fora. Classe local publication-consent,
  input 16×16 sem padding e texto em span adjacente (gap .5rem), com quebra interna.
- 7 testes do acervo e build aprovados; runner de navegação real verificou tamanho,
  distância e contenção do texto em 1440px/390px. Captura mobile também inspecionada.
  Workflow antes/depois idêntico, sem enviar documento/publicar. Alteração só visual.

### Botão Publicar no Acervo — 05/11/2026

- Reproduzida falha lista → detalhe: Dashboard guardava apenas o tipo de página;
  `#/publication` e `#/publication/UUID` resultavam no mesmo estado React, sem
  renderizar o documento. Agora o estado guarda o hash completo e deriva a página,
  mantendo proteção de alterações não salvas. Corrige também trocas entre IDs.
- Link da fila renomeado de "Abrir fluxo do acervo" para **Publicar no Acervo**,
  como solicitado. Apenas abre o painel; não pula revisão/aceite/Secretaria.
- Teste de integração do App agora cobre clique na lista além do link direto;
  clique falhou antes da correção. **80 testes frontend aprovados**, cobertura
  configurada **95,12%**, lint sem erros/build aprovado (warnings preexistentes).
- UI/API reais como `fluxo.aluno1` no #5: clique, painel/formulário, voltar,
  avançar e recarga aprovados em 1440px/390px. Resposta integral do workflow
  idêntica antes/depois, sem enviar documento nem publicar. Runner privado
  `.runtime/validate_acervo_navigation.cjs`; capturas acervo-navigation-1440.png
  e acervo-navigation-390.png na mesma pasta. Guia atualizado com o novo texto.

### Correção da navegação do avaliador — 05/11/2026

- Reproduzido relato do usuário: Avaliações → Avaliar grupo gerava
  `#/group-evaluation/<project-id>`, mas pageFromHash só reconhecia a rota estática
  e projectIdFromHash tampouco extraía esse ID. Resultado: fallback silencioso Início.
- App.tsx reconhece a rota dinâmica e abre ShowcasePresencePanel filtrado pelo
  projeto, reutilizando presença/nota direta existentes, sem formulário paralelo.
  Sem apresentação disponível, informa verificar agendamento/designação.
- Dois testes novos reproduziram a falha antes da correção (clique/link direto)
  e agora passam, incluindo exclusão de outros projetos e ausência de rubrica.
  Frontend **79 passed**, cobertura configurada **95,10%**, lint sem erros (warning
  Fast Refresh preexistente) e build aprovado (warning Three.js preexistente).
- Navegação UI/API real como `fluxo.avaliador` no #5: clique, projeto correto e
  recarga aprovados em 1440px/390px. Comparação da resposta da agenda antes/depois
  idêntica; sem gravar presença/nota ou alterar agendamento. Evidências privadas
  `.runtime/evaluation-navigation-1440.png` e `evaluation-navigation-390.png`;
  runner `.runtime/validate_evaluation_navigation.cjs`, senha via ambiente/DPAPI.
- Uma execução intermediária falhou por consultar heading durante animação e por
  falha transitória do teste de criação já existente. Heading novo agora usa
  findByRole; suíte completa seguinte passou sem alterar o teste de criação.

### Remoção da rubrica da interface — 05/11/2026

- Usuário pediu retirar a rubrica após identificar o formulário antigo de avaliação.
  `GroupEvaluationPanel` agora mostra nota/histórico e encaminha a **Registro de
  presença**, que já oferece nota única 0–10 e observações após presença individual.
  Sem envio por critérios ou conclusão paralela pela interface do projeto.
- Gestão de rubricas retirada do perfil do professor. Serviços/modelos e registros
  antigos preservados; não houve alteração no banco nem remoção de histórico.
- Validação: frontend 77 testes aprovados, build aprovado, lint sem erros (somente
  warning preexistente Fast Refresh em projectLifecycle.tsx). Sem execução de E2E
  nesta alteração. Testes verificam ausência do formulário e da gestão no perfil,
  link para presença e consulta dos históricos por critérios e nota direta.

### Homologação preparada para o usuário — projeto #5

- Pedido autorizado de preparar um projeto para a Secretaria agendar: criado
  **#5 — Projeto Homologação Fluxo Acervo**, sem modificar o #2 ou contas anteriores.
- Contas exclusivas: `fluxo.aluno1` (líder, HML5001), `fluxo.aluno2` (HML5002),
  `fluxo.secretaria`, `fluxo.orientador` e `fluxo.avaliador`. Sem staff/superuser.
- Proposta enviada pelo aluno, convite aceito, proposta e entrega PDF aprovadas
  pelo orientador, encaminhamento real à Secretaria e avaliador designado.
  Sem agendamento, presença, nota, documento publicável ou publicação.
- Cinco logins/perfis/vínculos/permissões/logouts HTTP validados. Secretaria vê
  o grupo elegível entre os não agendados; evidência em
  `.runtime/homologation-project5-agenda.png`. Fingerprints preexistentes idênticos.
- Backup/dump validado, manifest, reversão e resultados em
  `.runtime/showcase-homologation-20261105-185449/`. Senha comum nova somente em
  `credentials.dpapi`; não está em `.env.e2e` nem em texto claro no repositório.
- Entrega via clipboard bloqueada pelo Windows (Set-Clipboard, WinForms e
  clip.exe). Janela local aberta com `.runtime/show_homologation_credentials.ps1`;
  evento Shown confirmado por `credentials-window-shown.txt`. Senha exibida
  somente nessa janela; usuário confirmou que visualizou as credenciais.
- Próximo passo do usuário: entrar como `fluxo.secretaria` em
  `http://127.0.0.1:5173/`, abrir Agenda da Mostra e agendar o #5.
- Vite encerrou durante a primeira conferência; reiniciado com node/caminho
  absoluto em background, identidade registrada em `.runtime/processes.json`.
  Depois disso, os cinco acessos passaram. Não rerodar a criação da fixture.

- Atualização posterior autorizada pelo usuário ("Pode definir algum"): `ra4001`
  definido como líder do único grupo ativo do projeto #2. Era integrante ativo e
  o campo leader estava nulo. Correção administrativa pontual, com evento/auditoria
  SET_HOMOLOGATION_LEADER; sem reabrir a proposta nem alterar composição ou notas.
  Backup/reversão em `.runtime/project2-leader-20261105-184704/`. API do acervo
  validada: RA4001 permissions.leader=true; RA4002=false. Inventário confirmou
  preservação de membros, avaliador, orientador, agenda/status, notas e documentos.

- Implementação autorizada por "Implemente". Contrato: presença individual, nota
  DO GRUPO inclusive ausentes; orientador recebe resultados e avalia individualmente
  em outra plataforma; somente líder envia/aceita documento; Secretaria confirma.
- Backend novo em publication_workflow.py/publication_workflow_views.py e PDF
  server-side ReportLab 5.1.0 em publication_pdf.py. Estados LEGACY, ADVISOR,
  LEADER, SECRETARIAT, PUBLISHED; texto/PDF/snapshot imutáveis por versão, parent,
  SHA-256, revisão/aceite e confirmação da Secretaria. Locks de projeto e ID da
  versão vigente protegem concorrência. Não foi criado segundo acervo paralelo.
- Publicação exige entrega vigente aprovada, encaminhamento, apresentação,
  presenças individuais e nota concluída em todos os grupos ativos, consentimento
  e versão vigente validada. URL antiga de publicação delega ao mesmo serviço e
  não permite atalhos por aluno/orientador. Uploads legados preservados, mas não
  liberam publicação nova e não interferem em fluxo iniciado pelo formulário.
- Novo frontend acervoWorkflow.tsx, área **Publicação no acervo** para todos os
  atores; fila por projeto, resultados ao orientador, formulário do líder,
  revisão/aceite, histórico e confirmação/retirada pela Secretaria. Rotas antigas
  de documentos/formulário são aliases da interface nova. Rascunho é local ao
  formulário até enviar (sem autosave no servidor); falhas preservam os campos.
- Resultado da Mostra notifica orientador e as transições notificam o próximo
  responsável com link direto. Notas/presenças/RA não entram no PDF publicável.
- Migrações accounts 0007/projects 0025 aplicadas no backend Docker saudável;
  check e makemigrations --check aprovados. Inventários de projetos/agendas/notas/
  presenças/documentos/publicações antes/depois idênticos. SQLite/uploads anteriores
  preservados. Backup privado `.runtime/acervo-workflow-20261105-181418/`, dump
  validado e imagem exata `before-acervo-workflow-20261105`, reversão registrada.
- Projeto #2: PRESENTED pelo registro geral antigo, líder RA4001 (definido com
  autorização posterior acima), sem entrega vigente
  aprovada, sem presença individual/nota concluída. Avaliador avaliador.e2e.acervo,
  integrantes RA4001/RA4002, orientador prof.orientador1. Não
  fabricar outros atos acadêmicos automaticamente. Próxima validação do usuário deve
  sanar essas pendências pelo fluxo existente. Guia docs/ACERVO_WORKFLOW_GUIDE.md.

### Validação atual concluída

- UI/API/PostgreSQL reais: **4 passed** (desktop/mobile, aprovação direta e correção
  com aceite), desde presença/nota pela UI até documento/PDF, troca real de usuários
  com CSRF, confirmação da Secretaria e consulta no acervo. Runner
  scripts/validate_acervo_live.py, config dedicada playwright.acervo-live.config.ts.
  Somente bases test_acervo_live_UUID e arquivos temporários, sem dados normais.
- PostgreSQL descartável: scripts/validate_publication_postgres.py passou nos dois
  caminhos; submissões concorrentes criam uma versão e publicações concorrentes
  criam uma publicação. Nenhuma base test_publication/test_acervo_live remanescente.
- Frontend **76 passed**, cobertura configurada App/API **95,10%**, lint sem erros
  (warning preexistente Fast Refresh), build OK (warning preexistente Three.js).
- Playwright de contrato: **6 passed**, acervo e presença desktop/mobile, além dos
  quatro testes integrados reais acima. PDF sintético de cinco páginas lido:
  acentuação, paginação e conteúdo literal escapado corretos; preview privado em
  .runtime/acervo-pdf-preview.pdf.
- Backend final: **165 passed**, todos os 18 arquivos executados em lotes por
  arquivo, cobertura acumulada **93,14%**, limite original 85% respeitado em
  .runtime/.coverage-acervo-final. O lote final em background terminou com sucesso
  conforme notificação da ferramenta (92 testes iniciais + 73 finais). Tentativas
  integrais anteriores encerraram nativamente sem traceback em pontos diferentes;
  a causa local não foi determinada. Não houve exclusão de testes nem troca de
  hashers/limites; a validação integral inicial de 164 testes também havia passado.
- Ruff backend e novos runners aprovados. Ruff global scripts ainda tem os erros
  preexistentes de create_test_data.py/validate_planning_postgres.py; não executados.
  CI remoto e E2E legado global não executados; GF09/GF10 legado foi adaptado ao
  novo contrato e os novos testes integrados reais validam os dois caminhos.
- Smoke pós-migração no banco normal: login real avaliador.e2e.acervo, consulta
  do fluxo do #2 com RA4001/RA4002 e ações de publicação ocultas/negadas ao avaliador;
  logout. Captura .runtime/acervo-workflow-live-project2.png. Nenhum ato acadêmico.
- Descoberta corrigida pelo teste real: grading.py gravava group.name em
  ProjectStateEvent.new_status (varchar20), gerando 500 em nomes longos no PostgreSQL.
  Agora eventos preservam project.status e mantêm nome do grupo no motivo.
  Regressão permanente em test_member_attendance.py e E2E com nomes longos.
- O runner integrado agora gera o nome do banco no host e possui limpeza externa
  do UUID exato além do finally do servidor. Uma base residual de execução abortada
  foi identificada por seus quatro usuários/projetos sintéticos e removida sem
  tocar outros bancos. Não usar remoção por prefixo amplo.

### Retomada

- Branch main/HEAD 377bef8; mudanças preexistentes preservadas, sem commit/push.
- Implementação/validação técnica desta solicitação concluídas. Próximo passo é
  funcional: realizar entrega/aprovação e avaliação e seguir o guia no #2 sem fabricar pré-requisitos.
  Pode usar modelo rápido para orientar esse roteiro; mudança de fluxo/permissões
  exige modelo forte. Não confundir os atos pendentes do usuário com falha técnica.

## Pedido mais recente — validação do fluxo completo do acervo

- Correção explícita do usuário: presença por integrante e NOTA DO GRUPO, inclusive
  para ausentes. Não atribuir zero nem excluir nota por ausência. Resultados apenas
  recebidos/registrados pelo orientador (avaliação externa fora desta plataforma);
  aluno preenche formulário gerador de PDF; orientador aprova ou edita; edição
  retorna ao aluno validar; Secretaria confirma publicação. Histórico visível.
- Análise em docs/ACERVO_END_TO_END_VALIDATION.md. O fluxo atual NÃO atende esse
  requisito de ponta a ponta: falta encaminhar nota/presenças ao orientador,
  PDF é upload, edição não versiona
  texto/PDF, não há aceite do aluno e aluno publica diretamente.
- Nenhuma alteração funcional feita para esse novo requisito ainda. A implementação
  anterior abaixo foi validada, mas seus testes não comprovam o novo fluxo.
- Regras fechadas no chat: nota do grupo também para ausentes; orientador decide
  avaliação individual em outra plataforma. Somente o líder envia o documento e
  valida correções. Demais integrantes não representam o grupo nesses atos.
  Consentimento de dados continua regra separada. Não há decisões de negócio
  pendentes das duas perguntas anteriores.
- Próximo passo requer modelo forte: definir estados, migrações preservadoras,
  permissões por objeto/versão e testes dos dois caminhos. Não executar publicação
  no #2 para simular sucesso; preservar dados e todas as alterações preexistentes.

## Estado atual — presença individual/nota integrada, 05/11/2026

Esta seção substitui as fotografias históricas abaixo para a tarefa atual.

- Pedido autorizado implementado: checkboxes por GroupMember ativo; confirmação abre
  formulário de nota do grupo 0–10/observações. Ausência total não abre avaliação.
  Presença e nota são etapas persistentes e podem ser retomadas após recarregar.
- Modelo `ShowcaseMemberAttendance` guarda presença/autor/data, sem nota individual.
  `GradeSubmission.direct_value` e rubric opcional reutilizam histórico, média,
  conclusão e notificações existentes. Rubricas e IndividualGrade do orientador
  preservadas. Constraint garante rubrica OU nota direta 0–10, não ambas.
- Reenvios idênticos são idempotentes; lista completa obrigatória, sem integrantes
  externos/duplicados. Somente avaliador designado ativo; grupo ativo/projeto mutável.
  Avaliação concluída bloqueia novas notas em ambos os fluxos. Não foi implementada
  janela por horário nem alteradas as condições de publicação.
- Presença geral legada pode ser complementada antes da conclusão, mas sem mudar
  o resultado agregado. Não presumir integrantes presentes a partir de PRESENTED.
- Projeto #2 está PRESENTED pelo fluxo antigo, sem presenças individuais/nota.
  Avaliador: `avaliador.e2e.acervo`; integrantes RA4001/RA4002. O usuário deve
  complementar os checkboxes (ao menos um presente para manter PRESENTED), confirmar,
  preencher nota/observações e salvar. Nenhum desses atos foi realizado pelo agente.
- Backend Docker reconstruído e saudável; migração 0024 aplicada. Inventários de
  projetos, agendamentos/status e contagem de notas antes/depois idênticos. SQLite e
  uploads não foram alterados. Plataforma em http://127.0.0.1:5173/.
- Backup privado: `.runtime/member-attendance-20261105-173458/`, dump custom validado
  por pg_restore --list, inventários e REVERSAO.md. A imagem original do container
  já não constava no inventário Docker; código projects em execução foi copiado.
  Tag `before-member-attendance-20261105` preserva latest pré-rebuild (não a imagem
  exata que estava em execução). Não reverter schema depois de novas notas diretas
  sem planejar preservação dos dados; não restaurar dump sobre dados novos.

### Validações desta tarefa

- Backend completo: **150 passed**, cobertura **92,88%**, incluindo
  test_local_environment.py, sem excluir/mover testes. Execução via Python da .venv
  da raiz, load_environment e sys.path incluindo raiz; SQLite isolado pelo pytest.
- Frontend: **69 passed**, cobertura configurada App/API **91,70%**; lint sem erros
  (warning preexistente Fast Refresh) e build OK (warning preexistente Three.js).
- Playwright: **2 passed**, desktop/mobile, API controlada; confirma presença
  parcial, foco na nota, erro recuperável preservando campos, salvar e recarregar.
  Capturas `.runtime/member-attendance-desktop.png` e `...-mobile.png` inspecionadas.
- PostgreSQL descartável: `scripts/validate_attendance_postgres.py` passou;
  confirmações e notas simultâneas retornam o mesmo resultado, uma única linha.
  A base temporária foi removida; não copiou dados da plataforma.
- Login HTTP/CSRF e UI reais do avaliador no PostgreSQL: RA4001/RA4002 visíveis,
  habilitados e desmarcados; nenhum envio de presença/nota. Logout validado.
  Captura `.runtime/member-attendance-live-project2.png`.
- Ruff backend + novo script OK; Django check e makemigrations --check OK.
  Ruff global backend/scripts ainda acusa 15 erros preexistentes em
  create_test_data.py/validate_planning_postgres.py. O primeiro contém credencial
  embutida; não reutilizar/publicar sem saneamento. Nenhum desses scripts foi
  executado nesta tarefa. CI remoto, E2E legado completo e concorrência de
  avaliadores/empilhamento da agenda não foram revalidados nesta tarefa.

### Git e retomada

- Branch main, HEAD 377bef8; numerosas alterações anteriores preservadas, sem commit/push.
- Plano/contrato/fontes: docs/MEMBER_ATTENDANCE_PLAN.md. Código novo principal:
  backend/tests/test_member_attendance.py, migration 0024,
  frontend/src/showcasePresence.tsx e frontend/e2e/member-attendance.spec.ts.
- Próximo passo funcional: usuário testa avaliação do #2, depois documento do aluno
  RA4001/RA4002, aprovação por prof.orientador1 e publicação segundo os gates reais.
  Não usar contas do #1. Roteiro mecânico pode usar modelo rápido; mudança de regra
  de negócio/segurança exige análise mais forte.

## Fotografia operacional — 05/11/2026

### Entrega atual — notificações e agenda visual

- Atualização posterior autorizada: usuário esclareceu que Admin também inclui Secretaria nesses cadastros. Criação/renomeação de prédios/salas agora usa `require_showcase_staff` no backend e fica visível para ambos na interface. Não foram ampliados privilégios de superusuário Django nem promovida conta da Secretaria.
- Criado `admin.teste` no PostgreSQL com papel ADMIN da aplicação e a credencial de homologação existente; is_staff e is_superuser permanecem falsos. Conta não existia e nenhuma conta anterior foi sobrescrita. Registro/auditoria em `.runtime/admin-secretariat-20261105-112337/created-account.json` e AuditEvent CREATE_HOMOLOGATION_USER (sem senha no artefato).
- Validado após ajuste: 16 testes backend de planejamento, 7 testes frontend de agenda, Ruff/lint/build; logins HTTP/perfis/logout de secretaria.teste e admin.teste; ambos chegam à validação de entrada de cadastro (400, não 403), sem criar locais fictícios. Alunos/professores continuam com 403 nos testes. Backend Docker reconstruído e saudável. Suítes completas da entrega anterior abaixo são históricas, não repetidas nesta alteração localizada.
- Para reverter apenas a conta sintética após uso, preferir desativá-la com autorização, preservando histórico; registro contém o UUID exato para não confundir com outras contas. A revisão da regra de permissão deve sempre respeitar o esclarecimento atual do usuário.
- Projeto #1 permanece `PENDING_APPROVAL`, sem encaminhamento real; precisa seguir aprovação/entrega/encaminhamento existentes antes de aparecer no quadro. Não há mais bloqueio de conta Admin para cadastro de locais.
- Implementação solicitada no chat concluída e disponível no PostgreSQL Docker em `http://127.0.0.1:5173/`. Sem commit/push; manter as alterações preexistentes de CI, inicializadores, importação e Mostra.
- Corrigidas duplicatas de Agenda/Acervo no App e retirada a navegação paralela de Agendamento da Mostra (rota antiga é alias da mesma tela). Interface única em `showcaseScheduler.tsx`; antigo formulário ShowcasePanel removido e seus testes substituídos pelos do fluxo registrado.
- Secretaria/Admin criam/renomeiam prédios/salas; letras e números crescentes estáveis. Secretaria/Admin cadastram dias/janelas e agendam grupos aprovados/encaminhados. Grade de 30 min com drag-and-drop, movimentação, resize inferior, botões ±30 e formulário acessível. Busca por projeto, integrante/usuário ou número, inclusive horários em outros dias/salas; ocupação da grade não some com o filtro.
- Fonte única: ShowcaseEntry estendido com day/room/end_date, integrado à presença/publicação. Backend em `projects/planning.py` aplica papel, encaminhamento, limites, colisão e versão updated_at. Modelo de protótipo ShowcaseSession preservado, mas rotas antigas não gravam e respondem 410 para staff.
- Migração 0022 aplicada: locais/dias/contador, novos campos da entrada e Project.number único/crescente/read-only. Projetos existentes numerados por created_at/id, sem alterar UUIDs. Projeto sintético existente agora é **#1**.
- Notificações: corrigido clique externo em captura que desmontava o item antes do onClick. API fornece target_url por tipo/destinatário (projeto/documento/publicação/convites/sala). Falha ao marcar leitura não bloqueia navegar. Migração 0023 aplicada: vínculo ausente em avisos antigos de encaminhamento reparado apenas por título exato e único.
- O aviso de secretaria.teste tinha project nulo e não havia ProjectForwarding no banco. Link recuperado para projeto #1 sem inventar encaminhamento. O teste de navegador real abriu o projeto pela notificação e marcou-a como lida. Ainda não há grupos elegíveis, locais ou datas na base normal; não foram criados exemplos artificiais.
- Removido setState desnecessário no listener nativo de input em captura: ele apagava valores controlados antes do onChange React. DirtyRef continua protegendo formulários não salvos; filtros da agenda são explicitamente não-mutáveis.

#### Validações desta entrega

- Backend completo: **119 passed**, cobertura **92,29%** com limite 85%, SQLite isolado de testes; não usou o SQLite preservado da plataforma.
- Frontend: **61 passed**, cobertura configurada App/API **91,64%**, lint sem erros (warning preexistente em projectLifecycle), build OK (warning preexistente de chunk Three.js).
- Playwright novo: **4 passed** em desktop/mobile, com API controlada, incluindo arrastar, aumentar/diminuir duração, mover cartão, recarregar, buscar integrante, clicar notificação e ausência de duplicatas/erros de página. Capturas em `.runtime/planning-desktop.png` e `.runtime/planning-mobile.png`.
- Navegador real + PostgreSQL: login secretaria.teste, clique no aviso antigo abre projeto #1, Agenda/Acervo únicos e logout; captura `.runtime/planning-live-secretariat.png`. Não foram feitos agendamentos fictícios na base normal.
- PostgreSQL concorrente real em base descartável: 8 criações simultâneas obtiveram números únicos; duas reservas simultâneas na mesma sala/horário resultaram em uma gravação e um conflito. Script `scripts/validate_planning_postgres.py` cria e remove somente base temporária própria, sem copiar dados da plataforma.
- Ruff backend/scripts OK; Django check e makemigrations --check --dry-run no Docker OK. CI remoto e E2E legado completo não repetidos nesta entrega.
- Backup pré-migrações em `.runtime/showcase-planning-20261105-104956/`, dump custom, inventários/reversão; imagem anterior preservada. Contagens e UUIDs/status dos projetos conferidos após migração, sem exclusões de banco/uploads. Não houve alteração de senhas nesta entrega.
- Guia: `docs/SHOWCASE_PLANNING_GUIDE.md`. Fontes oficiais/decisões: `docs/SHOWCASE_PLANNING_PLAN.md`. Próximo passo é a validação funcional pelo usuário: Admin cadastra locais, Secretaria datas, orientador conclui encaminhamento real do #1; não antecipar esses atos institucionais. Pode usar modelo rápido para esse roteiro; regra futura de janela de avaliação exige decisão de negócio.
- Melhorias de UX da agenda (05/11/2026): `rowHeight` aumentado de 112 para 160 (maior espaço entre horários); cards de grupos não agendados reduzidos (padding 0.6rem, margin 0.5rem); múltiplos grupos podem ser agendados na mesma sala e mesmo horário (validação de conflito de sala removida; apenas o avaliador tem restrição de conflito). No frontend, múltiplos bookings no mesmo slot são empilhados verticalmente com offset de 42px.

### Estado anterior do dia (histórico)

- Última atualização: a pedido explícito do usuário, as mesmas cinco contas sintéticas receberam a senha simplificada escolhida para homologação; credencial E2E local atualizada e cinco logins/sessões/logouts HTTP novamente aprovados. Regras globais de senha NÃO foram relaxadas; exceção aplicada diretamente apenas a essas contas de teste. Backup DPAPI de hashes/configuração anteriores: `.runtime/homolog-password-reset-20261105-092146/previous-state.dpapi`. A entrega por clipboard anterior foi substituída pela credencial solicitada, também copiada para a área de transferência. Nenhum segredo registrado aqui.
- Atualização posterior, autorizada explicitamente pelo usuário: redefinidas as senhas de somente `ra3001`, `ra3002`, `prof.teste1`, `secretaria.teste`, `avaliador.e2e.acervo` no PostgreSQL para a credencial E2E local existente. Backup dos hashes anteriores criptografado com DPAPI em `.runtime/synthetic-password-reset-20261105-090349/`, com reversão documentada. Sem mudança em contas reais ou no SQLite.
- Login agora validado: as cinco contas passaram em login/perfil/logout HTTP pelo proxy Vite para Docker; sessão bloqueada após logout; login sem CSRF bloqueado; projeto PostgreSQL encontrado. A pendência de credencial descrita abaixo foi resolvida. Senha entregue pela área de transferência, não no chat/documentação. Próximo passo é o fluxo manual de aprovação/entrega/encaminhamento/Mostra/avaliação, não executado nesta redefinição.
- Pedido atual concluído: usuário escolheu PostgreSQL Docker como banco único do uso normal. Não houve mesclagem nem exclusão de dados; nenhuma senha alterada. Sem commit/push.
- `Iniciar Plataforma.bat` usa `scripts/start_platform.ps1`: backend/db Docker com build atualizado e espera de saúde; Vite local em `http://127.0.0.1:5173/`, `/api` pelo proxy para Docker em `127.0.0.1:8000`. Não inicia Django SQLite.
- Helper `scripts/platform_common.ps1`: projeto/arquivos Compose explícitos; verifica conexão real PostgreSQL, não só health; sem fallback SQLite. `compose.yaml` fixa `DATABASE_ENGINE=postgresql`; override expõe backend somente em loopback.
- `Parar Plataforma.bat` para Vite identificado por PID/data de criação/caminho e os serviços Compose, preservando volumes. Registros de PIDs antigos não autorizam encerrar processos desconhecidos. Atalhos auxiliares também usam Docker.
- Plataforma deixada em execução. Projeto PostgreSQL preservado: `Projeto E2E Acervo - Teste Completo`, ID `36da1dac-6533-46a5-8119-8c179620ae7d`, ainda `PENDING_APPROVAL`. Migração preexistente no working tree `0021_showcasesession` aplicada ao reconstruir backend.
- Backup/reversão local: `.runtime/docker-standardization-20261105-081510/` (arquivos anteriores, cópia SQLite, dump PostgreSQL custom, `REVERSAO.txt`). Imagem anterior preservada com tag `plataforma_extensionista-backend:before-standardization-20261105`. Backup contém dados privados: não publicar. Não restaurar PIDs antigos.
- Validações executadas: iniciar, iniciar novamente reutilizando Vite, parar e reiniciar; conexão PostgreSQL real; projeto preservado; SQLite com hash idêntico; frontend/API direta/API pelo proxy HTTP 200; `manage.py check` sem issues; teste de porta ocupada recusada sem encerrar processo; `scripts/tests/platform_launchers.ps1` passou (mocks de Docker, propagação de falhas, segurança de PIDs e sintaxe).
- Login HTTP tentado com credencial E2E local retornou 400; conferência `check_password` confirmou divergência da senha no PostgreSQL. Não é evidência de regressão de autenticação. Login manual não validado nesta etapa, nenhuma senha alterada.
- Não foram repetidos pytest completo, lint/build frontend ou E2E nesta padronização. Resultados de sessões anteriores abaixo são históricos.
- Working tree já continha alterações de Mostra, CI e scripts não rastreados; preservados. O novo agendamento `ShowcaseSession` segue incompleto (autorização, associação, relação inválida `leader`, integração com presença); usar **Agenda da Mostra** para o fluxo existente. A janela de avaliação por horário foi adiada explicitamente pelo usuário.
- Próxima ação: validar o fluxo manual com credenciais válidas do PostgreSQL. Se for preciso redefinir contas de teste, obter autorização específica. Essa operação mecânica pode usar modelo rápido; integração da agenda exige análise mais forte.

## Registro anterior (histórico; não descreve o ambiente atual)

## Fotografia operacional — 29/10/2026

Pedido atual: finalização técnica dos E2E GF-09/GF-10, autorizada pelo usuário.
Escopo corrigido e validado; o projeto **não está globalmente verde**.
Histórico de funcionalidades e decisões da Sprint 7 permanece em `TASKS.md` e
`docs/sprints/SPRINT_07_SPEC.md`. A especificação tem aceite registrado.

## Git e preservação de dados

- Branch `main`, HEAD `fb956d1`. Nenhum commit/push nesta etapa.
- Working tree já tinha diversas mudanças e scripts não rastreados antes desta etapa.
  Não usar limpeza ampla, reset, stash ou `git add .`.
- Não foram apagados bancos, uploads ou arquivos experimentais.
- E2E cria projetos sintéticos e cancela ativos somente com prefixo
  `Projeto E2E Acervo `, associados aos usuários de teste. Demais projetos preservados.
- `.gitignore` novo protege `.env`, ambientes, banco SQLite, uploads privados,
  builds, caches e relatórios. Scripts locais antigos ainda exigem revisão seletiva.

## Correções desta etapa

1. **Segurança do login:** `backend/accounts/views.py` no próprio HEAD aceitava
   qualquer senha, não exigia CSRF e imprimia credenciais. Restaurado o fluxo seguro
   já existente no histórico `4a396bc`: `authenticate()` antes de `login()`,
   resposta genérica, validação de usuário ativo e tentativas por identificador/IP.
   Removidos leitura manual de body e logs sensíveis. O teste novo falhou contra
   o login antigo (200 em vez de 400) e passa contra o corrigido em oito variações.
2. **Frontend:** encoding CP1252/UTF-8 de `App.tsx` reparado sem perder lógica.
   Mantidos carregamento real dos projetos nas três rotas de publicação e regex
   corrigida; removidos três `reload` não usados. Novo teste cobre rota de publicação
   e reconhecimento do membro pelo projeto real.
3. **Proxy/configuração:** removidos callbacks redundantes de Cookie/Set-Cookie,
   logs e comentários experimentais. Mantido proxy padrão Vite para 127.0.0.1:8000
   e fallback relativo `/api/v1`. CORS usa allowlist, não liberação global.
4. **E2E:** `page.request` compartilha cookies; eliminada cópia manual, debug e espera
   fixa. Cenários independentes com nomes diferentes. Contextos novos sem sessão
   comprovam acesso anônimo, HTTP 200, ausência de `sessionid` e renderização concluída.
   GF-09 publica pela interface (201), encontra projeto no acervo e verifica PDF
   autenticado (200) / anônimo (403). GF-10 confirma erro JSON exato (400), nenhuma
   publicação persistida e ausência no acervo após resposta e carregamento.
5. **Execução local:** `backend/run_server.ps1`/`.bat` leem `.env` com LF ou CRLF
   sem imprimir valores. Runner `scripts/validate_showcase_e2e.py` gerencia os seus
   próprios servidores durante a execução; recusa portas ocupadas e encerra apenas
   seus processos em `finally`. Não embute senha. Avaliador auxiliar também usa env.
6. **Documentação:** contexto, tarefas, README e desafios corrigidos. Retiradas
   instruções antigas incorretas que sugeriam relaxar autenticação.

## Validações realmente executadas

| Validação | Resultado atual |
| --- | --- |
| GF-09/GF-10 desktop, `--repeat-each=2` | **4 passed**, 37,4 s na última execução, incluindo restrição de PDF |
| `npm run lint` | 0 erros, 1 warning preexistente em `projectLifecycle.tsx` |
| `npm test` | **51 passed**, 7 arquivos; cobertura de linhas 90,43% |
| `npm run build` | OK; aviso de chunk Three.js maior que 500 kB |
| pytest completo com cobertura | **98 passed**, cobertura **92%** (limite 85%) |
| `manage.py check` | OK |
| `makemigrations --check --dry-run` | Sem mudanças |
| Ruff global `backend` + `scripts` | 0 erros |
| Backend Docker rotacionado (chave + senha PostgreSQL) | Saudável, `health` 200, volume preservado |
| Testes de segurança de login no PostgreSQL | CSRF, senha inválida, login válido e sessão OK; usuário transitório revertido |

Não foram executados CI remoto, pip-audit ou E2E completo em PostgreSQL.
O runner encerrou os servidores locais após os testes; backend em Docker permanece ativo.

## Correções de segurança concluídas nesta etapa

1. **Login seguro restaurado:** `authenticate()` antes de `login()`, CSRF obrigatório,
   resposta genérica, validação de usuário ativo, controle de tentativas por identificador/IP,
   sem logs de credenciais. Oito variações de regressão.
2. **Frontend:** encoding CP1252/UTF-8 de `App.tsx` reparado; removidos logs de senha/cookies,
   callbacks experimentais do proxy, esperas fixas e cópia manual de `sessionid`.
3. **E2E:** contextos anônimos isolados, nomes distintos de projeto, espera de renderização,
   verificação de PDF autenticado (200) / anônimo (403).
4. **Artefatos locais:** scripts experimentais com credenciais arquivados sanitizados e
   removidos do working tree; logs sanitizados; `.gitignore` protege `.env`, bancos e uploads.
5. **Rotação:** chave de aplicação local, senha PostgreSQL e senhas das cinco contas sintéticas
   rotacionadas com backup criptografado (DPAPI) em `.runtime/rotation-20261029-141253/`.
6. **Docker:** `protected-media` montado como volume nomeado; imagem reconstruída sem
   expor credenciais em argv/stdout.

## Não alterados nesta etapa

- Regra de convites: mantida a decisão do commit `542f8f2` (qualquer integrante ativo pode
  convidar); teste ajustado e autorização de consulta de alunos coberta.
- Nenhum banco ou upload apagado; nenhum commit/push neste ponto.

Para repetir apenas o escopo aprovado, com fixtures existentes e senha fornecida
via variável `E2E_TEST_PASSWORD`: executar `scripts/validate_showcase_e2e.py` com Python
local. O script usa `backend/.venv` para Django, Node do PATH e SQLite. A `.venv`
da raiz contém pytest e Ruff; `backend/.venv` não contém esses runners.
Fixtures: RA3001, RA3002, prof.teste1, secretaria.teste, avaliador.e2e.acervo;
vínculos ativos, sala SALA-A, tema Sala A, matrícula EXT101-E2E e competência Extensão.
Não registrar senha em documentação ou código. Nenhuma senha de usuário real alterada nesta etapa.

## Fontes oficiais consultadas

- Django 5.2.17: https://docs.djangoproject.com/en/5.2/topics/auth/default/#authenticating-users
- Playwright 1.62.1: https://playwright.dev/docs/api/class-browser#browser-new-context
  (`newContext` não compartilha cookies/cache; deve ser fechado explicitamente).
