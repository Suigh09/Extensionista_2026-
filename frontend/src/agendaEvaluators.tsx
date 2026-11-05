import {useEffect,useState,type FormEvent} from 'react'
import {designateEvaluator,getGroupEvaluatorOptions,type GroupEvaluatorOptions} from './api'

const saved=()=>window.dispatchEvent(new Event('platform:changes-saved'))

export function AgendaEvaluatorPicker({group,projectName,onClose,onAssigned}:{group:string;projectName:string;onClose:()=>void;onAssigned:()=>Promise<void>}){
  const[data,setData]=useState<GroupEvaluatorOptions|null>(null),[selected,setSelected]=useState('')
  const[error,setError]=useState(''),[busy,setBusy]=useState(false)
  useEffect(()=>{
    let active=true
    getGroupEvaluatorOptions(group).then(result=>{
      if(!active)return
      setData(result)
      setSelected(result.current??'')
    }).catch(reason=>{if(active)setError(reason instanceof Error?reason.message:'Falha ao buscar avaliadores.')})
    return()=>{active=false}
  },[group])
  const choice=data?.recommendations.find(option=>option.professor_profile_id===selected)
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault()
    const reason=String(new FormData(event.currentTarget).get('justification')??'')
    if(!choice?.available||busy)return
    setBusy(true);setError('')
    try{
      await designateEvaluator(group,{professor:selected,justification:reason})
      saved();await onAssigned()
    }catch(reason){setError(reason instanceof Error?reason.message:'Falha ao designar avaliador.')}
    finally{setBusy(false)}
  }
  return <section className="planning-settings" aria-label="Designação individual do grupo">
    <h2>Avaliador · {projectName}</h2>
    <p>Padrão: 1 avaliador por grupo. O orientador não pode avaliar o próprio projeto.</p>
    {error&&<p role="alert" className="alert error">{error}</p>}
    {!data?<p>Carregando avaliadores…</p>:data.locked?<p className="empty-state">Presença ou notas já registradas. A troca de avaliador está bloqueada.</p>:<form className="project-form compact" onSubmit={submit}>
      <p>Atual: {data.current_name||'Não alocado'}. Aderência considera as competências do encaminhamento; sem aderência, justifique a escolha manual.</p>
      <label>Avaliador do grupo<select value={selected} onChange={e=>setSelected(e.target.value)} required disabled={busy}>
        <option value="">Escolha um avaliador</option>
        {data.recommendations.map(option=><option key={option.professor_profile_id} value={option.professor_profile_id} disabled={!option.available}>{option.name} · aderência {option.match_count} · carga {option.load}{option.available?'':` · ${option.unavailable_reason}`}</option>)}
      </select></label>
      {data.recommendations.length===0&&<p className="empty-state">Nenhum avaliador elegível cadastrado.</p>}
      {choice&&<p>{choice.available?'Disponível neste horário.':choice.unavailable_reason}{choice.requires_justification&&' Justificativa obrigatória para esta escolha.'}</p>}
      <label>Justificativa da escolha<textarea name="justification" rows={3} maxLength={2000} required={choice?.requires_justification} disabled={busy}/></label>
      <button className="button" disabled={busy||!choice?.available||selected===data.current}>{busy?'Alocando…':'Alocar avaliador'}</button>
    </form>}
    <button className="button secondary" type="button" disabled={busy} onClick={()=>{saved();onClose()}}>Fechar escolha de avaliador</button>
  </section>
}
