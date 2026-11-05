import{cleanup,fireEvent,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,describe,expect,it,vi}from'vitest'
import{createRubric,gradeIndividual,groupGrades,listRubrics,submitGrades,usableRubrics}from'./api'
import type{Project,ProjectGroup}from'./api'
import{GroupEvaluationPanel,IndividualGradesPanel,RubricManagement}from'./grading'

vi.mock('./api',()=>({listRubrics:vi.fn(),createRubric:vi.fn(),updateRubricTitle:vi.fn(),addCriterion:vi.fn(),deleteCriterion:vi.fn(),deleteRubric:vi.fn(),usableRubrics:vi.fn(),groupGrades:vi.fn(),submitGrades:vi.fn(),concludeEvaluation:vi.fn(),individualGrades:vi.fn(),gradeIndividual:vi.fn()}))

const listRubricsMock=vi.mocked(listRubrics)
const createRubricMock=vi.mocked(createRubric)
const usableMock=vi.mocked(usableRubrics)
const gradesMock=vi.mocked(groupGrades)
const submitMock=vi.mocked(submitGrades)
const gradeIndividualMock=vi.mocked(gradeIndividual)

afterEach(()=>{cleanup();vi.clearAllMocks()})

const rubric={id:'rubric-1',title:'Rubrica Base',criteria:[{id:'crit-1',name:'Clareza',description:'',position:0},{id:'crit-2',name:'Impacto',description:'',position:1}],created_at:'',updated_at:''}
const project={id:'project-1',name:'Projeto',about:'Sobre',status:'APPROVED'}as Project
const group={id:'group-1',name:'Grupo principal',member_count:2,members:[{user_id:'1',student_id:11,name:'Aluno Um',ra:'RA1',joined_at:''}]}as unknown as ProjectGroup

describe('rubricas',()=>{
  it('professor cria rubrica com critérios',async()=>{
    listRubricsMock.mockResolvedValue([])
    createRubricMock.mockResolvedValue(rubric)
    listRubricsMock.mockResolvedValueOnce([]).mockResolvedValueOnce([rubric])
    const user=userEvent.setup();render(<RubricManagement/>)
    expect(await screen.findByText('Nenhuma rubrica cadastrada.')).toBeInTheDocument()
    await user.type(screen.getByLabelText('Título da rubrica'),'Rubrica Base')
    await user.type(screen.getByLabelText(/Critérios/), 'Clareza\nImpacto')
    await user.click(screen.getByRole('button',{name:'Criar rubrica'}))
    expect(createRubricMock).toHaveBeenCalledWith({title:'Rubrica Base',criteria:[{name:'Clareza',description:''},{name:'Impacto',description:''}]})
    expect(await screen.findByText('Rubrica criada.')).toBeInTheDocument()
  })
})

describe('avaliação do grupo',()=>{
  it('encaminha à nota direta da Mostra sem consultar ou enviar rubricas',async()=>{
    gradesMock.mockResolvedValue({average:null,submissions:[]})
    render(<GroupEvaluationPanel project={project} group={group}/>)
    expect(await screen.findByRole('link',{name:'Registrar presença e avaliar grupo'})).toHaveAttribute('href','#/showcase-presence')
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Enviar notas'})).not.toBeInTheDocument()
    expect(usableMock).not.toHaveBeenCalled()
    expect(submitMock).not.toHaveBeenCalled()
  })

  it('preserva a consulta do histórico antigo sem formulário de rubrica',async()=>{
    gradesMock.mockResolvedValue({average:'8.13',submissions:[{id:'sub-1',group:'group-1',rubric:'rubric-1',rubric_title:'Rubrica Base',author_name:'Avaliador',comment:'Registro anterior',concluded:true,created_at:'2026-11-05T12:00:00Z',items:[]}]})
    render(<GroupEvaluationPanel project={project} group={group}/>)
    expect(await screen.findByText('Nota do grupo: 8.13')).toBeInTheDocument()
    expect(screen.getByText('Rubrica Base')).toBeInTheDocument()
    expect(screen.getByText('Registro anterior')).toBeInTheDocument()
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument()
    expect(screen.queryByRole('link',{name:'Registrar presença e avaliar grupo'})).not.toBeInTheDocument()
  })

  it('mostra nota direta e observações no histórico',async()=>{
    gradesMock.mockResolvedValue({average:'9.00',submissions:[{id:'sub-2',group:'group-1',rubric:null,rubric_title:'',direct_value:'9.00',author_name:'Avaliador',comment:'Boa apresentação',concluded:true,created_at:'2026-11-05T12:00:00Z',items:[]}]})
    render(<GroupEvaluationPanel project={project} group={group}/>)
    expect(await screen.findByText('Boa apresentação')).toBeInTheDocument()
    expect(screen.getAllByText('Nota do grupo: 9.00')).toHaveLength(2)
  })
})

describe('notas individuais',()=>{
  it('orientador registra nota do aluno',async()=>{
    const {individualGrades}=await import('./api')
    vi.mocked(individualGrades).mockResolvedValue({current:null,history:[]})
    gradeIndividualMock.mockResolvedValue({id:'g1',student_name:'Aluno Um',value:'9.50'} as never)
    const user=userEvent.setup();render(<IndividualGradesPanel group={group}/>)
    await user.click(await screen.findByText(/Aluno Um/))
    fireEvent.change(screen.getByLabelText(/Nota \(0 a 10\)/),{target:{value:'9.5'}})
    await user.click(screen.getByRole('button',{name:'Registrar nota'}))
    expect(gradeIndividualMock).toHaveBeenCalledWith('11',{value:'9.5',comment:''})
    expect(await screen.findByText(/Aluno Um registrada/)).toBeInTheDocument()
  })
})
