import{expect,test,type APIRequestContext}from'@playwright/test'

// Sprint 7 contra backend real: GF-09 publicação válida; GF-10 bloqueio de publicação inválida.
// Pula sem backend (CI). Requer E2E_TEST_PASSWORD.

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

async function csrf(request:APIRequestContext){
  return (await(await request.get(`${API}/auth/csrf/`)).json()).csrfToken
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
    if(!dec.ok())throw new Error(`E2E aprovar cancelamento falhou: ${dec.status()} ${await dec.text()}`)
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
  const submitted=await request.post(`${API}/projects/${project.id}/submit/`,{headers:{'X-CSRFToken':await csrf(request)},data:{}})
  if(!submitted.ok())throw new Error(`E2E submeter projeto falhou: ${submitted.status()} ${(await submitted.text()).slice(0,200)}`)
  const profToken=await apiLogin(request,ORIENTADOR.identifier,ORIENTADOR.password)
  const approved=await request.post(`${API}/projects/${project.id}/approve/`,{headers:{'X-CSRFToken':await csrf(request)},data:{feedback:''}})
  if(!approved.ok())throw new Error(`E2E aprovar projeto falhou: ${approved.status()} ${(await approved.text()).slice(0,200)}`)
  return project.id as string
}

async function createApprovedDocument(request:APIRequestContext,projectId:string){
  const docData=new FormData()
  docData.append('pdf',new Blob([Buffer.from('%PDF-1.4 documento e2e')],{type:'application/pdf'}),'documento.pdf')
  docData.append('consent_given','true')
  const docResp=await request.post(`${API}/projects/${project.id}/publication-documents/`,{headers:{'X-CSRFToken':await csrf(request)},body:docData})
  if(!docResp.ok())throw new Error(`E2E gerar documento falhou: ${docResp.status()} ${(await docResp.text()).slice(0,200)}`)
  const doc=await docResp.json() as {id:string}
  const profToken=await apiLogin(request,ORIENTADOR.identifier,ORIENTADOR.password)
  const docApproved=await request.post(`${API}/projects/publication-documents/${doc.id}/review/`,{headers:{'X-CSRFToken':await csrf(request)},body:JSON.stringify({status:'APPROVED',review:'Aprovado para acervo E2E'})})
  if(!docApproved.ok())throw new Error(`E2E aprovar documento falhou: ${docApproved.status()} ${(await docApproved.text()).slice(0,200)}`)
  return doc.id
}

test.describe.configure({mode:'serial'})

test.beforeEach(async({request},testInfo)=>{
  if(testInfo.project.name!=='desktop')test.skip(true,'acervo mobile na Sprint 6')
  if(!await backendAvailable(request))test.skip(true,'backend de desenvolvimento indisponível')
  requirePassword()
  await cancelActive(request,ALUNO.identifier)
})

test('GF-09: publicacao valida do aluno no acervo',async({request})=>{
  test.slow()
  const projectId=await prepareApprovedProject(request)
  void projectId
  const studentToken=await apiLogin(request,ALUNO.identifier,ALUNO.password)
  await createApprovedDocument(request,projectId,studentToken)
  const publishResp=await request.post(`${API}/projects/publications/`,{headers:{'X-CSRFToken':await csrf(request)},body:JSON.stringify({project:projectId,document:''}}))
  if(!publishResp.ok())throw new Error(`E2E publicar falhou: ${publishResp.status()} ${(await publishResp.text()).slice(0,200)}`)
  const pubs=await(await request.get(`${API}/projects/publications/`,{headers:{'X-CSRFToken':await csrf(request)}})).json() as any[]
  const found=pubs.find(p=>p.project===projectId)
  if(!found)throw new Error('E2E publicação não encontrada no acervo')
  if(!found.is_published)throw new Error('E2E publicação não está publicada')
})

test('GF-10: bloqueio de publicacao invalida',async({request})=>{
  test.slow()
  const projectId=await prepareApprovedProject(request)
  void projectId
  const studentToken=await apiLogin(request,ALUNO.identifier,ALUNO.password)
  const publishResp=await request.post(`${API}/projects/publications/`,{headers:{'X-CSRFToken':await csrf(request)},body:JSON.stringify({project:projectId,document:''})})
  if(publishResp.ok())throw new Error('E2E publicação inválida não foi bloqueada')
  const body=await publishResp.text()
  if(!/aprovado/i.test(body))throw new Error(`E2E mensagem de erro inesperada: ${body}`)
})
