# Documentos da Entrega 1 - Análise e Modelagem

Esta pasta reúne a primeira versão rastreável da análise e modelagem da Plataforma Extensionista.
Os modelos refletem o código e as regras documentadas até a Sprint 4.7. Funcionalidades futuras são
marcadas como **planejadas** e não devem ser interpretadas como implementadas.

## Índice

- [`caso-de-uso/diagrama-casos-de-uso.md`](caso-de-uso/diagrama-casos-de-uso.md): atores, casos de uso e associações.
- [`atividades/`](atividades/README.md): fluxos principais, decisões e exceções.
- [`entidades/diagrama-classes.md`](entidades/diagrama-classes.md): classes de domínio e relacionamentos implementados.
- [`estados/diagramas-de-estados.md`](estados/diagramas-de-estados.md): ciclos de vida relevantes.
- [`matriz-rastreabilidade/atores-funcionalidades.md`](matriz-rastreabilidade/atores-funcionalidades.md): perfis, permissões e casos de uso.
- [`matriz-rastreabilidade/atores-funcionalidades.csv`](matriz-rastreabilidade/atores-funcionalidades.csv): versão tabular reutilizável.
- [`especificacoes/escopo-e-fontes.md`](especificacoes/escopo-e-fontes.md): escopo, premissas, fontes e limites.

Os diagramas usam Mermaid, renderizado diretamente pelo GitHub. O texto-fonte permanece versionável,
comparável em pull requests e fácil de atualizar conforme o sistema evolui.

## Convenções de rastreabilidade

- `UC-xxx`: caso de uso.
- `RF-xxx`: requisito funcional.
- `RN-xxx`: regra de negócio.
- `IMP`: implementado no código atual.
- `PLN`: planejado/documentado, ainda não implementado.

## Licença

Este conteúdo integra o Software definido na raiz do repositório e é disponibilizado sob a Licença MIT.
Os PDFs fornecidos como material de aula foram usados apenas como referência e não foram copiados para
o repositório nem relicenciados.
