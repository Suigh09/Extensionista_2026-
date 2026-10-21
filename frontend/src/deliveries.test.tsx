import{cleanup,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,describe,expect,it,vi}from'vitest'
import{forwardProject,getForwarding,listDeliveries,listForwarded,reviewDelivery,submitDelivery}from'./api'
import type{Delivery,Forwarding,Profile,Project}from'./api'
import{DeliveriesPanel,ForwardedQueue}from'./deliveries'

vi.mock('./api',()=>({listDeliveries:vi.fn(),submitDelivery:vi.fn(),reviewDelivery:vi.fn(),getForwarding:vi.fn(),forwardProject:vi.fn(),listForwarded:vi.fn(),deliveryDownloadUrl:(path:string)=>`http://teste${path}`}))

const listDeliveriesMock=vi.mocked(listDeliveries)
const submitDeliveryMock=vi.mocked(submitDelivery)
const reviewDeliveryMock=vi.mocked(reviewDelivery)
const getForwardingMock=vi.mocked(getForwarding)
const forwardProjectMock=vi.mocked(forwardProject)
const listForwardedMock=vi.mocked(listForwarded)

afterEach(()=>{cleanup();vi.clearAllMocks()})

const student={id:'1',username:'aluno',name:'Aluno Teste',email:'',role:'STUDENT',profile:{ra:'RA1'}}as Profile
const professor={id:'p1',username:'professor',name:'Professor Teste',email:'',role:'PROFESSOR',profile:{registration:'P1'}}as Profile
const project={id:'project-1',name:'Projeto',about:'Sobre',status:'APPROVED',can_manage:true}as Project

function delivery(overrides:Partial<Delivery>={}):Delivery{
  return{id:'delivery-1',project:'project-1',group:'group-1',group_name:'Grupo principal',version:1,title_snapshot:'Projeto',about_snapshot:'Sobre',notes:'',original_name:'entrega.pdf',content_type:'application/pdf',size:1024,status:'SUBMITTED',submitted_by_name:'Aluno Teste',submitted_at:'2026-09-25T12:00:00Z',review_feedback:'',reviewed_by_name:null,reviewed_at:null,download_url:'/projects/deliveries/delivery-1/download/',...overrides}
}

