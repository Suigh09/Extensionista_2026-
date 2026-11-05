# Decisões técnicas

## 05/11/2026 — Implementação do acervo versionado

- Autorizada explicitamente no chat após o contrato de negócio. Reutilizar os
  modelos de documento/publicação com campos aditivos e estado LEGACY para dados
  anteriores; não converter uploads antigos em aprovações/aceites novos fictícios.
- Estados ADVISOR → SECRETARIAT ou ADVISOR → LEADER → SECRETARIAT → PUBLISHED.
  PDF/texto/snapshot por versão, parent, autor/datas, aceite e confirmação específicos
  da versão. Nenhum texto enviado é sobrescrito pelo novo fluxo.
- ReportLab 5.1.0 escolhido para formulário textual institucional: dispensa runtime
  nativo de HTML/CSS do WeasyPrint; exige layout programado, aceito para esse template.
  Fontes TTF empacotadas preservam português; textos escapados não carregam HTML,
  arquivos ou URLs externas. PDF não inclui RA/notas/presenças.
- Gravar sob lock do projeto, com expected_document obrigatório (null apenas no
  primeiro envio). Alternativa count()+1/estado só no frontend rejeitada por corrida
  e atalhos de autorização. Testes concorrentes em PostgreSQL confirmaram unicidade.
- Líder envia e aceita; orientador aprova sem alterações ou cria revisão; Secretaria/
  Admin confirma publicação. API antiga não publica diretamente como aluno.
  Retirada institucional/histórico/vedação de republicação preservadas.
- Orientador recebe resultados sem gate de avaliação individual externa. Formulário
  local é rascunho até o envio; autosave persistente não foi acrescentado ao escopo.
- Fontes: docs/ACERVO_END_TO_END_VALIDATION.md, documentação oficial Django 5.2 e
  ReportLab Platypus. Guia de uso em docs/ACERVO_WORKFLOW_GUIDE.md.

## 05/11/2026 — Esclarecimento do fluxo completo do acervo

- Decisão de negócio explícita no chat: nota da Mostra é do grupo, inclusive para
  integrantes ausentes, pois a contribuição ocorre durante o projeto. Presença é
  individual e independente da nota. Não gerar nota zero/excluir nota por ausência.
- Orientador recebe nota/presenças/observações para registro; eventual julgamento
  individual é realizado em outra plataforma, sem novo gate ou integração externa.
- Somente o líder envia o formulário e valida alterações do orientador. Secretaria
  confirma publicação final. Outros integrantes não podem representar o grupo
  nesses atos, embora possam consultar o histórico autorizado.
- Estado: contrato funcional esclarecido, novo fluxo completo ainda não implementado.
  Evidências/lacunas/critérios em docs/ACERVO_END_TO_END_VALIDATION.md.

## 05/11/2026 — Presença por integrante e nota direta do grupo

- Pedido autorizado: checkboxes e nota 0–10/observações após confirmar presença.
- Usar ShowcaseMemberAttendance somente para presença auditada de GroupMember.
  Não atribuir nota por aluno sem pedido; IndividualGrade continua do orientador.
- Reutilizar GradeSubmission com rubric nullable e direct_value, constraint
  mutuamente exclusiva. Alternativa rejeitada: tabela de notas paralela, que
  exigiria resolver médias/conclusões conflitantes e duplicar histórico.
- Consequência: avaliação direta aparece como avaliação concluída nas APIs antigas;
  rubricas continuam disponíveis, mas não podem sobrescrever conclusão e vice-versa.
- Complementar presença geral legada só antes da conclusão e sem mudar o agregado;
  nunca presumir presença individual. Confirmação e avaliação separadas permitem
  recuperação após falha sem reenviar/duplicar registros. Sem novo gate de publicação.
- Fontes e contrato: docs/MEMBER_ATTENDANCE_PLAN.md. Migração aditiva 0024 aplicada;
  downgrade após notas diretas exige estratégia de dados, não rollback cego.

## 05/11/2026 — Agenda única, locais físicos e identificação curta

- Pedido do usuário autoriza cadastro de locais físicos e dias por Admin/Secretaria (esclarecimento explícito posterior: ao dizer Admin, também inclui Secretaria nestes cadastros) e agenda por sala com meias horas, movimentação/redimensionamento e pesquisa. Isso não concede superusuário Django nem promove contas da Secretaria para o papel ADMIN.
- Preservar `ShowcaseEntry` como fonte para presença/publicação, estendendo com dia, sala e fim. Retirar o protótipo paralelo da interface e da gravação, mantendo dados/modelo. Evita duas agendas inconsistentes.
- Prédios e salas físicos não reutilizam `AcademicRoom`, que possui responsabilidades acadêmicas distintas. Nomes editáveis, códigos/números crescentes e estáveis, sem exclusão destrutiva.
- Número curto é campo adicional: trocar a PK UUID quebraria referências/URLs. Contadores persistentes com locks evitam `count()+1`/`max()+1` sujeitos a corrida; números existentes atribuídos por ordem de criação, sem mudar UUID.
- Gravações serializadas por grupo/projeto/dia; checar colisões na sala, limites e versão da entrada. Reservas concorrentes verificadas em PostgreSQL real descartável.
- Sem dependência frontend extra: drag-and-drop nativo, Pointer Events para resize, formulário/botões para teclado/mobile. Persistir ao soltar e reconsultar após erro.
- Reparar links legados de notificações só com correspondência exata/única do título; não usar aproximação e não inventar encaminhamento a partir de aviso.
- Fontes oficiais e guia em `docs/SHOWCASE_PLANNING_PLAN.md` e `docs/SHOWCASE_PLANNING_GUIDE.md`.

## 05/11/2026 — Banco único no uso normal

- Contexto: os atalhos iniciavam Django/SQLite enquanto havia backend PostgreSQL Docker. Os bancos tinham projetos com o mesmo nome, mas IDs e credenciais distintos, confundindo a validação manual.
- Decisão: aceita explicitamente pelo usuário; uso normal exclusivamente no PostgreSQL Docker. Manter Vite local na porta 5173 para acompanhar alterações de frontend; API por proxy ao backend Docker na porta 8000, exposta somente em loopback.
- Alternativa: apenas SQLite simplificaria a execução sem Docker, mas preservaria diferenças de persistência/concorrência em relação à produção. Escolhido PostgreSQL pela consistência e proximidade da stack de implantação.
- Consequências: Docker Desktop obrigatório; inicializadores falham sem Docker, sem fallback. A imagem backend é reconstruída no início, migrações são aplicadas pelo comando Compose e o helper verifica conexão PostgreSQL real.
- Preservação: SQLite e volumes existentes mantidos, sem mesclagem de dados/senhas. Testes explicitamente isolados ainda podem usar SQLite, sem disputar as portas da plataforma aberta.
- Status: implementada e validada por ciclo iniciar/reutilizar/parar/reiniciar. Após autorização adicional, senhas das cinco contas sintéticas redefinidas com backup DPAPI; login/perfil/logout HTTP das cinco contas validados via proxy Docker.
