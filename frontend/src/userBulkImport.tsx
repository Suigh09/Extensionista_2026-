import {useState,FormEvent} from 'react'
import {importUsersFromCsv,type BulkImportResult} from './api'

export function UserBulkImport({user}:{user:{role:string}}){
  void user;
  const[file,setFile]=useState<File|null>(null)
  const[result,setResult]=useState<BulkImportResult|null>(null)
  const[busy,setBusy]=useState(false)
  const[error,setError]=useState('')

  async function handleImport(event:FormEvent<HTMLFormElement>){
    event.preventDefault()
    setError('')
    setResult(null)
    if(!file)return
    setBusy(true)
    try{
      const res=await importUsersFromCsv(file)
      setResult(res)
      window.dispatchEvent(new Event('platform:changes-saved'))
      if(res.success){
        setError('')
      }else{
        setError(`Importação concluída com ${res.errors} erro(s).`)
      }
    }catch(reason){
      setError(reason instanceof Error?reason.message:'Falha ao importar usuários.')
    }finally{
      setBusy(false)
    }
  }

  return (
    <section className="profile-section" aria-labelledby="bulk-import-title">
      <div className="showcase-header">
        <div>
          <span className="eyebrow">Importação em massa</span>
          <h2 id="bulk-import-title">Importar usuários via CSV</h2>
          <p>Envie um arquivo CSV com os dados dos usuários. Apenas usuários Admin/Secretaria podem importar.</p>
        </div>
      </div>

      <div className="subheading">
        <h3>Formato do CSV</h3>
        <p>Colunas obrigatórias: <code>username</code>, <code>role</code>, <code>first_name</code>, <code>last_name</code>, <code>password</code>.</p>
        <p>Colunas opcionais: <code>email</code>, <code>ra</code> (só aluno), <code>course_code</code> (só aluno), <code>class_offering_code</code> (só aluno), <code>registration</code> (só professor).</p>
      </div>

      <div className="example-table">
        <table className="data-table">
          <thead>
            <tr><th>username</th><th>role</th><th>first_name</th><th>last_name</th><th>email</th><th>password</th><th>ra</th><th>course_code</th><th>class_offering_code</th><th>registration</th></tr>
          </thead>
          <tbody>
            <tr><td>aluno.demo01</td><td>STUDENT</td><td>Ana</td><td>Demo</td><td>ana.demo@exemplo.local</td><td>Uma-senha-segura-123</td><td>AD001</td><td>ADS</td><td>ADS-2026.2</td><td></td></tr>
            <tr><td>prof.demo01</td><td>PROFESSOR</td><td>Carlos</td><td>Demo</td><td>carlos.demo@exemplo.local</td><td>Uma-senha-segura-123</td><td></td><td></td><td></td><td>P001</td></tr>
            <tr><td>sec.demo01</td><td>SECRETARIAT</td><td>Diana</td><td>Demo</td><td>diana.demo@exemplo.local</td><td>Uma-senha-segura-123</td><td></td><td></td><td></td><td></td></tr>
          </tbody>
        </table>
      </div>

      <form className="project-form compact" onSubmit={handleImport}>
        <label>Arquivo CSV<input type="file" accept=".csv" required onChange={event=>{const f=event.target.files?.[0];if(f)setFile(f)}}/></label>
        <button className="button" type="submit" disabled={!file||busy}>{busy?'Importando…':'Importar usuários'}</button>
      </form>

      {error&&<p className="alert error" role="alert">{error}</p>}

      {result&&(
        <div className="import-result">
          <h3>Resultado</h3>
          <div className="import-stats">
            <span className="badge {result.success?'positive':'negative'}">{result.created} criado(s)</span>
            <span className="badge {result.errors>0?'negative':'neutral'}">{result.errors} erro(s)</span>
          </div>
          {result.users.length>0&&(
            <div>
              <h4>Usuários criados</h4>
              <table className="data-table">
                <thead><tr><th>Usuário</th><th>Perfil</th></tr></thead>
                <tbody>
                  {result.users.map(u=>(<tr key={u.username}><td>{u.username}</td><td>{u.role}</td></tr>))}
                </tbody>
              </table>
            </div>
          )}
          {result.error_details.length>0&&(
            <div>
              <h4>Erros</h4>
              <table className="data-table">
                <thead><tr><th>Linha</th><th>Campo</th><th>Mensagem</th></tr></thead>
                <tbody>
                  {result.error_details.map(e=>(<tr key={`${e.row}-${e.field}`}><td>{e.row}</td><td>{e.field}</td><td>{e.message}</td></tr>))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
