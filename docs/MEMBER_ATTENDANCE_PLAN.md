# Presença individual e avaliação integrada — 05/11/2026

Pedido autorizado no chat: checkboxes por integrante e abrir nota 0–10/observações
após confirmar presença, sem exigir rubrica cadastrada.

## Contrato

- Presença identifica a PK de GroupMember, exige todos os integrantes ativos,
  sem duplicatas ou membros externos. Algum presente = PRESENTED; nenhum = ABSENT.
- Confirmação é imutável; reenvio idêntico é idempotente, divergente é rejeitado.
- Nota é do grupo, não do integrante. Reutilizar GradeSubmission com rubric opcional
  e direct_value; rubricas existentes permanecem intactas. Não usar IndividualGrade,
  reservado ao orientador. Nota direta concluída bloqueia outra avaliação, e vice-versa.
- Presença e avaliação são duas etapas persistentes; avaliação pendente pode ser
  retomada após recarregar. Nenhuma restrição nova por horário ou para publicação.
- Nota direta somente para avaliador designado, grupo ativo/projeto mutável,
  presença individual registrada e ao menos um presente; valores finitos 0–10.
- Presença geral legada pode ser complementada antes da conclusão da avaliação,
  sem alterar seu resultado agregado (PRESENTED exige ao menos um presente;
  ABSENT exige todos ausentes). Nunca presumir presenças individuais anteriores.
  Não executar atos acadêmicos no projeto #2 durante testes.

## Execução

1. Reparar implementação parcial; modelos/serviços/serializers/views e migração.
2. Frontend com checkboxes e segunda etapa acessível; testes de regressão.
3. Testes completos sem excluir arquivos; backup PostgreSQL antes de reconstruir
   backend e aplicar migração. Validar saúde, schema e dados preservados.
4. Atualizar handoff com resultados reais e limitações.

## Fontes

- Django 5.2: https://docs.djangoproject.com/en/5.2/topics/db/transactions/
- React 19: https://react.dev/reference/react-dom/components/input

Atomicidade e locks protegem confirmação/avaliação; estado controlado dos
checkboxes segue o padrão já adotado no frontend.
