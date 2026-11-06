import{cleanup,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,beforeEach,describe,expect,it,vi}from'vitest'
import{createPublicationDocument,listAcervo,listPublicationDocuments,listPublications,listShowcaseEntries,publishProject,recordMemberAttendance,recordShowcaseGrade,reviewPublicationDocument,type AcervoItem,type Publication,type PublicationDocument,type Project,type ShowcaseEntry,type Profile}from'./api'
import{AcervoPanel,PublicAcervoPanel,PublicationDocumentPanel,PublicationPanel,ShowcasePresencePanel}from'./showcase'
import {listAcervoPublico} from './api'

vi.mock('./api',()=>({
  cancelShowcaseEntry:vi.fn(),
  createPublicationDocument:vi.fn(),
  createShowcaseEntry:vi.fn(),
  listAcervo:vi.fn(),
  listAcervoPublico:vi.fn(),
  listPublicationDocuments:vi.fn(),
  listPublications:vi.fn(),
  listShowcaseEntries:vi.fn(),
  publishProject:vi.fn(),
  publicationDocumentDownloadUrl:(documentId:string)=>`http://teste/projects/publication-documents/${documentId}/download/`,
  acervoPdfUrl:(publicationId:string)=>`/api/v1/projects/acervo/${publicationId}/pdf/`,
  recordMemberAttendance:vi.fn(),
  recordShowcaseGrade:vi.fn(),
  reviewPublicationDocument:vi.fn(),
  withdrawPublication:vi.fn(),
}))

afterEach(()=>{cleanup();vi.clearAllMocks();vi.restoreAllMocks()})

const secretariat={id:'s1',username:'secretaria',name:'Secretaria Teste',email:'',role:'ADMIN'}as Profile
const professor={id:'p1',username:'professor',name:'Professor Teste',email:'',role:'PROFESSOR',profile:{registration:'P1'}}as Profile
const student={id:'a1',username:'aluno',name:'Aluno Teste',email:'',role:'STUDENT',profile:{ra:'RA1'}}as Profile

const entry:ShowcaseEntry={id:'entry-1',group:'group-1',group_name:'Grupo A',project_id:'project-1',project_name:'Projeto Cidadania',date:'2026-12-10T14:00:00Z',location:'Auditório Central',status:'SCHEDULED',decided_by:'s1',decided_by_name:'Secretaria Teste',notes:'',is_evaluator:false,created_at:'2026-09-25T12:00:00Z',updated_at:'2026-09-25T12:00:00Z'}

const document:PublicationDocument={id:'doc-1',project:'project-1',project_name:'Projeto Cidadania',version:1,content:'',original_name:'documento.pdf',content_type:'application/pdf',size:1024,status:'PENDING',review:null,reviewed_by_name:null,reviewed_at:null,consent_given:true,consent_at:'2026-09-25T12:00:00Z',consent_by_name:'Aluno Teste',generated_by_name:'Aluno Teste',download_url:'/projects/publication-documents/doc-1/download/',created_at:'2026-09-25T12:00:00Z'}

const publication:Publication={id:'pub-1',project:'project-1',project_name:'Projeto Cidadania',document:'doc-1',document_version:1,document_status:'APPROVED',published_at:'2026-09-25T12:00:00Z',withdrawn_at:null,withdrawal_reason:null,withdrawn_by_name:null,is_published:true,created_at:'2026-09-25T12:00:00Z',updated_at:'2026-09-25T12:00:00Z'}

const acervoItem:AcervoItem={id:'pub-1',project_name:'Projeto Cidadania',document_version:1,published_at:'2026-09-25T12:00:00Z',created_at:'2026-09-25T12:00:00Z',members:['Ana','Bia'],abstract:'Ações de cidadania na comunidade.'}

beforeEach(()=>{
  vi.spyOn(window,'confirm').mockReturnValue(true)
})

const project={id:'project-1',name:'Projeto Cidadania',about:'Sobre',class_offering:'class-1',status:'APPROVED',is_active:true,created_at:'2026-09-25T12:00:00Z',updated_at:'2026-09-25T12:00:00Z',created_by_name:'Aluno Teste',submitted_at:'2026-09-24T12:00:00Z',reviewed_at:'2026-09-25T10:00:00Z',review_feedback:'Aprovado',reviewed_by:'Professor Teste',group:{id:'group-1',name:'Grupo A',class_offering:'class-1',member_count:2,formation_status:'FORMED',members:[{user_id:'a1',student_id:1,name:'Aluno Teste',ra:'RA1',joined_at:'2026-09-25T12:00:00Z'}],responsible_professor_name:'Professor Teste',evaluator_name:'Professor Teste',leader:1,leader_user_id:'a1'},groups:[{id:'group-1',name:'Grupo A',class_offering:'class-1',member_count:2,formation_status:'FORMED',members:[{user_id:'a1',student_id:1,name:'Aluno Teste',ra:'RA1',joined_at:'2026-09-25T12:00:00Z'}],responsible_professor_name:'Professor Teste',evaluator_name:'Professor Teste',leader:1,leader_user_id:'a1'}]} as Project

