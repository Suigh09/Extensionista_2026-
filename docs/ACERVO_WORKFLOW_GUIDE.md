# Fluxo completo de publicação no acervo

## Onde acessar

Abrir **Publicação no acervo** na navegação, escolher o projeto e usar
**Publicar no Acervo**. Essa área está disponível para aluno, orientador,
avaliador e Administrador, com ações autorizadas pelo backend.
As rotas antigas de formulário/documento abrem a mesma interface.

## Pré-requisitos

### Repetição do teste com alocação automática — #6

**Projeto Homologação Alocação Automática**, preparado em 05/11/2026:
`fluxo.aluno3` é líder (HML5003), `fluxo.aluno4` é integrante (HML5004),
`fluxo.orientador` é orientador e `fluxo.secretaria` realiza a agenda.
Os novos alunos usam a mesma senha fluxo.* já entregue; nenhuma senha anterior
foi alterada. Proposta/entrega aprovadas e encaminhadas, ainda sem agenda/avaliador.

Agendar o #6 e usar **Alocar avaliadores automaticamente** no dia/sala escolhido.
Os candidatos compatíveis são `prof.orientador1`, `prof.orientador2` e
`prof.orientador3`, com competência sintética Homologação Automática.
O algoritmo verifica conflitos/carga no momento da alocação; não é sorteio.
Depois, seguir presença/nota e documento nas etapas abaixo. O #5 foi preservado.

### Projeto pronto para iniciar pela agenda — #5

Preparado em 05/11/2026: **Projeto Homologação Fluxo Acervo**. Proposta e entrega
aprovadas pelo orientador e encaminhadas à Secretaria; avaliador já designado.
Ainda não há agendamento, presença, nota ou publicação. O #2 foi preservado.

| Papel | Usuário |
| --- | --- |
| Aluno líder (HML5001) | `fluxo.aluno1` |
| Aluno integrante (HML5002) | `fluxo.aluno2` |
| Secretaria | `fluxo.secretaria` |
| Orientador | `fluxo.orientador` |
| Avaliador | `fluxo.avaliador` |

Os cinco acessos foram validados por HTTP. A senha não é registrada neste guia.
Começar em `http://127.0.0.1:5173/` como Secretaria, abrir **Agenda da Mostra** e
agendar o projeto **#5** entre os grupos não agendados. Depois seguir as etapas
abaixo, alternando os usuários. Somente o líder envia/aceita o documento do grupo.

### Condições para o documento publicável

- Projeto ativo e aprovado, sem cancelamento pendente.
- Entrega vigente aprovada e encaminhamento à Secretaria.
- Apresentação realizada na Mostra.
- Presença individual dos integrantes registrada e avaliação do grupo concluída.
- Líder ativo designado e integrante do grupo. Só o líder representa os alunos.

O quadro informa pendências reais; não cria notas, presenças nem aprovações para
permitir avançar. Ausência parcial não reduz nem zera a nota: a nota é do grupo,
inclusive para os ausentes. Ausência total da apresentação continua não elegível
ao acervo, conforme regra anterior da Mostra.

## 1. Avaliador

Em **Registro de presença**, marcar os integrantes que compareceram e confirmar.
Preencher a nota do grupo (0 a 10) e observações. Salvar conclui a avaliação.
Se a presença geral foi registrada pelo fluxo anterior, complementar sem alterar
o resultado agregado. Reenvios idênticos não duplicam registros.

## 2. Orientador recebe os resultados

O orientador recebe notificação com link para o projeto no fluxo do acervo.
O painel mostra presença individual, nota comum e observações, preservadas no
banco. Não é exigida confirmação/nota individual do orientador aqui: sua avaliação
posterior ocorre em outra plataforma, sem integração externa automática.

## 3. Líder prepara o documento

O líder acessa **Publicação no acervo**, confere projeto/integrantes/curso/ano e
preenche título, resumo e descrição. Participantes e projeto vêm dos vínculos
reais, não de nomes livres. Confirmar o consentimento e clicar
**Gerar PDF e enviar ao orientador**.

- O servidor cria uma versão e seu PDF a partir do mesmo texto e snapshot.
- O PDF contém os dados do documento, não notas, presenças, RA ou credenciais.
- O formulário preserva os campos se o envio falhar.
- Alterações ainda não enviadas permanecem somente no formulário; não há gravação
  automática de rascunho no servidor. A proteção de navegação avisa sobre mudanças.
- Cada envio é uma nova versão. Documentos enviados não são sobrescritos.

## 4. Orientador revisa

Na versão aguardando revisão, conferir texto e PDF e escolher:

- **Aprovar sem alterações**: a versão vai para confirmação da Secretaria.
- **Revisar texto**: editar título/resumo/descrição e clicar **Enviar correção ao
  líder**. O sistema gera nova versão/PDF e notifica o líder.

O orientador não publica diretamente. Uma alteração não pode reutilizar o aceite
da versão anterior.

## 5. Líder valida a correção

Na etapa **Aguardando validação do líder**, ler a versão revisada, consultar o
histórico e baixar o PDF. **Validar correção e encaminhar à Secretaria** aceita
exatamente essa versão. Outro integrante não pode validar no lugar do líder.

## 6. Administrador confirma a publicação

Na etapa **Aguardando confirmação do Administrador**, conferir a versão aprovada e
clicar **Confirmar publicação no acervo**, confirmando a ação.

Só esse ato cria a publicação visível no acervo. Tentativas por aluno/orientador,
versão antiga ou etapa antecipada são bloqueadas pela API, inclusive na URL antiga.

## Histórico e retirada

No **Acervo** autenticado, clicar no título do projeto ou em **Ler PDF** abre
em nova aba o PDF exato da versão publicada. Não abre rascunhos nem outras
versões. Publicação retirada deixa de permitir leitura por esse link. A consulta
pública sem sessão exibe nomes dos integrantes e resumo da versão publicada,
conforme autorização posterior, mas continua sem acesso ao PDF e sem RA/contatos.

O histórico mostra versões, texto, PDF correspondente, snapshot dos integrantes,
autor, data, revisão/aceite e hash SHA-256 do PDF. Aprovação/aceite e responsável
pela confirmação são registrados; publicações anteriores não recebem autoria
fictícia na migração.

O Administrador pode usar **Retirar publicação**, informando o motivo.
A retirada preserva documentos e histórico e remove o item do acervo consultável.
Não há republicação do mesmo projeto, conforme regra anterior.

## Projeto #2 no ambiente de homologação

Fotografia somente leitura em 05/11/2026 após a atualização:

- Avaliador: `avaliador.e2e.acervo`.
- Integrantes: `RA4001` e `RA4002`; orientador: `prof.orientador1`.
- Líder: `RA4001`, definido após autorização explícita do usuário para escolher um
  integrante; vínculo/permissão do backend validados.
- O grupo está marcado como apresentado pelo fluxo geral anterior, mas não possui
  presença individual nem avaliação concluída.
- Ainda não há entrega vigente aprovada. Realizar entrega/aprovação pelos responsáveis.
- A liderança foi a única correção administrativa autorizada nesse projeto;
  nenhuma nota, presença individual, entrega ou publicação foi criada pelo agente
  para simular sucesso.
