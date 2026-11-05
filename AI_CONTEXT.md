# AI_CONTEXT.md — Plataforma Extensionista

## Objetivo

Plataforma web para controle e acompanhamento de projetos de extensão, avaliação/premiação e acervo/publicação. Estruturada como um desk manager para otimizar a gestão acadêmica de projetos extensionistas da instituição.

## Problema

A gestão acadêmica tradicional é complexa e exige esforço manual. A plataforma busca maior precisão nas avaliações docentes e transparência contínua para os discentes, com rastreabilidade de requisitos (UC-xxx, RF-xxx, RN-xxx) e estados IMP/PLN.

## Usuários / Atores

- Aluno
- Professor (orientador, avaliador contextual, responsável por sala)
- Secretaria
- Administrador
- Público (acervo, com restrições de visibilidade no MVP)

## Stack

- Backend: Django (Python 3.11), PostgreSQL 17 via Docker Compose. Apps: `accounts`, `academic`, `core`, `projects`.
- Frontend: Vite + React + TypeScript.
- Lint/qualidade: ruff (backend), ESLint (frontend).
- Testes: pytest (backend, cobertura mínima 85%), Vitest + Playwright (frontend/E2E).
- CI: GitHub Actions (backend + frontend).

## Integrações

- Banco de dados PostgreSQL 17 (Docker).
- Armazenamento de arquivos privados (uploads validados por tipo/tamanho).
- Documentos publicáveis em PDF e notificações internas da Sprint 7 implementados.

## Persistência

- Modelos de domínio: usuário, perfil de aluno/professor, curso, disciplina, turma, matrícula, sala acadêmica, projeto, grupo, membro do grupo, convite, follow-up, anexo, marco, oportunidade de parceria, candidatura, evento de auditoria.
- Modelos da Sprint 7 implementados: `ShowcaseEntry`, `PublicationDocument`, `Publication`.
- Fluxo completo do acervo (05/11/2026): presença por integrante e nota do grupo,
  inclusive para ausentes; orientador recebe resultados, sem lançar avaliação
  individual nesta etapa. Líder envia formulário gerador de PDF server-side
  (ReportLab); orientador aprova ou gera versão corrigida para aceite do líder;
  Secretaria/Admin confirma publicação. Versões/texto/PDF/snapshot/hash e decisões
  preservados. Serviço único em publication_workflow.py e interface acervoWorkflow.tsx;
  aliases de rotas anteriores, sem publicação direta pelo aluno. Guia em
  docs/ACERVO_WORKFLOW_GUIDE.md; testes integrados usam PostgreSQL descartável.
- Agenda visual unificada (05/11/2026): locais físicos `ShowcaseBuilding`/`ShowcaseRoom` e dias `ShowcaseDay` gerenciados por Secretaria/Admin, agendamentos de 30 min no próprio `ShowcaseEntry`. O usuário esclareceu que Admin também inclui Secretaria nesses cadastros, sem conceder superusuário Django. `Project.number` fornece identificação curta crescente sem trocar UUID. API de planejamento só staff; presença/publicação continuam na mesma entrada. Protótipo `ShowcaseSession` preservado sem gravação/uso na interface.
- Chaves críticas usam `PROTECT` para preservar histórico acadêmico.
- Registros acadêmicos e históricos não expiram automaticamente.
- CPF não é persistido integralmente (apenas hash e últimos 4 dígitos).

## Execução

- Backend: `cd backend && python manage.py check && ruff check backend && pytest --cov`
- Frontend: `cd frontend && npm ci && npm run lint && npm test && npm run build`
- Docker: `docker compose up --build`
- Scripts locais: `Iniciar Plataforma.bat`, `Parar Plataforma.bat`, `scripts/start_platform.ps1`, `scripts/stop_platform.ps1`
- Desde 05/11/2026, os atalhos usam exclusivamente backend/PostgreSQL Docker e interface Vite local em `http://127.0.0.1:5173/`. `scripts/platform_common.ps1` fixa o projeto/arquivos Compose e verifica conexão PostgreSQL real; falha do Docker não aciona SQLite. SQLite anterior preservado e reservado a uso explicitamente isolado/testes, sem sincronização de dados ou senhas.

## Prioridades

1. Manter compatibilidade com o código existente (UC-001 a UC-016 já implementadas).
2. Manter a Sprint 7 conforme a especificação aceita (`docs/sprints/SPRINT_07_SPEC.md`).
3. Cobertura mínima de testes: 85% (backend).
4. Autorização no backend e por objeto; negação por padrão.

## Restrições conhecidas

- Não implementar funcionalidades fora do escopo da tarefa solicitada.
- Não expor CPF integral, senhas, tokens ou segredos em diagramas/artefatos.
- Não commitar credenciais, chaves ou dados pessoais sensíveis.
- Ocultar botão não concede segurança: todo caso de uso mutável exige autorização no backend.
- O módulo geral de eventos permanece fora do escopo; somente o encaminhamento necessário à Mostra Extensionista é contemplado.
- O acervo anônimo expõe metadados; o download do PDF exige autenticação.
- Login usa `authenticate()` antes de criar sessão, exige CSRF e mantém bloqueio por identificador/endereço.
- Pontos pendentes de decisão/documentação: marcado como `desconhecido` ou `pendente de confirmação` quando não verificável nos artefatos.

## Rastreabilidade (UCs)

- UC-001 a UC-016: IMP (implementado).
- UC-017 a UC-023: implementados; resultados de validação e pendências em `docs/HANDOFF.md`.
