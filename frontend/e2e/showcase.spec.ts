import{expect,test,type APIRequestContext,type Page}from'@playwright/test'

// Sprint 7 contra backend real: aluno gera documento → orientador aprova →
// aluno publica no acervo (GF-09); publicação inválida é bloqueada (GF-10);
// secretaria retira publicação.
// Pula sem backend (CI). Requer usuários teste1/teste2 e senha via E2E_TEST_PASSWORD.

const API=process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
const PASSWORD=process.env.E2E_TEST_PASSWORD ?? ''
function requirePassword(){
  if(!PASSWORD)throw new Error('Defina E2E_TEST_PASSWORD com a senha dos usuários de teste locais.')
}
const ALUNO={identifier:'RA3001',password:PASSWORD}
const ORIENTADOR={identifier:'prof.teste1',password:PASSWORD}
const SECRETARIAT={identifier:'secretaria.teste',password:PASSWORD}
const PROJECT_NAME=`Projeto E2E Acervo ${Date.now()}`

type ProjectSummary={id:string;status:string}

async function backendAvailable(request:APIRequestContext){
  try{
    const health=await request.get(`${API}/health/`,{timeout:5000})
    return health.ok()
  }catch{
    return false
  }
}

async function apiLogin(request:APIRequestContext,identifier:string,password:string){
  for(let attempt=0;attempt<3;attempt++){
    const csrf=(await(await request.get(`${API}/auth/csrf/`)).json()).csrfToken
    const login=await request.post(`${API}/auth/login/`,{headers:{'X-CSRFToken':csrf},data:{identifier,password}})
    if(login.status()===429&&attempt<2){await new Promise(r=>setTimeout(r,65000));continue}
    if(!login.ok())throw new Error(`E2E login falhou: ${identifier} ${login.status()}`)
    const fresh=(await(await request.get(`${API}/auth/csrf/`)).json()).csrfToken as string
    return fresh
  }
  throw new Error(`E2E login falhou: ${identifier} 429 persistente`)
}

async function userProjects(request:APIRequestContext){
  const list=await(await request.get(`${API}/projects/?q=`)).json()
  return (list as ProjectSummary[]).filter(p=>!['COMPLETED','ARCHIVED','CANCELLED'].includes(p.status))
}

async function cancelActive(request:APIRequestContext,identifier:string){
  const token=await apiLogin(request,identifier,PASSWORD)
  const actives=await userProjects(request)
  if(actives.length===0)return
  for(const project of actives){
    const req=await request.post(`${API}/projects/${project.id}/lifecycle/`,{headers:{'X-CSRFToken':token},data:{action:'request-cancellation',reason:'Limpeza E2E'}})
    const body=await req.text()
    if(!req.ok()&&!body.includes('pendente'))throw new Error(`E2E solicitar cancelamento falhou: ${req.status()} ${body.slice(0,200)}`)
  }
  const secToken=await apiLogin(request,SECRETARIAT.identifier,SECRETARIAT.password)
  for(const project of actives){
    const dec=await request.post(`${API}/projects/${project.id}/lifecycle/`,{headers:{'X-CSRFToken':secToken},data:{action:'approve-cancellation',reason:'Limpeza E2E'}})
    if(!dec.ok())throw new Error(`E2E aprovar cancelamento falhou: ${dec.status()} ${(await dec.text()).slice(0,200)}`)
  }
}

async function prepareApprovedProject(request:APIRequestContext){
  const token=await apiLogin(request,ALUNO.identifier,ALUNO.password)
  const themes=await(await request.get(`${API}/projects/themes/`)).json() as {id:string;room_name:string}[]
  const theme=themes.find(t=>t.room_name==='Sala A') ?? themes[0]
  const created=await request.post(`${API}/projects/`,{headers:{'X-CSRFToken':token},data:{name:PROJECT_NAME,about:'Proposta E2E de acervo.',theme:theme.id}})
  if(!created.ok())throw new Error(`E2E criar projeto falhou: ${created.status()} ${(await created.text()).slice(0,200)}`)
  const project=await created.json() as {id:string}
  const eligible=await(await request.get(`${API}/projects/eligible-students/?q=RA3002&project=${project.id}`,{headers:{'X-CSRFToken':token}})).json() as {id:string}[]
  const invitation=await request.post(`${API}/projects/${project.id}/invitations/`,{headers:{'X-CSRFToken':token},data:{invitee:eligible[0].id}})
  if(!invitation.ok())throw new Error(`E2E convidar falhou: ${invitation.status()}`)
  const token2=await apiLogin(request,'RA3002',PASSWORD)
  const mine=await(await request.get(`${API}/projects/invitations/mine/`)).json() as {id:string;project_name:string}[]
  const mineForProject=mine.find(i=>i.project_name===PROJECT_NAME) ?? mine[0]
  const accepted=await request.post(`${API}/projects/invitations/${mineForProject.id}/accept/`,{headers:{'X-CSRFToken':token2},data:{}})
  if(!accepted.ok())throw new Error(`E2E aceitar falhou: ${accepted.status()}`)
  const approved=await request.post(`${API}/projects/${project.id}/approve/`,{headers:{'X-CSRFToken':token},data:{feedback:''}})
  if(!approved.ok())throw new Error(`E2E aprovar projeto falhou: ${approved.status()}`)
  return project.id as string
}

test.describe.configure({mode:'serial'})

