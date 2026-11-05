# Uso da agenda unificada da Mostra

Endereço de homologação: http://127.0.0.1:5173/#/showcase

## Avaliador — presença individual e nota

1. Entrar como avaliador designado e abrir **Registro de presença**.
2. Marcar somente os integrantes presentes e clicar **Confirmar presença**.
   Se todos estiverem desmarcados, será solicitada confirmação de ausência total.
3. Havendo presentes, abre **Avaliação do grupo**: nota 0–10 e observações opcionais.
4. **Salvar avaliação** conclui e bloqueia novas notas; **Avaliar depois** permite
   retomar nessa tela mesmo após recarregar. A nota é do grupo, não do aluno.
5. Presença geral antiga pode ser complementada sem mudar seu resultado e antes
   da conclusão. Um grupo já apresentado precisa de ao menos um integrante presente.

No projeto #2, usar avaliador.e2e.acervo e integrantes RA4001/RA4002.
Documento/aprovação/publicação continuam no fluxo existente; orientador é
prof.orientador1. Não confundir com os usuários do projeto #1.

## Admin e Secretaria — locais físicos

1. Abrir **Agenda da Mostra → Cadastrar prédios e salas**.
2. **Adicionar prédio** gera A, B, C… Z, AA… automaticamente.
3. **Adicionar sala** gera Sala 1, Sala 2… dentro do prédio escolhido.
4. Os formulários de renomeação permitem nomes como Anfiteatro ou Auditório,
   preservando os números/códigos internos. Admin e Secretaria podem cadastrar e
   renomear locais; alunos e professores não podem, inclusive pela API.

Salas físicas são diferentes das salas acadêmicas que reúnem alunos/orientadores.

## Secretaria/Admin — datas e agendamento

1. Em **Cadastrar datas da Mostra**, informar dia, início e fim da programação.
   A janela vale para as salas; início/fim devem usar 00 ou 30 minutos, no mesmo dia.
2. No topo, escolher uma data e um local já cadastrados.
3. A coluna esquerda mostra grupos ativos, aprovados e encaminhados à Secretaria.
4. Arrastar um grupo para o horário da coluna direita; a duração inicial é 30 min.
5. Arrastar a borda inferior do cartão para aumentar/diminuir em passos de 30 min.
   Também há botões −30/+30 min e formulário para agendar/reagendar sem arrastar.
6. Arrastar um cartão já agendado move seu horário preservando a duração. Para
   trocar de data/sala sem arrastar, selecionar o destino e usar o formulário.
7. **Retirar** cancela o horário, preservando a entrada/histórico; o grupo elegível
   volta à coluna esquerda. É possível reagendar reutilizando a mesma entrada.
8. **Múltiplos grupos na mesma sala/horário:** a sala pode receber mais de um grupo
   no mesmo horário; eles são exibidos empilhados verticalmente na grade.

O backend permite múltiplos grupos na mesma sala e mesmo horário (apenas o avaliador
tem restrição de conflito). Horários fora da janela, duração inválida, projetos não
encaminhados e alterações concorrentes sobre versão desatualizada continuam sendo
rejeitados. Presença já registrada como Apresentado/Ausente bloqueia reagendamento.

## Busca e números de projeto

- Pesquisar pelo nome do projeto, nome/usuário de integrante ou número, com ou sem #.
- Resultados incluem horários em outras datas/salas e agendamentos históricos.
- **Localizar na agenda** seleciona o dia/local; **Abrir projeto** abre o projeto.
- A busca não esconde horários ocupados na grade, evitando falsa disponibilidade.
- Números visíveis são sequenciais; UUIDs continuam nas relações/URLs. Não usar
  o número curto como autorização de acesso.

## Notificações

- Encaminhamentos, entregas e avaliações abrem o projeto correspondente.
- Documentos abrem a área de documentos do projeto; publicações abrem sua publicação.
- Convites abrem Projetos, onde o convite pode ser aceito antes de obter acesso.
- Avisos de sala/transferência abrem a área apropriada ao papel do destinatário.
- A leitura é marcada sem bloquear a navegação se essa marcação falhar. Um aviso
  sem vínculo recuperável informa que não possui destino, em vez de adivinhar.

## Dados de homologação e limites desta entrega

O projeto existente recebeu número **#1**. Não foram cadastrados prédios, salas,
datas ou apresentações fictícias no banco da plataforma. Na conferência final,
ele continuava aguardando aprovação e não havia registro real de encaminhamento,
apesar da notificação antiga;
esse vínculo da notificação foi reparado, mas o estágio não foi fabricado. Para
aparecer como disponível, a entrega deve ser aprovada e o orientador precisa
encaminhar o projeto à Secretaria pelo fluxo existente.

Após autorização explícita, foi criada a conta sintética `admin.teste` no PostgreSQL,
com a credencial de homologação existente, sem privilégios de superusuário Django.
O usuário também esclareceu que, para estes cadastros, Admin inclui Secretaria:
`secretaria.teste` pode cadastrar prédios e salas diretamente, sem trocar de conta.

A janela que limita o lançamento de notas ao horário da apresentação continua
adiada por decisão do usuário; esta entrega não a implementa.
