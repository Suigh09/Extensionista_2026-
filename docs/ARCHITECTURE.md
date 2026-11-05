# Arquitetura atual — visão operacional

## Execução normal no Windows (05/11/2026)

`Iniciar Plataforma.bat` → `scripts/start_platform.ps1` → helper `scripts/platform_common.ps1`:

1. Docker Compose inicia/reconstrói backend Django e aguarda PostgreSQL/backend saudáveis.
2. Backend usa PostgreSQL (`DATABASE_ENGINE=postgresql` fixado no Compose), preservado no volume `postgres_data`; uploads permanecem no volume `protected_media`.
3. Node executa Vite local em `127.0.0.1:5173`; o proxy `/api` encaminha ao backend Docker em `127.0.0.1:8000`.
4. O helper abre conexão no backend e confirma PostgreSQL. O inicializador verifica API pelo proxy antes de informar disponibilidade.

`Parar Plataforma.bat` encerra somente o Vite registrado com identidade confirmada e executa Compose `stop`, sem remover volumes. O Compose também define frontend empacotado em 8080, mas esse serviço não é iniciado pelo atalho normal.

## Aplicação e testes

- Fluxo completo do acervo (05/11/2026): publication_workflow.py centraliza
  elegibilidade/autorizações/transições; publication_workflow_views.py expõe fila e
  recurso por projeto. PublicationDocument versiona título/resumo/conteúdo/snapshot/
  PDF/hash/parent, com metadados de aprovação/aceite; Publication.confirmed_by registra
  o ato final institucional. ReportLab gera o PDF privado no servidor.
  acervoWorkflow.tsx unifica as interfaces por papel e substitui rotas antigas de
  formulário/documento/publicação; o backend antigo de publicação delega ao serviço
  único. Notificações SHOWCASE_RESULTS/PUBLICATION_WORKFLOW apontam ao fluxo.
- Validação integrada isolada: runner host cria container temporário na porta 8002,
  base PostgreSQL UUID e arquivos temporários; navegador usa Vite existente com
  encaminhamento das requisições para a API real isolada. Não há respostas mockadas
  nesse teste. Finalmente encerra só seu container e remove só sua base UUID.

- Presença individual (05/11/2026): ShowcaseMemberAttendance referencia entrada e
  GroupMember; confirmação completa/idempotente sob lock de grupo/entrada. Fonte
  única de nota do grupo continua GradeSubmission, agora rubrica OU direct_value.
  Novo endpoint evaluation conclui nota direta com observações, reutilizando
  média/histórico/notificações. ShowcaseAttendanceCard abre formulário após presença,
  preserva campos em falhas e oferece retomada. Nenhum gate novo de publicação.

- Backend: Django/DRF; apps `accounts`, `academic`, `core`, `projects`; autenticação por sessão com CSRF.
- Frontend: React/TypeScript/Vite; API relativa `/api/v1` na execução pelos atalhos.
- SQLite `backend/test.sqlite3` é legado preservado, não banco da execução normal. Scripts E2E isolados ainda podem usá-lo explicitamente; não há sincronização com PostgreSQL.
- Agenda visual unificada: `ShowcaseDay` (dia/janela), `ShowcaseBuilding`/`ShowcaseRoom` (locais físicos), `ShowcaseEntry` (grupo/dia/sala/início/fim e presença). Admin e Secretaria gerenciam locais/datas, conforme esclarecimento do usuário. `planning.py` aplica permissões, elegibilidade, passos de 30 min, conflitos e controle otimista por updated_at, com bloqueios de grupo/projeto/dia no PostgreSQL.
- `NumberSequence` fornece números únicos crescentes para projetos/prédios/salas. `Project.number` é visível/read-only na API; UUID primário preservado. Migração 0022 numera projetos existentes por created_at/id.
- `ShowcaseSession` é legado sem interface ativa; endpoints antigos não gravam e respondem 410 a staff. Os registros/modelo foram preservados; o banco atual não continha sessões desse protótipo.
- Notificações recebem `target_url` calculado na API por tipo/destinatário; clique fora usa containment do sino, sem desmontar os itens antes do clique interno. Migração 0023 recupera project ausente em avisos de encaminhamento apenas se o título identifica exatamente um único projeto.
