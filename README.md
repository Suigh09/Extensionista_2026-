# Extensionista 2026

Trabalho extensionista 2026 segundo semestre — Plataforma Extensionista, para controle e
acompanhamento de projetos de extensão, avaliação/premiação e acervo/publicação.

# Apresentação do Projeto 

Visão Geral: O presente documento consolida os artefatos de análise, modelagem e
especificação funcional da Plataforma Extensionista.

Equipe Desenvolvedora: Gustavo (DEV), Mauricio (NEGÒCIO), Bruno (DEV), Carlos (DEV) e Enzo (NEGÓCIO).

Justificativa e Objetivo: A Plataforma Extensionista é uma aplicação web baseada no
conceito de desk manager estruturada para otimizar o acompanhamento, a avaliação e a
organização do acervo de projetos extensionistas da instituição. O sistema mitiga a
complexidade e o esforço manual associados à gestão acadêmica tradicional, proporcionando
maior precisão nas avaliações docentes e transparência contínua para os discentes. 

## Estrutura do repositório

```
.
├── documentos/                 # Análise e modelagem rastreável da Entrega 1
│   ├── caso-de-uso/             # Diagrama de casos de uso (atores e associações)
│   ├── atividades/              # Diagramas de atividade dos principais fluxos
│   ├── entidades/                # Diagrama de classes de domínio
│   ├── estados/                  # Diagramas de estados (ciclos de vida)
│   ├── matriz-rastreabilidade/  # Atores x funcionalidades (md e csv)
│   ├── especificacoes/           # Escopo, fontes e regras de negócio
│   └── repositorio-github/       # Configuração e checklist deste repositório
├── .github/workflows/ci.yml    # Placeholder de CI (a completar com o stack do projeto)
└── LICENSE                     # MIT
```

Veja [`documentos/README.md`](documentos/README.md) para o índice completo da documentação,
incluindo as convenções de rastreabilidade (`UC-xxx`, `RF-xxx`, `RN-xxx`, `IMP`/`PLN`).

## Status

O código-fonte do projeto ainda será adicionado. Este commit inicial cobre a organização do
repositório e a documentação de análise/modelagem da Entrega 1.

## Como contribuir

1. Crie uma branch a partir de `main` para sua alteração.
2. Abra um Pull Request descrevendo o que foi feito.
3. Mantenha a pasta `/documentos` atualizada conforme o sistema evoluir — os diagramas usam
   Mermaid e são renderizados diretamente pelo GitHub.

## Licença

Este repositório é disponibilizado sob a [Licença MIT](LICENSE).