describe('painel de entregas',()=>{
  it('estudante envia entrega com documento',async()=>{
    listDeliveriesMock.mockResolvedValue([])
    getForwardingMock.mockRejectedValue(new Error('sem encaminhamento'))
    submitDeliveryMock.mockResolvedValue(delivery())
    listDeliveriesMock.mockResolvedValueOnce([]).mockResolvedValueOnce([delivery()])
    const user=userEvent.setup();render(<DeliveriesPanel project={project} user={student}/>)
    expect(await screen.findByText('Nenhuma entrega enviada.')).toBeInTheDocument()
    await user.click(screen.getByText('Nova entrega'))
    const file=new File(['%PDF-1.4 teste'],'entrega.pdf',{type:'application/pdf'})
    await user.upload(screen.getByLabelText(/Documento da entrega/),file)
    await user.type(screen.getByLabelText('Observações da versão'),'Primeira versão')
    await user.click(screen.getByRole('button',{name:'Enviar entrega'}))
    expect(submitDeliveryMock).toHaveBeenCalled()
    const sent=submittedForm()
    expect(sent.get('notes')).toBe('Primeira versão')
    expect(sent.has('document')).toBe(true)
    expect(await screen.findByText('Entrega enviada ao orientador.')).toBeInTheDocument()
  })

  it('exige documento com mensagem explícita',async()=>{
    listDeliveriesMock.mockResolvedValue([])
    getForwardingMock.mockRejectedValue(new Error('sem encaminhamento'))
    const user=userEvent.setup();render(<DeliveriesPanel project={project} user={student}/>)
    await user.click(await screen.findByText('Nova entrega'))
    await user.click(screen.getByRole('button',{name:'Enviar entrega'}))
    expect(await screen.findByText('Anexe o documento da entrega.')).toBeInTheDocument()
    expect(submitDeliveryMock).not.toHaveBeenCalled()
  })

  it('orientador aprova entrega com parecer',async()=>{
    listDeliveriesMock.mockResolvedValue([delivery()])
    getForwardingMock.mockRejectedValue(new Error('sem encaminhamento'))
    reviewDeliveryMock.mockResolvedValue(delivery({status:'APPROVED',review_feedback:'Excelente.'}))
    const user=userEvent.setup();render(<DeliveriesPanel project={project} user={professor}/>)
    expect(await screen.findByText('Versão 1 · Aguardando avaliação')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Parecer'),'Excelente.')
    await user.click(screen.getByRole('button',{name:'Aprovar entrega'}))
    expect(reviewDeliveryMock).toHaveBeenCalledWith('delivery-1','APPROVED','Excelente.')
    expect(await screen.findByText('Entrega aprovada.')).toBeInTheDocument()
  })

  it('orientador encaminha com observações e competências',async()=>{
    listDeliveriesMock.mockResolvedValue([delivery({status:'APPROVED'})])
    getForwardingMock.mockRejectedValue(new Error('sem encaminhamento'))
    const forwarding={project:'project-1',project_name:'Projeto',snapshot:{},observations:'Turma dedicada.',required_competencies:'Metodologia.',forwarded_by_name:'Professor Teste',forwarded_at:'2026-09-25T13:00:00Z'}as Forwarding
    forwardProjectMock.mockResolvedValue(forwarding)
    const user=userEvent.setup();render(<DeliveriesPanel project={project} user={professor}/>)
    await user.click(screen.getByText('Encaminhar à secretaria'))
    await user.type(screen.getByLabelText(/Observações ao setor/),'Turma dedicada.')
    await user.type(screen.getByLabelText(/Competências requeridas/),'Metodologia.')
    await user.click(screen.getByRole('button',{name:'Revisar encaminhamento'}))
    expect(await screen.findByRole('heading',{name:'Encaminhar projeto?'})).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Confirmar encaminhamento'}))
    expect(forwardProjectMock).toHaveBeenCalledWith('project-1',{observations:'Turma dedicada.',required_competencies:'Metodologia.'})
    expect(await screen.findByText('Projeto encaminhado à secretaria.')).toBeInTheDocument()
  })

  it('exibe encaminhamento existente',async()=>{
    listDeliveriesMock.mockResolvedValue([delivery({status:'APPROVED'})])
    getForwardingMock.mockResolvedValue({project:'project-1',project_name:'Projeto',snapshot:{},observations:'',required_competencies:'',forwarded_by_name:'Professor Teste',forwarded_at:'2026-09-25T13:00:00Z'}as Forwarding)
    render(<DeliveriesPanel project={project} user={professor}/>)
    expect(await screen.findByText(/Encaminhado à secretaria em/)).toBeInTheDocument()
    expect(screen.queryByText('Encaminhar à secretaria')).not.toBeInTheDocument()
  })
})

describe('fila de recebidos',()=>{
  it('secretaria consulta encaminhamentos e abre o projeto',async()=>{
    listForwardedMock.mockResolvedValue([{project:'project-1',project_name:'Projeto Cidadania',snapshot:{},observations:'Turma dedicada.',required_competencies:'Metodologia.',forwarded_by_name:'Professor Teste',forwarded_at:'2026-09-25T13:00:00Z'} as Forwarding])
    const seen:string[]=[]
    const listener=(event:Event)=>{seen.push((event as CustomEvent<string>).detail)}
    window.addEventListener('platform:navigate',listener)
    try{
      const user=userEvent.setup();render(<ForwardedQueue/>)
      expect(await screen.findByText('Projeto Cidadania')).toBeInTheDocument()
      expect(screen.getByText(/Turma dedicada/)).toBeInTheDocument()
      await user.click(screen.getByRole('button',{name:'Abrir projeto'}))
      expect(seen).toContain('#/projects/project-1')
    }finally{
      window.removeEventListener('platform:navigate',listener)
    }
  })

  it('mostra vazio sem recebidos',async()=>{
    listForwardedMock.mockResolvedValue([])
    render(<ForwardedQueue/>)
    expect(await screen.findByText('Nenhum encaminhamento recebido.')).toBeInTheDocument()
  })
})

function submittedForm(){
  return submitDeliveryMock.mock.calls[0][1] as FormData
}
