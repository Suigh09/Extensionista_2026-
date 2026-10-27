import {useCallback,useEffect,useRef,useState,type FormEvent} from 'react'
import {addCriterion,concludeEvaluation,createRubric,deleteCriterion,deleteRubric,gradeIndividual,groupGrades,individualGrades,listRubrics,submitGrades,updateRubricTitle,usableRubrics,type GradeSubmission,type IndividualGrade,type Project,type ProjectGroup,type Rubric} from './api'

const saved=()=>window.dispatchEvent(new Event('platform:changes-saved'))
const failure=(error:unknown)=>error instanceof Error?error.message:'Não foi possível concluir a operação.'

export function RubricManagement(){
  const[rubrics,setRubrics]=useState<Rubric[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(true),[draft,setDraft]=useState(''),[confirmDelete,setConfirmDelete]=useState<string|null>(null),[addingTo,setAddingTo]=useState<string|null>(null)
  async function refresh(){setBusy(true);try{setRubrics(await listRubrics())}catch(e){setMessage(failure(e))}finally{setBusy(false)}}
  useEffect(()=>{void refresh()},[])
  async function create(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const data=new FormData(event.currentTarget)
    const criteria=String(data.get('criteria')||'').split('\n').map(line=>line.trim()).filter(Boolean).map(name=>({name,description:''}))
    setMessage('')
    try{
      await createRubric({title:String(data.get('title')),criteria})
      setDraft('');(event.target as HTMLFormElement).reset();await refresh();setMessage('Rubrica criada.')
    }catch(e){setMessage(failure(e))}
  }
  async function rename(event:FormEvent<HTMLFormElement>,rubric:Rubric){
    event.preventDefault();const title=String(new FormData(event.currentTarget).get('title')||'')
    try{await updateRubricTitle(rubric.id,title);await refresh()}catch(e){setMessage(failure(e))}
  }
  async function add(event:FormEvent<HTMLFormElement>,rubric:Rubric){
    event.preventDefault();const data=new FormData(event.currentTarget)
    try{
      await addCriterion(rubric.id,{name:String(data.get('name')),description:String(data.get('description')||'')})
      setAddingTo(null);await refresh()
    }catch(e){setMessage(failure(e))}
  }
  async function remove(rubric:Rubric,criterionId:string){
    try{await deleteCriterion(criterionId);await refresh()}catch(e){setMessage(failure(e))}
  }
  return <section className="profile-section" aria-labelledby="rubric-title"><h2 id="rubric-title">Rubricas de avaliação</h2><p>Critérios de 0 a 10; a nota do grupo é a média, com 2 decimais.</p>{message&&<p role="status" className="alert">{message}</p>}{busy?<p>Carregando rubricas…</p>:<><form className="project-form" onSubmit={create}><label>Título da rubrica<input name="title" required maxLength={160}/></label><label>Critérios (um por linha)<textarea name="criteria" rows={3} required value={draft} onChange={e=>setDraft(e.target.value)} placeholder={'Clareza\nImpacto social'}/></label><button className="button">Criar rubrica</button></form>{rubrics.length===0?<p className="empty-state">Nenhuma rubrica cadastrada.</p>:rubrics.map(rubric=><article className="project-card" key={rubric.id}><h3>{rubric.title}</h3><ul>{rubric.criteria.map(item=><li key={item.id}>{item.name} <button type="button" className="button secondary" onClick={()=>void remove(rubric,item.id)}>Excluir critério</button></li>)}</ul><form className="project-form compact" onSubmit={event=>void rename(event,rubric)}><label>Renomear<input name="title" required maxLength={160} defaultValue={rubric.title}/></label><button className="button secondary">Salvar título</button></form>{addingTo===rubric.id?<form className="project-form compact" onSubmit={event=>void add(event,rubric)}><label>Novo critério<input name="name" required maxLength={160}/></label><label>Descrição<textarea name="description" rows={2}/></label><div className="action-row"><button className="button">Adicionar</button><button className="button secondary" type="button" onClick={()=>setAddingTo(null)}>Cancelar</button></div></form>:<button type="button" className="button secondary" onClick={()=>setAddingTo(rubric.id)}>Adicionar critério</button>}{confirmDelete===rubric.id?<form className="project-form compact" onSubmit={async event=>{event.preventDefault();try{await deleteRubric(rubric.id);setConfirmDelete(null);await refresh()}catch(e){setMessage(failure(e))}}}><p>Rubricas usadas em avaliações não podem ser excluídas.</p><div className="action-row"><button className="button danger">Confirmar exclusão</button><button className="button secondary" type="button" onClick={()=>setConfirmDelete(null)}>Voltar</button></div></form>:<button type="button" className="button secondary" onClick={()=>setConfirmDelete(rubric.id)}>Excluir rubrica</button>}</article>)}</>}</section>
}

export function GroupEvaluationPanel({project,group}:{project:Project;group:ProjectGroup}){
  const rubricIdRef = useRef<string|null>(null)
  const[rubrics,setRubrics]=useState<Rubric[]>([]),[rubricId,setRubricId]=useState(''),[average,setAverage]=useState<string|null>(null),[submissions,setSubmissions]=useState<GradeSubmission[]>([]),[message,setMessage]=useState(''),[busy,setBusy]=useState(true),[concluded,setConcluded]=useState(false)
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{
      const[available,grades]=await Promise.all([usableRubrics(project.id),groupGrades(group.id)])
      setRubrics(available);setAverage(grades.average);setSubmissions(grades.submissions)
      setConcluded(grades.submissions.length>0&&grades.submissions[grades.submissions.length-1].concluded)
      if(!rubricIdRef.current&&available.length>0)setRubricId(available[0].id)
    }catch(e){setMessage(failure(e))}finally{setBusy(false)}
  },[project.id,group.id])
  useEffect(()=>{void refresh()},[refresh])
  useEffect(()=>{rubricIdRef.current = rubricId},[rubricId])
  const selected=rubrics.find(item=>item.id===rubricId)
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const data=new FormData(event.currentTarget)
    const items=(selected?.criteria??[]).map(item=>({criterion:item.id,value:String(data.get(`grade-${item.id}`)??'')}))
    setMessage('')
    try{
      const created=await submitGrades(group.id,{rubric:rubricId,comment:String(data.get('comment')||''),items})
      setAverage(created.average);saved();await refresh();setMessage(`Notas enviadas. Média do grupo: ${created.average}.`)
    }catch(e){setMessage(failure(e))}
  }
  async function conclude(){
    setMessage('')
    try{await concludeEvaluation(group.id);saved();await refresh();setMessage('Avaliação concluída e grupo notificado.')}catch(e){setMessage(failure(e))}
  }
  return <section className="profile-section" aria-labelledby="evaluation-title"><h3 id="evaluation-title">Avaliação do grupo</h3>{message&&<p role="status" className="alert">{message}</p>}{busy?<p>Carregando avaliação…</p>:<>{average!==null&&<p role="status"><strong>Nota do grupo: {average}</strong>{concluded?' · Avaliação concluída':''}</p>}{concluded?<p className="empty-state">Avaliação concluída. Novas notas do avaliador estão bloqueadas.</p>:<form className="project-form" onSubmit={submit}><label>Rubrica<select value={rubricId} onChange={e=>setRubricId(e.target.value)} required>{rubrics.map(item=><option key={item.id} value={item.id}>{item.title}</option>)}</select></label>{selected?.criteria.map(item=><label key={item.id}>{item.name}<input name={`grade-${item.id}`} type="number" min={0} max={10} step="0.01" required inputMode="decimal"/></label>)??<p className="empty-state">Nenhuma rubrica disponível.</p>}<label>Comentário geral<textarea name="comment" rows={3} maxLength={2000}/></label><button className="button">Enviar notas</button></form>}{!concluded&&submissions.length>0&&<div className="action-row"><button className="button secondary" onClick={()=>void conclude()}>Concluir avaliação</button></div>}{submissions.length>0&&<details><summary>Histórico de notas ({submissions.length})</summary><ol>{submissions.map(item=><li key={item.id}><strong>{item.rubric_title}</strong> — {item.items.map(entry=>`${entry.criterion_name}: ${entry.value}`).join(' · ')}<p>{item.comment||'Sem comentário.'}</p><small>{item.author_name} · {new Date(item.created_at).toLocaleString('pt-BR')}{item.concluded?' · concluída':''}</small></li>)}</ol></details>}</>}</section>
}

