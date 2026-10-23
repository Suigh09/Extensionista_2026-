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

## O que parece funcionar

- `ruff check backend`: OK
- `python manage.py check`: OK
- `makemigrations --check --dry-run`: OK (sem mudanças pendentes)
- pytest backend: 82 passed, 1 falha pré-existente (`App > cria o projeto antes de formar o grupo`)
- Coverage backend: 92% (mínimo 85%)
- `npm run lint` frontend: OK (0 erros, 3 warnings pré-existentes)
- `npm run build` frontend: OK (após correção do fixture `showcase.test.tsx`)
- `npm test` frontend: 49/50 tests passing (1 falha pré-existente `App > cria o projeto antes de formar o grupo`)

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

## O que parece funcionar (validado)

- `ruff check backend`: OK
- `manage.py check`: 0 issues
- `makemigrations --check --dry-run`: OK
- pytest backend: **82 passed**, coverage **92%**
- `npm run lint`: 0 erros, 3 warnings pré-existentes
- `npm run build`: OK
- `npm test` frontend: **49/50** (1 falha pré-existente confirmada no HEAD limpo)
- `npm run build` frontend: OK

## Trabalho feito

### Sprint 7 backend (arquivos novos/modificados)
- `backend/projects/models.py`: modelos `ShowcaseEntry`, `PublicationDocument`, `Publication`
- `backend/projects/showcase.py`: serviços transacionais (agenda, presença, cancelamento, geração de documento, revisão, publicação, retirada)
- `backend/projects/showcase_views.py`: 8 views da Sprint 7 (com correção de bugs críticos no diff anterior)
- `backend/projects/serializers.py`: serializers dos modelos da Sprint 7
- `backend/projects/urls.py`: URLs da Sprint 7 + endpoint `/acervo-publico/`
- `backend/accounts/models.py`: novos `Notification.Kind` (DOCUMENT_PENDING, DOCUMENT_APPROVED, DOCUMENT_REJECTED, PUBLICATION_CREATED, PUBLICATION_WITHDRAWN)
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

## Arquivos modificados (não commitados antes do commit)

- `backend/projects/showcase_views.py`
- `backend/projects/urls.py`
- `backend/tests/test_showcase.py`
- `frontend/src/App.tsx`
- `frontend/src/showcase.tsx`
- `frontend/src/showcase.test.tsx`
- `frontend/src/styles.css`
- `frontend/src/notifications.tsx`
- `frontend/e2e/showcase.spec.ts`
- `backend/accounts/models.py`
- `backend/accounts/migrations/0006_alter_notification_kind.py`
- `backend/projects/lifecycle.py`
- `backend/projects/serializers.py`
- `backend/tests/test_lifecycle.py`
- `frontend/src/api.ts`
- `frontend/src/projectLifecycle.tsx`
- `TASKS.md`
- `DESAFIOS.md`
- `docs/HANDOFF.md`

## Branch e commits recentes

- Branch: `main`, **7 commits à frente de `origin/main`** (não empurrados)
- Último commit: `8adf4f7` feat: UI da tela do aluno em blocos e acesso público ao acervo

## Próximas ações

1. **Commit** das mudanças já realizado (`feat: UI da tela do aluno em blocos e acesso público ao acervo`)
2. Validar visualmente no navegador (blocos da tela de projetos)
3. **Ideia 1 (notificações deletáveis)**: implementada nesta sessão (ver acima)
4. **Ideia 2 (professor criar projeto + puxar alunos)**: implementada nesta sessão (ver acima)
5. Executar testes E2E Playwright no CI (GF-09/GF-10)
6. Definir decisão sobre atalhos duplicados da home ('Acervo' vs 'Acervo publicado')