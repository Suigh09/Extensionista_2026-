import {cleanup,fireEvent,render,screen,waitFor,within} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {autoAllocateEvaluators,getShowcasePlanning,scheduleShowcaseGroup,type ShowcasePlanning} from './api'
import {ShowcaseScheduler} from './showcaseScheduler'

vi.mock('./api',()=>({autoAllocateEvaluators:vi.fn(),getGroupEvaluatorOptions:vi.fn(),designateEvaluator:vi.fn(),getShowcasePlanning:vi.fn(),scheduleShowcaseGroup:vi.fn(),cancelShowcaseEntry:vi.fn(),createShowcaseBuilding:vi.fn(),createShowcaseRoom:vi.fn(),createShowcaseDay:vi.fn(),renameShowcaseBuilding:vi.fn(),renameShowcaseRoom:vi.fn()}))
const fetchMock=vi.mocked(getShowcasePlanning),scheduleMock=vi.mocked(scheduleShowcaseGroup)
const fixture=():ShowcasePlanning=>({
  buildings:[{id:'building',code:'A',number:1,name:'Prédio A'}],
  rooms:[{id:'room',building:'building',number:1,name:'Sala 1'}],
  days:[{id:'day',date:'2026-12-10',start_time:'08:00:00',end_time:'10:00:00'}],
  groups:[{id:'group',project:'project',number:1,eligible:true,name:'Grupo 1',project_name:'Projeto Escola',members:['Maria Silva'],entry:null}],entries:[],
})
beforeEach(()=>{fetchMock.mockResolvedValue(fixture());scheduleMock.mockResolvedValue({id:'entry',date:'2026-12-10T11:00:00Z',end_date:'2026-12-10T11:30:00Z',day:'day',room:'room',location:'Prédio A / Sala 1',status:'SCHEDULED',updated_at:'2026-11-05T12:00:00Z'})})
afterEach(()=>{cleanup();vi.resetAllMocks()})

