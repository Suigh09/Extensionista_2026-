# Diagrama de Casos de Uso

```mermaid
flowchart LR
  AL[Aluno]
  PR[Professor]
  SE[Secretaria]
  AD[Administrador]
  AV[Professor no papel contextual de avaliador]
  PU[Público]

  subgraph Plataforma Extensionista
    UC001((UC-001 Autenticar-se))
    UC002((UC-002 Consultar perfil))
    UC003((UC-003 Gerenciar usuários))
    UC004((UC-004 Gerenciar estrutura acadêmica))
    UC005((UC-005 Gerenciar sala acadêmica))
    UC006((UC-006 Solicitar transferência de aluno))
    UC007((UC-007 Decidir transferência))
    UC008((UC-008 Gerenciar competências))
    UC009((UC-009 Criar e editar projeto))
    UC010((UC-010 Formar grupo e decidir convites))
    UC011((UC-011 Submeter proposta))
    UC012((UC-012 Revisar proposta))
    UC013((UC-013 Publicar follow-up e anexo))
    UC014((UC-014 Configurar marcos))
    UC015((UC-015 Consultar timeline))
    UC016((UC-016 Formar parceria interdisciplinar))
    UC017((UC-017 Encaminhar projeto à Mostra - PLN))
    UC018((UC-018 Agendar apresentação - PLN))
    UC019((UC-019 Avaliar grupo - PLN))
    UC020((UC-020 Registrar nota individual - PLN))
    UC021((UC-021 Aprovar publicação - PLN))
    UC022((UC-022 Publicar ou retirar do acervo - PLN))
    UC023((UC-023 Consultar acervo público - PLN))
  end

  AL --- UC001 & UC002 & UC009 & UC010 & UC011 & UC013 & UC015 & UC016
  PR --- UC001 & UC002 & UC005 & UC006 & UC008 & UC012 & UC013 & UC014 & UC015 & UC017 & UC020 & UC021
  SE --- UC001 & UC002 & UC007 & UC018 & UC022
  AD --- UC001 & UC002 & UC003 & UC004 & UC007 & UC022
  AV --- UC001 & UC002 & UC015 & UC019
  PU --- UC023

  UC005 -. pode gerar .-> UC006
  UC009 -. inclui .-> UC010
  UC011 -. exige grupo formado .-> UC010
  UC017 -. precede .-> UC018
  UC018 -. habilita .-> UC019
  UC019 -. contribui para .-> UC021
  UC021 -. habilita .-> UC022
```

## Observações

- “Professor”, “orientador” e “avaliador” não são subclasses rígidas. Orientador e avaliador são
  papéis contextuais, calculados pelo vínculo com sala, grupo, projeto ou atribuição.
- Casos marcados `PLN` derivam das regras aprovadas e do roadmap, mas ainda não constituem evidência
  de funcionalidade entregue.
- A matriz de rastreabilidade detalha a associação de cada caso com seus atores e restrições.
