import {test,expect} from '@playwright/test'

test('alocação automática preserva pendência e permite escolha individual',async({page},testInfo)=>{
  const entries=[
    {id:'e1',group:'g1',project_name:'Projeto Escola',number:1,date:'2026-12-10T09:00:00-03:00',end_date:'2026-12-10T09:30:00-03:00',day:'day',room:'room',location:'Prédio A / Sala 1',status:'SCHEDULED',updated_at:'2026-11-05T12:00:00Z',evaluator_id:null as string|null,evaluator_name:null as string|null},
    {id:'e2',group:'g2',project_name:'Projeto Horta',number:2,date:'2026-12-10T10:00:00-03:00',end_date:'2026-12-10T10:30:00-03:00',day:'day',room:'room',location:'Prédio A / Sala 1',status:'SCHEDULED',updated_at:'2026-11-05T12:00:00Z',evaluator_id:null as string|null,evaluator_name:null as string|null},
  ]
  let assignments=0
  const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message))
  page.on('dialog',dialog=>dialog.accept())
  await page.route('**/api/v1/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/auth/session/'))return route.fulfill({json:{id:'secretary',username:'secretaria.teste',role:'SECRETARIAT',name:'Secretaria',profile:null}})
    if(path.endsWith('/auth/csrf/'))return route.fulfill({json:{csrfToken:'test-csrf'}})
    if(path.endsWith('/allocate-evaluators/')){
      expect(route.request().postDataJSON()).toEqual({day:'day',room:'room'})
      entries[0].evaluator_id='1';entries[0].evaluator_name='Ana'
      return route.fulfill({json:{allocated:[{group:'g1',name:'Ana'}],preserved:[],pending:[{group:'g2',project_name:'Projeto Horta',reason:'Sem aderência: escolha manualmente.'}]}})
    }
    if(path.endsWith('/groups/g2/evaluator-options/'))return route.fulfill({json:{group:'g2',current:null,current_name:null,keywords:['horta'],locked:false,recommendations:[{professor_profile_id:'2',name:'Rui',match_count:0,matched:{},load:0,available:true,unavailable_reason:'',requires_justification:true}]}})
    if(path.endsWith('/groups/g2/designate-evaluator/')){
      expect(route.request().postDataJSON()).toEqual({professor:'2',justification:'Rodízio autorizado.'})
      entries[1].evaluator_id='2';entries[1].evaluator_name='Rui';assignments++
      return route.fulfill({status:201,json:{id:'assignment'}})
    }
    if(path.includes('/showcase-planning/'))return route.fulfill({json:{buildings:[{id:'building',number:1,code:'A',name:'Prédio A'}],rooms:[{id:'room',building:'building',number:1,name:'Sala 1'}],days:[{id:'day',date:'2026-12-10',start_time:'09:00:00',end_time:'11:00:00'}],groups:[],entries}})
    return route.fulfill({json:[]})
  })
  await page.goto('/#/showcase')
  await page.getByRole('button',{name:'Alocar avaliadores automaticamente'}).click()
  await expect(page.getByRole('status',{name:'Resultado da alocação'})).toContainText('1 alocado(s) · 0 preservado(s) · 1 pendente(s)')
  await expect(page.getByTestId('booking-e1')).toContainText('Avaliador: Ana')
  await page.getByRole('button',{name:'Escolher avaliador de Projeto Horta'}).click()
  await page.getByLabel('Avaliador do grupo').selectOption('2')
  await expect(page.getByLabel('Justificativa da escolha')).toHaveAttribute('required','')
  await page.getByLabel('Justificativa da escolha').fill('Rodízio autorizado.')
  await page.getByRole('button',{name:'Alocar avaliador',exact:true}).click()
  await expect(page.getByTestId('booking-e2')).toContainText('Avaliador: Rui')
  expect(assignments).toBe(1)
  await page.reload()
  await expect(page.getByTestId('booking-e2')).toContainText('Avaliador: Rui')
  expect(errors).toEqual([])
  await expect(page.locator('.showcase-planning')).toHaveCSS('opacity','1')
  await page.screenshot({path:`../.runtime/evaluators-${testInfo.project.name}.png`,fullPage:true})
})