describe('registro de presenca',()=>{
  it('confirma integrantes e abre avaliação com nota e observações',async()=>{
    const members=[{member_id:11,name:'Ana',ra:'RA1',present:null},{member_id:12,name:'Bia',ra:'RA2',present:null}]
    const presented={...entry,is_evaluator:true,status:'PRESENTED' as const,members:members.map((member,index)=>({...member,present:index===0}))}
    vi.mocked(listShowcaseEntries).mockResolvedValue([{...entry,is_evaluator:true,members}])
    vi.mocked(recordMemberAttendance).mockResolvedValue(presented)
    vi.mocked(recordShowcaseGrade).mockResolvedValue({...presented,evaluation:{value:'8.50',observations:'Boa apresentação',concluded:true}})
    const user=userEvent.setup();render(<ShowcasePresencePanel user={professor}/>)
    await user.click(await screen.findByRole('checkbox',{name:'Ana · RA1'}))
    await user.click(screen.getByRole('button',{name:'Confirmar presença'}))
    expect(recordMemberAttendance).toHaveBeenCalledWith('entry-1',[{member_id:11,present:true},{member_id:12,present:false}])
    expect(await screen.findByText('Presença registrada.')).toBeInTheDocument()
    const note=await screen.findByLabelText('Nota (0 a 10)')
    expect(note).toHaveFocus()
    await user.type(note,'8.5')
    await user.type(screen.getByLabelText('Observações'),'Boa apresentação')
    await user.click(screen.getByRole('button',{name:'Salvar avaliação'}))
    expect(recordShowcaseGrade).toHaveBeenCalledWith('entry-1','8.5','Boa apresentação')
    expect(await screen.findByText('Avaliação concluída · Nota: 8.50')).toBeInTheDocument()
  })

  it('confirma ausência total sem abrir nota',async()=>{
    const members=[{member_id:11,name:'Ana',ra:'RA1',present:null}]
    vi.mocked(listShowcaseEntries).mockResolvedValue([{...entry,is_evaluator:true,members}])
    vi.mocked(recordMemberAttendance).mockResolvedValue({...entry,is_evaluator:true,status:'ABSENT',members:[{...members[0],present:false}]})
    const user=userEvent.setup();render(<ShowcasePresencePanel user={professor}/>)
    await user.click(await screen.findByRole('button',{name:'Confirmar presença'}))
    expect(await screen.findByText('Ausência registrada.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Nota (0 a 10)')).not.toBeInTheDocument()
  })

  it('retoma avaliação depois de recarregar e preserva campos após falha',async()=>{
    vi.mocked(listShowcaseEntries).mockResolvedValue([{...entry,is_evaluator:true,status:'PRESENTED',members:[{member_id:11,name:'Ana',ra:'RA1',present:true}]}])
    vi.mocked(recordShowcaseGrade).mockRejectedValue(new Error('Falha de conexão'))
    const user=userEvent.setup();render(<ShowcasePresencePanel user={professor}/>)
    await user.click(await screen.findByRole('button',{name:'Avaliar grupo'}))
    await user.type(screen.getByLabelText('Nota (0 a 10)'),'0')
    await user.type(screen.getByLabelText('Observações'),'Reavaliar')
    await user.click(screen.getByRole('button',{name:'Salvar avaliação'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('Falha de conexão')
    expect(screen.getByLabelText('Nota (0 a 10)')).toHaveValue(0)
    expect(screen.getByLabelText('Observações')).toHaveValue('Reavaliar')
  })

  it('permite complementar presença legada sem presumir presentes',async()=>{
    vi.mocked(listShowcaseEntries).mockResolvedValue([{...entry,is_evaluator:true,status:'PRESENTED',members:[{member_id:11,name:'Ana',ra:'RA1',present:null}]}])
    render(<ShowcasePresencePanel user={professor}/>)
    expect(await screen.findByRole('checkbox',{name:'Ana · RA1'})).not.toBeChecked()
    expect(screen.getByRole('button',{name:'Confirmar presença'})).toBeEnabled()
    expect(screen.queryByRole('button',{name:'Avaliar grupo'})).not.toBeInTheDocument()
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
  it('mostra integrantes e resumo no card público sem liberar PDF privado',async()=>{
    vi.mocked(listAcervoPublico).mockResolvedValue([acervoItem])
    render(<PublicAcervoPanel/>)
    expect(await screen.findByText('Projeto Cidadania')).toBeInTheDocument()
    expect(screen.getByText(/Ana · Bia/)).toBeInTheDocument()
    expect(screen.getByText(/Ações de cidadania na comunidade/)).toBeInTheDocument()
    expect(screen.queryByRole('link',{name:/Ler PDF/})).not.toBeInTheDocument()
  })
  it('informa quando publicação antiga não possui integrantes e resumo',async()=>{
    vi.mocked(listAcervo).mockResolvedValue([{...acervoItem,members:[],abstract:''}])
    render(<AcervoPanel/>)
    expect(await screen.findByText(/Integrantes não informados nesta versão/)).toBeInTheDocument()
    expect(screen.getByText(/Resumo não informado nesta versão/)).toBeInTheDocument()
  })
  it('lista projetos publicados',async()=>{
    vi.mocked(listAcervo).mockResolvedValue([acervoItem])
    render(<AcervoPanel/>)
    expect(await screen.findByText('Acervo de projetos publicados')).toBeInTheDocument()
    expect(await screen.findByText('Projeto Cidadania')).toBeInTheDocument()
    expect(screen.getByText(/Ana · Bia/)).toBeInTheDocument()
    expect(screen.getByText(/Ações de cidadania na comunidade/)).toBeInTheDocument()
    const link=screen.getByRole('link',{name:'Projeto Cidadania'})
    expect(link).toHaveAttribute('href','/api/v1/projects/acervo/pub-1/pdf/')
    expect(link).toHaveAttribute('target','_blank')
    expect(screen.getByRole('link',{name:/Ler PDF/})).toHaveAttribute('href',link.getAttribute('href'))
  })

  it('pesquisa por titulo',async()=>{
    vi.mocked(listAcervo).mockResolvedValue([acervoItem])
    const user=userEvent.setup();render(<AcervoPanel/>)
    await user.type(screen.getByLabelText('Buscar'),'Cidadania')
    await user.click(screen.getByRole('button',{name:'Pesquisar'}))
    expect(listAcervo).toHaveBeenCalledWith('Cidadania')
  })
})
