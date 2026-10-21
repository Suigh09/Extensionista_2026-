import{cleanup,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,describe,expect,it,vi}from'vitest'
import{listNotifications,markAllNotificationsRead,markNotificationRead}from'./api'
import type{NotificationItem}from'./api'
import{NotificationBell}from'./notifications'

vi.mock('./api',()=>({listNotifications:vi.fn(),markNotificationRead:vi.fn(),markAllNotificationsRead:vi.fn()}))

const listMock=vi.mocked(listNotifications)
const readMock=vi.mocked(markNotificationRead)
const readAllMock=vi.mocked(markAllNotificationsRead)

afterEach(()=>{cleanup();vi.clearAllMocks()})

function item(overrides:Partial<NotificationItem>={}):NotificationItem{
  return{id:'note-1',kind:'GROUP_INVITATION',title:'Convite para Projeto X',body:'Você foi convidado.',project:'project-1',project_name:'Projeto X',is_read:false,read_at:null,created_at:'2026-09-27T12:00:00Z',...overrides}
}

describe('sino de notificações',()=>{
  it('exibe contagem de não lidas e abre o projeto ao clicar',async()=>{
    listMock.mockResolvedValue([item(),item({id:'note-2',title:'Sala atualizada',is_read:true})])
    readMock.mockResolvedValue(item({is_read:true}))
    const seen:string[]=[]
    const listener=(event:Event)=>{seen.push((event as CustomEvent<string>).detail)}
    window.addEventListener('platform:navigate',listener)
    try{
      const user=userEvent.setup();render(<NotificationBell/>)
      expect(await screen.findByRole('button',{name:'Notificações, 1 não lidas'})).toBeInTheDocument()
      await user.click(screen.getByRole('button',{name:'Notificações, 1 não lidas'}))
      expect(await screen.findByRole('button',{name:/Convite para Projeto X/})).toBeInTheDocument()
      await user.click(screen.getByRole('button',{name:/Convite para Projeto X/}))
      expect(readMock).toHaveBeenCalledWith('note-1')
      expect(seen).toContain('#/projects/project-1')
    }finally{
      window.removeEventListener('platform:navigate',listener)
    }
  })

  it('marca todas como lidas',async()=>{
    listMock.mockResolvedValue([item()])
    readAllMock.mockResolvedValue(undefined)
    const user=userEvent.setup();render(<NotificationBell/>)
    await user.click(await screen.findByRole('button',{name:/Notificações/}))
    await user.click(await screen.findByRole('button',{name:'Marcar todas como lidas'}))
    expect(readAllMock).toHaveBeenCalled()
  })

  it('mostra vazio sem notificações',async()=>{
    listMock.mockResolvedValue([])
    const user=userEvent.setup();render(<NotificationBell/>)
    await user.click(await screen.findByRole('button',{name:'Notificações'}))
    expect(await screen.findByText('Nenhuma notificação.')).toBeInTheDocument()
  })
})
