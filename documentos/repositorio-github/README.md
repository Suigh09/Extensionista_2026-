# Configuração do Repositório GitHub

## Estado verificado em 28/08/2026

- repositório Git local existente, ainda sem commits;
- branch local atual: `master`;
- nenhum remoto configurado;
- GitHub Actions presente em `.github/workflows/ci.yml`;
- cliente de linha de comando do GitHub não instalado;
- navegador disponível sem sessão autenticada no GitHub;
- publicação, membros da equipe e orientador: **pendentes**.

## Configuração recomendada

- nome sugerido: `plataforma-extensionista`;
- visibilidade: privada, desde que o orientador possa receber acesso de leitura; pública apenas se a equipe decidir conscientemente;
- branch principal: `main`;
- proteção: pull request obrigatório, CI obrigatório e bloqueio de force push;
- acesso da equipe: `Write` para integrantes que desenvolvem;
- acesso do orientador: `Read` quando a conta/organização permitir; se o GitHub oferecer apenas o papel padrão de colaborador em repositório pessoal, confirmar o alcance antes do convite;
- segredos: somente em GitHub Actions Secrets, nunca em arquivos versionados.

## Checklist antes da publicação

- [x] README com visão geral, execução, contribuição e estrutura.
- [x] Pasta `/documentos` organizada e rastreável.
- [x] Arquivo `LICENSE` MIT.
- [x] Workflow de CI versionado.
- [ ] Confirmar conta/organização de destino.
- [ ] Confirmar nome e visibilidade do repositório.
- [ ] Informar usernames GitHub dos integrantes.
- [ ] Informar username GitHub do orientador.
- [ ] Revisar arquivos que entrarão no primeiro commit.
- [ ] Criar primeiro commit e publicar somente após confirmação.
- [ ] Convidar equipe e orientador; conferir permissões após aceite.
- [ ] Habilitar proteção da branch principal.
- [ ] Verificar a execução real do CI remoto.

## Evidência esperada para a entrega

Após a integração, registrar aqui a URL do repositório, a branch padrão, a visibilidade, a data da
publicação, os perfis convidados e o papel concedido. Não registrar e-mails, tokens ou qualquer
credencial. A tela de colaboradores deve ser conferida sem expor dados pessoais desnecessários.
