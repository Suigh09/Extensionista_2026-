import{expect,test,type APIRequestContext,type Page}from'@playwright/test'

// Sprint 5 contra backend real: aluno entrega → orientador aprova → encaminha →
// secretaria consulta os recebidos. Isolamento via API (cancela projetos vigentes).
// Pula sem backend (CI). Requer sala com tema e os usuários teste1/teste2.

const API=process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
// Senha dos usuários de teste via ambiente (nunca versionada).
const PASSWORD=process.env.E2E_TEST_PASSWORD ?? ''
function requirePassword(){
  if(!PASSWORD)throw new Error('Defina E2E_TEST_PASSWORD com a senha dos usuários de teste locais.')
}
const ALUNO1={identifier:'RA3001',password:PASSWORD}
const ALUNO2={identifier:'RA3002',password:PASSWORD}
const PROFESSOR={identifier:'prof.teste1',password:PASSWORD}
const SECRETARIAT={identifier:'secretaria.teste',password:PASSWORD}
const PROJECT_NAME=`Projeto E2E ${Date.now()}`

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
    const fresh=(await(await request.get(`${API}/auth/csrf/`)).json()).csrfToken
    return fresh as string
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
  // Ordem importa: usa o token do aluno ANTES do login da secretaria,
  // pois cada login rotaciona o CSRF da sessão compartilhada.
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

async function prepareGroup(request:APIRequestContext){
  const token=await apiLogin(request,ALUNO1.identifier,ALUNO1.password)
  const themes=await(await request.get(`${API}/projects/themes/`)).json() as {id:string;room_name:string}[]
  const theme=themes.find(t=>t.room_name==='Sala A') ?? themes[0]
  const created=await request.post(`${API}/projects/`,{headers:{'X-CSRFToken':token},data:{name:PROJECT_NAME,about:'Proposta E2E de entrega.',theme:theme.id}})
  if(!created.ok())throw new Error(`E2E criar projeto falhou: ${created.status()} ${(await created.text()).slice(0,200)}`)
  const project=await created.json() as {id:string}
  const eligible=await(await request.get(`${API}/projects/eligible-students/?q=RA3002&project=${project.id}`,{headers:{'X-CSRFToken':token}})).json() as {id:string}[]
  const invitation=await request.post(`${API}/projects/${project.id}/invitations/`,{headers:{'X-CSRFToken':token},data:{invitee:eligible[0].id}})
  if(!invitation.ok())throw new Error(`E2E convidar falhou: ${invitation.status()}`)
  const token2=await apiLogin(request,ALUNO2.identifier,ALUNO2.password)
  const mine=await(await request.get(`${API}/projects/invitations/mine/`)).json() as {id:string;project_name:string}[]
  const mineForProject=mine.find(i=>i.project_name===PROJECT_NAME) ?? mine[0]
  const accepted=await request.post(`${API}/projects/invitations/${mineForProject.id}/accept/`,{headers:{'X-CSRFToken':token2},data:{}})
  if(!accepted.ok())throw new Error(`E2E aceitar falhou: ${accepted.status()}`)
  return project.id as string
}

test.describe.configure({mode:'serial'})

test.beforeEach(async({request},testInfo)=>{
  // Desktop cobre o fluxo multissessão; mobile volta na Sprint 6 junto da
  // avaliação mobile-first. Rodar ambos estoura o throttle de login (20/min/IP).
  if(testInfo.project.name!=='desktop')test.skip(true,'entregas mobile na Sprint 6')
  if(!await backendAvailable(request))test.skip(true,'backend de desenvolvimento indisponível')
  requirePassword()
  await cancelActive(request,ALUNO1.identifier)
  await cancelActive(request,ALUNO2.identifier)
})
test.afterEach(async({request},testInfo)=>{
  if(testInfo.project.name!=='desktop')return
  if(!await backendAvailable(request))return
  await cancelActive(request,ALUNO1.identifier)
  await cancelActive(request,ALUNO2.identifier)
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
  const byCard=page.getByRole('button',{name:new RegExp(safe)})
  await expect(byArticle.or(byCard).first()).toBeVisible({timeout:15000})
  if(await byArticle.count()>0){
    await byArticle.first().getByRole('button',{name:/Abrir/}).click()
  }else{
    await byCard.first().click()
  }
  await page.waitForURL(/#\/projects\/.+/)
  await expect(page.getByRole('heading',{name,exact:true}).first()).toBeVisible()
}

test('entrega formal até a secretaria',async({page,request})=>{
  test.slow()
  const projectId=await prepareGroup(request)
  void projectId
  await uiLogin(page,ALUNO1.identifier)
  await openProject(page,PROJECT_NAME)
  await page.getByRole('button',{name:'Enviar projeto para aprovação'}).click()
  await expect(page.getByText('Projeto enviado ao professor orientador.')).toBeVisible()
  await uiLogout(page)

  await uiLogin(page,PROFESSOR.identifier)
  await openProject(page,PROJECT_NAME)
  await page.getByRole('button',{name:'Aprovar projeto'}).click()
  await expect(page.getByText('Projeto aprovado.')).toBeVisible()
  await uiLogout(page)

  await uiLogin(page,ALUNO1.identifier)
  await openProject(page,PROJECT_NAME)
  await page.getByText('Nova entrega').click()
  await page.locator('input[name="document"]').setInputFiles({name:'entrega.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 entrega e2e')})
  await page.getByLabel('Observações da versão').fill('Primeira versão E2E')
  await page.getByRole('button',{name:'Enviar entrega'}).click()
  await expect(page.getByText('Entrega enviada ao orientador.')).toBeVisible()
  await uiLogout(page)

  await uiLogin(page,PROFESSOR.identifier)
  await openProject(page,PROJECT_NAME)
  await page.getByLabel('Parecer').fill('Documento conferido.')
  await page.getByRole('button',{name:'Aprovar entrega'}).click()
  await expect(page.getByText('Entrega aprovada.')).toBeVisible()
  await page.getByText('Encaminhar à secretaria').click()
  await page.getByLabel(/Observações ao setor/).fill('Turma dedicada.')
  await page.getByLabel(/Competências requeridas/).fill('Metodologia.')
  await page.getByRole('button',{name:'Revisar encaminhamento'}).click()
  await expect(page.getByRole('heading',{name:'Encaminhar projeto?'})).toBeVisible()
  await page.getByRole('button',{name:'Confirmar encaminhamento'}).click()
  await expect(page.getByText('Projeto encaminhado à secretaria.')).toBeVisible()
  await uiLogout(page)

  await uiLogin(page,SECRETARIAT.identifier)
  await page.getByRole('button',{name:'Projetos'}).first().click()
  await expect(page.getByText('Recebidos da orientação')).toBeVisible()
  const card=page.locator('article').filter({has:page.getByRole('heading',{name:PROJECT_NAME,exact:true})})
  await expect(card.getByText(/Turma dedicada/)).toBeVisible()
  await card.getByRole('button',{name:/Abrir/}).click()
  await page.waitForURL(/#\/projects\/.+/)
  await expect(page.getByRole('heading',{name:'Designação de avaliadores'})).toBeVisible()
  await page.getByLabel(/Buscar professor/).fill('Teste 2')
  await page.getByRole('button',{name:'Selecionar Professor Teste 2'}).click()
  await page.getByLabel('Justificativa').fill('Rodízio E2E.')
  await page.getByRole('button',{name:'Confirmar designação'}).click()
  await expect(page.getByText('Avaliador designado.')).toBeVisible()
})
