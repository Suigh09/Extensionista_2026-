import {useCallback,useEffect,useState,type FormEvent} from 'react'
import {deliveryDownloadUrl,forwardProject,getForwarding,listDeliveries,listForwarded,reviewDelivery,submitDelivery,type Delivery,type Forwarding,type Profile,type Project} from './api'

const saved=()=>window.dispatchEvent(new Event('platform:changes-saved'))
const navigate=(hash:string)=>window.dispatchEvent(new CustomEvent('platform:navigate',{detail:hash}))
const failure=(error:unknown)=>error instanceof Error?error.message:'Não foi possível concluir a operação.'
const deliveryLabels:Record<Delivery['status'],string>={SUBMITTED:'Aguardando avaliação',APPROVED:'Aprovada',CHANGES_REQUESTED:'Ajustes solicitados'}

export function DeliveriesPanel({project,user}:{project:Project;user:Profile}){
  const[deliveries,setDeliveries]=useState<Delivery[]>([]),[forwarding,setForwarding]=useState<Forwarding|null>(null),[pendingForward,setPendingForward]=useState<{observations:string;required_competencies:string}|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(true)
  const terminal=['CANCELLED','COMPLETED','ARCHIVED'].includes(project.status)
  const professor=user.role!=='STUDENT',manager=project.can_manage!==false
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{
      setDeliveries(await listDeliveries(project.id))
      try{setForwarding(await getForwarding(project.id))}catch{setForwarding(null)}
    }catch(e){setMessage(failure(e))}finally{setBusy(false)}
  },[project.id])
  useEffect(()=>{void refresh()},[refresh])
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const form=event.currentTarget
    const data=new FormData(form)
    const picked=(form.querySelector('input[name="document"]') as HTMLInputElement|null)?.files?.[0]
    setMessage('')
    if(!picked||picked.size===0){setMessage('Anexe o documento da entrega.');return}
    try{
      setDeliveries(await submitDelivery(project.id,data).then(async()=>listDeliveries(project.id)))
      form.reset();saved();setMessage('Entrega enviada ao orientador.')
    }catch(e){setMessage(failure(e))}
  }
  async function review(delivery:Delivery,decision:'APPROVED'|'CHANGES_REQUESTED',form:HTMLFormElement){
    setMessage('')
    try{
      await reviewDelivery(delivery.id,decision,String(new FormData(form).get('feedback')||''))
      saved();await refresh();setMessage(decision==='APPROVED'?'Entrega aprovada.':'Ajustes solicitados ao grupo.')
    }catch(e){setMessage(failure(e))}
  }
  async function forward(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const data=new FormData(event.currentTarget)
    setPendingForward({observations:String(data.get('observations')||''),required_competencies:String(data.get('required_competencies')||'')})
  }
  async function confirmForward(){
    if(!pendingForward)return
    setMessage('');setBusy(true)
    try{
      setForwarding(await forwardProject(project.id,pendingForward))
      setPendingForward(null);saved();setMessage('Projeto encaminhado à secretaria.')
    }catch(e){setMessage(failure(e))}finally{setBusy(false)}
  }
  return <section className="profile-section" aria-labelledby="deliveries-title"><h3 id="deliveries-title">Entregas formais</h3><p>Cada versão congela o documento e o conteúdo da proposta. Follow-ups continuam livres e não contam como entrega.</p>{message&&<p role="status" className="alert">{message}</p>}{forwarding&&<p role="status" className="alert">Encaminhado à secretaria em {new Date(forwarding.forwarded_at).toLocaleString('pt-BR')} por {forwarding.forwarded_by_name}.</p>}{busy?<p>Carregando entregas…</p>:deliveries.length===0?<p className="empty-state">Nenhuma entrega enviada.</p>:<ol>{deliveries.map(item=><li key={item.id}><article className="project-card"><h4>Versão {item.version} · {deliveryLabels[item.status]}</h4><p>{item.title_snapshot}</p><p><a href={deliveryDownloadUrl(item.download_url)}>{item.original_name}</a> <small>{(item.size/1024/1024).toFixed(2)} MB</small></p><small>Enviada por {item.submitted_by_name} em {new Date(item.submitted_at).toLocaleString('pt-BR')}</small>{item.review_feedback&&<p><strong>Parecer:</strong> {item.review_feedback}</p>}{professor&&manager&&!terminal&&item.status==='SUBMITTED'&&<form className="project-form compact" onSubmit={event=>{event.preventDefault();void review(item,(event.nativeEvent as SubmitEvent).submitter?.getAttribute('value')==='APPROVED'?'APPROVED':'CHANGES_REQUESTED',event.currentTarget)}}><label>Parecer<textarea name="feedback" rows={3} maxLength={2000}/></label><div className="action-row"><button className="button" value="APPROVED">Aprovar entrega</button><button className="button secondary" value="CHANGES">Solicitar ajustes</button></div></form>}</article></li>)}</ol>}{!terminal&&!professor&&project.status==='APPROVED'&&<details><summary>Nova entrega</summary><form className="project-form" onSubmit={submit}><label>Documento da entrega<input name="document" type="file" accept=".pdf,.docx,.xlsx,.pptx,.txt,.csv,.jpg,.jpeg,.png,.webp,.zip"/><small>Arquivo único, até 25 MB. Executáveis e macros não são aceitos.</small></label><label>Observações da versão<textarea name="notes" rows={3} maxLength={2000}/></label><button className="button">Enviar entrega</button></form></details>}{!terminal&&!forwarding&&professor&&manager&&<details><summary>Encaminhar à secretaria</summary><form className="project-form" onSubmit={forward}><p>Exige entrega aprovada de todos os grupos. A secretaria não devolve o encaminhamento.</p><label>Observações ao setor<textarea name="observations" rows={3} maxLength={2000}/></label><label>Competências requeridas do avaliador<textarea name="required_competencies" rows={3} maxLength={2000}/></label><button className="button">Revisar encaminhamento</button></form></details>}{pendingForward&&!forwarding&&<div className="modal-backdrop"><section className="confirmation-modal" role="dialog" aria-modal="true" aria-labelledby="forward-title"><h2 id="forward-title">Encaminhar projeto?</h2><p>Esta decisão é registrada e a secretaria não devolve o encaminhamento.</p><p><strong>Observações:</strong> {pendingForward.observations||'—'}</p><p><strong>Competências:</strong> {pendingForward.required_competencies||'—'}</p><div className="action-row"><button type="button" className="button secondary" disabled={busy} onClick={()=>setPendingForward(null)}>Voltar</button><button type="button" className="button" disabled={busy} onClick={()=>void confirmForward()}>{busy?'Enviando…':'Confirmar encaminhamento'}</button></div></section></div>}</section>
}

export function ForwardedQueue(){
  const[items,setItems]=useState<Forwarding[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(true)
  useEffect(()=>{listForwarded().then(setItems).catch(e=>setMessage(failure(e))).finally(()=>setBusy(false))},[])
  return <section aria-labelledby="forwarded-title"><div className="subheading"><h2 id="forwarded-title">Recebidos da orientação</h2><p>Projetos encaminhados aguardando designação de avaliador.</p></div>{message&&<p role="alert" className="alert error">{message}</p>}{busy?<p>Carregando recebidos…</p>:items.length===0?<p className="empty-state">Nenhum encaminhamento recebido.</p>:items.map(item=><article className="project-card" key={item.project}><h3>{item.project_name}</h3><p><strong>Observações:</strong> {item.observations||'—'}</p><p><strong>Competências requeridas:</strong> {item.required_competencies||'—'}</p><small>Encaminhado por {item.forwarded_by_name} em {new Date(item.forwarded_at).toLocaleString('pt-BR')}</small><div className="action-row"><button className="button" onClick={()=>navigate(`#/projects/${item.project}`)}>Abrir projeto</button></div></article>)}</section>
}
