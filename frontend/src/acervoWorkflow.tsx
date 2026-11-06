import {useEffect,useId,useState,type FormEvent} from 'react'
import {actOnAcervoWorkflow,getAcervoWorkflow,listAcervoWorkflows,publicationDocumentDownloadUrl,withdrawPublication,type AcervoAction,type AcervoQueueItem,type AcervoVersion,type AcervoWorkflow,type AcervoWorkflowState} from './api'
import './acervoWorkflow.css'

const labels:Record<AcervoWorkflowState,string>={NOT_STARTED:'Aguardando documento do líder',LEGACY:'Documento anterior — reenviar pelo formulário',ADVISOR:'Aguardando revisão do orientador',LEADER:'Aguardando validação do líder',ADMIN:'Aguardando confirmação do Administrador',PUBLISHED:'Publicado no acervo',WITHDRAWN:'Publicação retirada'}
const failure=(error:unknown)=>error instanceof Error?error.message:'Não foi possível concluir a operação.'

export function AcervoWorkflowPage({projectId=''}:{projectId?:string}){
  const[items,setItems]=useState<AcervoQueueItem[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(true)
  useEffect(()=>{
    if(projectId)return
    let active=true
    listAcervoWorkflows().then(value=>{if(active)setItems(value)}).catch(error=>{if(active)setError(failure(error))}).finally(()=>{if(active)setLoading(false)})
    return()=>{active=false}
  },[projectId])
  if(projectId)return <AcervoWorkflowPanel key={projectId} projectId={projectId}/>
  return <section className="profile-section" aria-label="Fluxo do acervo">
    <h2>Publicação no acervo</h2><p>Acompanhe os resultados da Mostra, o documento e a confirmação do Administrador.</p>
    {error&&<p role="alert" className="alert">{error}</p>}
    {loading?<p>Carregando projetos…</p>:items.length===0?<p>Nenhum projeto disponível.</p>:<div className="module-grid">{items.map(item=><article key={item.id} className="project-card"><h3>#{item.number} · {item.name}</h3><p>{labels[item.state]}</p><a className="button" href={`#/publication/${item.id}`}>Publicar no Acervo</a></article>)}</div>}
  </section>
}

export function AcervoWorkflowPanel({projectId}:{projectId:string}){
  const[data,setData]=useState<AcervoWorkflow|null>(null),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false),[editing,setEditing]=useState(false)
  useEffect(()=>{
    let active=true
    getAcervoWorkflow(projectId).then(value=>{if(active)setData(value)}).catch(error=>{if(active)setError(failure(error))})
    return()=>{active=false}
  },[projectId])
  async function act(payload:AcervoAction){
    if(busy)return
    setBusy(true);setError('');setMessage('')
    try{
      const updated=await actOnAcervoWorkflow(projectId,payload)
      setData(updated);setEditing(false)
      setMessage(payload.action==='publish'?'Publicação confirmada pelo Administrador.':'Etapa concluída. O próximo responsável foi notificado.')
      window.dispatchEvent(new Event('platform:changes-saved'))
    }catch(error){setError(failure(error))}
    finally{setBusy(false)}
  }
  async function withdraw(event:FormEvent<HTMLFormElement>){
    event.preventDefault()
    if(!data?.publication||busy)return
    const reason=String(new FormData(event.currentTarget).get('reason')||'').trim()
    if(!reason)return
    setBusy(true);setError('')
    try{
      await withdrawPublication(data.publication,reason)
      setData(await getAcervoWorkflow(projectId))
      setMessage('Publicação retirada. Histórico preservado; não é permitido republicar.')
      window.dispatchEvent(new Event('platform:changes-saved'))
    }catch(error){setError(failure(error))}
    finally{setBusy(false)}
  }
  if(!data)return <section>{error?<p role="alert">{error}</p>:<p>Carregando fluxo do acervo…</p>}</section>
  const latest=data.versions[0]
  const expected=latest?.id??null
  const blocked=data.blockers.length>0
  const canSubmit=data.permissions.leader&&['NOT_STARTED','LEGACY','ADVISOR'].includes(data.state)&&!blocked
  const canReview=data.permissions.advisor&&data.state==='ADVISOR'&&!blocked
  const terminal=['PUBLISHED','WITHDRAWN'].includes(data.state)
  return <section className="profile-section" aria-label="Fluxo do acervo">
    <h2>#{data.number} · {data.project_name}</h2>
    <p role="status"><strong>{labels[data.state]}</strong></p>
    {data.publication_detail&&<p>{data.publication_detail.confirmed_by?`Publicação confirmada por ${data.publication_detail.confirmed_by}`:'Publicação anterior, sem confirmação registrada do Administrador'} · {new Date(data.publication_detail.published_at).toLocaleString('pt-BR')}</p>}
    <p>Líder envia → orientador revisa → líder valida se houver correção → Administrador publica.</p>
    {error&&<p role="alert" className="alert">{error}</p>}{message&&<p role="status" className="alert">{message}</p>}
    {!terminal&&blocked&&<div className="alert"><h3>Pré-requisitos pendentes</h3><ul>{data.blockers.map(reason=><li key={reason}>{reason}</li>)}</ul></div>}
    <section aria-label="Resultados da Mostra"><h3>Resultados recebidos da Mostra</h3>
      <p>A nota é do grupo, inclusive para ausentes. O orientador consulta estes registros e realiza sua avaliação individual em outra plataforma.</p>
      {data.results.map(group=><article key={group.group}><h4>{group.name||'Grupo'} · Nota: {group.grade??'Pendente'}{group.concluded?' · Concluída':''}</h4><p>{group.observations||'Sem observações.'}</p><ul>{group.members.map(member=><li key={member.ra}>{member.name} · {member.ra} — {member.present===null?'Presença não registrada':member.present?'Presente':'Ausente'}</li>)}</ul></article>)}
    </section>
    <section><h3>Dados do documento</h3><p>Projeto: {data.snapshot.project_name} · Ano: {data.snapshot.year}</p><p>Orientador(es): {data.snapshot.advisors.join(', ')}</p><ul>{data.snapshot.members.map((member,index)=><li key={index}>{member.name} · {member.course}</li>)}</ul></section>
    {!data.permissions.leader&&!data.permissions.advisor&&!data.permissions.admin&&<p>Somente o líder representa o grupo no envio e na validação. Você pode consultar os resultados e o histórico.</p>}
    <div className="acervo-document-layout">
    <div className="acervo-document-editor">
    {canSubmit&&<VersionForm key={expected??'initial'} latest={latest} initialTitle={data.project_name} busy={busy} action="submit" onSubmit={values=>void act({...values,action:'submit',expected_document:expected})}/>}
    {canReview&&<div className="action-row"><button className="button" disabled={busy} onClick={()=>void act({action:'approve',expected_document:expected})}>Aprovar sem alterações</button><button className="button secondary" disabled={busy} onClick={()=>setEditing(!editing)}>Revisar texto</button></div>}
    {canReview&&editing&&<VersionForm key={expected} latest={latest} initialTitle={data.project_name} busy={busy} action="correct" onSubmit={values=>void act({...values,action:'correct',expected_document:expected})}/>}
    {data.permissions.leader&&data.state==='LEADER'&&!blocked&&<section><h3>Valide a correção do orientador</h3><p>Leia a versão {latest?.version} no histórico e confira o PDF antes de aceitar. As versões anteriores permanecem disponíveis.</p><button className="button" disabled={busy} onClick={()=>void act({action:'accept',expected_document:expected})}>Validar correção e encaminhar ao Administrador</button></section>}
    {data.permissions.admin&&data.state==='ADMIN'&&!blocked&&<button className="button" disabled={busy} onClick={()=>{if(window.confirm(`Confirmar publicação da versão ${latest?.version} no acervo?`))void act({action:'publish',expected_document:expected})}}>Confirmar publicação no acervo</button>}
    {data.permissions.admin&&data.state==='PUBLISHED'&&<details><summary>Retirar publicação</summary><form className="project-form" onSubmit={event=>void withdraw(event)}><label>Motivo da retirada<textarea name="reason" required maxLength={2000}/></label><button className="button secondary" disabled={busy}>Confirmar retirada</button></form></details>}
    </div>
    <aside className="acervo-document-versions" aria-label="Versões do projeto"><VersionHistory versions={data.versions}/></aside>
    </div>
  </section>
}

function VersionHistory({versions}:{versions:AcervoVersion[]}){
  return <section><h3>Histórico de versões</h3>{versions.length===0?<p>Nenhuma versão enviada.</p>:versions.map((version,index)=><details key={version.id} open={index===0} className="profile-section">
    <summary>Versão {version.version} · {version.generated_by_name} · {new Date(version.created_at).toLocaleString('pt-BR')} · {index===0?labels[version.workflow]:'Histórica'}</summary>
    <h4>{version.title||'Documento anterior'}</h4>
    {version.snapshot?.members&&<p>Integrantes desta versão: {version.snapshot.members.map(member=>`${member.name} (${member.course})`).join(', ')}</p>}
    <p style={{whiteSpace:'pre-wrap'}}>{version.abstract}</p><p style={{whiteSpace:'pre-wrap'}}>{version.content}</p>
    <a className="button secondary" href={publicationDocumentDownloadUrl(version.id)}>Baixar PDF da versão {version.version}</a>
    {version.reviewed_by_name&&<p>Orientador: {version.reviewed_by_name} · {version.review}</p>}
    {version.accepted_at&&<p>Correção validada por {version.accepted_by_name} · {new Date(version.accepted_at).toLocaleString('pt-BR')}</p>}
    {version.pdf_sha256&&<small style={{overflowWrap:'anywhere'}}>SHA-256: {version.pdf_sha256}</small>}
  </details>)}</section>
}

function VersionForm({latest,initialTitle,busy,action,onSubmit}:{latest?:AcervoVersion;initialTitle:string;busy:boolean;action:'submit'|'correct';onSubmit:(values:{title:string;abstract:string;content:string;consent:boolean})=>void}){
  const id=useId()
  const[title,setTitle]=useState(latest?.title||initialTitle),[abstract,setAbstract]=useState(latest?.abstract||''),[content,setContent]=useState(latest?.content||''),[consent,setConsent]=useState(false)
  function submit(event:FormEvent){event.preventDefault();onSubmit({title,abstract,content,consent})}
  return <form className="project-form publication-version-form" aria-label={action==='submit'?'Formulário padronizado do acervo':'Revisão do orientador'} onSubmit={submit}>
    <h3>{action==='submit'?'Elaborar documento publicável':'Correção do documento'}</h3><p>Cada envio cria uma nova versão e um PDF, sem alterar os anteriores. Notas e presenças não entram no documento publicável.</p>
    <fieldset disabled={busy}><legend>Texto da versão</legend>
      <div><label htmlFor={`${id}-title`}>Título</label><input id={`${id}-title`} maxLength={180} required value={title} onChange={event=>setTitle(event.target.value)}/></div>
      <div><label htmlFor={`${id}-abstract`}>Resumo</label><textarea id={`${id}-abstract`} maxLength={4000} rows={4} required value={abstract} onChange={event=>setAbstract(event.target.value)}/></div>
      <div><label htmlFor={`${id}-content`}>Descrição do projeto</label><textarea id={`${id}-content`} maxLength={40000} rows={12} required value={content} onChange={event=>setContent(event.target.value)}/></div>
      {action==='submit'&&<label className="publication-consent"><input type="checkbox" required checked={consent} onChange={event=>setConsent(event.target.checked)}/><span>Confirmo o encaminhamento desta versão para publicação e o consentimento para uso dos dados do documento no acervo.</span></label>}
      <button className="button" type="submit">{busy?'Enviando…':action==='submit'?'Gerar PDF e enviar ao orientador':'Enviar correção ao líder'}</button>
    </fieldset>
  </form>
}