export function IndividualGradesPanel({group}:{group:ProjectGroup}){
  const[members,setMembers]=useState<{student_id:number;name:string;ra:string}[]>([]),[grades,setGrades]=useState<Record<number,IndividualGrade|null>>({}),[message,setMessage]=useState('')
  useEffect(()=>{
    setMembers(group.members.map(m=>({student_id:m.student_id,name:m.name,ra:m.ra})))
  },[group])
  async function load(studentId:number){
    try{
      const data=await individualGrades(String(studentId))
      setGrades(current=>({...current,[studentId]:data.current}))
    }catch(e){setMessage(failure(e))}
  }
  useEffect(()=>{members.forEach(m=>void load(m.student_id))},[members])
  async function submit(event:FormEvent<HTMLFormElement>,studentId:number){
    event.preventDefault();const data=new FormData(event.currentTarget)
    setMessage('')
    try{
      const created=await gradeIndividual(String(studentId),{value:String(data.get('value')),comment:String(data.get('comment')||'')})
      setGrades(current=>({...current,[studentId]:created}));saved();setMessage(`Nota individual de ${created.student_name} registrada.`)
    }catch(e){setMessage(failure(e))}
  }
  return <section className="profile-section" aria-labelledby="individual-title"><h3 id="individual-title">Notas individuais do orientador</h3><p>Opcional, por aluno. Alterações geram novo registro com histórico.</p>{message&&<p role="status" className="alert">{message}</p>}{members.map(member=><details key={member.student_id}><summary>{member.name} · atual: {grades[member.student_id]?.value??'—'}</summary><form className="project-form compact" onSubmit={event=>void submit(event,member.student_id)}><label>Nota (0 a 10)<input name="value" type="number" min={0} max={10} step="0.01" required inputMode="decimal"/></label><label>Comentário<textarea name="comment" rows={2} maxLength={2000}/></label><button className="button">Registrar nota</button></form></details>)}</section>
}
