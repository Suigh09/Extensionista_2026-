import {useCallback,useMemo,useState}from'react'
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
}

export function ProjectListTable({projects,total,page,pageSize,onPageChange,onSort,sortField,sortDir}:ProjectListTableProps){
  const columns=[
    {key:'number',label:'#',sortable:false},
    {key:'name',label:'Título',sortable:true},
    {key:'theme',label:'Tema',sortable:false},
    {key:'status',label:'Status',sortable:true},
    {key:'created',label:'Data de abertura',sortable:true},
    {key:'updated',label:'Última atualização',sortable:true},
    {key:'leader',label:'Líder',sortable:false},
    {key:'advisor',label:'Orientador',sortable:false},
    {key:'evaluator',label:'Avaliador',sortable:false},
  ]

  const totalPages=Math.max(1,Math.ceil(total/pageSize))
  const start=(page-1)*pageSize+1
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
    let startPage=Math.max(1,page-show)
    let endPage=Math.min(totalPages,page+show)
    if(startPage>1)pages.push(1)
    if(startPage>2)pages.push(-1)
    for(let i=startPage;i<=endPage;i++)pages.push(i)
    if(endPage<totalPages-1)pages.push(-1)
    if(endPage<totalPages)pages.push(totalPages)
    return pages
  },[page,totalPages])

  return (
    <section className="project-list-table" aria-label="Lista de projetos">
      <table role="grid" aria-label="Projetos">
        <thead>
          <tr>
            <th scope="col" style={{width:'40px'}}>
              <input type="checkbox" aria-label="Selecionar todos"/>
            </th>
            {columns.map(col=>
              col.sortable?(
                <th key={col.key} scope="col" role="columnheader" tabIndex={0} onKeyDown={e=>e.key==='Enter'&&handleSort(col.key)} onClick={()=>handleSort(col.key)} style={{cursor:'pointer',userSelect:'none'}}>
                  {col.label}{sortField===col.key&&(sortDir==='asc'?' ▲':' ▼')}
                </th>
              ):(
                <th key={col.key} scope="col">{col.label}</th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {(projects??[]).length===0?(
            <tr><td colSpan={columns.length+1} role="cell">Nenhum projeto encontrado.</td></tr>
          ):(
            projects.map((project: Project)=>{
              const group=project.groups?.[0]??project.group
              const leader=group?.members.find((m:any)=>m.student_id===group?.leader_user_id)??group?.members[0]
              const themeTitle=project.theme_snapshot?.title??'—'
              return (
                <tr key={project.id} role="row" onClick={()=>{window.location.hash=`#/projects/${project.id}`}} style={{cursor:'pointer'}}>
                  <td role="cell">{project.number}</td>
                  <td role="cell">{project.name}</td>
                  <td role="cell">{themeTitle}</td>
                  <td role="cell"><span className={`badge neutral ${String(project.status)}`}>{statusLabels[String(project.status)]??project.status}</span></td>
                  <td role="cell"><time>{new Date(project.created_at).toLocaleString('pt-BR')}</time></td>
                  <td role="cell"><time>{new Date(project.updated_at).toLocaleString('pt-BR')}</time></td>
                  <td role="cell">{leader?.name??'—'}</td>
                  <td role="cell">{group?.responsible_professor_name??'—'}</td>
                  <td role="cell">{group?.evaluator_name??'—'}</td>
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
          {pageNumbers.map(p=>
            p===-1?(
              <span key="ellipsis" className="button secondary" style={{cursor:'default',pointerEvents:'none'}}>…</span>
            ):(
              <button key={p} className={page===p?'button':'button secondary'} onClick={()=>onPageChange(p)}>{p}</button>
            )
          )}
          <button className="button secondary" disabled={page>=totalPages} onClick={()=>onPageChange(page+1)}>Próxima</button>
          <button className="button secondary" disabled={page>=totalPages} onClick={()=>onPageChange(totalPages)}>Fim »</button>
        </div>
      </nav>
    </section>
  )
}
