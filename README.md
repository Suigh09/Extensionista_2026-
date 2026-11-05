# Extensionista 2026

Trabalho extensionista 2026 segundo semestre — Plataforma Extensionista, para controle e
acompanhamento de projetos de extensão, avaliação/premição e acervo/publicação.

# Apresentação do Projeto

Visão Geral: O presente documento consolida os artefatos de análise, modelagem e
especificação funcional da Plataforma Extensionista.

Equipe Desenvolvedora: Gustavo (DEV), Mauricio (NEGÓCIO), Bruno (DEV), Carlos (DEV) e Enzo (NEGÓCIO).

Justificativa e Objetivo: A Plataforma Extensionista é uma aplicação web baseada no
conceito de desk manager estruturada para otimizar o acompanhamento, a avaliação e a
organização do acervo de projetos extensionistas da instituição. O sistema mitiga a
complexidade e o esforço manual associados à gestão acadêmica tradicional, proporcionando
maior precisão nas avaliações docentes e transparência contínua para os discentes.

## Estrutura do repositório

```
.
├── backend/            # Django (apps: accounts, academic, core, projects)
├── frontend/           # Vite + React + TypeScript
├── docs/               # Especificações de sprint (ex: SPRINT_07_SPEC.md)
├── documentos/         # Análise e modelagem rastreável da Entrega 1
│   ├── caso-de-uso/             # Diagrama de casos de uso (atores e associações)
│   ├── atividades/              # Diagramas de atividade dos principais fluxos
│   ├── entidades/                # Diagrama de classes de domínio
│   ├── estados/                  # Diagramas de estados (ciclos de vida)
│   ├── matriz-rastreabilidade/  # Atores x funcionalidades (md e csv)
│   ├── especificacoes/           # Escopo, fontes e regras de negócio
│   └── repositorio-github/       # Configuração e checklist deste repositório
├── scripts/            # Scripts de iniciar/parar plataforma
├── compose.yaml        # Docker Compose (db, backend, frontend)
├── .github/workflows/ci.yml    # CI (backend + frontend)
├── AGENTS.md           # Regras de trabalho para agentes
├── AI_CONTEXT.md       # Contexto do projeto (objetivo, stack, execução, restrições)
├── TASKS.md            # Tarefas pendentes e em andamento
├── LICENSE                     # MIT
└── README.md
```

Veja [`documentos/README.md`](documentos/README.md) para o índice completo da documentação,
incluindo as convenções de rastreabilidade (`UC-xxx`, `RF-xxx`, `RN-xxx`, `IMP`/`PLN`).

## Status

O código-fonte inclui a Sprint 7 (Mostra, publicação e acervo — UC-017 a UC-023),
com aceite registrado em `TASKS.md`. GF-09/GF-10 foram validados localmente;
isso não representa aprovação de toda a suíte ou do CI. Veja os resultados e
pendências atuais em `docs/HANDOFF.md`.

## Como contribuir

1. Crie uma branch a partir de `main` para sua alteração.
2. Abra um Pull Request descrevendo o que foi feito.
3. Mantenha a pasta `/documentos` atualizada conforme o sistema evoluir — os diagramas usam
   Mermaid e são renderizados diretamente pelo GitHub.
4. Antes de implementar funcionalidades da Sprint 7, confirme o aceite da especificação
   (`docs/sprints/SPRINT_07_SPEC.md`).

## Execução e testes

- Publicação completa: [guia do fluxo do acervo](docs/ACERVO_WORKFLOW_GUIDE.md).
  Líder gera PDF pelo formulário; orientador aprova ou corrige com aceite do líder;
  Secretaria confirma a versão final. Resultados da Mostra chegam ao orientador.
- Teste integrado isolado (Vite ativo, Docker disponível):
  `.venv/Scripts/python.exe scripts/validate_acervo_live.py`. Usa PostgreSQL UUID
  descartável/API na porta 8002; não realiza atos no banco normal.
- Runner backend local: `.venv/Scripts/python.exe scripts/validate_backend.py`;
  carrega ambiente e executa pytest em SQLite isolado, incluindo todos os testes.

- Agenda da Mostra: [guia de locais, datas, quadro visual e busca](docs/SHOWCASE_PLANNING_GUIDE.md). Secretaria/Admin cadastram locais, dias e agendam grupos encaminhados. Notificações abrem o destino correspondente e projetos possuem número curto visível, preservando UUIDs internos.
- **Uso normal no Windows:** abrir `Iniciar Plataforma.bat`, com Docker Desktop em execução e Node.js/npm instalados. Acesso único: `http://127.0.0.1:5173/`.
- Backend + PostgreSQL rodam no Docker; a interface Vite roda localmente e encaminha `/api` ao backend Docker. Não há fallback para SQLite. O inicializador reconstrói a imagem backend com o código atual e aguarda os serviços ficarem saudáveis.
- `Parar Plataforma.bat` encerra a interface identificada e para os serviços Compose, preservando volumes e uploads. Os atalhos `backend/run_server.bat` e `frontend/start_dev.bat` seguem o mesmo backend Docker.
- `backend/test.sqlite3` foi preservado, mas não participa do uso normal. Scripts E2E explicitamente isolados ainda podem usar SQLite; não executá-los nas mesmas portas enquanto a plataforma estiver aberta. As credenciais e os dados dos dois bancos não são sincronizados.
- Regressões dos inicializadores: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/tests/platform_launchers.ps1` (mocks, sem alterar bancos).
- Backend: `cd backend && python manage.py check && ruff check backend && pytest --cov` (coverage mínima 85%).
- Frontend: `cd frontend && npm ci && npm run lint && npm test && npm run build && npm run test:e2e`.
- Docker: `docker compose up --build`.

## Licença

Este repositório é disponibilizado sob a [Licença MIT](LICENSE).
