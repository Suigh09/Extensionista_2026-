import{expect,test,type APIRequestContext,type APIResponse,type Page}from'@playwright/test'

const API='http://127.0.0.1:8000/api/v1'
const PASSWORD=process.env.E2E_TEST_PASSWORD ?? ''
function requirePassword(){
  if(!PASSWORD)throw new Error('Defina E2E_TEST_PASSWORD com a senha dos usuários de teste locais.')
}
const ALUNO={identifier:'RA3001',password:PASSWORD}
const ORIENTADOR={identifier:'prof.teste1',password:PASSWORD}
const SECRETARIAT={identifier:'secretaria.teste',password:PASSWORD}

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

async function csrf(request:APIRequestContext){
  return (await(await request.get(`${API}/auth/csrf/`)).json()).csrfToken
}

async function userProjects(request:APIRequestContext){
  const response=await request.get(`${API}/projects/?q=`)
  await expect(response).toBeOK()
  const data=await response.json()
  const list=Array.isArray(data)?data:data.results
  expect(Array.isArray(list),'Contrato da lista de projetos').toBe(true)
  return (list as {id:string;name:string;status:string}[]).filter(p=>p.name.startsWith('Projeto E2E Acervo ')&&!['COMPLETED','ARCHIVED','CANCELLED'].includes(p.status))
}

async function cancelActive(request:APIRequestContext,identifier:string){
  await apiLogin(request,identifier,PASSWORD)
  const actives=await userProjects(request)
  if(actives.length===0)return
  const secToken=await apiLogin(request,SECRETARIAT.identifier,SECRETARIAT.password)
  for(const project of actives){
    const dec=await request.post(`${API}/projects/${project.id}/lifecycle/`,{headers:{'X-CSRFToken':secToken},data:{action:'cancel',reason:'Finalização dos projetos sintéticos E2E de acervo'}})
    if(!dec.ok())throw new Error(`E2E aprovar cancelamento falhou: ${dec.status()} ${await dec.text()}`)
  }
}

async function prepareApprovedProject(request:APIRequestContext,projectName:string){
  const token=await apiLogin(request,ALUNO.identifier,ALUNO.password)
  const themes=await(await request.get(`${API}/projects/themes/`)).json() as {id:string;title:string}[]
  const theme=themes.find(t=>t.title==='Sala A') ?? themes[0]
  expect(theme,'Aluno precisa de vínculo ativo com sala e tema aberto').toBeTruthy()
   const created=await request.post(`${API}/projects/`,{headers:{'X-CSRFToken':token},data:{name:projectName,about:'Proposta E2E de acervo.',theme:theme.id}})
  if(!created.ok())throw new Error(`E2E criar projeto falhou: ${created.status()} ${(await created.text()).slice(0,200)}`)
  const project=await created.json() as {id:string}
  const eligible=await(await request.get(`${API}/projects/eligible-students/?q=RA3002&project=${project.id}`,{headers:{'X-CSRFToken':token}})).json() as {id:string}[]
  const invitation=await request.post(`${API}/projects/${project.id}/invitations/`,{headers:{'X-CSRFToken':token},data:{invitee:eligible[0].id}})
  if(!invitation.ok())throw new Error(`E2E convidar falhou: ${invitation.status()}`)
  const token2=await apiLogin(request,'RA3002',PASSWORD)
  const mine=await(await request.get(`${API}/projects/invitations/mine/`)).json() as {id:string;project_name:string}[]
  const mineForProject=mine.find(i=>i.project_name===projectName)
  expect(mineForProject,'Convite deve pertencer ao projeto do cenário').toBeTruthy()
  if(!mineForProject)throw new Error('Convite do projeto E2E não encontrado')
  const accepted=await request.post(`${API}/projects/invitations/${mineForProject.id}/accept/`,{headers:{'X-CSRFToken':token2},data:{}})
  if(!accepted.ok())throw new Error(`E2E aceitar falhou: ${accepted.status()}`)
  const submitted=await request.post(`${API}/projects/${project.id}/submit/`,{headers:{'X-CSRFToken':await csrf(request)},data:{}})
  if(!submitted.ok())throw new Error(`E2E submeter projeto falhou: ${submitted.status()} ${(await submitted.text()).slice(0,200)}`)
  await apiLogin(request,ORIENTADOR.identifier,ORIENTADOR.password)
  const approved=await request.post(`${API}/projects/${project.id}/approve/`,{headers:{'X-CSRFToken':await csrf(request)},data:{feedback:''}})
  if(!approved.ok())throw new Error(`E2E aprovar projeto falhou: ${approved.status()} ${(await approved.text()).slice(0,200)}`)
  return project.id as string
}

