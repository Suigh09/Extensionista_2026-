import {cleanup,render,screen,waitFor} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {afterEach,beforeEach,describe,expect,it,vi} from 'vitest'
import {designateEvaluator,getGroupEvaluatorOptions,type GroupEvaluatorOptions} from './api'
import {AgendaEvaluatorPicker} from './agendaEvaluators'

vi.mock('./api',()=>({designateEvaluator:vi.fn(),getGroupEvaluatorOptions:vi.fn()}))
const fixture=():GroupEvaluatorOptions=>({group:'g',current:null,current_name:null,keywords:['extensao'],locked:false,recommendations:[
  {professor_profile_id:'1',name:'Ana',match_count:1,matched:{extensao:['Extensão']},load:0,available:true,unavailable_reason:'',requires_justification:false},
  {professor_profile_id:'2',name:'Bia',match_count:0,matched:{},load:0,available:true,unavailable_reason:'',requires_justification:true},
  {professor_profile_id:'3',name:'Caio',match_count:1,matched:{},load:1,available:false,unavailable_reason:'Já alocado neste horário.',requires_justification:false},
]})
beforeEach(()=>{vi.mocked(getGroupEvaluatorOptions).mockResolvedValue(fixture());vi.mocked(designateEvaluator).mockResolvedValue({} as never)})
afterEach(()=>{cleanup();vi.resetAllMocks()})

describe('avaliador individual da agenda',()=>{
  it('escolhe um avaliador, bloqueia indisponível e persiste',async()=>{
    const assigned=vi.fn().mockResolvedValue(undefined),user=userEvent.setup()
    render(<AgendaEvaluatorPicker group="g" projectName="Escola" onClose={vi.fn()} onAssigned={assigned}/>)
    const select=await screen.findByLabelText('Avaliador do grupo')
    expect(screen.getByRole('option',{name:/Caio/})).toBeDisabled()
    await user.selectOptions(select,'1')
    await user.click(screen.getByRole('button',{name:'Alocar avaliador'}))
    await waitFor(()=>expect(assigned).toHaveBeenCalled())
    expect(designateEvaluator).toHaveBeenCalledWith('g',{professor:'1',justification:''})
  })
  it('exige justificativa para escolha sem aderência',async()=>{
    const user=userEvent.setup()
    render(<AgendaEvaluatorPicker group="g" projectName="Escola" onClose={vi.fn()} onAssigned={vi.fn()}/>)
    await user.selectOptions(await screen.findByLabelText('Avaliador do grupo'),'2')
    expect(screen.getByLabelText('Justificativa da escolha')).toBeRequired()
    await user.type(screen.getByLabelText('Justificativa da escolha'),'Rodízio autorizado.')
    await user.click(screen.getByRole('button',{name:'Alocar avaliador'}))
    expect(designateEvaluator).toHaveBeenCalledWith('g',{professor:'2',justification:'Rodízio autorizado.'})
  })
  it('erro de conflito não finge sucesso',async()=>{
    vi.mocked(designateEvaluator).mockRejectedValue(new Error('Avaliador ocupado neste horário.'))
    const assigned=vi.fn(),user=userEvent.setup()
    render(<AgendaEvaluatorPicker group="g" projectName="Escola" onClose={vi.fn()} onAssigned={assigned}/>)
    await user.selectOptions(await screen.findByLabelText('Avaliador do grupo'),'1')
    await user.click(screen.getByRole('button',{name:'Alocar avaliador'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Avaliador ocupado')
    expect(assigned).not.toHaveBeenCalled()
  })
  it('bloqueia troca após presença ou notas',async()=>{
    vi.mocked(getGroupEvaluatorOptions).mockResolvedValue({...fixture(),locked:true})
    render(<AgendaEvaluatorPicker group="g" projectName="Escola" onClose={vi.fn()} onAssigned={vi.fn()}/>)
    expect(await screen.findByText(/A troca de avaliador está bloqueada/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Avaliador do grupo')).not.toBeInTheDocument()
  })
})