test.beforeEach(async({request},testInfo)=>{
  if(testInfo.project.name!=='desktop')test.skip(true,'acervo mobile na Sprint 6')
  if(!await backendAvailable(request))test.skip(true,'backend de desenvolvimento indisponível')
  requirePassword()
  await cancelActive(request,ALUNO.identifier)
})
test.afterEach(async({request},testInfo)=>{
  if(testInfo.project.name!=='desktop')return
  if(!await backendAvailable(request))return
  await cancelActive(request,ALUNO.identifier)
})

async function uiLogin(page:Page,identifier:string){
  await page.goto('/')
  await page.getByLabel('CPF, RA ou usuário').fill(identifier)
  await page.getByLabel('Senha',{exact:true}).fill(PASSWORD)
  await page.getByRole('button',{name:'Entrar'}).click()
  await expect(page.getByRole('heading',{name:'Início'})).toBeVisible()
}

async function uiLogout(page:Page){
  await page.getByRole('button',{name:'Sair'}).first().click()
  await expect(page.getByRole('heading',{name:'Entrar na plataforma'})).toBeVisible()
}

async function openProject(page:Page,name:string){
  await page.getByRole('button',{name:'Projetos'}).first().click()
  const safe=name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')
  const byArticle=page.locator('article').filter({has:page.getByRole('heading',{name,exact:true})})
  await expect(byArticle.first()).toBeVisible({timeout:15000})
  await byArticle.first().getByRole('button',{name:/Abrir/}).click()
  await page.waitForURL(/#\/projects\/.+/)
  await expect(page.getByRole('heading',{name,exact:true}).first()).toBeVisible()
}

test('GF-09: publicacao valida do aluno no acervo',async({page,request})=>{
  test.slow()
  const projectId=await prepareApprovedProject(request)
  void projectId
  await uiLogin(page,ALUNO.identifier)
  await openProject(page,PROJECT_NAME)

  // Orientador designa avaliador (pré-requisito para agendar a Mostra)
  await page.getByRole('button',{name:'Designar avaliador'}).click()
  await page.getByLabel(/Buscar professor/).fill('Teste 2')
  await page.getByRole('button',{name:/Selecionar Professor Teste 2/}).click()
  await page.getByLabel('Justificativa').fill('Rodízio E2E.')
  await page.getByRole('button',{name:'Confirmar designação'}).click()
  await expect(page.getByText('Avaliador designado.')).toBeVisible()
  await uiLogout(page)

  // Secretaria agenda a Mostra
  await uiLogin(page,SECRETARIAT.identifier)
  await page.getByRole('button',{name:'Agenda da Mostra'}).click()
  await page.getByLabel(/Grupo \(UUID\)/).fill('')
  await page.getByLabel('Data e hora').fill('2026-12-10T14:00')
  await page.getByLabel('Local').fill('Auditório Central')
  await page.getByRole('button',{name:'Agendar'}).click()
  await expect(page.getByText('Mostra agendada.')).toBeVisible()
  await uiLogout(page)

  // Avaliador registra PRESENTED
  await uiLogin(page,ORIENTADOR.identifier)
  await page.getByRole('button',{name:'Registro de presença'}).click()
  await page.getByRole('button',{name:'Apresentado'}).click()
  await expect(page.getByText('Presença registrada.')).toBeVisible()
  await uiLogout(page)

  // Aluno gera documento com consentimento
  await uiLogin(page,ALUNO.identifier)
  await openProject(page,PROJECT_NAME)
  await page.getByRole('button',{name:'Documento publicável'}).click()
  await page.getByText('Gerar novo documento').click()
  await page.locator('input[name="pdf"]').setInputFiles({name:'documento.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 documento e2e')})
  await page.getByLabel(/consentimento/).click()
  await page.getByRole('button',{name:'Gerar documento'}).click()
  await expect(page.getByText('Documento gerado e enviado para aprovacao.')).toBeVisible()
  await uiLogout(page)

  // Orientador aprova o documento
  await uiLogin(page,ORIENTADOR.identifier)
  await openProject(page,PROJECT_NAME)
  await page.getByRole('button',{name:'Documento publicável'}).click()
  await page.getByRole('button',{name:'Aprovar'}).click()
  await page.getByLabel('Parecer').fill('Documento conforme.')
  await page.getByRole('button',{name:'Aprovar'}).click()
  await expect(page.getByText('Documento aprovado.')).toBeVisible()
  await uiLogout(page)

  // Aluno publica no acervo
  await uiLogin(page,ALUNO.identifier)
  await openProject(page,PROJECT_NAME)
  await page.getByRole('button',{name:'Publicação no acervo'}).click()
  await page.getByText('Publicar no acervo').click()
  await page.getByRole('button',{name:'Publicar'}).click()
  await expect(page.getByText('Projeto publicado no acervo.')).toBeVisible()
  await uiLogout(page)

  // Acervo exibe o projeto publicado (autenticado)
  await uiLogin(page,SECRETARIAT.identifier)
  await page.getByRole('button',{name:'Acervo publicado'}).click()
  await expect(page.getByText(PROJECT_NAME)).toBeVisible()
  await uiLogout(page)
})

test('GF-10: bloqueio de publicacao invalida',async({page,request})=>{
  test.slow()
  const projectId=await prepareApprovedProject(request)
  void projectId
  await uiLogin(page,ALUNO.identifier)
  await openProject(page,PROJECT_NAME)

  // Sem documento aprovado: publica deve falhar
  await page.getByRole('button',{name:'Publicação no acervo'}).click()
  await page.getByText('Publicar no acervo').click()
  await page.getByRole('button',{name:'Publicar'}).click()
  await expect(page.getByText(/aprovado/i)).toBeVisible()
  await uiLogout(page)
})
