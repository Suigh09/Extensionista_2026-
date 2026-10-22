# Sprint 7 — Mostra, publicação e acervo

Especificação aceita. Implementação autorizada.

## 1. Contexto (confirmado)

- O encaminhamento à Mostra pertence ao módulo Controle (não é módulo geral de
  eventos, que permanece fora do escopo) e usa os estados `PENDING`, `SCHEDULED`,
  `PRESENTED`, `ABSENT` ou `CANCELLED`.
- A secretaria não rejeita nem devolve o encaminhamento aprovado pelo orientador;
  informa data, local e avaliador designado.
- Projeto é elegível ao acervo depois de entregue, aprovado pelo orientador e
  avaliado na Mostra; **não há nota mínima**. No MVP, somente trabalho
  apresentado é elegível.
- O aluno gera o documento publicável em ferramenta de layout padronizado, e o
  orientador aprova esse documento antes da publicação.
- A secretaria pode retirar a publicação sem remover seu histórico.
- Registros acadêmicos e históricos não possuem expiração automática.
- Definição de data/local gera notificação interna; notificações de documento
  aprovado/reprovado, publicação realizada e publicação retirada (Q6 definido: sim).
- Pré-requisitos já implementados: entrega formal + encaminhamento (Sprint 5),
  avaliador designado (5.1), avaliação concluída com notas (Sprint 6).
- Pendentes hoje: visibilidade pública de nomes e documentos completos no acervo
  (Q5 definido: autenticados com nome+curso; leitura pública anônima fora do MVP).
- Não existe código de Mostra, documento padronizado, publicação ou acervo;
  Golden Flows GF-09 (publicação válida) e GF-10 (bloqueio de publicação
  inválida) estão reservados para esta Sprint.

## 2. Proposta de funcionamento

- **Mostra (avaliador)**: agenda a apresentação por grupo encaminhado (data,
  local; avaliador exibido é o designado na 5.1, sem nova designação):
  `PENDING` → `SCHEDULED`. Após a Mostra, o avaliador registra `PRESENTED`
  ou `ABSENT` (Q1 definido). `CANCELLED` só por cancelamento do projeto.
- **Elegibilidade derivada (não editável)**: entregue (delivery aprovada) +
  proposta aprovada + avaliação concluída (Sprint 6) + `PRESENTED` na Mostra.
- **Documento padronizado (aluno)**: ferramenta gera PDF server-side a partir de
  template institucional com os dados do projeto (proposta de campos — ver Q3);
  versionado; cada geração é uma linha nova.
- **Aprovação do documento (orientador)**: aprova ou reprova com parecer; sem
  aprovação vigente, a publicação é bloqueada.
- **Publicação (Q2 definido)**: aluno + orientador publicam projeto elegível com
  documento aprovado; acervo com metadados e pesquisa.
- **Retirada (Q7 definido)**: secretaria despublica mantendo todo o histórico;
  projeto sai do acervo consultável; **republicação não é permitida** — um
  projeto publicado não retorna ao acervo em novo ciclo.
- **Minimização LGPD (Q5 definido)**: no MVP o acervo é visível a usuários
  autenticados e expõe de alunos no máximo nome + curso.
- Permissões no backend e por objeto; auditoria de agenda, presença, gerações,
  aprovações, publicações e retiradas.

## 3. Critérios de aceite

1. Secretaria agenda Mostra (data/local) de grupo encaminhado; `PENDING` →
   `SCHEDULED`; grupo notificado.
2. Avaliador registra `PRESENTED`/`ABSENT`; só a combinação elegível completa
   libera a publicação.
3. Projeto não apresentado (ou sem entrega/aprovação/avaliação) → tentativa de
   publicar é bloqueada pela API (GF-10).
4. Aluno gera documento padronizado em PDF com os dados do projeto; versões
   preservadas.
5. Orientador aprova/reprova o documento com parecer; sem aprovação vigente, a
   publicação é bloqueada.
6. Projeto elegível + documento aprovado → publicação com metadados pesquisáveis
   no acervo (GF-09).
7. Secretaria retira a publicação; histórico preservado; item sai da consulta.
8. Autorização por objeto: aluno de outro projeto, avaliador e anônimo recebem
   403/404/401 conforme o caso; ocultar botão não autoriza.
9. Acervo expõe de alunos no máximo nome + curso até decisão de visibilidade
   pública.

## 4. Arquitetura e dados

- Novos modelos `ShowcaseEntry` (grupo, data, local, status, decided_by),
  `PublicationDocument` (projeto, versão, PDF, status, parecer) e `Publication`
  (projeto, documento, publicada/retirada em, motivo); migrations só adicionam;
  constraints de vigência única; locks e auditoria/eventos no backend.
- Geração de PDF server-side a partir de template institucional (biblioteca a
  definir na implementação).
- Frontend: agenda da Mostra (secretaria), gerador de documento (aluno),
  aprovação (orientador), página do acervo com pesquisa; mobile-first.

## 5. Validação

API, permissões/IDOR, regressão cumulativa, componentes, build, fluxo autenticado
real, E2E desktop+mobile (GF-09/GF-10), reviews, simulações. Postgres/Docker + CI
para PASS.

## 6. Decisões para aceite

- **Q1.** Quem registra `PRESENTED`/`ABSENT`: **avaliador da Mostra** (definido).
- **Q2.** Ato de publicar: **aluno + orientador** (definido).
- **Q3.** Documento PDF server-side via template institucional (definido: sim).
  Campos obrigatórios iniciais: título, resumo, integrantes, orientador, curso, ano.
- **Q4.** Consentimento (nome, curso, PDF): **aceite explícito ao gerar/publicar** (definido: sim);
  registro de aceite no modelo `PublicationDocument`.
- **Q5.** Acervo no MVP: **usuários autenticados com minimização nome+curso** (definido: sim).
- **Q6.** Novas notificações: documento aprovado/reprovado, publicação
  realizada, publicação retirada (definido: sim).
- **Q7.** Retirada permite republicação em novo ciclo: **não** (definido) — um
  projeto publicado não retorna ao acervo; não há novo ciclo de publicação
  para o mesmo projeto.
