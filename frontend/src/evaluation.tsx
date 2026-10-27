import {useCallback,useEffect,useState,type FormEvent} from 'react'
import {designateEvaluator,recommendEvaluators,searchProfessors,type EvaluationGroup,type RecommendationResponse,type SearchedProfessor} from './api'

const saved=()=>window.dispatchEvent(new Event('platform:changes-saved'))
const failure=(error:unknown)=>error instanceof Error?error.message:'Não foi possível concluir a operação.'

export function EvaluatorDesignation({projectId}:{projectId:string}) {
  const[data,setData]=useState<RecommendationResponse|null>(null),[message,setMessage]=useState(''),[busy,setBusy]=useState(true),[unavailable,setUnavailable]=useState(false)
  const[selected,setSelected]=useState<{group:EvaluationGroup;professor:{id:string;name:string;matched:Record<string,string[]>;match_count:number}}|null>(null)
  const refresh=useCallback(async()=>{
    setBusy(true)
    try{
      setData(await recommendEvaluators(projectId))
      setUnavailable(false)
    }catch(e){
      const detail=failure(e)
      if(detail.includes('encaminhado'))setUnavailable(true)
      else setMessage(detail)
    }finally{setBusy(false)}
  },[projectId])
  useEffect(()=>{void refresh()},[refresh])
  async function confirm(event:FormEvent<HTMLFormElement>,group:EvaluationGroup,professorId:string){
    event.preventDefault();const reason=String(new FormData(event.currentTarget).get('justification')||'')
    setMessage('')
    try{
      await designateEvaluator(group.group_id,{professor:professorId,justification:reason})
      setSelected(null);saved();await refresh();setMessage('Avaliador designado.')
    }catch(e){setMessage(failure(e))}
  }
  if(unavailable)return <p className="empty-state">A designação fica disponível após o encaminhamento à secretaria.</p>
  return <section className="profile-section" aria-labelledby="evaluator-title"><h3 id="evaluator-title">Designação de avaliadores</h3><p>A recomendação é assistiva: considera aderência às competências e menor carga. A decisão final é da secretaria.</p>{message&&<p role="status" className="alert">{message}</p>}{busy?<p>Carregando recomendações…</p>:!data?<p className="empty-state">Recomendações indisponíveis.</p>:<>{data.keywords.length>0&&<p><strong>Palavras buscadas:</strong> {data.keywords.join(', ')}</p>}{data.groups.map(group=><article className="project-card" key={group.group_id}><h4>{group.group_name||'Grupo'}</h4><p>Orientador: {group.responsible_professor_name||'—'}</p><p>Avaliador atual: {group.evaluator_name||'não designado'}</p>{data.recommendations.filter(r=>r.match_count>0).map(item=><div className="candidate-card" key={item.professor_profile_id}><div><strong>{item.name}</strong><span>Aderência: {Object.entries(item.matched).map(([word,texts])=>`${word} (${texts.join(', ')})`).join('; ')||'—'} · Carga: {item.load}</span></div><button className="button secondary" type="button" onClick={()=>setSelected({group,professor:{id:item.professor_profile_id,name:item.name,matched:item.matched,match_count:item.match_count}})}>Selecionar {item.name}</button></div>)}{data.recommendations.every(r=>r.match_count===0)&&<p className="empty-state">Nenhum professor compatível. Busque manualmente e justifique.</p>}<ProfessorSearch onSelect={professor=>setSelected({group,professor:{id:professor.id,name:professor.name,matched:{},match_count:0}})}/>{selected&&selected.group.group_id===group.group_id&&<form className="project-form compact" onSubmit={event=>void confirm(event,group,selected.professor.id)}><p>Selecionado: <strong>{selected.professor.name}</strong>{selected.professor.match_count===0&&' (sem aderência — justificativa obrigatória)'}</p><label>Justificativa<textarea name="justification" rows={3} maxLength={2000} required={selected.professor.match_count===0}/></label><div className="action-row"><button className="button">Confirmar designação</button><button className="button secondary" type="button" onClick={()=>setSelected(null)}>Cancelar</button></div></form>}</article>)}{data.history.length>0&&<details><summary>Histórico de designações</summary><ol>{data.history.map(item=><li key={item.id}><strong>{item.evaluator_name}</strong> — {item.group_name||'grupo'}<p>{item.justification||'Sem justificativa registrada.'}</p><small>{item.decided_by_name} · {new Date(item.decided_at).toLocaleString('pt-BR')}</small></li>)}</ol></details>}</>}</section>
}

function ProfessorSearch({onSelect}:{onSelect:(professor:SearchedProfessor)=>void}){
  const[query,setQuery]=useState(''),[items,setItems]=useState<SearchedProfessor[]>([]),[busy,setBusy]=useState(false)
  useEffect(()=>{let active=true;setItems([]);if(query.trim().length<2)return;setBusy(true);const timer=setTimeout(()=>{searchProfessors(query).then(value=>{if(active)setItems(value)}).finally(()=>{if(active)setBusy(false)})},300);return()=>{active=false;clearTimeout(timer)}},[query])
  return <div className="student-search"><label>Buscar professor por nome<input type="search" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Nome ou matrícula, no mínimo 2 caracteres"/></label><div aria-live="polite">{busy&&query.length>=2?<p>Pesquisando…</p>:query.length>=2&&items.length===0?<p>Nenhum professor encontrado.</p>:items.map(item=><div className="candidate-card" key={item.id}><span>{item.name}</span><button className="button secondary" type="button" onClick={()=>{onSelect(item);setQuery('');setItems([])}}>Selecionar {item.name}</button></div>)}</div></div>
}
