# Avaliadores na agenda — 05/11/2026

Pedido: fechar o fluxo com escolha manual ou alocação automática, padrão de
**um avaliador por grupo**. Interpretação comunicada no chat; não se trata de
escolher um único professor obrigatório para toda a Mostra.

## Implementação

- Reutilizar `ProjectGroup.evaluator` e histórico `EvaluatorAssignment` (sem
  segundo cadastro de designações nem mudança de cardinalidade).
- Secretaria/Admin escolhem manualmente no cartão da agenda ou alocam
  automaticamente os grupos sem avaliador do dia/sala selecionados.
- Automático não substitui designações existentes. Usa aderência às competências,
  menor carga e desempate determinístico. Sem candidato compatível e disponível,
  registra pendência na resposta; a Secretaria pode decidir manualmente com a
  justificativa já exigida pelo fluxo existente.
- Alternativa de sortear qualquer docente completaria mais alocações, mas perderia
  a aderência e a explicação. Recomenda-se pendência explícita, não preenchimento
  arbitrário. Sem solver global: escolha gulosa é simples/auditável, sem promessa
  de solução ótima para toda a grade.
- Bloquear próprio orientador, inativos, sobreposição de apresentações para o
  avaliador e trocas após presença/notas. Reagendamento/resize também revalidam
  disponibilidade do avaliador para não criar conflito por outro caminho.
- Locks por grupo/projeto e professor na mesma ordem; automático processa cada
  designação em transação própria (sem manter locks entre grupos), revalidando
  candidatos e preservando escolhas feitas concorrentemente.
- Horários adjacentes permitidos, sem tempo de deslocamento arbitrário. Agenda
  legada sem fim usa 30 min para verificação conservadora. Janela de lançamento
  de notas por horário permanece adiada.

## Validação prevista

Permissões, um avaliador, automático idempotente, exclusão do orientador, candidato
sem aderência, conflito entre salas, movimentação/resize, histórico/notificações,
concorrência em PostgreSQL isolado e regressões frontend/navegador.

## Fontes

- https://docs.djangoproject.com/en/5.2/ref/models/querysets/#select-for-update
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- https://react.dev/reference/react/useEffect

Estado: implementado e validado em 05/11/2026.
