import {useCallback,useEffect,useRef,useState,type FormEvent,type PointerEvent} from 'react'
import {autoAllocateEvaluators,cancelShowcaseEntry,createShowcaseBuilding,createShowcaseDay,createShowcaseRoom,getShowcasePlanning,renameShowcaseBuilding,renameShowcaseRoom,scheduleShowcaseGroup,type AllocationResult,type CalendarEntry,type PlanningEntry,type Profile,type ShowcasePlanning} from './api'
import {AgendaEvaluatorPicker} from './agendaEvaluators'
import './showcaseScheduler.css'

const minutes=(value:string)=>{const [h,m]=value.split(':').map(Number);return h*60+m}
const clock=(value:number)=>`${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`
const localClock=(iso:string)=>new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(iso))
const dayLabel=(date:string)=>date.split('-').reverse().join('/')
const entryDate=(iso:string)=>new Intl.DateTimeFormat('pt-BR',{timeZone:'America/Sao_Paulo',dateStyle:'short'}).format(new Date(iso))
const failure=(error:unknown)=>error instanceof Error?error.message:'Não foi possível concluir a operação.'
const saved=()=>window.dispatchEvent(new Event('platform:changes-saved'))
const editable=(entry:PlanningEntry)=>entry.status==='SCHEDULED'
const rowHeight=160

