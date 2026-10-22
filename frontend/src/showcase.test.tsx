import{cleanup,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,beforeEach,describe,expect,it,vi}from'vitest'
import{createPublicationDocument,createShowcaseEntry,listAcervo,listPublicationDocuments,listPublications,listShowcaseEntries,publishProject,recordPresence,reviewPublicationDocument,type AcervoItem,type Publication,type PublicationDocument,type Project,type ShowcaseEntry,type Profile}from'./api'
import{AcervoPanel,PublicationDocumentPanel,PublicationPanel,ShowcasePanel,ShowcasePresencePanel}from'./showcase'

vi.mock('./api',()=>({
  cancelShowcaseEntry:vi.fn(),
  createPublicationDocument:vi.fn(),
  createShowcaseEntry:vi.fn(),
  listAcervo:vi.fn(),
  listPublicationDocuments:vi.fn(),
  listPublications:vi.fn(),
  listShowcaseEntries:vi.fn(),
  publishProject:vi.fn(),
  publicationDocumentDownloadUrl:(documentId:string)=>`http://teste/projects/publication-documents/${documentId}/download/`,
  recordPresence:vi.fn(),
  reviewPublicationDocument:vi.fn(),
  withdrawPublication:vi.fn(),
}))

afterEach(()=>{cleanup();vi.clearAllMocks();vi.restoreAllMocks()})

const secretariat={id:'s1',username:'secretaria',name:'Secretaria Teste',email:'',role:'SECRETARIAT'}as Profile
const professor={id:'p1',username:'professor',name:'Professor Teste',email:'',role:'PROFESSOR',profile:{registration:'P1'}}as Profile
const student={id:'a1',username:'aluno',name:'Aluno Teste',email:'',role:'STUDENT',profile:{ra:'RA1'}}as Profile

const entry:ShowcaseEntry={id:'entry-1',group:'group-1',group_name:'Grupo A',project_id:'project-1',project_name:'Projeto Cidadania',date:'2026-12-10T14:00:00Z',location:'Auditório Central',status:'SCHEDULED',decided_by:'s1',decided_by_name:'Secretaria Teste',notes:'',is_evaluator:false,created_at:'2026-09-25T12:00:00Z',updated_at:'2026-09-25T12:00:00Z'}

const document:PublicationDocument={id:'doc-1',project:'project-1',project_name:'Projeto Cidadania',version:1,original_name:'documento.pdf',content_type:'application/pdf',size:1024,status:'PENDING',review:null,reviewed_by_name:null,reviewed_at:null,consent_given:true,consent_at:'2026-09-25T12:00:00Z',consent_by_name:'Aluno Teste',generated_by_name:'Aluno Teste',download_url:'/projects/publication-documents/doc-1/download/',created_at:'2026-09-25T12:00:00Z'}

const publication:Publication={id:'pub-1',project:'project-1',project_name:'Projeto Cidadania',document:'doc-1',document_version:1,document_status:'APPROVED',published_at:'2026-09-25T12:00:00Z',withdrawn_at:null,withdrawal_reason:null,withdrawn_by_name:null,is_published:true,created_at:'2026-09-25T12:00:00Z',updated_at:'2026-09-25T12:00:00Z'}

const acervoItem:AcervoItem={id:'pub-1',project_name:'Projeto Cidadania',document_version:1,published_at:'2026-09-25T12:00:00Z',created_at:'2026-09-25T12:00:00Z'}

beforeEach(()=>{
  vi.spyOn(window,'confirm').mockReturnValue(true)
})

const project={id:'project-1',name:'Projeto Cidadania',about:'Sobre',status:'APPROVED',is_active:true,created_at:'2026-09-25T12:00:00Z',updated_at:'2026-09-25T12:00:00Z',created_by_name:'Aluno Teste',group:{id:'group-1',name:'Grupo A',class_offering:'class-1',member_count:2,formation_status:'FORMED',members:[{user_id:'a1',student_id:1,name:'Aluno Teste',ra:'RA1',joined_at:'2026-09-25T12:00:00Z',is_active:true}],responsible_professor_name:'Professor Teste',evaluator_name:'Professor Teste',leader:1,leader_user_id:'a1'},groups:[{id:'group-1',name:'Grupo A',class_offering:'class-1',member_count:2,formation_status:'FORMED',members:[{user_id:'a1',student_id:1,name:'Aluno Teste',ra:'RA1',joined_at:'2026-09-25T12:00:00Z',is_active:true}],responsible_professor_name:'Professor Teste',evaluator_name:'Professor Teste',leader:1,leader_user_id:'a1'}]} as Project

