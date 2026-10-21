import{cleanup,fireEvent,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,describe,expect,it,vi}from'vitest'
import{assignProjectStudent,createProject,listThemes,projectTransition,searchThemeStudents}from'./api'
import type{Profile,Project,ProjectTheme}from'./api'
import{LifecyclePanel,ProfessorGroupAssignment,ThemeProjectCreate}from'./projectLifecycle'

vi.mock('./api',()=>({listThemes:vi.fn(),createProject:vi.fn(),listRooms:vi.fn(),saveTheme:vi.fn(),updateTheme:vi.fn(),searchThemeStudents:vi.fn(),projectTransition:vi.fn(),assignProjectStudent:vi.fn(),listInstitutionalProjects:vi.fn()}))

const listThemesMock=vi.mocked(listThemes)
const createProjectMock=vi.mocked(createProject)
const projectTransitionMock=vi.mocked(projectTransition)
const assignProjectStudentMock=vi.mocked(assignProjectStudent)
const searchThemeStudentsMock=vi.mocked(searchThemeStudents)

afterEach(()=>{cleanup();vi.clearAllMocks()})

const student={id:'1',username:'aluno',name:'Aluno Teste',email:'',role:'STUDENT',profile:{ra:'RA1'}}as Profile
const professor={id:'p1',username:'professor',name:'Professor Teste',email:'',role:'PROFESSOR',profile:{registration:'P1'}}as Profile
const theme={id:'theme-1',title:'Tema Cidadania',description:'Orientações',room:'room-1',room_name:'Sala Teste',is_open:true,max_projects:null,project_count:0}as ProjectTheme

function draftProject(status:Project['status']='DRAFT'):Project{
  return{id:'project-1',name:'Projeto Cidadania',about:'Proposta.',status,theme:'theme-1',theme_snapshot:{title:'Tema Cidadania',description:'Orientações'},can_manage:true}as Project
}

describe('criação de projeto por tema',()=>{
  it('estudante cria projeto informando o tema da sala',async()=>{
    listThemesMock.mockResolvedValue([theme])
    const created={...draftProject(),group:{id:'group-1',member_count:1}}as Project
    createProjectMock.mockResolvedValue(created)
    const navigated:string[]=[]
    const listener=(event:Event)=>{navigated.push((event as CustomEvent<string>).detail)}
    window.addEventListener('platform:navigate',listener)
    try{
      const user=userEvent.setup();render(<ThemeProjectCreate user={student}/>)
      await screen.findByRole('option',{name:/Tema Cidadania/})
      fireEvent.change(await screen.findByLabelText('Tema do projeto'),{target:{value:'theme-1'}})
      await user.type(await screen.findByLabelText('Título do projeto'),'Projeto Cidadania')
      await user.type(screen.getByLabelText('Sobre o projeto'),'Proposta de impacto social.')
      await user.click(screen.getByRole('button',{name:'Criar projeto'}))
      expect(createProjectMock).toHaveBeenCalledWith({name:'Projeto Cidadania',about:'Proposta de impacto social.',theme:'theme-1'})
      expect(navigated).toContain('#/projects/project-1')
    }finally{
      window.removeEventListener('platform:navigate',listener)
    }
  })

  it('informa quando não há tema disponível e bloqueia a criação',async()=>{
    listThemesMock.mockResolvedValue([])
    render(<ThemeProjectCreate user={student}/>)
    expect(await screen.findByText(/Nenhum tema disponível/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Criar projeto'})).toBeDisabled()
    expect(createProjectMock).not.toHaveBeenCalled()
  })

  it('professor só cria projeto após indicar o líder',async()=>{
    listThemesMock.mockResolvedValue([theme])
    searchThemeStudentsMock.mockResolvedValue([])
    render(<ThemeProjectCreate user={professor}/>)
    await screen.findByRole('option',{name:/Tema Cidadania/})
    fireEvent.change(await screen.findByLabelText('Tema do projeto'),{target:{value:'theme-1'}})
    expect(await screen.findByText('Líder do grupo')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Criar projeto'})).toBeDisabled()
    expect(createProjectMock).not.toHaveBeenCalled()
  })
})

describe('ciclo de vida do projeto',()=>{
  it('estudante pausa o projeto com justificativa',async()=>{
    const paused={...draftProject('PAUSED'),previous_status:'DRAFT'}as Project
    projectTransitionMock.mockResolvedValue(paused)
    const onChanged=vi.fn()
    const user=userEvent.setup();render(<LifecyclePanel project={draftProject()} user={student} onChanged={onChanged}/>)
    await user.click(screen.getByRole('button',{name:'Pausar projeto'}))
    expect(await screen.findByRole('heading',{name:'Pausar projeto?'})).toBeInTheDocument()
    await user.type(screen.getByLabelText('Motivo ou justificativa'),'Recesso acadêmico')
    await user.click(screen.getByRole('button',{name:'Confirmar'}))
    expect(projectTransitionMock).toHaveBeenCalledWith('project-1','pause','Recesso acadêmico')
    await vi.waitFor(()=>expect(onChanged).toHaveBeenCalledWith(paused))
  })

  it('retomada informa o estado de retorno sem prorrogar prazos',()=>{
    render(<LifecyclePanel project={{...draftProject('PAUSED'),previous_status:'APPROVED'}} user={student} onChanged={vi.fn()}/>)
    expect(screen.getByText(/A retomada retorna para Aprovado/)).toBeInTheDocument()
    expect(screen.getByText(/prazos não são prorrogados/)).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Retomar projeto'})).toBeInTheDocument()
  })

  it('cancelamento pendente mantém o grupo vigente até a decisão',()=>{
    const pending={id:'request-1',reason:'Mudança de curso',status:'PENDING',requested_by_name:'Aluno Teste',decision_note:'',created_at:'',decided_at:null}
    render(<LifecyclePanel project={{...draftProject(),cancellation_requests:[pending]}} user={student} onChanged={vi.fn()}/>)
    expect(screen.getByText('Cancelamento aguardando Secretaria/Admin')).toBeInTheDocument()
    expect(screen.getByText(/permanece vigente até a decisão/)).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Solicitar cancelamento'})).not.toBeInTheDocument()
  })
})

describe('associação pelo professor',()=>{
  it('não renderiza sem tema vinculado',()=>{
    const{container}=render(<ProfessorGroupAssignment project={{...draftProject(),theme:null}} onChanged={async()=>{}}/>)
    expect(container).toBeEmptyDOMElement()
  })

  it('associa aluno com opção de liderança',async()=>{
    const eligible={id:'7',user:'7',name:'Colega Dois',ra:'RA2',course_name:'ADS',class_code:'A',term:'2026.2'}
    searchThemeStudentsMock.mockImplementation(async()=> [eligible])
    assignProjectStudentMock.mockResolvedValue(draftProject())
    const onChanged=vi.fn()
    const user=userEvent.setup()
    render(<ProfessorGroupAssignment project={draftProject()} onChanged={onChanged}/>)
    await user.type(screen.getByPlaceholderText(/Nome ou RA/), 'Colega')
    expect(await screen.findByText('Colega Dois · RA2')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Selecionar Colega Dois'}))
    await user.click(screen.getByLabelText('Definir como líder'))
    await user.click(screen.getByRole('button',{name:'Confirmar associação'}))
    expect(assignProjectStudentMock).toHaveBeenCalledWith('project-1',7,true)
    expect(onChanged).toHaveBeenCalled()
  })
})
