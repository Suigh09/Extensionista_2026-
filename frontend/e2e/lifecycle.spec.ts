import{expect,test,type APIRequestContext}from'@playwright/test'

// Fluxos 4.9/4.10 contra backend real (sqlite local de desenvolvimento).
// Requer backend em 127.0.0.1:8000 com sala, tema e o aluno smoke2.
// O isolamento entre execuções é feito via API: antes e depois do cenário,
// cancela-se qualquer projeto vigente do usuário (pedido + aprovação).

const API=process.env.E2E_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
// Senha dos usuários de teste via ambiente (nunca versionada).
const TEST_PASSWORD=process.env.E2E_TEST_PASSWORD ?? ''
const STUDENT={identifier:'RA3001',password:TEST_PASSWORD}
const SECRETARIAT={identifier:'secretaria.teste',password:TEST_PASSWORD}
function requirePassword(){
  if(!TEST_PASSWORD)throw new Error('Defina E2E_TEST_PASSWORD com a senha dos usuários de teste locais.')
}

type ProjectSummary={id:string;status:string}

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

async function activeProjects(request:APIRequestContext){
  const list=await(await request.get(`${API}/projects/?q=`)).json()
  return (list as ProjectSummary[]).filter(p=>!['COMPLETED','ARCHIVED','CANCELLED'].includes(p.status))
}

async function backendAvailable(request:APIRequestContext){
  try{
    const health=await request.get(`${API}/health/`,{timeout:5000})
    return health.ok()
  }catch{
    return false
  }
}
async function cancelAllActive(request:APIRequestContext){
  const token=await apiLogin(request,STUDENT.identifier,STUDENT.password)
  const projects=await activeProjects(request)
  if(projects.length===0)return
  for(const project of projects){
    const req=await request.post(`${API}/projects/${project.id}/lifecycle/`,{headers:{'X-CSRFToken':token},data:{action:'request-cancellation',reason:'Limpeza E2E'}})
    const body=await req.text()
    if(!req.ok()&&!body.includes('pendente'))throw new Error(`E2E solicitar cancelamento falhou: ${req.status()}`)
  }
  const secToken=await apiLogin(request,SECRETARIAT.identifier,SECRETARIAT.password)
  for(const project of projects){
    const dec=await request.post(`${API}/projects/${project.id}/lifecycle/`,{headers:{'X-CSRFToken':secToken},data:{action:'approve-cancellation',reason:'Limpeza E2E'}})
    if(!dec.ok())throw new Error(`E2E aprovar cancelamento falhou: ${dec.status()}`)
  }
}

test.describe.configure({mode:'serial'})

test.beforeEach(async({request})=>{
  if(!await backendAvailable(request))test.skip(true,'backend de desenvolvimento indisponível')
  requirePassword()
  await cancelAllActive(request)
})
test.afterEach(async({request})=>{
  if(await backendAvailable(request))await cancelAllActive(request)
})

test('aluno cria projeto por tema e pausa o ciclo de vida',async({page})=>{
  await page.goto('/')
  await page.getByLabel('CPF, RA ou usuário').fill(STUDENT.identifier)
  await page.getByLabel('Senha',{exact:true}).fill(STUDENT.password)
  await page.getByRole('button',{name:'Entrar'}).click()
  await expect(page.getByRole('heading',{name:'Início'})).toBeVisible()
  await page.getByRole('button',{name:'Projetos'}).first().click()
  await expect(page.getByRole('heading',{name:'Meus projetos'})).toBeVisible()
  await page.getByRole('button',{name:'+ Criar projeto'}).click()
  const theme=page.getByLabel('Tema do projeto')
  await expect.poll(async()=>theme.locator('option').count(),{timeout:10000}).toBeGreaterThan(1)
  await theme.selectOption({index:1})
  await page.getByLabel('Título do projeto').fill('Projeto E2E Ciclo')
  await page.getByLabel('Sobre o projeto').fill('Proposta validada de ponta a ponta.')
  await page.getByRole('button',{name:'Criar projeto'}).click()
  await expect(page.getByRole('heading',{name:'Projeto E2E Ciclo'})).toBeVisible()
  await expect(page.getByText('Forme seu grupo antes de enviar')).toBeVisible()
  await page.getByRole('button',{name:'Pausar projeto'}).click()
  await expect(page.getByRole('heading',{name:'Pausar projeto?'})).toBeVisible()
  await page.getByLabel('Motivo ou justificativa').fill('Pausa validada no E2E')
  await page.getByRole('button',{name:'Confirmar'}).click()
  await expect(page.getByText(/A retomada retorna para Rascunho/)).toBeVisible()
})