test.beforeEach(async({page},testInfo)=>{
  if(testInfo.project.name!=='desktop')test.skip(true,'acervo mobile na Sprint 6')
  const request = page.request
  expect(await backendAvailable(request),'Backend E2E precisa estar disponível').toBe(true)
  requirePassword()
  await cancelActive(request,ALUNO.identifier)
})

async function openPublicAcervo(page:Page){
  const [response]=await Promise.all([
    page.waitForResponse(response=>new URL(response.url()).pathname==='/api/v1/projects/acervo-publico/'&&response.request().method()==='GET'),
    page.goto('/#/acervo-publico')
  ])
  expect(response.status()).toBe(200)
  expect((await response.request().allHeaders()).cookie??'').not.toContain('sessionid=')
  await expect(page.getByRole('heading',{name:'Acervo de projetos publicados',exact:true})).toBeVisible()
  await expect(page.getByText('Carregando acervo…',{exact:true})).toBeHidden()
  await expect(page.getByRole('status')).toHaveCount(0)
  expect((await page.request.get(`${API}/auth/session/`)).status()).toBe(403)
  return response.json() as Promise<{project_name:string}[]>
}

test('GF-09: publicacao anonima no acervo',async({page,browser,baseURL})=>{
  test.slow()
  const request = page.request
  const projectName=`Projeto E2E Acervo ${Date.now()} GF-09`
  const projectId=await prepareApprovedProject(request,projectName)
  const documentId=await preparePublication(request,projectId,true)
  // page.request compartilha os cookies do contexto do navegador.
  await apiLogin(request,ALUNO.identifier,ALUNO.password)
  await page.goto(`/#/publication/${projectId}`)
  await expect(page.getByRole('heading',{name:'Publicação do projeto'})).toBeVisible()
  await page.locator('summary').filter({hasText:'Publicar no acervo'}).click()
  await expect(page.getByLabel('Documento publicável')).toBeVisible()
  await expect(page.getByLabel('Documento publicável').locator(`option[value="${documentId}"]`)).toHaveCount(1)
  await page.getByLabel('Documento publicável').selectOption(documentId)
  const [published]=await Promise.all([
    page.waitForResponse(response=>new URL(response.url()).pathname==='/api/v1/projects/publications/'&&response.request().method()==='POST'),
    page.getByRole('button',{name:'Publicar',exact:true}).click()
  ])
  expect(published.status()).toBe(201)
  await expect(page.getByText('Projeto publicado no acervo.')).toBeVisible()
  const downloadPath=`${API}/projects/publication-documents/${documentId}/download/`
  const document=await request.get(downloadPath)
  await expect(document).toBeOK()
  expect(document.headers()['content-type']).toContain('application/pdf')
  const anonymous=await browser.newContext({baseURL,storageState:{cookies:[],origins:[]}})
  try{
    const publicPage=await anonymous.newPage()
    const items=await openPublicAcervo(publicPage)
    expect(items.some(item=>item.project_name===projectName)).toBe(true)
    await expect(publicPage.getByRole('heading',{name:projectName,exact:true})).toBeVisible()
    expect((await anonymous.request.get(downloadPath)).status()).toBe(403)
  }finally{await anonymous.close()}
})

