import {useEffect,useRef,useState} from 'react'
import {recordMemberAttendance,recordShowcaseGrade,type ShowcaseEntry} from './api'

export function ShowcaseAttendanceCard({entry,onUpdate}:{entry:ShowcaseEntry;onUpdate:(entry:ShowcaseEntry)=>void}){
  const[checked,setChecked]=useState<Record<number,boolean>>({})
  const[editing,setEditing]=useState(false)
  const[value,setValue]=useState('')
  const[observations,setObservations]=useState('')
  const[busy,setBusy]=useState(false)
  const[error,setError]=useState('')
  const gradeInput=useRef<HTMLInputElement>(null)
  const members=entry.members??[]
  const legacy=members.length>0&&members.every(member=>member.present===null)&&['PRESENTED','ABSENT'].includes(entry.status)
  const pending=entry.status==='SCHEDULED'||(legacy&&!entry.evaluation?.concluded)
  const canGrade=entry.status==='PRESENTED'&&members.some(member=>member.present===true)&&!entry.evaluation?.concluded
  useEffect(()=>{if(editing)gradeInput.current?.focus()},[editing])
  async function confirm(){
    if(busy)return
    if(!members.some(member=>checked[member.member_id])&&!window.confirm('Nenhum integrante marcado. Confirmar ausência de todo o grupo?'))return
    setBusy(true);setError('')
    try{
      const updated=await recordMemberAttendance(entry.id,members.map(member=>({member_id:member.member_id,present:!!checked[member.member_id]})))
      onUpdate(updated)
      window.dispatchEvent(new Event('platform:changes-saved'))
      setEditing(updated.status==='PRESENTED'&&!updated.evaluation?.concluded)
    }catch(error){setError(error instanceof Error?error.message:'Não foi possível registrar presença.')}
    finally{setBusy(false)}
  }
  async function evaluate(){
    if(busy)return
    if(value.trim()===''||!Number.isFinite(Number(value))||Number(value)<0||Number(value)>10){setError('Informe uma nota de 0 a 10.');return}
    setBusy(true);setError('')
    try{
      onUpdate(await recordShowcaseGrade(entry.id,value,observations))
      window.dispatchEvent(new Event('platform:changes-saved'))
      setEditing(false)
    }catch(error){setError(error instanceof Error?error.message:'Não foi possível salvar a avaliação.')}
    finally{setBusy(false)}
  }
  return <article className="profile-section" aria-label={`Presença de ${entry.project_name}`}>
    <h3>{entry.project_name}</h3><p>{entry.group_name} · {new Date(entry.date).toLocaleString('pt-BR')} · {entry.location}</p>
    {legacy&&<p>Presença geral já registrada como {entry.status==='PRESENTED'?'apresentado':'ausente'}. Complemente os integrantes mantendo esse resultado.</p>}
    {error&&<p role="alert" className="alert">{error}</p>}
    <fieldset disabled={busy||!pending}>
      <legend>Integrantes presentes</legend>
      <p>Marque somente quem compareceu. A confirmação não poderá ser alterada.</p>
      {members.map(member=><label key={member.member_id} className="checkbox-label">
        <input type="checkbox" checked={pending?!!checked[member.member_id]:member.present===true} onChange={event=>setChecked({...checked,[member.member_id]:event.target.checked})}/>
        {member.name||member.ra} · {member.ra}
      </label>)}
    </fieldset>
    {pending?<button className="button" disabled={busy||members.length===0} onClick={()=>void confirm()}>Confirmar presença</button>:<p role="status">{entry.status==='ABSENT'?'Ausência registrada.':'Presença registrada.'}</p>}
    {pending&&members.length===0&&<p>Nenhum integrante ativo encontrado. Atualize a página ou procure a Secretaria.</p>}
    {canGrade&&!editing&&<button className="button" disabled={busy} onClick={()=>setEditing(true)}>Avaliar grupo</button>}
    {canGrade&&editing&&<form className="project-form compact" aria-label="Avaliação do grupo" onSubmit={event=>{event.preventDefault();void evaluate()}}>
      <h4>Avaliação do grupo</h4>
      <p>A nota é do grupo. Notas individuais do orientador permanecem separadas.</p>
      <label>Nota (0 a 10)<input ref={gradeInput} type="number" min="0" max="10" step="0.01" required value={value} disabled={busy} onChange={event=>setValue(event.target.value)}/></label>
      <label>Observações<textarea maxLength={2000} value={observations} disabled={busy} onChange={event=>setObservations(event.target.value)}/></label>
      <div className="action-row"><button className="button" disabled={busy}>Salvar avaliação</button><button type="button" className="button secondary" disabled={busy} onClick={()=>setEditing(false)}>Avaliar depois</button></div>
    </form>}
    {entry.evaluation?.concluded&&<div role="status"><strong>Avaliação concluída · Nota: {entry.evaluation.value??'—'}</strong><p>{entry.evaluation.observations}</p></div>}
    {!pending&&members.some(member=>member.present===null)&&<p>Presença registrada pelo fluxo anterior, sem detalhamento individual.</p>}
  </article>
}
