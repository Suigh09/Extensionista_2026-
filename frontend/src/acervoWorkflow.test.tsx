import {cleanup,render,screen} from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import {afterEach,describe,expect,it,vi} from 'vitest'
import {AcervoWorkflowPage,AcervoWorkflowPanel} from './acervoWorkflow'
import {actOnAcervoWorkflow,getAcervoWorkflow,listAcervoWorkflows,withdrawPublication,type AcervoVersion,type AcervoWorkflow,type Publication} from './api'

vi.mock('./api',()=>({getAcervoWorkflow:vi.fn(),actOnAcervoWorkflow:vi.fn(),listAcervoWorkflows:vi.fn(),withdrawPublication:vi.fn(),publicationDocumentDownloadUrl:(id:string)=>`/pdf/${id}`}))
afterEach(()=>{cleanup();vi.resetAllMocks()})
const base:AcervoWorkflow={project:'p',project_name:'Projeto Ambiental',number:2,snapshot:{project_id:'p',project_name:'Projeto Ambiental',year:2026,advisors:['Orientador'],members:[{name:'Ana',course:'Computação'},{name:'Bia',course:'Computação'}]},blockers:[],permissions:{leader:true,advisor:false,secretariat:false},versions:[],state:'NOT_STARTED',publication:null,results:[{group:'g',name:'Grupo A',grade:'8.75',concluded:true,observations:'Boa apresentação',members:[{name:'Ana',ra:'RA1',present:true},{name:'Bia',ra:'RA2',present:false}]}]}
const version={id:'v1',version:1,title:'Título original',abstract:'Resumo original',content:'Texto original',generated_by_name:'Ana',created_at:'2026-11-05T12:00:00Z',workflow:'ADVISOR',pdf_sha256:'hash'} as AcervoVersion

