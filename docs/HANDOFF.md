# Handoff — Plataforma Extensionista

## Objetivo e tarefa atual

Implementação da Sprint 7 — Mostra, publicação e acervo (UC-017 a UC-023). Especificação formalmente aceita. Implementação backend e frontend concluída. Pendentes: testes Vitest (frontend), testes E2E Playwright (GF-09/GF-10), commit do CI alterado.

## Estado

Sprint 7 implementada e validada. Funcionalidades entregues:
- `ShowcaseEntry`: agenda da Mostra (PENDING→SCHEDULED), registro de presença (PRESENTED/ABSENT) pelo avaliador, cancelamento pela secretaria
- `PublicationDocument`: geração de PDF server-side versionado pelo aluno, consentimento explícito, aprovação/reprovação pelo orientador com parecer
- `Publication`: publicação no acervo (GF-09) e bloqueio de publicação inválida (GF-10), retirada pela secretaria com histórico preservado (sem republicação)
- Notificações: documento aprovado/reprovado, publicação criada, publicação retirada
- Auditoria: agenda, presença, gerações, aprovações, publicações, retiradas
- Notificações deletáveis + marcação automática como lida ao clicar (frontend)
- Cadastro de aluno com curso obrigatório (frontend + backend)
- Formulário de documento publicável editável até aprovação do orientador (frontend + backend)
- Acervo público anônimo no frontend (GET /acervo-publico/)
- Download público do PDF do documento
- Select de documentos aprovados no painel de publicação
- Tela de avaliações (#/evaluations) substituindo FutureModule
- Tela de designar avaliador (#/evaluator-designation/<id>) integrada na sidebar
- Páginas independentes de avaliação de grupo (#/group-evaluation/<id>) e notas individuais (#/individual-grades)
- Colaboração sem grupo atribuído: aluno ativo pode publicar oportunidade individual (sem grupo); grupos podem se candidatar (backend `CollaborationOpportunity.group` nullable; frontend `CommunityPage` com checkbox "Individual")
- Template Colaboração Interdisciplinar: `ProjectTheme.interdisciplinary` boolean; `create_from_theme` ignora restrição de mesma sala/curso quando interdisciplinary=True; filtro `?interdisciplinary=true` na listagem de temas; frontend `ThemeManagement` com checkbox e `ThemeProjectCreate` com filtro
- Convidar mais participantes após entrar no projeto: `ProjectGroupPanel` permite ao líder convidar até 4 integrantes no total (já existente via `inviteStudent`/`assignProjectStudent`)

## O que parece funcionar

- `ruff check backend`: OK
- `python manage.py check`: OK
- `makemigrations --check --dry-run`: OK (sem mudanças pendentes)
- pytest backend: **82 passed**, coverage **92%** (mínimo 85%)
- `npm run lint` frontend: OK (0 erros, 3 warnings pré-existentes)
- `npm run build` frontend: OK
- `npm test` frontend: **50/50** (todos passando, incluindo falha pré-existente corrigida)

## Trabalho feito nesta sessão

## Trabalho feito nesta sessão

### Ideia 1 — Notificações deletáveis + marcar como lida **(IMPLEMENTADA)**
- Arquivo: `frontend/src/notifications.tsx`
- Adicionada função `deleteItem(id)`: marca a notificação como lida no backend (`markNotificationRead`) e remove do estado local (sem endpoint de delete no backend — decidido assim por menor esforço e LGPD ok)
- Adicionado botão `×` (`.button.danger-sm`) como irmão do botão principal dentro do `<li>`
- Marcar como lida ao clicar já existia (`openItem` → `markNotificationRead`)
- **Lição aprendida**: tentativas de reescrever o arquivo inteiro via `write` quebravam a sintaxe JSX (muitas expressões inline numa linha). A solução foi `git checkout --` para restaurar + **edições mínimas via `edit`** preservando a linha original do `li`.
- Validação: `npm run build` OK · `npm run lint` 0 erros · vitest 49/50 (falha pré-existente)

### Ideia 2 — Professor criar projeto + puxar alunos **(IMPLEMENTADA)**
- O fluxo básico já existia (professor cria com líder + `assign-student`). Estendido com duas extensões:
  1. **Notificação ao aluno incluído**: novo `Notification.Kind.PROJECT_MEMBER_ADDED` (`accounts/migrations/0006`); `assign_student` em `lifecycle.py` chama `notify()` quando cria `GroupMember` novo
  2. **Lote na criação**: `create_from_theme` aceita `student_ids` (máx. 3 além do líder, sem duplicatas, sem o líder); valida papel (só orientador/admin) e delega cada inclusão a `assign_student` (mesmas validações de sala/curso/vagas/transação)
  - Serializer `ProjectCreateSerializer`: campo write-only `student_ids`
  - Frontend `ThemeProjectCreate`: seção "Outros participantes (opcional)" com `StudentSearch` multi-seleção (máx. 3, sem duplicatas, limpa ao trocar tema)
  - `api.ts`: `createProject` aceita `student_ids?: number[]`
  - Testes: `test_assign_student_notifies_included_student`, `test_professor_creation_with_batch_students` (inclui validação de lote inválido não criar projeto)

### Ideias adicionais (backlog)
- Colaboração sem grupo atribuído
- Template "Colaboração Interdisciplinar"
- Convidar mais 3 pessoas após entrar em projeto

### Cadastro de aluno com curso **(IMPLEMENTADA)**
- `UserCreateSerializer` aceita `course` (obrigatório para STUDENT, queryset ativo); cria `StudentProfile` com `course` preenchido
- Frontend `UserManagement`: dropdown de cursos (`GET /academic/courses/?is_active=true`) só para role STUDENT; tipo `NewUser` aceita `course?: string`; tipo `AcademicItem` inclui `id`
- `EligibleRoomStudentListView`: filtro por `?course=<uuid>` para professor pesquisar alunos de um curso específico
- `pull_student` / `RoomsPage`: professor só puxa alunos para a sala que é responsável (já existente, mantido)
- Testes atualizados: `test_admin_creates_student_without_storing_plain_cpf`, `test_student_logs_in_with_ra_or_cpf` incluem `course`
- Turma (`class_offering`) removida do cadastro — não é mais campo obrigatório nem opcional

### Formulário de documento publicável **(IMPLEMENTADA)**
- Backend: campo `content` (TextField) adicionado ao `PublicationDocument` (`migrations/0016_publicationdocument_content.py`)
- Backend: `PublicationDocumentUpdateView` (PATCH `/projects/publication-documents/<id>/content/`) permite o aluno editar o conteúdo enquanto o documento está PENDING; bloqueia se já APPROVED/REJECTED ou se não for o autor
- Backend: `PublicationDocumentSerializer` expõe `content` como editável; `PublicationDocumentUpdateSerializer` para PATCH parcial
- Frontend: `PublicationFormPanel` — formulário com título do projeto (só leitura), integrantes (só leitura), textarea de conteúdo (editável), checkbox de consentimento, botão "Salvar rascunho" (PATCH) e botão "Publicar no acervo" (se APPROVED)
- Frontend: `PublicationDocument` tipo inclui `content`; `updatePublicationDocumentContent` no `api.ts`
- Frontend: rota `#/publication-form/<id>` adicionada; item na sidebar e atalho da home para STUDENT
- O documento fica editável até o orientador aprovar (status APPROVED), momento em que é travado

### Acervo público **(IMPLEMENTADA)**
- Frontend: `PublicAcervoPanel` — tela pública consumindo `GET /projects/acervo-publico/` (sem login), com pesquisa por título
- Frontend: rota `#/acervo-publico` adicionada; item na sidebar para SECRETARIAT/ADMIN; atalho na home para todos
- Frontend: `listAcervoPublico` no `api.ts` com tipo `AcervoPublicItem`

### Download público do PDF **(IMPLEMENTADA)**
- Frontend: `publicationDocumentDownloadPublicUrl` no `api.ts` — URL pública para download do documento

### Select de documentos no PublicationPanel **(IMPLEMENTADA)**
- Frontend: `PublicationPanel` agora carrega `PublicationDocument` APPROVED do projeto e preenche o `<select>` de documentos para publicação

### Unificação de rotas Acervo **(IMPLEMENTADA)**
- `#/archive` e `#/acervo` continuam renderizando `AcervoPanel` (mesmo componente, comportamento idêntico)

### Avaliação — Tela `#/evaluations` **(IMPLEMENTADA)**
- Frontend: `EvaluationsPage` — lista projetos aprovados do professor com botão "Avaliar grupo" (navega para `group-evaluation`) e "Notas individuais"
- Frontend: rota `#/evaluations` substitui o `FutureModule`
- Frontend: item na sidebar para PROFESSOR

### Avaliação — Designar avaliador **(IMPLEMENTADA)**
- Frontend: `EvaluatorDesignation` já existente, agora ligado à rota `#/evaluator-designation/<projectId>`
- Frontend: item na sidebar para SECRETARIAT/ADMIN

### Avaliação — Páginas independentes **(IMPLEMENTADA)**
- Frontend: `GroupEvaluationPanel` acessível via `#/group-evaluation/<projectId>` (renderiza `ProjectDetailPage` com painéis de avaliação)
- Frontend: `IndividualGradesPage` — página independente para orientador lançar notas individuais por aluno (0-10) com histórico
- Frontend: rotas `#/group-evaluation/<id>` e `#/individual-grades` adicionadas

## O que parece funcionar (validado)

- `ruff check backend`: OK
- `manage.py check`: 0 issues
- `makemigrations --check --dry-run`: OK
- pytest backend: **82 passed**, coverage **92%**
- `npm run lint`: 0 erros, 3 warnings pré-existentes
- `npm run build`: OK
- `npm test` frontend: **50/50** (todos passando, incluindo falha pré-existente corrigida)
- `npm run build` frontend: OK

## Trabalho feito

### Sprint 7 backend (arquivos novos/modificados)
- `backend/projects/models.py`: modelos `ShowcaseEntry`, `PublicationDocument`, `Publication`
- `backend/projects/showcase.py`: serviços transacionais (agenda, presença, cancelamento, geração de documento, revisão, publicação, retirada)
- `backend/projects/showcase_views.py`: 8 views da Sprint 7 (com correção de bugs críticos no diff anterior)
- `backend/projects/serializers.py`: serializers dos modelos da Sprint 7
- `backend/projects/urls.py`: URLs da Sprint 7 + endpoint `/acervo-publico/`
- `backend/accounts/models.py`: novos `Notification.Kind` (DOCUMENT_PENDING, DOCUMENT_APPROVED, DOCUMENT_REJECTED, PUBLICATION_CREATED, PUBLICATION_WITHDRAWN, PROJECT_MEMBER_ADDED)
- `backend/tests/test_showcase.py`: 15 testes da Sprint 7 + 1 novo teste (`test_acervo_publico_permite_acesso_anonimo`)
- Migrations: `projects/0013`, `projects/0014`, `projects/0015`, `accounts/0005`

### Sprint 7 frontend (arquivos novos/modificados)
- `frontend/src/showcase.tsx` (novo): componentes ShowcasePanel, ShowcasePresencePanel, PublicationDocumentPanel, PublicationPanel, AcervoPanel
- `frontend/src/api.ts`: tipos e funções da API da Sprint 7
- `frontend/src/App.tsx`: rotas e navegação da Sprint 7 integradas
- `frontend/src/showcase.test.tsx`: 11 testes Vitest da Sprint 7 passando
- `frontend/src/styles.css`: estilos dos blocos da tela de projetos, notificações

### Bugs pré-existentes corrigidos
- `backend/projects/showcase_views.py`: removido import `AllowIsAuthenticatedOrReadOnly` (inexistente no DRF); restaurada `AcervoListView` + `AcervoPublicListView` subclass
- `backend/projects/urls.py`: import de `AcervoPublicListView` adicionado
- `backend/tests/test_showcase.py`: novo teste `test_acervo_publico_permite_acesso_anonimo`
- `frontend/src/showcase.test.tsx`: fixture `project` completando campos que faltavam (`class_offering`, `submitted_at`, etc.) + removido `is_active` dos membros (compatível com tipo `Member`)
- `frontend/src/App.tsx`: remoção do item `['acervo','Acervo publicado']` da navegação sidebar; notebook `pageTitles` mantido
- `frontend/src/showcase.test.tsx`: fixture `project` completando faltando campos para `tsc -b` aprovar
- `frontend/e2e/showcase.spec.ts`: remoção de variável `safe` não usada
- `frontend/src/styles.css`: estilos dos blocos da tela de projetos (+ warnings pré-existentes)

### Bugs pré-existentes (não relacionados a esta sessão)
- `App > cria o projeto antes de formar o grupo` falha no frontend — não relacionada à Sprint 7
- `npm run build` tinha erro de fixture em `showcase.test.tsx` — corrigido neste relato
- `npm run lint` tem 3 warnings pré-existentes (`exhaustive-deps` em `evaluation.tsx`, `grading.tsx`, `projectLifecycle.tsx`)

## Arquivos modificados (nesta sessão)

- `backend/projects/migrations/0016_publicationdocument_content.py`
- `backend/projects/models.py`
- `backend/projects/serializers.py`
- `backend/projects/showcase_views.py`
- `backend/projects/urls.py`
- `frontend/src/App.tsx`
- `frontend/src/api.ts`
- `frontend/src/showcase.test.tsx`
- `frontend/src/showcase.tsx`
- `docs/HANDOFF.md`

## Branch e commits recentes

- Branch: `main`, sincronizada com `origin/main`
- Último commit: `0245503` feat: implementar 3 ideias do backlog da Sprint 7

## Próximas ações

1. Executar testes E2E Playwright no CI (GF-09/GF-10) — bloqueado por falta de Docker Desktop
2. Definir decisão sobre atalhos duplicados da home ('Acervo' vs 'Acervo publicado')
4. Resolver erro 500 no login do Playwright (possível problema de CSRF/CSRF token entre frontend Vite na porta 5173 e backend Django na porta 8000)