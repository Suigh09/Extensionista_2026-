import {useCallback,useEffect,useState,type FormEvent} from 'react'
import {cancelShowcaseEntry,createShowcaseEntry,createPublicationDocument,listAcervo,listPublicationDocuments,listPublications,listShowcaseEntries,publishProject,publicationDocumentDownloadUrl,recordPresence,reviewPublicationDocument,withdrawPublication,type AcervoItem,type Publication,type PublicationDocument,type ShowcaseEntry,type Profile,type Project} from './api'

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

export function PublicationPanel({project,user}:{project:Project;user:Profile}){
  const[publications,setPublications]=useState<Publication[]>([])
  const[message,setMessage]=useState('')
  const[busy,setBusy]=useState(true)
  const[publishing,setPublishing]=useState<{project:string;document:string}|null>(null)
  const student=user.role==='STUDENT'
  const secretariat=user.role==='SECRETARIAT'||user.role==='ADMIN'
  const isMember=project.groups?.some(group=>group.members.some(member=>member.user_id===user.id))??false
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{setPublications(await listPublications())}catch(e){setMessage(failure(e))}
    finally{setBusy(false)}
  },[])
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
            <label>Documento publicável<select name="document" required><option value="">Selecione um documento aprovado</option></select></label>
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
      <div className="showcase-header">
        <div>
          <span className="eyebrow">Acervo</span>
          <h2 id="acervo-title">Acervo de projetos publicados</h2>
          <p>Consulta a projetos apresentados na Mostra e publicados com documento aprovado.</p>
        </div>
      </div>
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
