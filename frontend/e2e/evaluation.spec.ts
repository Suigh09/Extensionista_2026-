import{expect,test,type APIRequestContext}from'@playwright/test'

// Sprint 6 (GF-08): avaliador em viewport mobile lança notas por critério.
// Setup via API (projeto aprovado, entregue, encaminhado, avaliador designado,
// rubrica do orientador); UI cobre lançamento, média e conclusão.

const API=process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
const PASSWORD=process.env.E2E_TEST_PASSWORD ?? ''
const ALUNO1={identifier:'RA3001',password:PASSWORD}
const ALUNO2={identifier:'RA3002',password:PASSWORD}
const PROFESSOR={identifier:'prof.teste1',password:PASSWORD}
const EVALUATOR={identifier:'prof.teste3',password:PASSWORD}
const SECRETARIAT={identifier:'secretaria.teste',password:PASSWORD}
const PROJECT_NAME=`Projeto E2E Avalia ${Date.now()}`

function requirePassword(){
  if(!PASSWORD)throw new Error('Defina E2E_TEST_PASSWORD com a senha dos usuários de teste locais.')
}

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

type ProjectSummary={id:string;status:string}

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
    if(!req.ok()&&!body.includes('pendente'))throw new Error(`E2E solicitar cancelamento falhou: ${req.status()}`)
  }
  const secToken=await apiLogin(request,SECRETARIAT.identifier,SECRETARIAT.password)
  for(const project of actives){
    const dec=await request.post(`${API}/projects/${project.id}/lifecycle/`,{headers:{'X-CSRFToken':secToken},data:{action:'approve-cancellation',reason:'Limpeza E2E'}})
    if(!dec.ok())throw new Error(`E2E aprovar cancelamento falhou: ${dec.status()}`)
  }
}

async function prepareEvaluated(request:APIRequestContext){
  const token=await apiLogin(request,ALUNO1.identifier,ALUNO1.password)
  const themes=await(await request.get(`${API}/projects/themes/`)).json() as {id:string;room_name:string}[]
  const theme=themes.find(t=>t.room_name==='Sala A') ?? themes[0]
  const created=await request.post(`${API}/projects/`,{headers:{'X-CSRFToken':token},data:{name:PROJECT_NAME,about:'Proposta E2E de avaliação.',theme:theme.id}})
  if(!created.ok())throw new Error(`E2E criar falhou: ${created.status()} ${(await created.text()).slice(0,120)}`)
  const project=await created.json() as {id:string}
  const eligible=await(await request.get(`${API}/projects/eligible-students/?q=RA3002&project=${project.id}`)).json() as {id:string}[]
  const invitation=await request.post(`${API}/projects/${project.id}/invitations/`,{headers:{'X-CSRFToken':token},data:{invitee:eligible[0].id}})
  if(!invitation.ok())throw new Error('E2E convidar falhou')
  const token2=await apiLogin(request,ALUNO2.identifier,ALUNO2.password)
  const mine=await(await request.get(`${API}/projects/invitations/mine/`)).json() as {id:string;project_name:string}[]
  const mineForProject=mine.find(i=>i.project_name===PROJECT_NAME) ?? mine[0]
  const accepted=await request.post(`${API}/projects/invitations/${mineForProject.id}/accept/`,{headers:{'X-CSRFToken':token2},data:{}})
  if(!accepted.ok())throw new Error('E2E aceitar falhou')
  const tokenSubmit=await apiLogin(request,ALUNO1.identifier,ALUNO1.password)
  const submitted=await request.post(`${API}/projects/${project.id}/submit/`,{headers:{'X-CSRFToken':tokenSubmit},data:{}})
  if(!submitted.ok())throw new Error(`E2E enviar falhou: ${submitted.status()} ${(await submitted.text()).slice(0,200)}`)
  const profToken=await apiLogin(request,PROFESSOR.identifier,PROFESSOR.password)
  const approved=await request.post(`${API}/projects/${project.id}/approve/`,{headers:{'X-CSRFToken':profToken},data:{feedback:'Ok.'}})
  if(!approved.ok())throw new Error('E2E aprovar proposta falhou')
  const rubric=await request.post(`${API}/projects/rubrics/`,{headers:{'X-CSRFToken':profToken},data:{title:'Rubrica E2E',criteria:[{name:'Clareza',description:''},{name:'Impacto',description:''}]}})
  if(!rubric.ok())throw new Error(`E2E rubrica falhou: ${rubric.status()} ${(await rubric.text()).slice(0,200)}`)

  // Formal delivery + forwarding (required for evaluator recommendations)
  const tokenDelivery=await apiLogin(request,ALUNO1.identifier,ALUNO1.password)
  const pdfBuffer=Buffer.from('%PDF-1.4 formal delivery e2e')
  const formData=new FormData()
  formData.append('document',new Blob([pdfBuffer],{type:'application/pdf'}),'entrega.pdf')
  formData.append('notes','Entrega formal E2E')
  const delivery=await request.post(`${API}/projects/${project.id}/deliveries/`,{headers:{'X-CSRFToken':tokenDelivery},multipart:formData})
  if(!delivery.ok())throw new Error(`E2E entrega formal falhou: ${delivery.status()} ${(await delivery.text()).slice(0,200)}`)
  const deliveryJson=await delivery.json() as {id:string}
  const profToken2=await apiLogin(request,PROFESSOR.identifier,PROFESSOR.password)
  const review=await request.post(`${API}/projects/deliveries/${deliveryJson.id}/review/`,{headers:{'X-CSRFToken':profToken2},data:{decision:'APPROVED',feedback:'Documento conferido.'}})
  if(!review.ok())throw new Error(`E2E aprovar entrega falhou: ${review.status()} ${(await review.text()).slice(0,200)}`)
  const forward=await request.post(`${API}/projects/${project.id}/forward/`,{headers:{'X-CSRFToken':profToken2},data:{observations:'Turma dedicada.',required_competencies:'Metodologia.'}})
  if(!forward.ok())throw new Error(`E2E encaminhar falhou: ${forward.status()} ${(await forward.text()).slice(0,200)}`)

  const secToken=await apiLogin(request,SECRETARIAT.identifier,SECRETARIAT.password)
  const groups=await(await request.get(`${API}/projects/${project.id}/evaluator-recommendations/`,{headers:{'X-CSRFToken':secToken}})).json() as {groups:{group_id:string}[]}
  if(groups.groups.length===0)throw new Error('E2E nenhum grupo ativo para designar avaliador')
  const groupId=groups.groups[0].group_id
  const professors=await(await request.get(`${API}/academic/professors/search/?q=Teste%203`,{headers:{'X-CSRFToken':secToken}})).json() as {id:string}[]
  if(professors.length===0)throw new Error('E2E nenhum professor encontrado na busca')
  const designated=await request.post(`${API}/projects/groups/${groupId}/designate-evaluator/`,{headers:{'X-CSRFToken':secToken},data:{professor:professors[0].id,justification:'Rodízio E2E.'}})
  if(!designated.ok())throw new Error(`E2E designar falhou: ${designated.status()}`)
  return PROJECT_NAME
}

