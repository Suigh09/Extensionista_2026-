# Diagramas de Atividade

## UC-009 a UC-012 - Criação e aprovação inicial do projeto

```mermaid
flowchart TD
  A([Início]) --> B{Aluno autenticado e com sala ativa?}
  B -- Não --> X[Negar criação e orientar regularização] --> Z([Fim])
  B -- Sim --> C[Criar projeto em RASCUNHO e grupo inicial]
  C --> D[Convidar alunos elegíveis da mesma sala]
  D --> E{Convite aceito e grupo com 2 a 4 membros?}
  E -- Não --> D
  E -- Sim --> F[Submeter proposta]
  F --> G{Autorização e regras revalidadas no backend?}
  G -- Não --> H[Rejeitar operação sem alterar estado] --> Z
  G -- Sim --> I[Estado AGUARDANDO APROVAÇÃO]
  I --> J{Decisão do professor responsável}
  J -- Solicitar ajustes --> K[Registrar feedback e AJUSTES SOLICITADOS]
  K --> L[Aluno corrige proposta] --> F
  J -- Aprovar --> M[Registrar professor, data e APROVADO]
  M --> N[Liberar acompanhamento]
  N --> Z
```

## UC-005 a UC-007 - Inclusão ou transferência de aluno em sala

```mermaid
flowchart TD
  A([Início]) --> B[Professor seleciona sua sala ativa]
  B --> C[Pesquisar aluno por nome ou RA]
  C --> D{Aluno possui sala ativa?}
  D -- Não --> E[Validar autorização por objeto]
  E --> F[Encerrar qualquer inconsistência concorrente em transação]
  F --> G[Criar vínculo ativo e auditar] --> Z([Fim])
  D -- Sim --> H{Já existe solicitação pendente?}
  H -- Sim --> I[Informar duplicidade sem criar nova solicitação] --> Z
  H -- Não --> J[Criar solicitação PENDENTE]
  J --> K[Secretaria ou administrador analisa origem e destino]
  K --> L{Decisão}
  L -- Recusar --> M[Registrar motivo e RECUSADA] --> Z
  L -- Aprovar --> N[Revalidar salas, vínculo e concorrência]
  N --> O{Regras ainda válidas?}
  O -- Não --> P[Negar decisão e preservar vínculo atual] --> Z
  O -- Sim --> Q[Encerrar vínculo anterior e criar vínculo de destino]
  Q --> R[Registrar decisor, data e APROVADA] --> Z
```

## UC-013 a UC-015 - Acompanhamento livre e marcos configuráveis

```mermaid
flowchart TD
  A([Início]) --> B{Usuário participa do projeto ou é professor autorizado?}
  B -- Não --> X[Negar acesso por objeto] --> Z([Fim])
  B -- Sim --> C{Ação desejada}
  C -- Publicar follow-up --> D[Validar texto e anexos]
  D --> E{Tipo, tamanho e quantidade permitidos?}
  E -- Não --> F[Rejeitar upload com mensagem segura] --> Z
  E -- Sim --> G[Armazenar arquivo com nome seguro e acesso privado]
  G --> H[Registrar follow-up imutável]
  C -- Configurar marco --> I{Usuário é professor contextual autorizado?}
  I -- Não --> X
  I -- Sim --> J[Definir título, prazo, escopo e exigências]
  J --> K[Aplicar a projetos elegíveis sem etapa global fixa]
  H --> L[Projetar evento na timeline]
  K --> L
  L --> M[Exibir timeline cronológica] --> Z
```

## UC-016 - Parceria interdisciplinar

```mermaid
flowchart TD
  A([Início]) --> B[Grupo formado publica oportunidade]
  B --> C[Outro grupo formado envia candidatura]
  C --> D{É grupo distinto, sem membros sobrepostos e dentro do limite?}
  D -- Não --> X[Rejeitar candidatura] --> Z([Fim])
  D -- Sim --> E[Grupo anunciante analisa candidatura]
  E --> F{Decisão}
  F -- Recusar --> G[Marcar candidatura RECUSADA] --> Z
  F -- Cancelar pelo candidato --> H[Marcar CANCELADA] --> Z
  F -- Aceitar --> I[Bloquear oportunidade, candidatura, projetos e grupos]
  I --> J[Revalidar todas as regras em transação]
  J --> K{Condições ainda válidas?}
  K -- Não --> X
  K -- Sim --> L[Mover grupo candidato para o projeto anunciante]
  L --> M[Preservar turma, curso, orientador e avaliação do grupo]
  M --> N[Encerrar candidaturas concorrentes e projeto de origem vazio]
  N --> O[Registrar auditoria e PARCERIA FORMADA] --> Z
```
