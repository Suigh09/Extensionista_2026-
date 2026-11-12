import {useEffect,useMemo,useState}from'react'
import{type Project}from'./api'
import{statusLabels}from'./projectStatusLabels'

export type ProjectListTableProps={
  projects:Project[]
  total:number
  page:number
  pageSize:number
  onPageChange:(page:number)=>void
  onSort:(field:string,dir:'asc'|'desc')=>void
  sortField:string|null
  sortDir:'asc'|'desc'
  storageKey?:string
}

export function ProjectListTable({projects,total,page,pageSize,onPageChange,onSort,sortField,sortDir,storageKey='project-list-columns'}:ProjectListTableProps){
  const columns=[
    {key:'number',label:'#',sortable:false},
    {key:'name',label:'Título',sortable:true},
    {key:'status',label:'Status',sortable:true},
    {key:'room',label:'Sala/Turma',sortable:false},
    {key:'leader',label:'Líder',sortable:false},
    {key:'advisor',label:'Orientador',sortable:false},
    {key:'evaluator',label:'Avaliador',sortable:false},
    {key:'showcase',label:'Agenda da Mostra',sortable:false},
    {key:'updated_at',label:'Última atualização',sortable:true},
  ]
  const optionalColumns=[
    {key:'creator',label:'Criador',render:(project:Project)=>project.created_by_name||'—'},
    {key:'members',label:'Integrantes',render:(project:Project)=>{const group=project.groups?.[0]??project.group;return group?.member_count??'—'}},
    {key:'submitted',label:'Envio',render:(project:Project)=>project.submitted_at?new Date(project.submitted_at).toLocaleString('pt-BR'):'—'},
    {key:'reviewed',label:'Revisão',render:(project:Project)=>project.reviewed_at?`${new Date(project.reviewed_at).toLocaleString('pt-BR')}${project.reviewed_by?` · ${project.reviewed_by}`:''}`:'—'},
  ]
  const [showPicker,setShowPicker]=useState(false)
  const [visibleOptional,setVisibleOptional]=useState<Set<string>>(()=>{
    try{const raw=localStorage.getItem(storageKey);if(raw)return new Set(JSON.parse(raw))}catch{/* ignore */}
    return new Set(optionalColumns.map(c=>c.key))
  })
  useEffect(()=>{try{localStorage.setItem(storageKey,JSON.stringify([...visibleOptional]))}catch{/* ignore */}},[visibleOptional,storageKey])
  const toggleOptional=(key:string)=>{setVisibleOptional(prev=>{const next=new Set(prev);if(next.has(key))next.delete(key);else next.add(key);return next})}
  const visibleOptionalColumns=optionalColumns.filter(c=>visibleOptional.has(c.key))
  const totalColumns=9+visibleOptionalColumns.length
  const allColumns=[...columns.slice(0,7),...visibleOptionalColumns.map(c=>({key:c.key,label:c.label,sortable:false})),...columns.slice(7)]

  const totalPages=Math.max(1,Math.ceil(total/pageSize))
  const start=total===0?0:(page-1)*pageSize+1
  const end=Math.min(page*pageSize,total)

  const handleSort=(field:string)=>{
    if(sortField===field){
      onSort(field,sortDir==='asc'?'desc':'asc')
    }else{
      onSort(field,'asc')
    }
  }

  const pageNumbers=useMemo(()=>{
    const pages:number[]=[]
    const show=3
    const startPage=Math.max(1,page-show)
    const endPage=Math.min(totalPages,page+show)
    if(startPage>1)pages.push(1)
    if(startPage>2)pages.push(-1)
    for(let i=startPage;i<=endPage;i++)pages.push(i)
    if(endPage<totalPages-1)pages.push(-1)
    if(endPage<totalPages)pages.push(totalPages)
    return pages
  },[page,totalPages])

  const statusBadgeClass=(status:string)=>{
    switch(status){
      case 'APPROVED':return 'status-badge status-approved'
      case 'PENDING_APPROVAL':return 'status-badge status-pending'
      case 'DRAFT':return 'status-badge status-draft'
      case 'CHANGES_REQUESTED':return 'status-badge status-changes'
      case 'COMPLETED':return 'status-badge status-completed'
      case 'ARCHIVED':return 'status-badge status-archived'
      case 'CANCELLED':return 'status-badge status-cancelled'
      case 'PAUSED':return 'status-badge status-paused'
      default:return 'status-badge status-neutral'
    }
  }

  return (
    <section className="project-list-table" aria-label="Lista de projetos">
      <div className="column-picker"><button className="button secondary" type="button" onClick={()=>setShowPicker(v=>!v)}>Colunas</button>{showPicker&&<div className="column-picker-panel">{optionalColumns.map(c=><label key={c.key}><input type="checkbox" checked={visibleOptional.has(c.key)} onChange={()=>toggleOptional(c.key)}/>{c.label}</label>)}</div>}</div>
      <table role="grid" aria-label="Projetos">
        <thead>
          <tr>
            {allColumns.map(col=>
              col.sortable?(
                <th key={col.key} scope="col" role="columnheader" tabIndex={0} onKeyDown={e=>e.key==='Enter'&&handleSort(col.key)} onClick={()=>handleSort(col.key)} style={{cursor:'pointer',userSelect:'none'}}>
                  {col.label}{sortField===col.key&&(sortDir==='asc'?' ▲':' ▼')}
                </th>
              ):(
                <th key={col.key} scope="col">{col.label}</th>
              )
            )}
            <th scope="col" style={{width:'110px'}}>Ação</th>
          </tr>
        </thead>
        <tbody>
          {(projects??[]).length===0?(
            <tr><td colSpan={totalColumns+1} role="cell">Nenhum projeto encontrado.</td></tr>
          ):(
            projects.map((project: Project)=>{
              const group=project.groups?.[0]??project.group
              const leader=group?.members.find(m=>m.user_id===group?.leader_user_id)
              const themeTitle=project.theme_snapshot?.title??'—'
              const showcase=project.showcase_entry
              const showcaseStatusLabels:Record<string,string>={PENDING:'Pendente',SCHEDULED:'Agendado',PRESENTED:'Apresentado',ABSENT:'Ausente',CANCELLED:'Cancelado'}
              const showcaseLabel=showcase?`${new Date(showcase.date).toLocaleString('pt-BR', {day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})} · ${showcaseStatusLabels[showcase.status]??showcase.status}`:'—'
              return (
                <tr key={project.id} role="row" className="project-row" onClick={()=>{window.location.hash=`#/projects/${project.id}`}}>
                  <td role="cell" className="col-number">{project.number}</td>
                  <td role="cell" className="col-title">
                    <div className="project-title-cell">
                      <div className="project-title-main">{project.name}</div>
                      <div className="project-title-sub">{project.group?.name||'Sem grupo'}{themeTitle!=='—'?` · ${themeTitle}`:''}</div>
                    </div>
                  </td>
                  <td role="cell" className="col-status"><span className={statusBadgeClass(project.status)}>{statusLabels[String(project.status)]??project.status}</span></td>
                  <td role="cell" className="col-room">{project.class_offering_label??'—'}</td>
                  <td role="cell" className="col-person">{leader?.name??'—'}</td>
                  <td role="cell" className="col-person">{group?.responsible_professor_name??'—'}</td>
                  <td role="cell" className="col-person">{group?.evaluator_name??'—'}</td>
                  {visibleOptionalColumns.map(c=><td key={c.key} role="cell" className={`col-optional col-${c.key}`}>{c.render(project)}</td>)}
                  <td role="cell" className="col-showcase">{showcaseLabel}</td>
                  <td role="cell" className="col-date"><time dateTime={project.updated_at}>{new Date(project.updated_at).toLocaleString('pt-BR')}</time></td>
                  <td role="cell" className="col-actions"><button className="button secondary" onClick={(e)=>{e.stopPropagation();window.location.hash=`#/projects/${project.id}`}}>Abrir</button></td>
                </tr>
              )
            })
          )}
        </tbody>
      </table>
      <nav aria-label="Paginação">
        <p>{start} a {end} de {total} linhas</p>
        <div className="action-row" style={{display:'flex',alignItems:'center',gap:'0.5rem',marginTop:'0.5rem'}}>
          <button className="button secondary" disabled={page<=1} onClick={()=>onPageChange(1)}>« Início</button>
          <button className="button secondary" disabled={page<=1} onClick={()=>onPageChange(page-1)}>Anterior</button>
           {pageNumbers.map((p,index)=>
            p===-1?(
               <span key={`ellipsis-${index}`} className="button secondary" style={{cursor:'default',pointerEvents:'none'}}>…</span>
            ):(
              <button key={p} className={page===p?'button active':'button secondary'} onClick={()=>onPageChange(p)}>{p}</button>
            )
          )}
          <button className="button secondary" disabled={page>=totalPages} onClick={()=>onPageChange(page+1)}>Próxima</button>
          <button className="button secondary" disabled={page>=totalPages} onClick={()=>onPageChange(totalPages)}>Fim »</button>
        </div>
      </nav>
    </section>
  )
}


