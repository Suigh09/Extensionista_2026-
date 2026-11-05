# Agenda visual da Mostra — 05/11/2026

Pedido autorizado no chat: corrigir navegação de notificações e duplicatas de
Agenda/Acervo; unificar agendamento; locais e datas cadastrados por Admin/Secretaria
(esclarecimento posterior explícito do usuário); drag-and-drop/redimensionamento em passos de 30 minutos;
busca por projeto, integrante e número curto crescente.

## Decisões de implementação

- Manter UUIDs nas relações/URLs e acrescentar número sequencial visível ao projeto.
  Contadores persistentes com bloqueio transacional, nunca `count()+1`.
- Local físico separado de sala acadêmica: prédio com código A..Z, AA.. e nome
  editável; salas com numeração por prédio e nome editável. Sem exclusão de histórico.
- Dias da Mostra com janela de início/fim configurável, sempre em meias horas,
  horário institucional America/Sao_Paulo. A janela do dia vale para as salas.
- Fonte única dos agendamentos: `ShowcaseEntry`, preservando presença/publicação
  e dados legados. `ShowcaseSession` não deve continuar aceitando gravações soltas.
- Backend valida papel, encaminhamento/aprovação/atividade, limites, duração e
  colisões na sala; bloqueio do grupo/dia serializa gravações concorrentes.
- Uma agenda na navegação; rota antiga vira alias. Sem biblioteca adicional:
  drag-and-drop nativo e Pointer Events para redimensionar, com formulário/botões
  como alternativa para teclado/mobile. Salvar somente ao soltar; erro não deve
  deixar o cartão em posição não persistida.
- Busca na agenda inclui grupos agendados em outras datas/salas e permite localizar
  o agendamento. Não expor pesquisa de integrantes em endpoint público do acervo.
- Janela de avaliação por horário continua fora do escopo, adiada pelo usuário.

## Etapas

1. Corrigir notificações e renderizações duplicadas, com regressões.
2. Modelos, migrações preservadoras, permissões e API transacional.
3. Cadastros e quadro visual unificado com pesquisa e IDs visíveis.
4. Testes backend/frontend/E2E e validação PostgreSQL Docker após backup.

## Fontes oficiais

- Django 5.2: https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
- Pointer Events: https://developer.mozilla.org/en-US/docs/Web/API/Pointer_events
- React 19: https://react.dev/reference/react/useRef

## Estado

Implementado e integrado ao PostgreSQL Docker. Testes backend, frontend e navegador
estão descritos em `docs/HANDOFF.md`; concorrência também exercitada em PostgreSQL
descartável. Guia de uso: `docs/SHOWCASE_PLANNING_GUIDE.md`.

Notificações também passaram a receber `target_url` da API por tipo/destinatário.
Migração 0023 repara links antigos de encaminhamento somente por título exato e
projeto único (incluindo colisões por truncamento); não inventa encaminhamentos.
