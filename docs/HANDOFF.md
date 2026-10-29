# Handoff — Plataforma Extensionista

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