export type FilterOp='exact'|'not_exact'|'contains'|'not_contains'
export type FilterRow={field:string;op:FilterOp;value:string}
export type ProjectFilters={
  rows:FilterRow[]
  combiners:('and'|'or')[]
}

export function emptyProjectFilters():ProjectFilters{
  return {rows:[],combiners:[]}
}

export function filtersToExtra(filters:ProjectFilters,query=''):Record<string,string|string[]>{
  const extra:Record<string,string|string[]>={}
  const rows=query?[{field:'q',op:'contains',value:query},...filters.rows]:filters.rows
  extra.row_count=String(rows.length)
  rows.forEach((row,i)=>{
    extra[`field_${i}`]=row.field
    extra[`op_${i}`]=row.op
    extra[`value_${i}`]=row.value
  })
  // combiner_i existe apenas entre a linha i e a i+1
  filters.combiners.forEach((c,i)=>{
    if(i<rows.length-1){
      extra[`combiner_${i}`]=c
    }
  })
  return extra
}

const PROJECT_STATUSES=['DRAFT','PENDING_APPROVAL','CHANGES_REQUESTED','APPROVED','COMPLETED','ARCHIVED','PAUSED','CANCELLED']
const SHOWCASE_STATUSES=['PENDING','SCHEDULED','PRESENTED','ABSENT','CANCELLED']
const STATUS_LABELS:Record<string,string>={'DRAFT':'Rascunho','PENDING_APPROVAL':'Aguardando aprovação','CHANGES_REQUESTED':'Ajustes solicitados','APPROVED':'Aprovado','COMPLETED':'Concluído','ARCHIVED':'Arquivado','PAUSED':'Pausado','CANCELLED':'Cancelado'}
const SHOWCASE_LABELS:Record<string,string>={'PENDING':'Pendente','SCHEDULED':'Agendado','PRESENTED':'Apresentado','ABSENT':'Ausente','CANCELLED':'Cancelado'}

