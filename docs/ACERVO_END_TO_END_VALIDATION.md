# Validação do fluxo completo do acervo — 05/11/2026

## Resultado atual

Implementado e aplicado no Docker: documentos versionados/PDF server-side,
resultados ao orientador, revisão, aceite exclusivo do líder e confirmação final
da Secretaria. Guia: docs/ACERVO_WORKFLOW_GUIDE.md. Validação final: 165 backend
em lotes/cobertura 93,14%, 76 frontend, 4 E2E reais PostgreSQL e 6 de contrato.
Detalhes e limitações operacionais em docs/HANDOFF.md.

## Baseline e plano pré-implementação (histórico)

Implementação autorizada explicitamente no chat em 05/11/2026 ("Implemente").
Em execução: reutilizar documentos/publicação existentes com migração aditiva,
ReportLab 5.1.0, controle otimista por ID da versão e lock do projeto. A validação
histórica abaixo é o baseline pré-implementação; resultados atuais ficam no handoff.

Plano: backend/geração PDF/estados → frontend único para todos os atores → testes
de ambos os caminhos e atalhos negados → PostgreSQL descartável/concorrência →
backup antes de aplicar migrações no Docker → validação somente leitura do #2.

Fontes de implementação consultadas:
- https://docs.reportlab.com/reportlab/userguide/ch5_platypus/
- https://docs.djangoproject.com/en/5.2/topics/files/#the-file-object
- https://docs.djangoproject.com/en/5.2/topics/db/transactions/

Novo requisito recebido após a implementação de presença individual/nota do grupo.
Esta é análise do código e contrato funcional, NÃO implementação do novo fluxo
completo. As duas regras pendentes foram esclarecidas pelo usuário em 05/11/2026:
nota do grupo (inclusive para ausentes) e somente líder como representante.
As 150 validações backend/69 frontend/2 E2E anteriores cobrem o comportamento
anterior; não demonstram aderência ao requisito novo.

## Fluxo solicitado pelo usuário

1. Projeto segue criação, orientação, entrega/aprovação, encaminhamento,
   agendamento e designação do avaliador existentes.
2. Avaliador registra presença individual e uma nota 0–10 do grupo, com observações.
   A nota do grupo também se aplica aos integrantes ausentes: ausência na Mostra
   não significa ausência de contribuição no projeto. Não gerar zero nem nota
   individual diferente automaticamente por ausência.
3. Orientador recebe os resultados para consulta e registro, sem ter de lançar
   outra nota ou confirmar avaliação nesta plataforma. Sua avaliação posterior
   ocorre em outra plataforma; nenhuma integração externa foi solicitada.
4. Conclusão da avaliação libera somente o líder para elaborar formulário padronizado do
   acervo, vinculado ao projeto e aos integrantes, com título e conteúdo.
5. Servidor gera PDF e encaminha a versão ao orientador.
6. Orientador pode aprovar sem alteração, liberando para Secretaria, OU editar o
   texto, gerando nova versão que retorna ao aluno para validar.
7. Somente o líder valida a versão corrigida pelo orientador, liberando para Secretaria.
8. Secretaria confirma a publicação da versão final no acervo. Nada é público
   antes dessa confirmação. Aluno e professor não publicam diretamente.
9. Versões, conteúdo, PDF correspondente, autoria, data e decisões ficam visíveis
   aos envolvidos autorizados, sem sobrescrever versões anteriores.

## Evidências e divergências encontradas

| Etapa | Código atual | Divergência |
| --- | --- | --- |
| Presença/nota | ShowcaseMemberAttendance + GradeSubmission.direct_value | A separação atual está correta segundo esclarecimento do usuário: presença individual e nota do grupo. Manter nota comum inclusive para ausentes. IndividualGrade do orientador não participa desse fluxo. |
| Resultados ao orientador | grading.py conclude_evaluation notifica integrantes | Não há encaminhamento dedicado ao orientador reunindo presenças individuais, nota do grupo e observações. |
| Liberação do formulário | showcase.py generate_publication_document | Não exige conclusão da avaliação/presença individual; publicação exige PRESENTED mas não todas as condições do fluxo. |
| PDF | PublicationDocumentCreateSerializer exige upload pdf; showcase.py armazena arquivo | Não há geração server-side do formulário institucional. |
| Formulário | PublicationFormPanel exige documento prévio; título/integrantes só exibição | Não inicia o fluxo sozinho; salvar rascunho altera content sem regenerar PDF. Consentimento exibido nesse formulário não é enviado pelo PATCH. |
| Revisão | PublicationDocumentReviewView aceita APPROVED/REJECTED; UpdateView só autor | Orientador não edita texto; aluno não valida correção. |
| Histórico | versão nova por upload; PATCH altera content na mesma linha | Histórico parcial de uploads, não versões imutáveis de texto/PDF/revisão. |
| Publicação | publish_project exige require_student; PublicationPanel mostra botão ao aluno | Secretaria hoje retira publicação, mas não confirma publicação final. |
| Notificações | generate_publication_document notifica institutional_staff com DOCUMENT_APPROVED; helper usa PUBLICATION_CREATED genericamente | Destinatário/tipo não representam as etapas solicitadas; precisam estar ligados aos eventos corretos. |
| Permissões | listagem de documentos filtra projeto sem accessible_project; download verifica acesso | Corrigir autorização da listagem por objeto durante a implementação; não basta esconder botões. |

