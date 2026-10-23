import {useCallback,useEffect,useState} from 'react'
import {listNotifications,markAllNotificationsRead,markNotificationRead,type NotificationItem} from './api'

const navigate=(hash:string)=>window.dispatchEvent(new CustomEvent('platform:navigate',{detail:hash}))
const failure=(error:unknown)=>error instanceof Error?error.message:'Não foi possível concluir a operação.'

export function NotificationBell(){
  const[items,setItems]=useState<NotificationItem[]>([]),[open,setOpen]=useState(false),[message,setMessage]=useState('')
  const unread=items.filter(item=>!item.is_read).length
  const refresh=useCallback(async()=>{
    try{setItems(await listNotifications())}catch(e){setMessage(failure(e))}
  },[])
  useEffect(()=>{void refresh()},[refresh])
  useEffect(()=>{
    if(!open)return
    const close=()=>setOpen(false)
    const key=(e:KeyboardEvent)=>{if(e.key==='Escape')setOpen(false)}
    document.addEventListener('click',close,true)
    document.addEventListener('keydown',key)
    return()=>{document.removeEventListener('click',close,true);document.removeEventListener('keydown',key)}
  },[open])
  async function openItem(item:NotificationItem){
    try{
      if(!item.is_read)await markNotificationRead(item.id)
      setOpen(false)
      if(item.project)navigate(`#/projects/${item.project}`)
      else await refresh()
    }catch(e){setMessage(failure(e))}
  }
  async function readAll(){
    try{await markAllNotificationsRead();await refresh()}catch(e){setMessage(failure(e))}
  }
  async function deleteItem(id:string){
    try{await markNotificationRead(id)
    setItems(items=>items.filter(i=>i.id!==id))}catch(e){setMessage(failure(e))}
  }
  return <div className="notification-bell" onClick={e=>e.stopPropagation()}>
    <button type="button" className="nav-item" aria-pressed={open} aria-label={unread>0?`Notificações, ${unread} não lidas`:'Notificações'} onClick={()=>setOpen(value=>!value)}>
      <span aria-hidden="true">🔔</span>{unread>0&&<span className="badge">{unread}</span>}
    </button>
    {open&&<div className="notification-overlay">
      <section className="notification-panel" aria-label="Notificações">
        <div className="notification-header"><h2>Notificações</h2>{unread>0&&<button type="button" className="button secondary" onClick={()=>void readAll()}>Marcar todas como lidas</button>}</div>
        {message&&<p role="alert" className="alert error">{message}</p>}
        <div className="notification-list">
          {items.length===0?<p className="empty-state">Nenhuma notificação.</p>:<ul>{items.map(item=><li key={item.id}><button type="button" className={item.is_read?'notification-read':'notification-unread'} onClick={()=>void openItem(item)}><strong>{item.title}</strong><span>{item.body}</span><small>{new Date(item.created_at).toLocaleString('pt-BR')}</small></button><button type="button" className="button danger-sm" onClick={()=>void deleteItem(item.id)}>×</button></li>)}</ul>}
        </div>
      </section>
    </div>}
  </div>
}
