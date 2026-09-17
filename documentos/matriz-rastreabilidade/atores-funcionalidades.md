# Matriz de Rastreabilidade - Atores x Funcionalidades

Legenda: `E` executa; `C` consulta; `D` decide/aprova; `-` sem permissão; `PLN` planejado.
Todas as permissões dependem de autenticação quando aplicável e de autorização por objeto no backend.

| ID | Funcionalidade | Aluno | Professor | Secretaria | Admin | Avaliador contextual | Público | Estado | Regras/observações |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| UC-001 | Autenticar e encerrar sessão | E | E | E | E | E | - | IMP | bloqueio progressivo; sessão e CSRF |
| UC-002 | Consultar o próprio perfil | C | C | C | C | C | - | IMP | dados minimizados por papel |
| UC-003 | Criar e listar usuários | - | - | - | E | - | - | IMP | senha temporária; menor privilégio |
| UC-004 | Gerenciar cursos, disciplinas e turmas | - | - | - | E | - | - | IMP | operações auditadas |
| UC-005 | Criar, consultar e encerrar a própria sala | - | E | C | C | - | - | IMP | professor responsável; histórico preservado |
| UC-006 | Incluir aluno ou solicitar transferência | - | E | C | C | - | - | IMP | RN-003 e RN-004 |
| UC-007 | Aprovar ou recusar transferência | - | - | D | D | - | - | IMP | revalidação transacional |
| UC-008 | Gerenciar disciplinas e competências próprias | - | E | - | - | - | - | IMP | texto livre normalizado |
| UC-009 | Criar, consultar e editar projeto próprio | E | C | - | C | - | - | IMP | exige sala ativa; autorização por objeto |
| UC-010 | Convidar aluno e aceitar/recusar/cancelar convite | E | C | - | C | - | - | IMP | RN-001; elegibilidade revalidada |
| UC-011 | Submeter proposta ao orientador | E | C | - | C | - | - | IMP | grupo formado; transição controlada |
| UC-012 | Aprovar proposta ou solicitar ajustes | C | D | - | C | - | - | IMP | somente professor contextual |
| UC-013 | Publicar follow-up e anexos | E | E | - | C | - | - | IMP | RN-005; upload privado e validado |
| UC-014 | Configurar e aplicar marcos | C | E | - | C | - | - | IMP | RN-006; somente projetos elegíveis |
| UC-015 | Consultar timeline do projeto | C | C | - | C | C | - | IMP | participação ou vínculo contextual |
| UC-016 | Publicar oportunidade, candidatar e decidir parceria | E | C | - | C | - | - | IMP | RN-001 e RN-002; operação transacional |
| UC-017 | Encaminhar projeto à Mostra | C | E | C | C | - | - | PLN | aprovação do orientador |
| UC-018 | Definir data, local e avaliador | C | C | E | E | C | - | PLN | secretaria não rejeita encaminhamento aprovado |
| UC-019 | Avaliar grupo na Mostra | C | C | C | C | E | - | PLN | nota 0-10; orientador não avalia própria sala |
| UC-020 | Registrar notas individuais | C | E | C | C | - | - | PLN | trilha de alteração obrigatória |
| UC-021 | Aprovar documento publicável | C | D | C | C | - | - | PLN | documento gerado pelo aluno |
| UC-022 | Publicar ou retirar item do acervo | C | C | E | E | - | - | PLN | RN-008; retirada preserva histórico |
| UC-023 | Consultar acervo publicado | C | C | C | C | C | C | PLN | visibilidade pública ainda pendente de decisão |

## Controles transversais

- Ocultar um botão não concede segurança: todo caso de uso mutável exige autorização no backend.
- Professor acessa somente objetos para os quais possui vínculo contextual.
- Secretaria e administrador não recebem acesso irrestrito a dados pessoais além do necessário.
- Downloads e anexos exigem autorização por objeto; nomes armazenados são aleatórios e seguros.
- Ações acadêmicas relevantes devem produzir evento de auditoria sem segredos ou dados excessivos.
