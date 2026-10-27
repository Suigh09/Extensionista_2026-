import {useCallback,useEffect,useState,type FormEvent} from 'react'
import {cancelShowcaseEntry,createShowcaseEntry,createPublicationDocument,listAcervo,listAcervoPublico,listProfessorProjects,listPublicationDocuments,listPublications,listShowcaseEntries,publishProject,publicationDocumentDownloadUrl,recordPresence,reviewPublicationDocument,updatePublicationDocumentContent,withdrawPublication,individualGrades,gradeIndividual,type AcervoItem,type AcervoPublicItem,type Publication,type PublicationDocument,type ShowcaseEntry,type Profile,type Project,type IndividualGrade} from './api'

const saved=()=>window.dispatchEvent(new Event('platform:changes-saved'))
const failure=(error:unknown)=>error instanceof Error?error.message:'Não foi possível concluir a operação.'
const showcaseStatusLabels:Record<ShowcaseEntry['status'],string>={PENDING:'Pendente',SCHEDULED:'Agendado',PRESENTED:'Apresentado',ABSENT:'Ausente',CANCELLED:'Cancelado'}
const documentStatusLabels:Record<PublicationDocument['status'],string>={PENDING:'Pendente',APPROVED:'Aprovado',REJECTED:'Reprovado'}