Fontes locais: backend/projects/{showcase.py,showcase_views.py,grading.py,models.py,
serializers.py}, frontend/src/{showcase.tsx,showcasePresence.tsx,api.ts}.

## Contrato proposto para implementação

- Etapas explícitas: AVALIACAO_PENDENTE → DOCUMENTO_DO_ALUNO → REVISAO_ORIENTADOR
  → (VALIDACAO_ALUNO se houver edição) → CONFIRMACAO_SECRETARIA → PUBLICADO.
- Preservar avaliação de grupo/rubricas históricas sem converter automaticamente
  nota do grupo em nota individual nem criar notas fictícias para o projeto #2.
- Rascunho editável separado de versão enviada imutável. Toda submissão/revisão
  cria snapshot de título, participantes, projeto e conteúdo + PDF daquela versão.
- Aprovação/aceite vinculados à versão exata; alterar conteúdo invalida aprovação
  anterior. Somente versão vigente elegível pode ser publicada pela Secretaria.
- Não incluir notas/presenças no PDF público; são registros acadêmicos privados.
- Consentimento e minimização de dados preservados; definir representantes não
  autoriza um integrante a consentir irrestritamente pelos demais.
- Reutilizar Project/ProjectGroup/ShowcaseEntry/PublicationDocument/Publication,
  acrescentando estados/versões/eventos necessários. Preferível a um segundo módulo
  de acervo, que duplicaria permissões, histórico e fontes de verdade.
- Compatibilidade não significa manter endpoint antigo capaz de pular Secretaria:
  adaptar clientes/rotas legados para negar publicação direta e testar a regressão.
- Mudanças no PDF: comparar ReportLab (menos dependências nativas; layout programado)
  e WeasyPrint (template HTML/CSS mais simples; runtime Docker maior). Recomendação
  preliminar ReportLab para formulário textual fixo; validar fonte Unicode/layout
  e documentação oficial antes da implementação. Nenhuma dependência instalada.

## Regras confirmadas pelo usuário

1. A nota é do grupo e se aplica também aos ausentes. Não cabe a esta plataforma
   atribuir nota individual justa pelo trabalho: o orientador decide isso depois
   em outra plataforma. Preservar presença como informação independente da nota.
2. Somente o líder representa o grupo no envio do formulário e no aceite da versão
   corrigida pelo orientador. Demais integrantes podem consultar o histórico quando
   autorizados, mas não enviar nem validar em nome do grupo.

O usuário não solicitou bloqueio aguardando ato do orientador ao receber resultados;
tratar recebimento como registro/notificação, sem gate de avaliação externa.
Não acrescentar rejeição/edição pela Secretaria sem requisito adicional.

## Aceite a validar depois de implementar

- API e frontend bloqueiam etapas antecipadas e atores indevidos.
- Avaliação concluída notifica orientador com nota do grupo/presenças/observações,
  libera o líder e preserva auditoria, sem exigir ação do orientador sobre a nota.
- Nota do grupo permanece única para todos os integrantes; presença parcial não
  a divide, zera ou exclui sua referência para o integrante ausente.
- API bloqueia envio e aceite por integrante que não seja o líder, mesmo que ele
  tenha acesso de leitura ao projeto/histórico.
- Caminho A: aluno gera PDF → orientador aprova → Secretaria publica.
- Caminho B: aluno gera v1 → orientador edita v2 → aluno valida v2 → Secretaria
  publica v2; v1 e v2 visíveis e íntegros, sem reutilizar aprovação da v1.
- Aluno não consegue publicar diretamente pela API antiga; versão desatualizada
  não pode ser aprovada/publicada; concorrência não duplica versões/publicações.
- PDF baixado corresponde exatamente à versão revisada/aceita/publicada.
- Dados privados/rascunhos não vazam no acervo; acesso por objeto em todas as rotas.
- Testes PostgreSQL descartável + E2E desktop/mobile para os dois caminhos,
  antes de executar qualquer ato acadêmico no banco de homologação.
