import{cleanup,fireEvent,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,describe,expect,it,vi}from'vitest'
import{concludeEvaluation,createRubric,gradeIndividual,groupGrades,listRubrics,submitGrades,usableRubrics}from'./api'
import type{Project,ProjectGroup}from'./api'
import{GroupEvaluationPanel,IndividualGradesPanel,RubricManagement}from'./grading'

vi.mock('./api',()=>({listRubrics:vi.fn(),createRubric:vi.fn(),updateRubricTitle:vi.fn(),addCriterion:vi.fn(),deleteCriterion:vi.fn(),deleteRubric:vi.fn(),usableRubrics:vi.fn(),groupGrades:vi.fn(),submitGrades:vi.fn(),concludeEvaluation:vi.fn(),individualGrades:vi.fn(),gradeIndividual:vi.fn()}))

const listRubricsMock=vi.mocked(listRubrics)
const createRubricMock=vi.mocked(createRubric)
const usableMock=vi.mocked(usableRubrics)
const gradesMock=vi.mocked(groupGrades)
const submitMock=vi.mocked(submitGrades)
const concludeMock=vi.mocked(concludeEvaluation)
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
  it('avaliador lança notas e vê a média',async()=>{
    usableMock.mockResolvedValue([rubric])
    gradesMock.mockResolvedValue({average:null,submissions:[]})
    submitMock.mockResolvedValue({id:'sub-1',average:'8.13'} as never)
    const user=userEvent.setup();render(<GroupEvaluationPanel project={project} group={group}/>)
    expect(await screen.findByText('Clareza')).toBeInTheDocument()
    fireEvent.change(screen.getAllByRole('spinbutton')[0],{target:{value:'8.12'}})
    fireEvent.change(screen.getAllByRole('spinbutton')[1],{target:{value:'8.13'}})
    await user.click(screen.getByRole('button',{name:'Enviar notas'}))
    expect(submitMock).toHaveBeenCalledWith('group-1',expect.objectContaining({rubric:'rubric-1'}))
    expect(await screen.findByText(/Média do grupo: 8.13/)).toBeInTheDocument()
  })

  it('conclui a avaliação',async()=>{
    usableMock.mockResolvedValue([rubric])
    gradesMock.mockResolvedValue({average:'8.13',submissions:[{id:'sub-1',group:'group-1',rubric:'rubric-1',rubric_title:'Rubrica Base',author_name:'Avaliador',comment:'',concluded:false,created_at:'',items:[]}]})
    concludeMock.mockResolvedValue({id:'sub-1'} as never)
    const user=userEvent.setup();render(<GroupEvaluationPanel project={project} group={group}/>)
    await user.click(await screen.findByRole('button',{name:'Concluir avaliação'}))
    expect(concludeMock).toHaveBeenCalledWith('group-1')
    expect(await screen.findByText('Avaliação concluída e grupo notificado.')).toBeInTheDocument()
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