test('GF-10: bloqueio de publicacao invalida',async({page,browser,baseURL})=>{
  test.slow()
  const request = page.request
  const projectName=`Projeto E2E Acervo ${Date.now()} GF-10`
  const projectId=await prepareApprovedProject(request,projectName)
  const documentId=await preparePublication(request,projectId,false)
  await apiLogin(request,ALUNO.identifier,ALUNO.password)
  const publishResp=await request.post(`${API}/projects/publications/`,{headers:{'X-CSRFToken':await csrf(request)},data:{project:projectId,document:documentId}})
  expect(publishResp.status()).toBe(400)
  expect(await publishResp.json()).toEqual({non_field_errors:['O documento precisa estar aprovado para publicar.']})
  const publications=await json(await request.get(`${API}/projects/publications/`)) as {project:string}[]
  expect(publications.some(p=>p.project===projectId)).toBe(false)
  const anonymous=await browser.newContext({baseURL,storageState:{cookies:[],origins:[]}})
  try{
    const publicPage=await anonymous.newPage()
    const items=await openPublicAcervo(publicPage)
    expect(items.some(item=>item.project_name===projectName)).toBe(false)
    await expect(publicPage.getByRole('heading',{name:projectName,exact:true})).toHaveCount(0)
  }finally{await anonymous.close()}
})

async function json(response:APIResponse){
  await expect(response).toBeOK()
  return response.json()
}

async function post(request:APIRequestContext,path:string,data:Record<string,unknown>){
  return json(await request.post(`${API}/projects/${path}`,{headers:{'X-CSRFToken':await csrf(request)},data}))
}

async function preparePublication(request:APIRequestContext,projectId:string,approve:boolean){
  const pdf={name:'acervo-e2e.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\nDocumento sintético E2E\n%%EOF')}
  await apiLogin(request,ALUNO.identifier,PASSWORD)
  const delivery=await json(await request.post(`${API}/projects/${projectId}/deliveries/`,{headers:{'X-CSRFToken':await csrf(request)},multipart:{document:pdf}}))
  const document=await json(await request.post(`${API}/projects/${projectId}/publication-documents/`,{headers:{'X-CSRFToken':await csrf(request)},multipart:{pdf,consent_given:'true'}}))
  await apiLogin(request,ORIENTADOR.identifier,PASSWORD)
  await post(request,`deliveries/${delivery.id}/review/`,{decision:'APPROVED',feedback:'Entrega E2E validada'})
  await post(request,`${projectId}/forward/`,{required_competencies:'Extensão',observations:'Encaminhamento E2E'})
  if(approve)await post(request,`publication-documents/${document.id}/review/`,{status:'APPROVED',review:'Documento E2E validado'})
  await apiLogin(request,SECRETARIAT.identifier,PASSWORD)
  const project=await json(await request.get(`${API}/projects/${projectId}/`))
  const recommendations=await json(await request.get(`${API}/projects/${projectId}/evaluator-recommendations/`))
  const evaluator=recommendations.recommendations.find((p:{name:string})=>p.name==='Avaliador E2E Acervo')
  expect(evaluator,'Preparar professor avaliador E2E distinto do orientador').toBeTruthy()
  const group=project.groups[0].id
  await post(request,`groups/${group}/designate-evaluator/`,{professor:evaluator.professor_profile_id,justification:'Avaliador sintético dedicado ao E2E'})
  const entry=await post(request,'showcase/',{group,date:new Date(Date.now()+86400000).toISOString(),location:'Auditório E2E'})
  await apiLogin(request,'avaliador.e2e.acervo',PASSWORD)
  await post(request,`showcase/${entry.id}/`,{status:'PRESENTED',notes:'Apresentação E2E'})
  return document.id as string
}
