import {test,expect,type Page} from '@playwright/test'

const API=process.env.ACERVO_LIVE_API??''
const PASSWORD=process.env.E2E_TEST_PASSWORD??''

async function login(page:Page,actor:string){
  const csrf=(await(await page.request.get(API+'/auth/csrf/')).json()).csrfToken
  const response=await page.request.post(API+'/auth/login/',{headers:{'X-CSRFToken':csrf},data:{identifier:`live-${actor}`,password:PASSWORD}})
  expect(response.status(),'Login real com CSRF').toBe(200)
}

for(const corrected of [false,true])test(`UI + API + PostgreSQL: ${corrected?'correção':'aprovação direta'}`,async({page},testInfo)=>{
  expect(API).toBe('http://127.0.0.1:8002/api/v1')
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  page.on('dialog',dialog=>dialog.accept())
  // Encaminha para servidor real isolado; não simula respostas nem persistência.
  await page.route('**/api/v1/**',async route=>{
    const original=new URL(route.request().url())
    const response=await route.fetch({url:API+original.pathname.replace('/api/v1','')+original.search})
    await route.fulfill({response})
  })
  await login(page,'evaluator')
  const queue=await(await page.request.get(API+'/projects/publication-workflow/')).json() as {id:string;name:string}[]
  const project=queue.find(item=>item.name===`Acervo Integrado ${testInfo.project.name}-${corrected?'corrected':'direct'}`)
  expect(project).toBeTruthy()
  const projectId=project!.id
  await page.goto('/#/showcase-presence')
  const card=page.getByRole('article',{name:`Presença de ${project!.name}`})
  await card.getByRole('checkbox').check()
  await card.getByRole('button',{name:'Confirmar presença'}).click()
  await card.getByLabel('Nota (0 a 10)').fill('8.75')
  await card.getByLabel('Observações').fill('Resultado da Mostra para o orientador.')
  await card.getByRole('button',{name:'Salvar avaliação'}).click()
  await expect(card.getByText('Avaliação concluída · Nota: 8.75')).toBeVisible()
  await login(page,'advisor')
  await page.goto(`/#/publication/${projectId}`)
  await page.reload()
  await expect(page.getByText(/Nota: 8.75 · Concluída/)).toBeVisible()
  await expect(page.getByText('Resultado da Mostra para o orientador.')).toBeVisible()
  await login(page,'leader')
  await page.reload()
  await page.getByLabel('Resumo',{exact:true}).fill('Resumo com educação e extensão.')
  await page.getByLabel('Descrição do projeto',{exact:true}).fill('Texto original do líder.')
  await page.getByRole('checkbox').check()
  await page.getByRole('button',{name:'Gerar PDF e enviar ao orientador'}).click()
  await expect(page.getByText('Aguardando revisão do orientador',{exact:true})).toBeVisible()
  await login(page,'advisor');await page.reload()
  if(corrected){
    await page.getByRole('button',{name:'Revisar texto'}).click()
    await page.getByLabel('Descrição do projeto',{exact:true}).fill('Texto corrigido pelo orientador com inclusão.')
    await page.getByRole('button',{name:'Enviar correção ao líder'}).click()
    await expect(page.getByText('Aguardando validação do líder',{exact:true})).toBeVisible()
    await login(page,'leader');await page.reload()
    await expect(page.getByText('Texto corrigido pelo orientador com inclusão.',{exact:true})).toBeVisible()
    await page.getByRole('button',{name:'Validar correção e encaminhar à Secretaria'}).click()
  }else await page.getByRole('button',{name:'Aprovar sem alterações'}).click()
  await expect(page.getByText('Aguardando confirmação da Secretaria',{exact:true})).toBeVisible()
  await login(page,'secretary');await page.reload()
  await page.getByRole('button',{name:'Confirmar publicação no acervo'}).click()
  await expect(page.getByText('Publicação confirmada pela Secretaria.')).toBeVisible()
  const flow=await(await page.request.get(`${API}/projects/${projectId}/publication-workflow/`)).json()
  expect(flow.state).toBe('PUBLISHED')
  expect(flow.versions).toHaveLength(corrected?2:1)
  const document=await page.request.get(`${API}/projects/publication-documents/${flow.versions[0].id}/download/`)
  expect(document.status()).toBe(200)
  expect((await document.body()).subarray(0,5).toString()).toBe('%PDF-')
  await page.goto('/#/archive')
  await expect(page.getByRole('heading',{name:project!.name,exact:true})).toBeVisible()
  await page.screenshot({path:`../.runtime/acervo-live-${testInfo.project.name}-${corrected?'corrected':'direct'}.png`,fullPage:true})
  expect(errors).toEqual([])
})