test.describe.configure({mode:'serial'})

test.beforeEach(async({request},testInfo)=>{
  if(testInfo.project.name!=='mobile')test.skip(true,'GF-08 exige viewport mobile')
  if(!await backendAvailable(request))test.skip(true,'backend de desenvolvimento indisponível')
  requirePassword()
  await cancelActive(request,ALUNO1.identifier)
  await cancelActive(request,ALUNO2.identifier)
})
test.afterEach(async({request},testInfo)=>{
  if(testInfo.project.name!=='mobile')return
  if(!await backendAvailable(request))return
  await cancelActive(request,ALUNO1.identifier)
  await cancelActive(request,ALUNO2.identifier)
})

test('avaliador mobile lança notas e conclui',async({page,request})=>{
  test.slow()
  const name=await prepareEvaluated(request)
  await page.goto('/')
  await page.getByLabel('CPF, RA ou usuário').fill(EVALUATOR.identifier)
  await page.getByLabel('Senha',{exact:true}).fill(PASSWORD)
  await page.getByRole('button',{name:'Entrar'}).click()
  await expect(page.getByRole('heading',{name:'Início'})).toBeVisible()
  await page.getByRole('button',{name:'Projetos'}).first().click()
  const card=page.getByRole('button',{name:new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&'))}).first()
  await expect(card).toBeVisible({timeout:15000})
  await card.click()
  await page.waitForURL(/#\/projects\/.+/)
  await expect(page.getByRole('heading',{name:'Avaliação do grupo'})).toBeVisible()
  // Debug: wait for form to be ready
  await page.waitForSelector('label:has-text("Clareza")', {timeout: 15000})
  await page.getByLabel('Clareza').fill('8')
  await page.getByLabel('Impacto').fill('9')
  await page.getByLabel('Comentário geral').fill('Ótimo trabalho.')
  await page.getByRole('button',{name:'Enviar notas'}).click()
  await expect(page.getByText('Média do grupo: 8.50.')).toBeVisible()
  await page.getByRole('button',{name:'Concluir avaliação'}).click()
  await expect(page.getByText('Avaliação concluída e grupo notificado.')).toBeVisible()
})