export function ProjectFilterBar({filters,onChange,isAdmin}:{filters:ProjectFilters;onChange:(f:ProjectFilters)=>void;isAdmin:boolean}){
  const [adding,setAdding]=useState(false)
  const [editing,setEditing]=useState<number|null>(null)
  const [newField,setNewField]=useState('')
  const [newOp,setNewOp]=useState<FilterOp>('contains')
  const [newValue,setNewValue]=useState('')

  const fieldOptions=[
    {key:'q',label:'Texto (título/sobre/tema)'},
    {key:'status',label:'Status do projeto'},
    {key:'advisor',label:'Orientador'},
    {key:'evaluator',label:'Avaliador'},
    {key:'student',label:'Integrante'},
    {key:'leader',label:'Líder'},
    {key:'room',label:'Turma'},
    {key:'theme',label:'Tema'},
  ]
  if(isAdmin) fieldOptions.push({key:'is_active',label:'Ativo'})
  fieldOptions.push({key:'showcase_status',label:'Agenda da Mostra'})

  const opOptions=[
    {key:'contains',label:'Contém'},
    {key:'not_contains',label:'Não contém'},
    {key:'exact',label:'É'},
    {key:'not_exact',label:'Não é'},
  ]

  const statusOptions=PROJECT_STATUSES.map(s=>({key:s,label:STATUS_LABELS[s]??s}))
  const showcaseOptions=SHOWCASE_STATUSES.map(s=>({key:s,label:SHOWCASE_LABELS[s]??s}))

  // Condições É/NÃO É usam combo; CONTÉM/NÃO CONTÉM usam texto
  const isComboOp=(op:string)=>op==='exact'||op==='not_exact'
  // Campos com lista de opções fechada para uso em combo
  const comboOptionsForField=(field:string)=>{
    if(field==='status') return statusOptions
    if(field==='showcase_status') return showcaseOptions
    if(field==='is_active') return [
      {key:'true',label:'Ativo'},
      {key:'false',label:'Inativo'},
    ]
    return []
  }

  const addRow=()=>{
    if(!newField) return
    const row:FilterRow={field:newField,op:newOp,value:newValue.trim()}
    const nextRows=[...filters.rows,row]
    const nextCombiners:('and'|'or')[]=[...filters.combiners,'and']
    onChange({rows:nextRows,combiners:nextCombiners})
    setAdding(false);setNewField('');setNewOp('contains');setNewValue('')
  }

  const updateRow=(index:number,patch:Partial<FilterRow>)=>{
    const next=[...filters.rows]
    next[index]={...next[index],...patch}
    onChange({rows:next,combiners:[...filters.combiners]})
  }

  const setCombiner=(index:number,value:'and'|'or')=>{
    const next:('and'|'or')[]=[...filters.combiners]
    next[index]=value
    onChange({rows:[...filters.rows],combiners:next})
  }

  const removeRow=(index:number)=>{
    const nextRows=filters.rows.filter((_,i)=>i!==index)
    const nextCombiners=filters.combiners.filter((_,i)=>i!==index)
    onChange({rows:nextRows,combiners:nextCombiners})
  }

  const chips:string[]=[]
  filters.rows.forEach(row=>{
    const label=fieldOptions.find(f=>f.key===row.field)?.label??row.field
    const opLabel=opOptions.find(o=>o.key===row.op)?.label??row.op
    chips.push(`${label} ${opLabel} ${row.value||'(vazio)'}`)
  })

  const valueInput=(
    field:string,
    op:string,
    value:string,
    onChangeValue:(v:string)=>void,
    disabled=false
  )=>{
    if(isComboOp(op)){
      const options=comboOptionsForField(field)
      if(options.length===0){
        // Sem lista fechada: mostra texto mesmo em modo exato
        return (
          <input
            type="search"
            value={value}
            onChange={e=>onChangeValue(e.target.value)}
            placeholder="Valor…"
            disabled={disabled}
          />
        )
      }
      return (
        <select value={value} onChange={e=>onChangeValue(e.target.value)} disabled={disabled}>
          <option value="">Selecione…</option>
          {options.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
        </select>
      )
    }
    return (
      <input
        type="search"
        value={value}
        onChange={e=>onChangeValue(e.target.value)}
        placeholder="Valor…"
        disabled={disabled}
      />
    )
  }

  return (
    <section className="project-filter-bar compact" aria-label="Filtros de projetos">
      <div className="filter-toolbar">
        <button className="button secondary" type="button" onClick={()=>setAdding(v=>!v)}>+ Adicionar filtro</button>
        <label className="filter-combine">Combinar linhas
          <select value={filters.combiners.length?filters.combiners[0]:'and'} onChange={e=>{const v=e.target.value as 'and'|'or';const next=filters.combiners.map(()=>v);onChange({rows:[...filters.rows],combiners:next})}}>
            <option value="and">E (todas as linhas)</option>
            <option value="or">OU (qualquer linha)</option>
          </select>
        </label>
        {filters.rows.length>0&&<button className="button secondary" type="button" onClick={()=>onChange(emptyProjectFilters())}>Limpar filtros</button>}
        <span className="filter-count">{filters.rows.length} linha(s) de filtro</span>
      </div>
      {adding&&(
        <div className="filter-add-row">
          <select value={newField} onChange={e=>{setNewField(e.target.value);setNewOp('contains');setNewValue('')}}>
            <option value="">Escolha o campo…</option>
            {fieldOptions.map(f=><option key={f.key} value={f.key}>{f.label}</option>)}
          </select>
          <select value={newOp} onChange={e=>setNewOp(e.target.value as FilterOp)}>
            {opOptions.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
          </select>
          {valueInput(newField,newOp,newValue,v=>setNewValue(v))}
          <button className="button" type="button" onClick={addRow} disabled={!newField||!newValue.trim()}>Adicionar linha</button>
          <button className="button secondary" type="button" onClick={()=>{setAdding(false);setNewValue('')}}>Cancelar</button>
        </div>
      )}
      {filters.rows.length>0&&(
        <div className="filter-rows" aria-label="Linhas de filtro">
          {filters.rows.map((row,i)=>{
            const editingRow=editing===i
            return (
              <div key={i} className="filter-row">
                <select value={row.field} onChange={e=>updateRow(i,{field:e.target.value,op:'contains',value:''})}>
                  {fieldOptions.map(f=><option key={f.key} value={f.key}>{f.label}</option>)}
                </select>
                <select value={row.op} onChange={e=>updateRow(i,{op:e.target.value as FilterOp})}>
                  {opOptions.map(o=><option key={o.key} value={o.key}>{o.label}</option>)}
                </select>
                {editingRow&&(
                  <>
                  {valueInput(row.field,row.op,row.value,v=>updateRow(i,{value:v}))}
                  <button className="button secondary" type="button" onClick={()=>{setEditing(null);updateRow(i,{value:row.value})}}>OK</button>
                  <button className="button secondary" type="button" onClick={()=>setEditing(null)}>Cancelar</button>
                  </>
                )}
                {!editingRow&&(
                  <span className="filter-row-value">{row.value||'(vazio)'}</span>
                )}
                {i<filters.rows.length-1&&(
                  <select value={filters.combiners[i]??'and'} onChange={e=>setCombiner(i,e.target.value as 'and'|'or')}>
                    <option value="and">E</option>
                    <option value="or">OU</option>
                  </select>
                )}
                <button className="button secondary" type="button" onClick={()=>removeRow(i)} title="Remover linha">×</button>
                {!editingRow&&<button className="button secondary" type="button" onClick={()=>setEditing(i)}>Editar</button>}
              </div>
            )
          })}
        </div>
      )}
      {filters.rows.length>0&&(
        <div className="active-filters" aria-label="Filtros ativos">{chips.map((chip,i)=><span key={i} className="filter-chip">{chip}</span>)}</div>
      )}
    </section>
  )
}