export function ShowcasePanel({user}:{user:Profile}){
  const[entries,setEntries]=useState<ShowcaseEntry[]>([])
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const secretariat=user.role==='SECRETARIAT'||user.role==='ADMIN'
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{setEntries(await listShowcaseEntries())}catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[])
  useEffect(()=>{void refresh()},[refresh])
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const form=event.currentTarget;const data=new FormData(form)
    setMessage('')
    try{
      await createShowcaseEntry({group:String(data.get('group')),date:String(data.get('date')),location:String(data.get('location'))})
      form.reset();saved();setMessage('Mostra agendada.');await refresh()
    }catch(e){setMessage(failure(e))}
  }
  async function cancel(entryId:string,reason:string){
    setMessage('')
    try{
      setEntries(entries.map(e=>e.id===entryId?{...e,status:'CANCELLED',notes:reason}:e))
      await cancelShowcaseEntry(entryId,reason)
      saved();setMessage('Entrada cancelada.');await refresh()
    }catch(e){await refresh();setMessage(failure(e))}
  }
  if(!secretariat)return null
  return (
    <section className="profile-section" aria-labelledby="showcase-title">
      <div className="showcase-header">
        <div>
          <span className="eyebrow">Mostra Extensionista</span>
          <h2 id="showcase-title">Agenda da Mostra</h2>
          <p>Secretaria agenda a apresentação de grupos encaminhados.</p>
        </div>
      </div>
      {busy?<p>Carregando agenda…</p>:(
        <form className="project-form compact" onSubmit={submit}>
          <h3>Agendar apresentação</h3>
          <label>Grupo (UUID)<input name="group" required/></label>
          <label>Data e hora<input name="date" type="datetime-local" required/></label>
          <label>Local<input name="location" required maxLength={200}/></label>
          <button className="button" type="submit">Agendar</button>
        </form>
      )}
      {message&&<p role="status" className="alert">{message}</p>}
      <div className="subheading">
        <h3>Agenda</h3>
        <p>Entradas da Mostra por grupo.</p>
      </div>
      {entries.length===0?<p className="empty-state">Nenhuma entrada agendada.</p>:(
        <table className="data-table">
          <thead>
            <tr>
              <th>Grupo/Projeto</th><th>Data</th><th>Local</th><th>Status</th><th>Ação</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(entry=>
              <tr key={entry.id}>
                <td><strong>{entry.project_name}</strong><br/><small>{entry.group_name}</small></td>
                <td>{new Date(entry.date).toLocaleString('pt-BR')}</td>
                <td>{entry.location}</td>
                <td><span className={`badge ${entry.status==='SCHEDULED'?'neutral':entry.status==='PRESENTED'?'positive':'negative'}`}>{showcaseStatusLabels[entry.status]}</span></td>
                <td>{entry.status==='SCHEDULED'&&<button className="button secondary danger" onClick={()=>{if(!window.confirm('Motivo do cancelamento?'))return;void cancel(entry.id,'')}}>Cancelar</button>}</td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </section>
  )
}

export function ShowcasePresencePanel({user}:{user:Profile}){
  const[entries,setEntries]=useState<ShowcaseEntry[]>([])
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const professor=user.role==='PROFESSOR'
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{setEntries(await listShowcaseEntries())}catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[])
  useEffect(()=>{void refresh()},[refresh])
  async function record(entryId:string,status:'PRESENTED'|'ABSENT',notes:string){
    setMessage('')
    try{
      await recordPresence(entryId,status,notes)
      saved();setMessage(status==='PRESENTED'?'Presença registrada.':'Ausência registrada.');await refresh()
    }catch(e){setMessage(failure(e))}
  }
  if(!professor)return null
  const mine=entries.filter(entry=>entry.is_evaluator)
  return (
    <section className="profile-section" aria-labelledby="presence-title">
      <div className="showcase-header">
        <div>
          <span className="eyebrow">Mostra Extensionista</span>
          <h2 id="presence-title">Registro de presença</h2>
          <p>Avaliador designado registra apresentação ou ausência do grupo.</p>
        </div>
      </div>
      {message&&<p role="status" className="alert">{message}</p>}
      <div className="subheading">
        <h3>Minhas avaliações</h3>
        <p>Grupos para os quais você foi designado como avaliador.</p>
      </div>
      {busy?<p>Carregando…</p>:mine.length===0?<p className="empty-state">Nenhum grupo designado a você.</p>:(
        <table className="data-table">
          <thead>
            <tr><th>Grupo/Projeto</th><th>Data</th><th>Status</th><th>Registrar</th></tr>
          </thead>
          <tbody>
            {mine.map(entry=>entry.status!=='SCHEDULED'?null:(
              <tr key={entry.id}>
                <td><strong>{entry.project_name}</strong><br/><small>{entry.group_name}</small></td>
                <td>{new Date(entry.date).toLocaleString('pt-BR')}</td>
                <td>{showcaseStatusLabels[entry.status]}</td>
                <td>
                  <div className="action-row">
                    <button className="button" onClick={()=>void record(entry.id,'PRESENTED','')}>Apresentado</button>
                    <button className="button secondary" onClick={()=>void record(entry.id,'ABSENT','')}>Ausente</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export function PublicationDocumentPanel({project,user}:{project:Project;user:Profile}){
  const[documents,setDocuments]=useState<PublicationDocument[]>([])
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const[uploading,setUploading]=useState<{file:File|null}|null>(null)
  const student=user.role==='STUDENT'
  const professor=user.role==='PROFESSOR'
  const isMember=project.groups?.some(group=>group.members.some(member=>member.user_id===user.id))??false
  const isOrientador=professor&&(project.groups?.some(group=>group.responsible_professor_name&&project.groups?.some(g=>g.responsible_professor_name===user.name))??false)
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{setDocuments(await listPublicationDocuments(project.id))}catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[project.id])
  useEffect(()=>{void refresh()},[refresh])
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const form=event.currentTarget
    const file=(form.querySelector('input[name="pdf"]') as HTMLInputElement|null)?.files?.[0]
    const consent=form.querySelector('input[name="consent"]') as HTMLInputElement|null
    const consentGiven=consent?.checked===true
    if(!file){setMessage('Selecione o PDF.');return}
    setMessage('');setUploading({file})
    try{
      await createPublicationDocument({project:project.id,file,consent_given:consentGiven})
      form.reset();saved();setMessage('Documento gerado e enviado para aprovação.');await refresh()
    }catch(e){setUploading({file:null});setMessage(failure(e))}
  }
  async function review(documentId:string,status:'APPROVED'|'REJECTED',form:HTMLFormElement){
    setMessage('')
    try{
      await reviewPublicationDocument(documentId,status,String(new FormData(form).get('review')||''))
      saved();setMessage(status==='APPROVED'?'Documento aprovado.':'Documento reprovado.');await refresh()
    }catch(e){setMessage(failure(e))}
  }
  if(!student&&!professor)return null
  return (
    <section className="profile-section" aria-labelledby="document-title">
      <div className="showcase-header">
        <div>
          <span className="eyebrow">Documento publicável</span>
          <h2 id="document-title">Documento do projeto</h2>
          <p>O aluno gera o PDF padronizado e o orientador aprova ou reprova.</p>
        </div>
      </div>
      {message&&<p role="status" className="alert">{message}</p>}
      <div className="subheading">
        <h3>Documentos gerados</h3>
        <p>Cada geração preserva a versão anterior.</p>
      </div>
      {busy?<p>Carregando documentos…</p>:documents.length===0?<p className="empty-state">Nenhum documento gerado.</p>:(
        <table className="data-table">
          <thead>
            <tr><th>Versão</th><th>Arquivo</th><th>Tamanho</th><th>Status</th><th>Parecer</th><th>Ação</th></tr>
          </thead>
          <tbody>
            {documents.map(doc=>
              <tr key={doc.id}>
                <td>{doc.version}</td>
                <td><a href={publicationDocumentDownloadUrl(doc.id)}>{doc.original_name}</a></td>
                <td>{(doc.size/1024/1024).toFixed(2)} MB</td>
                <td><span className={`badge ${doc.status==='APPROVED'?'positive':doc.status==='REJECTED'?'negative':'neutral'}`}>{documentStatusLabels[doc.status]}</span></td>
                <td>{doc.review||'—'}</td>
                <td>
                  {doc.status==='PENDING'&&isOrientador?(
                    <form className="project-form compact" onSubmit={event=>{
                      event.preventDefault()
                      const submitter=(event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement|null
                      void review(doc.id,submitter?.getAttribute('value')==='APPROVED'?'APPROVED':'REJECTED',event.currentTarget)
                    }}>
                      <div className="action-row">
                        <button className="button" value="APPROVED">Aprovar</button>
                        <button className="button secondary" value="REJECTED">Reprovar</button>
                      </div>
                      <label>Parecer<textarea name="review" rows={2} maxLength={2000}/></label>
                    </form>
                  ):doc.status!=='PENDING'?<span>{doc.status==='APPROVED'?'Orientador aprovou.':'Orientador reprovou.'}</span>:null}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {student&&isMember&&!uploading&&(
        <details className="project-form">
          <summary>Gerar novo documento</summary>
          <form onSubmit={submit}>
            <label>Arquivo PDF<input name="pdf" type="file" accept=".pdf" required/><small>Até 10 MB.</small></label>
            <label><input name="consent" type="checkbox"/> Doy consentimento para uso do meu nome e curso no acervo público.</label>
            <button className="button" type="submit">Gerar documento</button>
          </form>
        </details>
      )}
      {uploading&&<p>Enviando PDF…</p>}
    </section>
  )
}

export function PublicationFormPanel({project,user}:{project:Project;user:Profile}){
  const[documents,setDocuments]=useState<PublicationDocument[]>([])
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const[content,setContent]=useState('')
  const[consentGiven,setConsentGiven]=useState(false)
  const student=user.role==='STUDENT'
  const isMember=project.groups?.some(group=>group.members.some(member=>member.user_id===user.id))??false
  const canEdit=student&&isMember
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{setDocuments(await listPublicationDocuments(project.id))}catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[project.id])
  useEffect(()=>{void refresh()},[refresh])
  const latest=documents[0]
  const isPending=latest&&latest.status==='PENDING'
  const isApproved=latest&&latest.status==='APPROVED'
  const isRejected=latest&&latest.status==='REJECTED'
  useEffect(()=>{
    setContent(latest?.content||'')
    setConsentGiven(latest?.consent_given??false)
  },[latest])
  async function saveDraft(){
    if(!canEdit){setMessage('Você não pode editar este documento.');return}
    if(!latest){setMessage('Não há documento para editar. Gere um primeiro no painel de documentos.');return}
    if(!isPending){setMessage('Somente documentos pendentes podem ser editados.');return}
    setMessage('');setBusy(true)
    try{
      await updatePublicationDocumentContent(latest.id,content)
      saved();setMessage('Rascunho salvo.');await refresh()
    }catch(e){setBusy(false);setMessage(failure(e))}
  }
  async function publish(){
    if(!latest||!isApproved){setMessage('O documento precisa estar aprovado para publicar.');return}
    setMessage('');setBusy(true)
    try{
      await publishProject({project:project.id,document:latest.id})
      saved();setMessage('Projeto publicado no acervo.');await refresh()
    }catch(e){setBusy(false);setMessage(failure(e))}
  }
  if(!student)return null
  const membros=project.groups?.flatMap(g=>g.members.map(m=>m.name)).join(', ')||'—'
  return (
    <section className="profile-section" aria-labelledby="form-title">
      <div className="showcase-header">
        <div>
          <span className="eyebrow">Formulário do documento</span>
          <h2 id="form-title">Elaborar documento do projeto</h2>
          <p>Preencha o conteúdo. O documento fica editável até o orientador aprovar.</p>
        </div>
      </div>
      {message&&<p role="status" className="alert">{message}</p>}
      <div className="subheading"><h3>Projeto</h3><p>{project.name}</p></div>
      <div className="subheading"><h3>Integrantes</h3><p>{membros}</p></div>
      {latest&&(
        <div className="subheading">
          <h3>Status</h3>
          <span className={`badge ${isApproved?'positive':isRejected?'negative':'neutral'}`}>{documentStatusLabels[latest.status]}</span>
          {latest.review&&<small> Parecer: {latest.review}</small>}
        </div>
      )}
      {!latest&&(
        <p>Não há documento gerado para este projeto. Use o painel "Documento publicável" para gerar o primeiro documento.</p>
      )}
      {canEdit&&isPending&&latest&&(
        <form className="project-form" onSubmit={event=>{
          event.preventDefault();void saveDraft()
        }}>
          <label>Conteúdo do documento<textarea name="content" rows={12} value={content} onChange={event=>setContent(event.currentTarget.value)} required/></label>
          <label><input name="consent" type="checkbox" checked={consentGiven} onChange={event=>setConsentGiven(event.currentTarget.checked)}/> Doy consentimento para uso do meu nome e curso no acervo público.</label>
          <div className="action-row">
            <button className="button" type="submit" disabled={busy}>{busy?'Salvando…':'Salvar rascunho'}</button>
          </div>
        </form>
      )}
      {canEdit&&isApproved&&latest&&(
        <p>O documento foi aprovado pelo orientador. Não é mais possível editar.</p>
      )}
      {canEdit&&isRejected&&latest&&(
        <p>O documento foi reprovado. Você pode editar o conteúdo e salvar novamente.</p>
      )}
      {isApproved&&canEdit&&latest&&(
        <div className="action-row">
          <button className="button" onClick={publish} disabled={busy}>{busy?'Publicando…':'Publicar no acervo'}</button>
        </div>
      )}
    </section>
  )
}

export function PublicationPanel({project,user}:{project:Project;user:Profile}){
  const[publications,setPublications]=useState<Publication[]>([])
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const[publishing,setPublishing]=useState<{project:string;document:string}|null>(null)
  const[approvedDocs,setApprovedDocs]=useState<PublicationDocument[]>([])
  const student=user.role==='STUDENT'
  const secretariat=user.role==='SECRETARIAT'||user.role==='ADMIN'
  const isMember=project.groups?.some(group=>group.members.some(member=>member.user_id===user.id))??false
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{
      await Promise.all([
        listPublications().then(setPublications),
        listPublicationDocuments(project.id).then(docs=>setApprovedDocs(docs.filter(d=>d.status==='APPROVED')))
      ])
    }catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[project.id])
  useEffect(()=>{void refresh()},[refresh])
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const form=event.currentTarget;const data=new FormData(form)
    setMessage('')
    setPublishing({project:project.id,document:String(data.get('document'))})
    try{
      await publishProject({project:project.id,document:String(data.get('document'))})
      form.reset();saved();setMessage('Projeto publicado no acervo.');await refresh()
    }catch(e){setPublishing(null);setMessage(failure(e))}
  }
  async function withdraw(publicationId:string,reason:string){
    setMessage('')
    try{
      await withdrawPublication(publicationId,reason)
      saved();setMessage('Publicação retirada do acervo.');await refresh()
    }catch(e){setMessage(failure(e))}
  }
  const mine=publications.filter(p=>p.project===project.id)
  if(!student&&!secretariat)return null
  return (
    <section className="profile-section" aria-labelledby="publication-title">
      <div className="showcase-header">
        <div>
          <span className="eyebrow">Acervo</span>
          <h2 id="publication-title">Publicação do projeto</h2>
          <p>Projeto apresentado + documento aprovado = publicação no acervo.</p>
        </div>
      </div>
      {message&&<p role="status" className="alert">{message}</p>}
      <div className="subheading">
        <h3>Publicações deste projeto</h3>
      </div>
      {busy?<p>Carregando…</p>:mine.length===0?<p className="empty-state">Nenhuma publicação.</p>:(
        <table className="data-table">
          <thead>
            <tr><th>Documento</th><th>Versão</th><th>Publicado em</th><th>Situação</th><th>Ação</th></tr>
          </thead>
          <tbody>
            {mine.map(pub=>
              <tr key={pub.id}>
                <td>{pub.document_version}</td>
                <td>{pub.document_status}</td>
                <td>{pub.published_at?new Date(pub.published_at).toLocaleString('pt-BR'):'—'}</td>
                <td>{pub.withdrawn_at?'Retirada':'Publicada'}</td>
                <td>{secretariat&&!pub.withdrawn_at?(
                  <button className="button secondary danger" onClick={()=>{
                    if(!window.confirm('Motivo da retirada?'))return
                    void withdraw(pub.id,'')
                  }}>Retirar</button>
                ):'—'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
      {student&&isMember&&mine.length===0&&!publishing&&(
        <details className="project-form">
          <summary>Publicar no acervo</summary>
          <p>O projeto precisa ter sido apresentado na Mostra e o documento aprovado pelo orientador.</p>
          <form onSubmit={submit}>
            <label>Documento publicável<select name="document" required><option value="">Selecione um documento aprovado</option>{approvedDocs.map(doc=><option key={doc.id} value={doc.id}>Versão {doc.version} · {doc.original_name}</option>)}</select></label>
            <button className="button" type="submit">Publicar</button>
          </form>
        </details>
      )}
      {secretariat&&(
        <details className="project-form">
          <summary>Gerenciar publicações</summary>
          <p>Secretaria pode retirar publicações. O histórico é preservado.</p>
        </details>
      )}
    </section>
  )
}

export function PublicAcervoPanel(){
  const[items,setItems]=useState<AcervoPublicItem[]>([])
  const[query,setQuery]=useState('')
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{setItems(await listAcervoPublico(query))}catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[query])
  useEffect(()=>{void refresh()},[refresh])
  return (
    <section className="profile-section" aria-labelledby="acervo-publico-title">
      <header className="showcase-header">
        <div>
          <span className="eyebrow">Acervo público</span>
          <h2 id="acervo-publico-title">Acervo de projetos publicados</h2>
          <p>Acesso público aos metadados de projetos apresentados na Mostra e publicados com documento aprovado.</p>
        </div>
      </header>
      {message&&<p role="status" className="alert">{message}</p>}
      <div className="subheading">
        <h3>Pesquisa</h3>
        <p>Busque por título do projeto.</p>
      </div>
      <form className="project-form compact" onSubmit={event=>{
        event.preventDefault()
        void refresh()
      }}>
        <label>Buscar<input name="q" type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Título do projeto"/></label>
        <button className="button" type="submit">Pesquisar</button>
      </form>
      {busy?<p>Carregando acervo…</p>:items.length===0?<p className="empty-state">Nenhum projeto publicado encontrado.</p>:(
        <div className="acervo-grid">
          {items.map(item=>
            <article key={item.id} className="project-card">
              <h3>{item.project_name}</h3>
              <p>Documento versão {item.document_version}</p>
              <small>Publicado em {new Date(item.published_at).toLocaleString('pt-BR')}</small>
            </article>
          )}
        </div>
      )}
    </section>
  )
}

export function AcervoPanel(){
  const[items,setItems]=useState<AcervoItem[]>([])
  const[query,setQuery]=useState('')
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{setItems(await listAcervo(query))}catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[query])
  useEffect(()=>{void refresh()},[refresh])
  return (
    <section className="profile-section" aria-labelledby="acervo-title">
      <header className="showcase-header">
        <div>
          <span className="eyebrow">Acervo</span>
          <h2 id="acervo-title">Acervo de projetos publicados</h2>
          <p>Consulta a projetos apresentados na Mostra e publicados com documento aprovado.</p>
        </div>
      </header>
      {message&&<p role="status" className="alert">{message}</p>}
      <div className="subheading">
        <h3>Pesquisa</h3>
        <p>Busque por título do projeto.</p>
      </div>
      <form className="project-form compact" onSubmit={event=>{
        event.preventDefault()
        void refresh()
      }}>
        <label>Buscar<input name="q" type="search" value={query} onChange={event=>setQuery(event.target.value)} placeholder="Título do projeto"/></label>
        <button className="button" type="submit">Pesquisar</button>
      </form>
      {busy?<p>Carregando acervo…</p>:items.length===0?<p className="empty-state">Nenhum projeto publicado encontrado.</p>:(
        <div className="acervo-grid">
          {items.map(item=>
            <article key={item.id} className="project-card">
              <h3>{item.project_name}</h3>
              <p>Documento versão {item.document_version}</p>
              <small>Publicado em {new Date(item.published_at).toLocaleString('pt-BR')}</small>
            </article>
          )}
        </div>
      )}
    </section>
  )
}

export function EvaluationsPage({user}:{user:Profile}){
  const[projects,setProjects]=useState<Project[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(true)
  async function refresh(){setBusy(true);try{const data=await listProfessorProjects();setProjects(data.filter(p=>p.status==='APPROVED'&&p.group))}catch(e){setMessage(failure(e))}finally{setBusy(false)}}
  useEffect(()=>{void refresh()},[])
  if(user.role!=='PROFESSOR'&&user.role!=='ADMIN'&&user.role!=='SECRETARIAT')return null
  return (
    <section className="profile-section" aria-labelledby="evaluations-title">
      <div className="showcase-header"><div><span className="eyebrow">Avaliação</span><h2 id="evaluations-title">Avaliações de grupo</h2><p>Avalie projetos aprovados e encaminhados à secretaria.</p></div></div>
      {message&&<p role="status" className="alert">{message}</p>}
      {busy?<p>Carregando avaliações…</p>:projects.length===0?<p className="empty-state">Nenhum projeto aprovado pendente de avaliação.</p>:(
        <div className="module-grid">
          {projects.map(project=><article key={project.id} className="project-card"><div><h3>{project.name}</h3><p>Grupo: {project.group.name} · {project.group.member_count}/4 integrantes</p><p>Avaliador: {project.group.evaluator_name||'Não designado'}</p></div><div className="action-row"><button className="button" onClick={()=>{window.location.hash=`#/group-evaluation/${project.id}`}}>Avaliar grupo</button>{user.role!=='STUDENT'&&project.can_manage&&<button className="button secondary" onClick={()=>{window.location.hash=`#/individual-grades`}}>Notas individuais</button>}</div></article>)}
        </div>
      )}
    </section>
  )
}

export function IndividualGradesPage({user}:{user:Profile}){
  const[projects,setProjects]=useState<Project[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(true),[selectedProject,setSelectedProject]=useState<Project|null>(null),[grades,setGrades]=useState<{current:IndividualGrade|null;history:IndividualGrade[]}|null>(null),[studentBusy,setStudentBusy]=useState(false)
  async function refresh(){setBusy(true);try{const data=await listProfessorProjects();setProjects(data.filter(p=>p.status==='APPROVED'&&p.group))}catch(e){setMessage(failure(e))}finally{setBusy(false)}}
  useEffect(()=>{void refresh()},[])
  async function loadStudentGrades(studentId:string){setStudentBusy(true);try{const data=await individualGrades(studentId);setGrades(data)}catch(e){setMessage(failure(e))}finally{setStudentBusy(false)}}
  async function submitGrade(studentId:string,value:string,comment=''){setStudentBusy(true);try{await gradeIndividual(studentId,{value,comment});setGrades(null);await loadStudentGrades(studentId);setMessage('Nota individual registrada.')}catch(e){setStudentBusy(false);setMessage(failure(e))}}
  if(user.role!=='PROFESSOR')return null
  return (
    <section className="profile-section" aria-labelledby="individual-grades-title">
      <div className="showcase-header"><div><span className="eyebrow">Notas individuais</span><h2 id="individual-grades-title">Notas individuais por aluno</h2><p>Orientador registra nota de 0 a 10 para cada aluno do seu grupo.</p></div></div>
      {message&&<p role="status" className="alert">{message}</p>}
      {busy?<p>Carregando projetos…</p>:projects.length===0?<p className="empty-state">Nenhum projeto aprovado com grupo.</p>:(
        <><div className="subheading"><h3>Escolha o projeto</h3></div>
        {projects.map(project=><button key={project.id} className="button secondary" onClick={()=>{setSelectedProject(project);setGrades(null)}}>{project.name} · Grupo {project.group.name}</button>)}
        {selectedProject&&(
          <><div className="subheading"><h3>{selectedProject.name} · Grupo {selectedProject.group.name}</h3></div>
          {selectedProject.group.members.map(member=><article key={member.user_id} className="project-card"><div><h4>{member.name}</h4><p>RA: {member.ra}</p></div>
          {grades&&grades.current&&grades.current.student===member.user_id?(
            <><p>Nota atual: <strong>{grades.current.value}</strong></p><p>Comentário: {grades.current.comment||'—'}</p><p><small>Registrado em {new Date(grades.current.created_at).toLocaleString('pt-BR')}</small></p></>
          ):(
            <form className="project-form compact" onSubmit={event=>{
              event.preventDefault();const data=new FormData(event.currentTarget);void submitGrade(member.user_id,String(data.get('value')),String(data.get('comment')||''))
            }}>
              <label>Nota (0 a 10)<input name="value" type="number" min="0" max="10" step="0.1" required/></label>
              <label>Comentário<textarea name="comment" rows={2} maxLength={2000}></textarea></label>
              <button className="button" type="submit" disabled={studentBusy}>{studentBusy?'Salvando…':'Salvar nota'}</button>
            </form>
          )}
          {grades&&grades.history.length>0&&(
            <details><summary>Histórico</summary>{grades.history.map(h=><p key={h.id}>{h.value} · {new Date(h.created_at).toLocaleString('pt-BR')}</p>)}</details>
          )}
          </article>)}
          </>
        )}
        </>
      )}
    </section>
  )
}