describe('agenda unificada',()=>{
  it('aloca um avaliador por grupo no dia/sala e mostra pendências',async()=>{
    const data=fixture()
    data.entries=[{id:'entry',group:'group',project_name:'Projeto Escola',number:1,date:'2026-12-10T11:00:00Z',end_date:'2026-12-10T11:30:00Z',day:'day',room:'room',location:'Prédio A / Sala 1',status:'SCHEDULED',updated_at:'version',evaluator_id:null}]
    data.groups[0].entry=data.entries[0]
    fetchMock.mockResolvedValue(data)
    vi.mocked(autoAllocateEvaluators).mockResolvedValue({allocated:[{group:'group',name:'Ana'}],preserved:[],pending:[{group:'pending',project_name:'Outro projeto',reason:'Sem aderência; escolha manualmente.'}]})
    vi.spyOn(window,'confirm').mockReturnValue(true)
    try{
      const user=userEvent.setup();render(<ShowcaseScheduler user={{role:'ADMIN'}}/>)
      await user.click(await screen.findByRole('button',{name:'Alocar avaliadores automaticamente'}))
      expect(autoAllocateEvaluators).toHaveBeenCalledWith('day','room')
      expect(await screen.findByRole('status',{name:'Resultado da alocação'})).toHaveTextContent('1 alocado(s) · 0 preservado(s) · 1 pendente(s)')
      expect(screen.getByText('Sem aderência; escolha manualmente.')).toBeInTheDocument()
    }finally{vi.restoreAllMocks()}
  })
  it('não oferece planejamento para alunos',()=>{
    render(<ShowcaseScheduler user={{role:'STUDENT'}}/>)
    expect(screen.getByRole('alert')).toHaveTextContent('Secretaria e Admin')
    expect(fetchMock).not.toHaveBeenCalled()
  })
  it('mostra seletores cadastrados, duas colunas e cadastro de locais para Secretaria',async()=>{
    render(<ShowcaseScheduler user={{role:'ADMIN'}}/>)
    expect(await screen.findByText('#1 · Projeto Escola')).toBeInTheDocument()
    expect(screen.getByLabelText('Data da Mostra')).toHaveValue('day')
    expect(screen.getByLabelText('Local (prédio / sala)')).toHaveValue('room')
    expect(screen.getByRole('region',{name:'Grupos não agendados'})).toBeInTheDocument()
    expect(screen.getByRole('region',{name:'Horários da sala'})).toBeInTheDocument()
    expect(screen.getByText('Adicionar prédio')).toBeInTheDocument()
    expect(screen.queryByLabelText('Grupo (UUID)')).not.toBeInTheDocument()
  })
  it('admin dispõe do cadastro de locais',async()=>{
    render(<ShowcaseScheduler user={{role:'ADMIN'}}/>)
    expect(await screen.findByText('Adicionar prédio')).toBeInTheDocument()
    expect(screen.getByLabelText('Nome do prédio A')).toHaveValue('Prédio A')
  })
  it('agenda por teclado/botão sem precisar arrastar',async()=>{
    const user=userEvent.setup();render(<ShowcaseScheduler user={{role:'ADMIN'}}/>)
    await user.click(await screen.findByText('Selecionar para agendar'))
    await user.click(screen.getByRole('button',{name:'Agendar grupo selecionado às 08:30'}))
    await waitFor(()=>expect(scheduleMock).toHaveBeenCalledWith({group:'group',day:'day',room:'room',start_time:'08:30',end_time:'09:00'}))
  })
  it('arrasta grupo para meia hora e mantém persistência no backend',async()=>{
    render(<ShowcaseScheduler user={{role:'ADMIN'}}/>)
    await screen.findByText('#1 · Projeto Escola')
    const slot=screen.getByRole('button',{name:'Agendar grupo selecionado às 09:00'}).parentElement!
    fireEvent.drop(slot,{dataTransfer:{getData:()=> 'group'}})
    await waitFor(()=>expect(scheduleMock).toHaveBeenCalledWith({group:'group',day:'day',room:'room',start_time:'09:00',end_time:'09:30'}))
  })
  it('resize usa a versão persistida e exibe erro sem fingir que salvou',async()=>{
    const data=fixture()
    data.entries=[{id:'entry',group:'group',project_name:'Projeto Escola',number:1,date:'2026-12-10T11:00:00Z',end_date:'2026-12-10T11:30:00Z',day:'day',room:'room',location:'Prédio A / Sala 1',status:'SCHEDULED',updated_at:'version'}]
    data.groups[0].entry=data.entries[0]
    fetchMock.mockResolvedValue(data)
    scheduleMock.mockRejectedValue(new Error('Este horário já está ocupado nesta sala.'))
    const user=userEvent.setup();render(<ShowcaseScheduler user={{role:'ADMIN'}}/>)
    await user.click(await screen.findByRole('button',{name:'Aumentar duração de Projeto Escola'}))
    expect(await screen.findByRole('status')).toHaveTextContent('Este horário já está ocupado')
    expect(scheduleMock).toHaveBeenCalledWith(expect.objectContaining({end_time:'09:00',expected_updated_at:'version'}))
    expect(within(screen.getByTestId('booking-entry')).getByText('08:00–08:30')).toBeInTheDocument()
  })
  it('busca projetos em todas as datas sem filtrar o quadro de ocupação',async()=>{
    const user=userEvent.setup();render(<ShowcaseScheduler user={{role:'ADMIN'}}/>)
    await screen.findByText('#1 · Projeto Escola')
    await user.type(screen.getByLabelText('Buscar projeto, integrante ou ID'),'Maria')
    await user.click(screen.getByText('Pesquisar'))
    await waitFor(()=>expect(fetchMock).toHaveBeenLastCalledWith('Maria'))
    expect(screen.getByRole('heading',{name:'Resultados em todas as datas e salas'})).toBeInTheDocument()
  })
})