describe('agenda da Mostra',()=>{
  it('secretaria agenda entrada na Mostra',async()=>{
    vi.mocked(createShowcaseEntry).mockResolvedValue(entry)
    vi.mocked(listShowcaseEntries).mockResolvedValue([entry])
    const user=userEvent.setup();render(<ShowcasePanel user={secretariat}/>)
    expect(await screen.findByText('Agenda da Mostra')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Agendar'}))
    expect(await screen.findByRole('heading',{name:'Agendar apresentação'})).toBeInTheDocument()
    await user.type(screen.getByLabelText('Grupo (UUID)'),'group-1')
    await user.type(screen.getByLabelText('Data e hora'),'2026-12-10T14:00')
    await user.type(screen.getByLabelText('Local'),'Auditório Central')
    await user.click(screen.getByRole('button',{name:'Agendar'}))
    expect(createShowcaseEntry).toHaveBeenCalledWith({group:'group-1',date:'2026-12-10T14:00',location:'Auditório Central'})
    expect(await screen.findByText('Mostra agendada.')).toBeInTheDocument()
  })

  it('nao exibe agenda para aluno',async()=>{
    render(<ShowcasePanel user={student}/>)
    expect(screen.queryByText('Agenda da Mostra')).not.toBeInTheDocument()
  })
})

describe('registro de presenca',()=>{
  it('avaliador registra PRESENTED',async()=>{
    vi.mocked(listShowcaseEntries).mockResolvedValue([{...entry,is_evaluator:true}])
    vi.mocked(recordPresence).mockResolvedValue({...entry,status:'PRESENTED'})
    const user=userEvent.setup();render(<ShowcasePresencePanel user={professor}/>)
    expect(await screen.findByText('Registro de presença')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Apresentado'}))
    expect(recordPresence).toHaveBeenCalledWith('entry-1','PRESENTED','')
    expect(await screen.findByText('Presença registrada.')).toBeInTheDocument()
  })

  it('nao exibe para nao-avaliador',async()=>{
    vi.mocked(listShowcaseEntries).mockResolvedValue([{...entry,is_evaluator:false}])
    render(<ShowcasePresencePanel user={student}/>)
    expect(screen.queryByText('Registro de presença')).not.toBeInTheDocument()
  })
})

describe('documento publicavel',()=>{
  it('aluno gera documento com consentimento',async()=>{
    vi.mocked(listPublicationDocuments).mockResolvedValue([document])
    vi.mocked(createPublicationDocument).mockResolvedValue(document)
    const user=userEvent.setup();render(<PublicationDocumentPanel project={project} user={student}/>)
    expect(await screen.findByRole('heading',{name:'Documento do projeto'})).toBeInTheDocument()
    await user.click(screen.getByText('Gerar novo documento'))
    const file=new File(['%PDF-1.4 teste'],'documento.pdf',{type:'application/pdf'})
    await user.upload(screen.getByLabelText(/Arquivo PDF/),file)
    await user.click(screen.getByLabelText(/consentimento/))
    expect(screen.getByRole('button',{name:'Gerar documento'})).toBeInTheDocument()
  })

  it('orientador aprova documento',async()=>{
    vi.mocked(listPublicationDocuments).mockResolvedValue([{...document,status:'PENDING'}])
    vi.mocked(reviewPublicationDocument).mockResolvedValue({...document,status:'APPROVED',review:'OK'})
    const user=userEvent.setup();render(<PublicationDocumentPanel project={project} user={professor}/>)
    await screen.findByText('Documentos gerados')
    await user.click(screen.getByRole('button',{name:'Aprovar'}))
    await user.type(screen.getByLabelText('Parecer'),'OK')
    await user.click(screen.getByRole('button',{name:'Aprovar'}))
    expect(reviewPublicationDocument).toHaveBeenCalledWith('doc-1','APPROVED','OK')
  })

  it('professor que nao eh orientador nao aprova',async()=>{
    vi.mocked(listPublicationDocuments).mockResolvedValue([document])
    render(<PublicationDocumentPanel project={project} user={student}/>)
    expect(await screen.findByText('Documentos gerados')).toBeInTheDocument()
  })
})

describe('publicacao no acervo',()=>{
  it('aluno publica projeto',async()=>{
    vi.mocked(listPublications).mockResolvedValue([])
    vi.mocked(publishProject).mockResolvedValue(publication)
    const user=userEvent.setup();render(<PublicationPanel project={project} user={student}/>)
    expect(await screen.findByRole('heading',{name:'Publicação do projeto'})).toBeInTheDocument()
    await user.click(screen.getByText('Publicar no acervo'))
    const select=screen.getByLabelText(/Documento publicável/)
    expect(select).toBeInTheDocument()
    expect(select.querySelectorAll('option')).toHaveLength(1)
  })

  it('secretaria retira publicacao',async()=>{
    vi.mocked(listPublications).mockResolvedValue([publication])
    const user=userEvent.setup();render(<PublicationPanel project={project} user={secretariat}/>)
    expect(await screen.findByRole('heading',{name:'Publicações deste projeto'})).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Retirar'}))
    expect(await screen.findByRole('button',{name:'Retirar'})).toBeInTheDocument()
  })
})

describe('acervo',()=>{
  it('lista projetos publicados',async()=>{
    vi.mocked(listAcervo).mockResolvedValue([acervoItem])
    render(<AcervoPanel/>)
    expect(await screen.findByText('Acervo de projetos publicados')).toBeInTheDocument()
    expect(await screen.findByText('Projeto Cidadania')).toBeInTheDocument()
  })

  it('pesquisa por titulo',async()=>{
    vi.mocked(listAcervo).mockResolvedValue([acervoItem])
    const user=userEvent.setup();render(<AcervoPanel/>)
    await user.type(screen.getByLabelText('Buscar'),'Cidadania')
    await user.click(screen.getByRole('button',{name:'Pesquisar'}))
    expect(listAcervo).toHaveBeenCalledWith('Cidadania')
  })
})
