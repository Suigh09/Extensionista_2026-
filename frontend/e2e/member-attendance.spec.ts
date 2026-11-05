import {test,expect} from '@playwright/test'

test('presença parcial abre nota, recupera erro e mantém avaliação após recarga',async({page},testInfo)=>{
  const errors:string[]=[]
  page.on('pageerror',error=>errors.push(error.message))
  let gradeAttempts=0
  const entry={id:'entry',group:'group',group_name:'Grupo Ambiental',project_id:'project',project_name:'Projeto Educação Ambiental',date:'2026-12-10T14:00:00Z',location:'Sala 1',status:'SCHEDULED',is_evaluator:true,members:[{member_id:11,name:'Ana',ra:'RA4001',present:null as boolean|null},{member_id:12,name:'Bruno',ra:'RA4002',present:null as boolean|null}],evaluation:null as {value:string;observations:string;concluded:boolean}|null}
  await page.route('**/api/v1/**',async route=>{
    const path=new URL(route.request().url()).pathname
    if(path.endsWith('/auth/session/'))return route.fulfill({json:{id:'evaluator',username:'avaliador',name:'Avaliador',role:'PROFESSOR',profile:{registration:'E1'}}})
    if(path.endsWith('/auth/csrf/'))return route.fulfill({json:{csrfToken:'test-csrf'}})
    if(path.endsWith('/showcase/'))return route.fulfill({json:[entry]})
    if(path.endsWith('/member-attendance/')){
      expect(route.request().postDataJSON()).toEqual([{member_id:11,present:true},{member_id:12,present:false}])
      entry.status='PRESENTED';entry.members[0].present=true;entry.members[1].present=false
      return route.fulfill({json:entry})
    }
    if(path.endsWith('/evaluation/')){
      gradeAttempts++
      if(gradeAttempts===1)return route.fulfill({status:400,json:{detail:'Falha temporária. Tente novamente.'}})
      expect(route.request().postDataJSON()).toEqual({value:'8.75',observations:'Apresentação clara.'})
      entry.evaluation={value:'8.75',observations:'Apresentação clara.',concluded:true}
      return route.fulfill({json:entry})
    }
    return route.fulfill({json:[]})
  })
  await page.goto('/#/showcase-presence')
  await page.getByRole('checkbox',{name:'Ana · RA4001'}).check()
  await page.getByRole('button',{name:'Confirmar presença'}).click()
  await expect(page.getByLabel('Nota (0 a 10)')).toBeFocused()
  await expect(page.getByRole('checkbox',{name:'Bruno · RA4002'})).not.toBeChecked()
  await page.getByLabel('Nota (0 a 10)').fill('8.75')
  await page.getByLabel('Observações').fill('Apresentação clara.')
  await expect(page.getByRole('form',{name:'Avaliação do grupo'})).toBeVisible()
  await page.screenshot({path:`../.runtime/member-attendance-${testInfo.project.name}.png`,fullPage:true})
  await page.getByRole('button',{name:'Salvar avaliação'}).click()
  await expect(page.getByRole('alert')).toContainText('Falha temporária')
  await expect(page.getByLabel('Nota (0 a 10)')).toHaveValue('8.75')
  await page.getByRole('button',{name:'Salvar avaliação'}).click()
  await expect(page.getByText('Avaliação concluída · Nota: 8.75')).toBeVisible()
  await page.reload()
  await expect(page.getByText('Avaliação concluída · Nota: 8.75')).toBeVisible()
  await expect(page.getByRole('button',{name:'Confirmar presença'})).toHaveCount(0)
  expect(errors).toEqual([])
})