describe('fluxo completo do acervo',()=>{
  it('separa edição e PDFs em painéis irmãos e preserva todas as versões',async()=>{
    vi.mocked(getAcervoWorkflow).mockResolvedValue({...base,state:'ADVISOR',versions:[{...version,id:'v2',version:2},version]})
    render(<AcervoWorkflowPanel projectId="p"/>)
    const form=await screen.findByRole('form',{name:'Formulário padronizado do acervo'})
    const versions=screen.getByRole('complementary',{name:'Versões do projeto'})
    expect(form.closest('.acervo-document-editor')?.parentElement).toBe(versions.parentElement)
    expect(versions).toContainElement(screen.getByRole('link',{name:'Baixar PDF da versão 2'}))
    expect(versions).toContainElement(screen.getByRole('link',{name:'Baixar PDF da versão 1'}))
    expect(form).not.toContainElement(versions)
  })
  it('líder envia formulário gerador de PDF com referência à versão vigente',async()=>{
    vi.mocked(getAcervoWorkflow).mockResolvedValue(base)
    vi.mocked(actOnAcervoWorkflow).mockResolvedValue({...base,state:'ADVISOR',versions:[version]})
    const user=userEvent.setup();render(<AcervoWorkflowPanel projectId="p"/>)
    await user.type(await screen.findByLabelText('Resumo'),'Resumo do projeto')
    await user.type(screen.getByLabelText('Descrição do projeto'),'Descrição completa')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button',{name:'Gerar PDF e enviar ao orientador'}))
    expect(actOnAcervoWorkflow).toHaveBeenCalledWith('p',{action:'submit',expected_document:null,title:'Projeto Ambiental',abstract:'Resumo do projeto',content:'Descrição completa',consent:true})
    expect(await screen.findByText('Aguardando revisão do orientador')).toBeInTheDocument()
    expect(screen.getByText(/Bia · RA2 — Ausente/)).toBeInTheDocument()
    expect(screen.getByText('Grupo A · Nota: 8.75 · Concluída')).toBeInTheDocument()
  })

  it('orientador envia correção como nova versão e líder valida a versão exata',async()=>{
    const advisor={...base,permissions:{leader:false,advisor:true,secretariat:false},state:'ADVISOR' as const,versions:[version]}
    vi.mocked(getAcervoWorkflow).mockResolvedValue(advisor)
    const second={...version,id:'v2',version:2,workflow:'LEADER' as const,content:'Texto revisado',generated_by_name:'Orientador'}
    vi.mocked(actOnAcervoWorkflow).mockResolvedValue({...advisor,state:'LEADER',versions:[second,version]})
    const user=userEvent.setup();const mounted=render(<AcervoWorkflowPanel projectId="p"/>)
    await user.click(await screen.findByRole('button',{name:'Revisar texto'}))
    await user.clear(screen.getByLabelText('Descrição do projeto'))
    await user.type(screen.getByLabelText('Descrição do projeto'),'Texto revisado')
    await user.click(screen.getByRole('button',{name:'Enviar correção ao líder'}))
    expect(actOnAcervoWorkflow).toHaveBeenCalledWith('p',expect.objectContaining({action:'correct',expected_document:'v1',content:'Texto revisado'}))
    expect(await screen.findByText('Aguardando validação do líder')).toBeInTheDocument()
    mounted.unmount()
    vi.mocked(getAcervoWorkflow).mockResolvedValue({...base,state:'LEADER',versions:[second,version]})
    vi.mocked(actOnAcervoWorkflow).mockResolvedValue({...base,state:'SECRETARIAT',versions:[{...second,workflow:'SECRETARIAT'},version]})
    render(<AcervoWorkflowPanel projectId="p"/>)
    await user.click(await screen.findByRole('button',{name:'Validar correção e encaminhar à Secretaria'}))
    expect(actOnAcervoWorkflow).toHaveBeenLastCalledWith('p',{action:'accept',expected_document:'v2'})
    expect(await screen.findByText('Aguardando confirmação da Secretaria')).toBeInTheDocument()
    expect(screen.getByText(/Versão 1 · Ana/)).toBeInTheDocument()
    expect(screen.getByRole('link',{name:'Baixar PDF da versão 2'})).toHaveAttribute('href','/pdf/v2')
  })

  it('somente Secretaria recebe confirmação de publicação',async()=>{
    vi.spyOn(window,'confirm').mockReturnValue(true)
    const data={...base,state:'SECRETARIAT' as const,permissions:{leader:false,advisor:false,secretariat:true},versions:[{...version,workflow:'SECRETARIAT' as const}]}
    vi.mocked(getAcervoWorkflow).mockResolvedValue(data)
    vi.mocked(actOnAcervoWorkflow).mockResolvedValue({...data,state:'PUBLISHED',publication:'pub'})
    const user=userEvent.setup();render(<AcervoWorkflowPanel projectId="p"/>)
    await user.click(await screen.findByRole('button',{name:'Confirmar publicação no acervo'}))
    expect(actOnAcervoWorkflow).toHaveBeenCalledWith('p',{action:'publish',expected_document:'v1'})
    expect(await screen.findByText('Publicação confirmada pela Secretaria.')).toBeInTheDocument()
  })

  it('bloqueia integrante não líder e mostra os pré-requisitos reais',async()=>{
    vi.mocked(getAcervoWorkflow).mockResolvedValue({...base,permissions:{leader:false,advisor:false,secretariat:false},blockers:['Falta concluir a avaliação do grupo.']})
    render(<AcervoWorkflowPanel projectId="p"/>)
    expect(await screen.findByText('Falta concluir a avaliação do grupo.')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Gerar PDF e enviar ao orientador'})).not.toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Confirmar publicação no acervo'})).not.toBeInTheDocument()
  })

  it('falha no envio preserva texto e informa que a etapa não foi concluída',async()=>{
    vi.mocked(getAcervoWorkflow).mockResolvedValue(base)
    vi.mocked(actOnAcervoWorkflow).mockRejectedValue(new Error('A versão mudou. Atualize a página.'))
    const user=userEvent.setup();render(<AcervoWorkflowPanel projectId="p"/>)
    await user.type(await screen.findByLabelText('Resumo'),'Resumo não salvo')
    await user.type(screen.getByLabelText('Descrição do projeto'),'Texto não salvo')
    await user.click(screen.getByRole('checkbox'))
    await user.click(screen.getByRole('button',{name:'Gerar PDF e enviar ao orientador'}))
    expect(await screen.findByRole('alert')).toHaveTextContent('A versão mudou')
    expect(screen.getByLabelText('Descrição do projeto')).toHaveValue('Texto não salvo')
  })

  it('fila oferece acesso direto ao fluxo de cada projeto',async()=>{
    vi.mocked(listAcervoWorkflows).mockResolvedValue([{id:'p',name:'Projeto Ambiental',number:2,state:'SECRETARIAT'}])
    render(<AcervoWorkflowPage/>)
    expect(await screen.findByRole('link',{name:'Publicar no Acervo'})).toHaveAttribute('href','#/publication/p')
  })

  it('preserva a retirada pela Secretaria sem permitir nova publicação',async()=>{
    const published={...base,permissions:{leader:false,advisor:false,secretariat:true},publication:'pub',state:'PUBLISHED' as const,versions:[{...version,workflow:'PUBLISHED' as const}]}
    vi.mocked(getAcervoWorkflow).mockResolvedValueOnce(published).mockResolvedValueOnce({...published,state:'WITHDRAWN'})
    vi.mocked(withdrawPublication).mockResolvedValue({id:'pub',withdrawn_at:'2026-11-05T14:00:00Z'} as Publication)
    const user=userEvent.setup();render(<AcervoWorkflowPanel projectId="p"/>)
    await user.click(await screen.findByText('Retirar publicação',{selector:'summary'}))
    await user.type(screen.getByLabelText('Motivo da retirada'),'Solicitação institucional')
    await user.click(screen.getByRole('button',{name:'Confirmar retirada'}))
    expect(withdrawPublication).toHaveBeenCalledWith('pub','Solicitação institucional')
    expect(await screen.findByText('Publicação retirada')).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Confirmar publicação no acervo'})).not.toBeInTheDocument()
  })
})
