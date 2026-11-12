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
