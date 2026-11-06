import {test,expect} from '@playwright/test'

for(const correction of [false,true])test(`acervo completo: ${correction?'correção e aceite do líder':'aprovação direta'}`,async({page},testInfo)=>{
  let actor='leader',state='NOT_STARTED',writes=0
  const versions:Record<string,unknown>[]=[]
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  page.on('dialog',dialog=>dialog.accept())
  function data(){return {project:'project',project_name:'Projeto Ambiental',number:2,state,blockers:[],snapshot:{project_id:'project',project_name:'Projeto Ambiental',year:2026,advisors:['Orientador'],members:[{name:'Ana',course:'Computação'},{name:'Bia',course:'Computação'}]},permissions:{leader:actor==='leader',advisor:actor==='advisor',admin:actor==='secretary'},versions,publication:state==='PUBLISHED'?'pub':null,results:[{group:'group',name:'Grupo A',grade:'8.75',concluded:true,observations:'Trabalho consistente.',members:[{name:'Ana',ra:'RA4001',present:true},{name:'Bia',ra:'RA4002',present:false}]}]}}
  await page.route('**/api/v1/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/auth/session/'))return route.fulfill({json:{id:actor,username:actor,name:actor==='leader'?'Ana':actor==='advisor'?'Orientador':'Administrador',role:actor==='leader'?'STUDENT':actor==='advisor'?'PROFESSOR':'ADMIN',profile:{}}})
    if(path.endsWith('/auth/csrf/'))return route.fulfill({json:{csrfToken:'test-csrf'}})
    if(path.endsWith('/publication-workflow/')){
      if(route.request().method()==='POST'){
        const payload=route.request().postDataJSON();writes++
        if(payload.action==='submit'){
          expect(actor).toBe('leader');expect(payload.expected_document).toBeNull();expect(payload.consent).toBe(true)
          state='ADVISOR';versions.unshift({id:'v1',version:1,title:payload.title,abstract:payload.abstract,content:payload.content,workflow:state,generated_by_name:'Ana',created_at:'2026-11-05T12:00:00Z',pdf_sha256:'hash-v1'})
        }else if(payload.action==='correct'){
          expect(actor).toBe('advisor');expect(payload.expected_document).toBe('v1')
          state='LEADER';versions.unshift({...versions[0],id:'v2',version:2,content:payload.content,workflow:state,generated_by_name:'Orientador',pdf_sha256:'hash-v2'})
        }else if(payload.action==='approve'){
          expect(actor).toBe('advisor');expect(payload.expected_document).toBe('v1');state='ADMIN';versions[0].workflow=state
        }else if(payload.action==='accept'){
          expect(actor).toBe('leader');expect(payload.expected_document).toBe('v2');state='ADMIN';versions[0].workflow=state
        }else if(payload.action==='publish'){
          expect(actor).toBe('secretary');expect(state).toBe('ADMIN');expect(payload.expected_document).toBe(correction?'v2':'v1');state='PUBLISHED';versions[0].workflow=state
        }else throw new Error('Ação inesperada')
      }
      return route.fulfill({json:data()})
    }
    return route.fulfill({json:[]})
  })
  await page.goto('/#/publication/project')
  await expect(page.getByText('Bia · RA4002 — Ausente')).toBeVisible()
  await page.getByLabel('Resumo',{exact:true}).fill('Resumo de extensão.')
  await page.getByLabel('Descrição do projeto',{exact:true}).fill('Texto escrito pelo líder.')
  await page.getByRole('checkbox').check()
  await page.getByRole('button',{name:'Gerar PDF e enviar ao orientador'}).click()
  await expect(page.getByText('Aguardando revisão do orientador',{exact:true})).toBeVisible()
  await expect(page.getByRole('button',{name:'Confirmar publicação no acervo'})).toHaveCount(0)
  actor='advisor';await page.reload()
  if(correction){
    await page.getByRole('button',{name:'Revisar texto'}).click()
    await page.getByLabel('Descrição do projeto',{exact:true}).fill('Texto corrigido pelo orientador.')
    await page.getByRole('button',{name:'Enviar correção ao líder'}).click()
    await expect(page.getByText('Aguardando validação do líder',{exact:true})).toBeVisible()
    actor='leader';await page.reload()
    await expect(page.getByText('Texto escrito pelo líder.',{exact:true})).toHaveCount(1)
    await page.getByRole('button',{name:'Validar correção e encaminhar ao Administrador'}).click()
  }else await page.getByRole('button',{name:'Aprovar sem alterações'}).click()
  await expect(page.getByText('Aguardando confirmação do Administrador',{exact:true})).toBeVisible()
  actor='secretary';await page.reload()
  await expect(page.getByRole('link',{name:`Baixar PDF da versão ${correction?2:1}`})).toBeVisible()
  await page.screenshot({path:`../.runtime/acervo-${correction?'corrected':'direct'}-${testInfo.project.name}.png`,fullPage:true})
  await page.getByRole('button',{name:'Confirmar publicação no acervo'}).click()
  await expect(page.getByText('Publicação confirmada pelo Administrador.')).toBeVisible()
  await page.reload()
  await expect(page.getByText('Publicado no acervo',{exact:true})).toBeVisible()
  expect(writes).toBe(correction?4:3)
  expect(errors).toEqual([])
})
