# Escopo, fontes e limites da modelagem

## Objetivo

Modelar a Plataforma Extensionista institucional para controle e acompanhamento de projetos,
avaliação/premiação e acervo/publicação. Não existe módulo geral de eventos; o produto contempla
somente o encaminhamento necessário à Mostra Extensionista.

## Fontes de verdade utilizadas

1. Código do backend e frontend no checkout atual.
2. `docs/ARCHITECTURE.md`, `docs/DOMAIN_RULES.md`, `docs/TESTING.md` e relatórios de Sprint.
3. Materiais de aula anexados, usados para entender o formato da entrega e o contexto acadêmico.

Em caso de divergência, as regras formalmente registradas no repositório prevalecem sobre exemplos
visuais dos materiais de aula. Os anexos não autorizam mudanças no produto.

## Estado considerado

- **Implementado (IMP):** autenticação; identidade acadêmica; usuários; salas; transferências;
  competências; projetos; grupos; convites; revisão inicial; follow-ups; marcos; timeline; colaboração
  interdisciplinar.
- **Planejado (PLN):** entrega formal versionada; encaminhamento à Mostra; designação e avaliação;
  premiação; elegibilidade; aprovação do documento publicável; publicação e retirada do acervo.

## Regras centrais rastreadas

- `RN-001`: grupo acadêmico com 2 a 4 estudantes.
- `RN-002`: projeto interdisciplinar com no máximo dois grupos no MVP.
- `RN-003`: aluno com no máximo uma sala acadêmica ativa.
- `RN-004`: transferência de aluno já vinculado depende de secretaria ou administração.
- `RN-005`: follow-ups são livres e não possuem aprovação.
- `RN-006`: marcos são configuráveis; não existem etapas globais fixas.
- `RN-007`: papéis de professor são contextuais e a autorização é por objeto.
- `RN-008`: somente trabalho apresentado é elegível para publicação no MVP.
- `RN-009`: orientador não pode avaliar projeto da própria sala.
- `RN-010`: registros acadêmicos e históricos não expiram automaticamente.

## Segurança e proteção de dados

Os modelos assumem negação por padrão, menor privilégio, autorização no backend e por objeto, UUIDs
externos, uploads privados, validação de tipo/tamanho e auditoria de ações acadêmicas relevantes.
CPF integral, senhas, tokens e segredos não aparecem nos diagramas nem nos artefatos desta entrega.