test('agenda única: drag, resize, persistência e busca por integrante',async({page},testInfo)=>{
  if(testInfo.project.name==='desktop')await page.setViewportSize({width:1280,height:1000})
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  const data={
    buildings:[{id:'building',number:1,code:'A',name:'Prédio A'}],
    rooms:[{id:'room',building:'building',number:1,name:'Sala 1'}],
    days:[{id:'day',date:'2026-12-10',start_time:'08:00:00',end_time:'12:00:00'}],
    groups:[{id:'group',name:'Grupo Escola',project:'project',number:1,eligible:true,project_name:'Extensão na Escola',members:['Maria Silva','João Santos'],entry:null as Record<string,unknown>|null}],
    entries:[] as Record<string,unknown>[],
  }
  const writes:Record<string,string>[]=[]
  await page.route('**/api/v1/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/auth/session/'))return route.fulfill({json:{id:'secretary',username:'secretaria.teste',name:'Secretaria Teste',role:'SECRETARIAT',profile:null}})
    if(path.endsWith('/auth/csrf/'))return route.fulfill({json:{csrfToken:'test-csrf'}})
    if(path.includes('/showcase-planning/')){
      if(route.request().method()==='POST'){
        const payload=route.request().postDataJSON();writes.push(payload)
        const entry={id:'entry',group:'group',project_name:'Extensão na Escola',number:1,day:'day',room:'room',status:'SCHEDULED',location:'Prédio A / Sala 1',date:`2026-12-10T${payload.start_time}:00-03:00`,end_date:`2026-12-10T${payload.end_time}:00-03:00`,updated_at:new Date().toISOString()}
        data.groups[0].entry=entry;data.entries=[entry]
        return route.fulfill({json:entry})
      }
      return route.fulfill({json:data})
    }
    return route.fulfill({json:[]})
  })
  await page.goto('/#/showcase')
  await expect(page.getByLabel('Data da Mostra')).toHaveCount(1)
  await expect(page.getByRole('button',{name:'Agendamento da Mostra',exact:true})).toHaveCount(0)
  await expect(page.getByText('#1 · Extensão na Escola',{exact:true})).toBeVisible()
  if(testInfo.project.name==='desktop'){
    await page.locator('.planning-group').dragTo(page.locator('.planning-slot').nth(2),{sourcePosition:{x:20,y:12},targetPosition:{x:100,y:12}})
  }else{
    await page.getByRole('button',{name:'Selecionar para agendar'}).click()
    await page.getByRole('button',{name:'Agendar grupo selecionado às 09:00'}).click()
  }
  await expect.poll(()=>writes.length).toBe(1)
  await expect(page.getByTestId('booking-entry')).toContainText('09:00–09:30')
  if(testInfo.project.name==='desktop'){
    const handle=page.getByRole('button',{name:'Redimensionar duração de Extensão na Escola'})
    await handle.scrollIntoViewIfNeeded()
    const box=await handle.boundingBox();expect(box).not.toBeNull()
    await page.mouse.move(box!.x+box!.width/2,box!.y+box!.height/2)
    await page.mouse.down()
    await page.mouse.move(box!.x+box!.width/2,box!.y+box!.height/2+112,{steps:8})
    await page.mouse.up()
  }else{
    await page.getByRole('button',{name:'Aumentar duração de Extensão na Escola'}).click()
  }
  await expect.poll(()=>writes.length).toBe(2)
  expect(writes[1].expected_updated_at).toBeTruthy()
  await expect(page.getByTestId('booking-entry')).toContainText('09:00–10:00')
  await page.reload()
  await expect(page.getByTestId('booking-entry')).toContainText('09:00–10:00')
  if(testInfo.project.name==='desktop'){
    const handle=page.getByRole('button',{name:'Redimensionar duração de Extensão na Escola'})
    await handle.scrollIntoViewIfNeeded()
    const box=await handle.boundingBox();expect(box).not.toBeNull()
    await page.mouse.move(box!.x+box!.width/2,box!.y+box!.height/2)
    await page.mouse.down()
    await page.mouse.move(box!.x+box!.width/2,box!.y+box!.height/2-112,{steps:8})
    await page.mouse.up()
  }else{
    await page.getByRole('button',{name:'Diminuir duração de Extensão na Escola'}).click()
  }
  await expect.poll(()=>writes.length).toBe(3)
  await expect(page.getByTestId('booking-entry')).toContainText('09:00–09:30')
  if(testInfo.project.name==='desktop'){
    await page.getByTestId('booking-entry').dragTo(page.locator('.planning-slot').nth(6),{sourcePosition:{x:20,y:12},targetPosition:{x:100,y:12}})
    await expect.poll(()=>writes.length).toBe(4)
    await expect(page.getByTestId('booking-entry')).toContainText('11:00–11:30')
  }
  await page.getByLabel('Buscar projeto, integrante ou ID').fill('Maria')
  await expect(page.getByLabel('Buscar projeto, integrante ou ID')).toHaveValue('Maria')
  await page.getByRole('button',{name:'Pesquisar',exact:true}).click()
  await expect(page.getByRole('region',{name:'Resultados da busca'})).toContainText('Maria Silva')
  await page.getByRole('button',{name:'Localizar na agenda'}).click()
  await page.screenshot({path:`../.runtime/planning-${testInfo.project.name}.png`,fullPage:true})
  expect(errors).toEqual([])
})

test('notificação de encaminhamento abre o projeto e acervo não duplica',async({page})=>{
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  await page.route('**/api/v1/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/auth/session/'))return route.fulfill({json:{id:'secretary',username:'secretaria.teste',name:'Secretaria Teste',role:'SECRETARIAT',profile:null}})
    if(path.endsWith('/auth/csrf/'))return route.fulfill({json:{csrfToken:'test-csrf'}})
    if(path.endsWith('/notifications/'))return route.fulfill({json:[{id:'note',title:'Encaminhamento recebido',body:'Projeto recebido da orientação',project:'project',kind:'PROJECT_FORWARDED',is_read:false,created_at:'2026-11-05T12:00:00Z'}]})
    if(path.endsWith('/projects/project/'))return route.fulfill({json:{id:'project',number:1,name:'Projeto encaminhado',about:'Proposta de extensão',status:'APPROVED',groups:[],group:{id:'group',member_count:2,members:[],formation_status:'FORMED'},is_active:true,can_manage:false}})
    if(path.endsWith('/evaluator-recommendations/'))return route.fulfill({json:{keywords:[],recommendations:[],groups:[],history:[]}})
    return route.fulfill({json:[]})
  })
  await page.goto('/#/archive')
  await expect(page.getByRole('heading',{name:'Acervo de projetos publicados'})).toHaveCount(1)
  await expect(page.getByRole('button',{name:'Pesquisar',exact:true})).toHaveCount(1)
  await page.getByRole('button',{name:/Notificações, 1 não lidas/}).filter({visible:true}).click()
  await page.getByRole('button',{name:/Encaminhamento recebido/}).click()
  await expect(page).toHaveURL(/#\/projects\/project$/)
  await expect(page.getByRole('heading',{name:'Projeto encaminhado',exact:true})).toBeVisible()
  expect(errors).toEqual([])
})