export function ShowcaseScheduler({user}:{user:Pick<Profile,'role'>}){
  const[data,setData]=useState<ShowcasePlanning|null>(null),[message,setMessage]=useState('')
  const[busy,setBusy]=useState(false),[query,setQuery]=useState(''),[search,setSearch]=useState('')
  const[dayId,setDayId]=useState(''),[roomId,setRoomId]=useState(''),[selected,setSelected]=useState('')
  const[manualStart,setManualStart]=useState(''),[manualEnd,setManualEnd]=useState('')
  const[resize,setResize]=useState<{id:string;end:number}|null>(null)
  const[evaluatorGroup,setEvaluatorGroup]=useState(''),[allocation,setAllocation]=useState<AllocationResult|null>(null)
  const gesture=useRef<{entry:CalendarEntry;y:number;initialEnd:number;end:number}|null>(null)
  const revision=useRef(0)
  const staff=user.role==='ADMIN'||user.role==='SECRETARIAT'
  const refresh=useCallback(async()=>{
    const version=++revision.current
    const result=await getShowcasePlanning(search)
    if(version!==revision.current)return
    setData(result)
    setDayId(current=>result.days.some(d=>d.id===current)?current:result.days[0]?.id??'')
    setRoomId(current=>result.rooms.some(r=>r.id===current)?current:result.rooms[0]?.id??'')
  },[search])
  useEffect(()=>{if(staff)void refresh().catch(error=>setMessage(failure(error)))},[refresh,staff])
  const day=data?.days.find(d=>d.id===dayId)
  const start=day?minutes(day.start_time):0,end=day?minutes(day.end_time):0
  const slots=Array.from({length:Math.max(0,(end-start)/30)},(_,i)=>start+i*30)
  const entries=data?.entries.filter(e=>e.day===dayId&&e.room===roomId)??[]
  const unassigned=data?.groups.filter(g=>g.eligible&&(!g.entry||g.entry.status==='CANCELLED'))??[]
  const roomLabel=(id:string)=>{
    const room=data?.rooms.find(r=>r.id===id)
    return room?`${data?.buildings.find(b=>b.id===room.building)?.name} / ${room.name}`:''
  }
  async function mutate(action:()=>Promise<unknown>,success:string){
    if(busy)return
    setBusy(true);setMessage('')
    try{await action();saved();await refresh();setMessage(success)}
    catch(error){setMessage(failure(error));await refresh().catch(()=>{})}
    finally{setBusy(false)}
  }
  async function place(groupId:string,from:number,to:number,entry?:PlanningEntry|null){
    if(!day||!roomId||busy)return
    const current=entry??data?.groups.find(g=>g.id===groupId)?.entry
    await mutate(()=>scheduleShowcaseGroup({group:groupId,day:dayId,room:roomId,start_time:clock(from),end_time:clock(to),...(current?{expected_updated_at:current.updated_at}:{})}),'Agendamento salvo.')
  }
  function beginResize(event:PointerEvent<HTMLButtonElement>,entry:CalendarEntry){
    if(busy||!editable(entry)||!entry.end_date)return
    event.preventDefault();event.stopPropagation()
    event.currentTarget.setPointerCapture(event.pointerId)
    const initialEnd=minutes(localClock(entry.end_date))
    gesture.current={entry,y:event.clientY,initialEnd,end:initialEnd}
    setResize({id:entry.id,end:initialEnd})
  }
  function moveResize(event:PointerEvent<HTMLButtonElement>){
    const g=gesture.current
    if(!g)return
    const from=minutes(localClock(g.entry.date))
    g.end=Math.max(from+30,Math.min(end,g.initialEnd+Math.round((event.clientY-g.y)/rowHeight)*30))
    setResize({id:g.entry.id,end:g.end})
  }
  function finishResize(){
    const g=gesture.current;gesture.current=null;setResize(null)
    if(g&&g.end!==g.initialEnd)void place(g.entry.group,minutes(localClock(g.entry.date)),g.end,g.entry)
  }
  function cancelResize(){gesture.current=null;setResize(null)}
  function manual(event:FormEvent<HTMLFormElement>){
    event.preventDefault()
    if(selected&&manualStart&&manualEnd)void place(selected,minutes(manualStart),minutes(manualEnd))
  }
  if(!staff)return <p role="alert">Agenda disponível para Secretaria e Admin.</p>
  return <section className="showcase-planning" aria-label="Planejamento da Mostra">
    <p>Selecione um dia e uma sala. Arraste grupos para a grade; ajuste a duração pela borda inferior ou pelos botões de 30 minutos.</p>
    {message&&<p className="alert" role="status">{message}</p>}
    {!data?<p>Carregando agenda…</p>:<>
      <div className="planning-filters">
        <label>Data da Mostra<select value={dayId} onChange={e=>{setDayId(e.target.value);cancelResize()}} disabled={busy}><option value="">Selecione a data</option>{data.days.map(d=><option key={d.id} value={d.id}>{dayLabel(d.date)} · {d.start_time.slice(0,5)}–{d.end_time.slice(0,5)}</option>)}</select></label>
        <label>Local (prédio / sala)<select value={roomId} onChange={e=>{setRoomId(e.target.value);cancelResize()}} disabled={busy}><option value="">Selecione o local</option>{data.rooms.map(r=><option key={r.id} value={r.id}>{roomLabel(r.id)}</option>)}</select></label>
      </div>
      <div className="planning-allocation">
        <p><strong>1 avaliador por grupo.</strong> A alocação automática considera competências, disponibilidade e carga, sem substituir os avaliadores já escolhidos. Para escolher manualmente, clique em “Avaliador” no cartão.</p>
        <button className="button" type="button" disabled={busy||!day||!roomId||!entries.some(e=>e.status==='SCHEDULED'&&!e.evaluator_id)} onClick={()=>{
          if(!window.confirm('Alocar 1 avaliador por grupo sem avaliador deste dia e sala? As escolhas atuais serão mantidas.'))return
          void mutate(async()=>setAllocation(await autoAllocateEvaluators(dayId,roomId)),'Alocação automática concluída. Confira o resultado abaixo.')
        }}>Alocar avaliadores automaticamente</button>
        {allocation&&<section role="status" aria-label="Resultado da alocação"><p>{allocation.allocated.length} alocado(s) · {allocation.preserved.length} preservado(s) · {allocation.pending.length} pendente(s).</p>{allocation.pending.length>0&&<ul>{allocation.pending.map(item=><li key={item.group}><strong>{item.project_name}:</strong> {item.reason}</li>)}</ul>}</section>}
      </div>
      {(!day||!roomId)&&<p className="empty-state">Cadastre uma data e um local abaixo para começar.</p>}
      <form data-filter-form className="planning-search" onSubmit={e=>{e.preventDefault();setSearch(query)}}><label>Buscar projeto, integrante ou ID<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Nome do projeto, integrante ou #123"/></label><button className="button" disabled={busy}>Pesquisar</button><button className="button secondary" type="button" onClick={()=>{setQuery('');setSearch('')}}>Limpar busca</button></form>
      {search&&<section aria-label="Resultados da busca" className="planning-results">
        <h2>Resultados em todas as datas e salas</h2>
        {data.groups.length===0?<p>Nenhum projeto encontrado.</p>:data.groups.map(g=><article key={g.id}>
          <strong>#{g.number} · {g.project_name}</strong><span>{g.members.join(', ')}</span>
          <p>{g.entry&&g.entry.status!=='CANCELLED'?`${entryDate(g.entry.date)} · ${localClock(g.entry.date)} · ${g.entry.location}`:'Ainda não agendado'}</p>
          {g.entry?.day&&g.entry.room&&g.entry.status!=='CANCELLED'&&<button className="button secondary" onClick={()=>{setDayId(g.entry!.day!);setRoomId(g.entry!.room!)}}>Localizar na agenda</button>}
          <button className="button secondary" onClick={()=>window.dispatchEvent(new CustomEvent('platform:navigate',{detail:`#/projects/${g.project}`}))}>Abrir projeto</button>
        </article>)}
      </section>}
      <div className="planning-columns">
        <section className="planning-pool" aria-label="Grupos não agendados"><h2>Grupos não agendados <small>({unassigned.length})</small></h2>
          <p>Projetos aprovados e encaminhados à Secretaria.</p>
          {unassigned.length===0&&<p className="empty-state">Nenhum grupo disponível{search?' para esta busca':''}.</p>}
          {unassigned.map(g=><article key={g.id} className={`planning-group ${selected===g.id?'selected':''}`} draggable={!busy} onDragStart={e=>{e.dataTransfer.setData('text/plain',g.id);e.dataTransfer.effectAllowed='move'}}>
            <strong>#{g.number} · {g.project_name}</strong><p>{g.name}</p><small>{g.members.join(', ')}</small>
            <button className="button secondary" disabled={busy} onClick={()=>{setSelected(g.id);setManualStart(clock(start));setManualEnd(clock(start+30))}}>Selecionar para agendar</button>
          </article>)}
        </section>
        <section className="planning-calendar" aria-label="Horários da sala">
          <div className="planning-calendar-header"><h2>{day?dayLabel(day.date):'Agenda'} · {roomLabel(roomId)||'Selecione a sala'}</h2></div>
          {day&&roomId&&<div className="planning-timeline" style={{height:slots.length*rowHeight}}>
            {slots.map(time=><div key={time} className="planning-slot" style={{top:(time-start)/30*rowHeight,height:rowHeight}} onDragOver={e=>{if(!busy){e.preventDefault();e.dataTransfer.dropEffect='move'}}} onDrop={e=>{
              e.preventDefault();if(busy)return
              const id=e.dataTransfer.getData('text/plain')
              const existing=data.entries.find(entry=>entry.group===id)
              if(!existing&&!data.groups.some(g=>g.id===id))return
              const duration=existing?.end_date?minutes(localClock(existing.end_date))-minutes(localClock(existing.date)):30
              void place(id,time,time+duration,existing)
            }}><span>{clock(time)}</span><button className="slot-action" type="button" disabled={busy||!selected} aria-label={`Agendar grupo selecionado às ${clock(time)}`} onClick={()=>void place(selected,time,time+30)}>+</button></div>)}
            {entries.map(entry=>{
              const from=minutes(localClock(entry.date))
              const to=resize?.id===entry.id?resize.end:entry.end_date?minutes(localClock(entry.end_date)):from+30
              // Empilha múltiplos grupos na mesma sala/horário com offset vertical
              const sameSlot = entries.filter(e=>e.day===entry.day&&e.room===entry.room&&minutes(localClock(e.date))===from)
              const slotIndex = sameSlot.indexOf(entry)
              const stackOffset = slotIndex * 42
              return <article key={entry.id} className="planning-booking" data-testid={`booking-${entry.id}`} style={{top:(from-start)/30*rowHeight+stackOffset,height:(to-from)/30*rowHeight-4-stackOffset}} draggable={!busy&&editable(entry)} onDragStart={e=>{e.dataTransfer.setData('text/plain',entry.group);e.dataTransfer.effectAllowed='move'}}>
                <strong>#{entry.number} · {entry.project_name}</strong><span>{clock(from)}–{clock(to)}</span>
                <button type="button" className="booking-evaluator" disabled={busy} onClick={()=>setEvaluatorGroup(entry.group)} aria-label={`Escolher avaliador de ${entry.project_name}`}>Avaliador: {entry.evaluator_name||'não alocado — escolher'}</button>
                {editable(entry)?<div className="booking-actions"><button disabled={busy||to-from<=30} aria-label={`Diminuir duração de ${entry.project_name}`} onClick={()=>void place(entry.group,from,to-30,entry)}>−30 min</button><button disabled={busy||to+30>end} aria-label={`Aumentar duração de ${entry.project_name}`} onClick={()=>void place(entry.group,from,to+30,entry)}>+30 min</button><button disabled={busy} onClick={()=>{if(window.confirm('Retirar este grupo da agenda?'))void mutate(()=>cancelShowcaseEntry(entry.id,'Reorganização da agenda'),'Grupo retirado da agenda.')}}>Retirar</button></div>:<small>{entry.status==='PRESENTED'?'Apresentado':'Ausente'} · horário bloqueado</small>}
                {editable(entry)&&<button className="booking-resize" aria-label={`Redimensionar duração de ${entry.project_name}`} onPointerDown={e=>beginResize(e,entry)} onPointerMove={moveResize} onPointerUp={finishResize} onPointerCancel={cancelResize} onLostPointerCapture={cancelResize} disabled={busy}>⋯</button>}
              </article>
            })}
          </div>}
        </section>
      </div>
      {evaluatorGroup&&<AgendaEvaluatorPicker key={evaluatorGroup} group={evaluatorGroup} projectName={data.entries.find(e=>e.group===evaluatorGroup)?.project_name??'Grupo'} onClose={()=>setEvaluatorGroup('')} onAssigned={async()=>{await refresh();setEvaluatorGroup('');setMessage('Avaliador alocado.')}}/>}
      <details open={!!selected} className="planning-settings"><summary>Agendar ou reagendar sem arrastar</summary>
        <form className="project-form compact" onSubmit={manual}><label>Grupo<select value={selected} onChange={e=>setSelected(e.target.value)} required><option value="">Selecione um grupo</option>{data.groups.filter(g=>!g.entry||['CANCELLED','SCHEDULED'].includes(g.entry.status)).map(g=><option key={g.id} value={g.id}>#{g.number} · {g.project_name} · {g.name}</option>)}</select></label><label>Início<input type="time" step={1800} required value={manualStart} onChange={e=>setManualStart(e.target.value)}/></label><label>Fim<input type="time" step={1800} required value={manualEnd} onChange={e=>setManualEnd(e.target.value)}/></label><button className="button" disabled={busy||!day||!roomId}>Salvar agendamento</button></form>
      </details>
      <details className="planning-settings"><summary>Cadastrar datas da Mostra</summary><form className="project-form compact" onSubmit={e=>{
        e.preventDefault();const form=e.currentTarget,values=new FormData(form)
        void mutate(async()=>{await createShowcaseDay({date:String(values.get('date')),start_time:String(values.get('start')),end_time:String(values.get('end'))});form.reset()},'Data cadastrada.')
      }}><label>Nova data<input type="date" name="date" required/></label><label>Início do dia<input type="time" name="start" step={1800} defaultValue="08:00" required/></label><label>Fim do dia<input type="time" name="end" step={1800} defaultValue="18:00" required/></label><button className="button" disabled={busy}>Cadastrar data</button></form></details>
      {staff&&<details className="planning-settings"><summary>Cadastrar prédios e salas</summary>
        <button className="button" disabled={busy} onClick={()=>void mutate(createShowcaseBuilding,'Prédio cadastrado.')}>Adicionar prédio</button>
        {data.buildings.map(building=><section key={building.id} className="planning-venue"><h3>{building.name} <small>· código {building.code}</small></h3>
          <form className="project-form compact" onSubmit={e=>{e.preventDefault();void mutate(()=>renameShowcaseBuilding(building.id,String(new FormData(e.currentTarget).get('name'))),'Prédio renomeado.')}}><label>Nome do prédio {building.code}<input name="name" defaultValue={building.name} key={building.name} maxLength={120} required/></label><button className="button secondary" disabled={busy}>Renomear prédio</button></form>
          <button className="button secondary" disabled={busy} onClick={()=>void mutate(()=>createShowcaseRoom(building.id),'Sala cadastrada.')}>Adicionar sala em {building.name}</button>
          {data.rooms.filter(r=>r.building===building.id).map(room=><form key={room.id} className="project-form compact" onSubmit={e=>{e.preventDefault();void mutate(()=>renameShowcaseRoom(room.id,String(new FormData(e.currentTarget).get('name'))),'Sala renomeada.')}}><label>Nome da sala {room.number} · {building.code}<input name="name" defaultValue={room.name} key={room.name} required maxLength={120}/></label><button className="button secondary" disabled={busy}>Renomear sala</button></form>)}
        </section>)}
      </details>}
    </>}
  </section>
}
