import{cleanup,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,describe,expect,it,vi}from'vitest'
import{designateEvaluator,recommendEvaluators,searchProfessors} from './api'
import type{RecommendationResponse}from'./api'
import{EvaluatorDesignation}from'./evaluation'

vi.mock('./api',()=>({designateEvaluator:vi.fn(),recommendEvaluators:vi.fn(),searchProfessors:vi.fn()}))

const recommendMock=vi.mocked(recommendEvaluators)
const designateMock=vi.mocked(designateEvaluator)
const searchMock=vi.mocked(searchProfessors)

afterEach(()=>{cleanup();vi.clearAllMocks()})

function response():RecommendationResponse{
  return{
    keywords:['metodologia'],
    recommendations:[
      {professor_profile_id:'prof-1',name:'Professora Ana',matched:{metodologia:['Metodologia de Pesquisa']},match_count:1,load:0},
      {professor_profile_id:'prof-2',name:'Professor Beto',matched:{},match_count:0,load:1},
    ],
    groups:[{group_id:'group-1',group_name:'Grupo principal',responsible_professor_name:'Orientador',evaluator_profile_id:null,evaluator_name:null}],
    history:[],
  }
}

describe('designação de avaliadores',()=>{
  it('exibe recomendação explicável e designa o primeiro sem justificativa',async()=>{
    recommendMock.mockResolvedValue(response())
    designateMock.mockResolvedValue({id:'a1'} as never)
    const user=userEvent.setup();render(<EvaluatorDesignation projectId="project-1"/>)
    expect(await screen.findByText(/Aderência: metodologia/)).toBeInTheDocument()
    expect(screen.getByText(/Carga: 0/)).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Selecionar Professora Ana'}))
    await user.click(screen.getByRole('button',{name:'Confirmar designação'}))
    expect(designateMock).toHaveBeenCalledWith('group-1',{professor:'prof-1',justification:''})
    expect(await screen.findByText('Avaliador designado.')).toBeInTheDocument()
  })

  it('exige justificativa fora da aderência via busca manual',async()=>{
    recommendMock.mockResolvedValue({...response(),recommendations:[]})
    searchMock.mockResolvedValue([{id:'prof-9',name:'Professor Nove',registration:'P9'}])
    designateMock.mockResolvedValue({id:'a2'} as never)
    const user=userEvent.setup();render(<EvaluatorDesignation projectId="project-1"/>)
    expect(await screen.findByText(/Nenhum professor compatível/)).toBeInTheDocument()
    await user.type(screen.getByLabelText(/Buscar professor/), 'Nove')
    expect(await screen.findByText('Professor Nove')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Selecionar Professor Nove'}))
    expect(screen.getByText(/justificativa obrigatória/)).toBeInTheDocument()
    await user.type(screen.getByLabelText('Justificativa'),'Rodízio entre docentes.')
    await user.click(screen.getByRole('button',{name:'Confirmar designação'}))
    expect(designateMock).toHaveBeenCalledWith('group-1',{professor:'prof-9',justification:'Rodízio entre docentes.'})
  })

  it('informa indisponibilidade antes do encaminhamento',async()=>{
    recommendMock.mockRejectedValue(new Error('O projeto precisa ser encaminhado antes de designar.'))
    render(<EvaluatorDesignation projectId="project-1"/>)
    expect(await screen.findByText(/após o encaminhamento/)).toBeInTheDocument()
  })
})
