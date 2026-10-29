import{cleanup,fireEvent,render,screen}from'@testing-library/react'
import userEvent from'@testing-library/user-event'
import{afterEach,describe,expect,it,vi}from'vitest'
import App from'./App'

afterEach(()=>{cleanup();vi.restoreAllMocks();window.history.replaceState({},'',window.location.pathname)})

const student={id:'1',username:'aluno',name:'Aluno Teste',email:'',role:'STUDENT',profile:{ra:'RA1',cpf:'***.***.***-0001'}}

describe('App',()=>{
  it('carrega o projeto real na rota de publicação e reconhece o integrante',async()=>{
    const projectId='b73ce311-c50c-419e-8ba6-f3c1a5332e15'
    const project={id:projectId,name:'Projeto real',groups:[{id:'grupo-1',members:[{user_id:student.id}]}]}
    window.history.replaceState({},'',`/#/publication/${projectId}`)
    const fetch=vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
      const url=String(input)
      if(url.endsWith('/auth/session/'))return new Response(JSON.stringify(student))
      if(url.endsWith(`/projects/${projectId}/`))return new Response(JSON.stringify(project))
      return new Response('[]')
    })
    render(<App/>)
    expect(await screen.findByRole('heading',{name:'Publicação do projeto'})).toBeInTheDocument()
    expect(screen.getByText('Publicar no acervo',{exact:true})).toBeInTheDocument()
    expect(fetch.mock.calls.some(([input])=>String(input).endsWith(`/projects/${projectId}/`))).toBe(true)
  })

  it('oferece login por CPF, RA ou usuário sem sessão',async()=>{
    vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response('{}',{status:403}))
    render(<App/>)
    expect(await screen.findByRole('heading',{name:'Entrar na plataforma'})).toBeInTheDocument()
    expect(screen.getByLabelText('CPF, RA ou usuário')).toBeInTheDocument()
  })

  it('alterna a visibilidade da senha no login',async()=>{
    vi.spyOn(globalThis,'fetch').mockResolvedValue(new Response('{}',{status:403}))
    const user=userEvent.setup();render(<App/>)
    const password=await screen.findByLabelText('Senha')
    expect(password).toHaveAttribute('type','password')
    await user.click(screen.getByRole('button',{name:'Mostrar senha'}))
    expect(screen.getByLabelText('Senha')).toHaveAttribute('type','text')
    expect(screen.getByRole('button',{name:'Ocultar senha'})).toHaveAttribute('aria-pressed','true')
    await user.click(screen.getByRole('button',{name:'Ocultar senha'}))
    expect(screen.getByLabelText('Senha')).toHaveAttribute('type','password')
  })

  it('exibe perfil e permite logout',async()=>{
    vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{
      const url=String(input)
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(student),{status:200})
      if(url.includes('/auth/csrf/'))return new Response(JSON.stringify({csrfToken:'token'}),{status:200})
      if(url.includes('/auth/logout/')&&init?.method==='POST')return new Response(null,{status:204})
      return new Response('{}',{status:403})
    })
    render(<App/>)
    expect(await screen.findByRole('heading',{name:'Início'})).toBeInTheDocument()
    expect(screen.getByText(/Olá, Aluno Teste/)).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button',{name:'Meu perfil'})[0])
    expect(screen.getByText('RA1')).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button',{name:'Sair'})[0])
    expect(await screen.findByRole('heading',{name:'Entrar na plataforma'})).toBeInTheDocument()
  })

  it('mostra criação de projeto e colegas elegíveis para aluno com turma',async()=>{
    const withClass={...student,profile:{...student.profile,class_offering:'class-1',class_offering_label:'A · 2026.2',active_room:{id:'room-1',name:'Sala Teste',status:'ACTIVE',professor_name:'Professor Teste'}}}
    vi.spyOn(globalThis,'fetch')
      .mockResolvedValueOnce(new Response(JSON.stringify(withClass),{status:200}))
      .mockResolvedValueOnce(new Response('[]',{status:200}))
      .mockResolvedValueOnce(new Response('[]',{status:200}))
      .mockResolvedValueOnce(new Response(JSON.stringify([{id:'profile-2',user:'2',name:'Colega Dois',ra:'RA2'}]),{status:200}))
    render(<App/>)
    expect(await screen.findByRole('heading',{name:'Início'})).toBeInTheDocument()
    await userEvent.click(screen.getAllByRole('button',{name:'Projetos'})[0])
    expect(await screen.findByRole('heading',{name:'Meus projetos'})).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button',{name:'+ Criar projeto'}))
    expect(screen.getByLabelText('Título do projeto')).toBeInTheDocument()
    expect(screen.getByLabelText('Sobre o projeto')).toBeInTheDocument()
  })

  it('cria o projeto antes de formar o grupo',async()=>{
    const withClass={...student,profile:{...student.profile,class_offering:'class-1',class_offering_label:'A · 2026.2',active_room:{id:'room-1',name:'Sala Teste',status:'ACTIVE',professor_name:'Professor Teste'}}}
    const project={id:'project-1',name:'Projeto Cidadania',about:'Proposta de impacto social.',created_by_name:'Aluno Teste',class_offering:'class-1',status:'DRAFT',is_active:true,created_at:'',updated_at:'',submitted_at:null,reviewed_at:null,review_feedback:'',reviewed_by:null,group:{id:'group-1',name:'Grupo principal',class_offering:'class-1',member_count:1,formation_status:'FORMING',members:[{user_id:'1',name:'Aluno Teste',ra:'RA1',joined_at:''}],responsible_professor_name:'Professor Orientador',evaluator_name:null}}
    let created=false
    vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{
      const url=String(input),method=init?.method??'GET'
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(withClass),{status:200})
      if(url.includes('/projects/themes/'))return new Response(JSON.stringify([{id:'theme-1',title:'Tema Cidadania',description:'Orientações',room:'room-1',room_name:'Sala Teste',is_open:true,max_projects:null,project_count:0}]),{status:200})
      if(url.includes('/auth/csrf/'))return new Response(JSON.stringify({csrfToken:'token'}),{status:200})
      if(url.includes('/projects/?q=')&&method==='GET')return new Response(JSON.stringify(created?[project]:[]),{status:200})
      if(url.endsWith('/projects/project-1/')&&method==='GET')return new Response(JSON.stringify(project),{status:200})
      if(url.endsWith('/projects/')&&method==='POST'){created=true;return new Response(JSON.stringify(project),{status:201})}
      if(url.includes('/invitations/mine/'))return new Response('[]',{status:200})
      if(url.includes('/project-1/invitations/'))return new Response('[]',{status:200})
      if(url.includes('/eligible-students/'))return new Response(JSON.stringify([{id:'profile-2',user:'2',name:'Colega Dois',ra:'RA2'}]),{status:200})
      return new Response('{}',{status:400})
    })
    const user=userEvent.setup();render(<App/>)
    await screen.findByRole('heading',{name:'Início'})
    await user.click(screen.getAllByRole('button',{name:'Projetos'})[0])
    await user.click(await screen.findByRole('button',{name:'+ Criar projeto'}))
    await screen.findByRole('option',{name:/Tema Cidadania/})
    fireEvent.change(await screen.findByLabelText('Tema do projeto'),{target:{value:'theme-1'}})
    await user.type(await screen.findByLabelText('Título do projeto'),'Projeto Cidadania')
    await user.type(screen.getByLabelText('Sobre o projeto'),'Proposta de impacto social.')
    await user.click(screen.getByRole('button',{name:'Criar projeto'}))
    expect(await screen.findByRole('heading',{name:'Projeto Cidadania'})).toBeInTheDocument()
    expect(screen.getAllByText('Proposta de impacto social.').length).toBeGreaterThan(0)
    expect(await screen.findByText('Forme seu grupo antes de enviar')).toBeInTheDocument()
    const search=screen.getByLabelText('Buscar aluno')
    expect(search).toBeInTheDocument()
    await user.type(search,'Colega')
    expect(await screen.findByText('Colega Dois')).toBeInTheDocument()
    expect(screen.getByRole('button',{name:'Convidar'})).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Enviar projeto para aprovação'})).not.toBeInTheDocument()
  })

  it('protege texto não salvo antes de trocar de tela',async()=>{
    const withClass={...student,profile:{...student.profile,class_offering:'class-1',class_offering_label:'A · 2026.2',active_room:{id:'room-1',name:'Sala Teste',status:'ACTIVE',professor_name:'Professor Teste'},projects:[]}}
    vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
      const url=String(input)
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(withClass),{status:200})
      if(url.includes('/projects/?q=')||url.includes('/invitations/mine/'))return new Response('[]',{status:200})
      return new Response('{}',{status:403})
    })
    const user=userEvent.setup();render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await user.click(screen.getAllByRole('button',{name:'Projetos'})[0])
    await user.click(await screen.findByRole('button',{name:'+ Criar projeto'}))
    const title=await screen.findByLabelText('Título do projeto')
    await user.type(title,'Texto que não pode ser perdido')
    const typedValue=(title as HTMLInputElement).value
    await user.click(screen.getAllByRole('button',{name:'Início'})[0])
    const dialog=await screen.findByRole('dialog',{name:'Descartar alterações?'})
    expect(dialog).toHaveAttribute('aria-describedby')
    expect(screen.getAllByRole('button',{name:'Cancelar'}).at(-1)!).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog',{name:'Descartar alterações?'})).not.toBeInTheDocument()
    expect(screen.getAllByRole('button',{name:'Início'})[0]).toHaveFocus()
    expect(screen.getByLabelText('Título do projeto')).toHaveValue(typedValue)
    await user.click(screen.getAllByRole('button',{name:'Início'})[0])
    await user.click(screen.getByRole('button',{name:'Descartar alterações'}))
    expect(await screen.findByRole('heading',{name:'Início'})).toBeInTheDocument()
  })

  it('navega da home para comunidade funcional',async()=>{
    vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
      const url=String(input)
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(student),{status:200})
      if(url.includes('/collaborations/opportunities/')||url.includes('/projects/?q='))return new Response('[]',{status:200})
      return new Response('{}',{status:403})
    })
    render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await userEvent.click(screen.getAllByRole('button',{name:'Colaborações Acadêmicas'})[0])
    expect(await screen.findByRole('heading',{name:'Colaborações Acadêmicas',level:2})).toBeInTheDocument()
    expect(await screen.findByText('Nenhum convite disponível.')).toBeInTheDocument()
  })

  it('publica oportunidade interdisciplinar pela comunidade',async()=>{
    const withClass={...student,profile:{...student.profile,class_offering:'class-1',class_offering_label:'A · 2026.2',active_room:{id:'room-1',name:'Sala Teste',status:'ACTIVE',professor_name:'Professor Teste'}}}
    const project={id:'project-1',name:'Projeto Cidadania',about:'Descrição',created_by_name:'Aluno Teste',class_offering:'class-1',status:'APPROVED',is_active:true,created_at:'',updated_at:'',submitted_at:'',reviewed_at:'',review_feedback:'',reviewed_by:null,group:{id:'group-1',name:'Grupo principal',class_offering:'class-1',member_count:2,formation_status:'FORMED',members:[],responsible_professor_name:null,evaluator_name:null},groups:[]}
    const opportunity={id:'opp-1',group:'group-1',project_id:'project-1',project_name:'Projeto Cidadania',group_name:'Grupo principal',class_label:'Extensão · A · 2026.2',member_count:2,title:'Apoio em experiência do usuário',description:'Precisamos validar a solução.',desired_skills:['UX'],status:'OPEN',created_at:'',updated_at:'',is_owner:true,applications:[]}
    let published=false
    vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{
      const url=String(input),method=init?.method??'GET'
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(withClass),{status:200})
      if(url.includes('/auth/csrf/'))return new Response(JSON.stringify({csrfToken:'token'}),{status:200})
      if(url.includes('/collaborations/opportunities/')&&method==='GET')return new Response(JSON.stringify(published?[opportunity]:[]),{status:200})
      if(url.includes('/collaborations/opportunities/')&&method==='POST'){published=true;return new Response(JSON.stringify(opportunity),{status:201})}
      if(url.includes('/projects/?q='))return new Response(JSON.stringify([project]),{status:200})
      return new Response('{}',{status:403})
    })
    const user=userEvent.setup();render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await user.click(screen.getAllByRole('button',{name:'Colaborações Acadêmicas'})[0])
    await screen.findByRole('heading',{name:'Colaborações Acadêmicas',level:2})
    await user.selectOptions(screen.getByLabelText('Projeto e grupo'),'group-1')
    await user.type(screen.getByLabelText('Título'),'Apoio em experiência do usuário')
    await user.type(screen.getByLabelText('Como outro grupo pode colaborar?'),'Precisamos validar a solução.')
    await user.click(screen.getByRole('button',{name:'Publicar convite'}))
    expect(await screen.findByText('Convite de colaboração publicado.')).toBeInTheDocument()
    expect(await screen.findByRole('heading',{name:'Apoio em experiência do usuário'})).toBeInTheDocument()
  })

  it('separa projetos e acompanhamento para o professor',async()=>{
    const professor={id:'p1',username:'professor',name:'Professora Teste',email:'',role:'PROFESSOR',profile:{registration:'P1',class_offerings:[{id:'class-1',label:'Extensão · A · 2026.2'}]}}
    vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
      const url=String(input)
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(professor),{status:200})
      if(url.includes('/available-to-professor/')||url.includes('/milestones/'))return new Response('[]',{status:200})
      return new Response('{}',{status:403})
    })
    render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await userEvent.click(screen.getAllByRole('button',{name:'Projetos'})[0])
    expect(await screen.findByRole('heading',{name:'Projetos sob minha responsabilidade'})).toBeInTheDocument()
    expect(screen.queryByRole('button',{name:'Acompanhamento'})).not.toBeInTheDocument()
  })

  it('professor administra sala e solicita transferência à secretaria',async()=>{
    const professor={id:'p1',username:'professor1',name:'Professor 1',email:'',role:'PROFESSOR',profile:{registration:'P1',class_offerings:[]}}
    const room={id:'room-1',name:'Sala de Projetos',academic_identifier:'2026.2',status:'ACTIVE',professor_name:'Professor 1',student_count:0}
    const candidate={id:'student-2',name:'Aluno Dois',ra:'RA2',course_name:'ADS',active_room:{id:'room-2',name:'Sala Anterior',status:'ACTIVE',professor_name:'Professor 2'}}
    vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{
      const url=String(input),method=init?.method??'GET'
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(professor),{status:200})
      if(url.includes('/auth/csrf/'))return new Response(JSON.stringify({csrfToken:'token'}),{status:200})
      if(url.endsWith('/academic/rooms/')&&method==='GET')return new Response(JSON.stringify([room]),{status:200})
      if(url.includes('/academic/rooms/room-1/students/'))return new Response('[]',{status:200})
      if(url.includes('/academic/eligible-students/'))return new Response(JSON.stringify([candidate]),{status:200})
      if(url.includes('/academic/rooms/room-1/pull-student/')&&method==='POST')return new Response(JSON.stringify({id:'transfer-1',status:'PENDING'}),{status:202})
      return new Response('{}',{status:403})
    })
    const user=userEvent.setup();render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await user.click(screen.getAllByRole('button',{name:'Salas'})[0])
    await user.click(await screen.findByRole('button',{name:/Sala de Projetos/}))
    await user.type(screen.getByLabelText('Buscar aluno por nome ou RA'),'Aluno')
    expect(await screen.findByText('Aluno Dois')).toBeInTheDocument()
    await user.click(screen.getByRole('button',{name:'Solicitar transferência'}))
    expect(await screen.findByRole('dialog',{name:'Solicitar transferência?'})).toHaveTextContent('Sala Anterior')
    await user.click(screen.getByRole('button',{name:'Enviar solicitação'}))
    expect(await screen.findByText(/enviada à secretaria/)).toBeInTheDocument()
  })

  it('professor cadastra competência livre no perfil',async()=>{
    const professor={id:'p1',username:'professor1',name:'Professor 1',email:'',role:'PROFESSOR',profile:{registration:'P1',class_offerings:[],expertise:[]}}
    const expertise={id:'exp-1',kind:'COMPETENCY',text:'Desenvolvimento Web',normalized_text:'desenvolvimento web'}
    let created=false
    vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{
      const url=String(input),method=init?.method??'GET'
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(professor),{status:200})
      if(url.includes('/auth/csrf/'))return new Response(JSON.stringify({csrfToken:'token'}),{status:200})
      if(url.endsWith('/academic/my-expertise/')&&method==='GET')return new Response(JSON.stringify(created?[expertise]:[]),{status:200})
      if(url.endsWith('/academic/my-expertise/')&&method==='POST'){created=true;return new Response(JSON.stringify(expertise),{status:201})}
      return new Response('{}',{status:403})
    })
    const user=userEvent.setup();render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await user.click(screen.getAllByRole('button',{name:'Meu perfil'})[0])
    await user.type(await screen.findByLabelText('Descrição'),'Desenvolvimento Web')
    await user.click(screen.getByRole('button',{name:'Adicionar'}))
    expect(await screen.findByText('Item adicionado.')).toBeInTheDocument()
    expect(await screen.findByText('Desenvolvimento Web')).toBeInTheDocument()
  })

  it('secretaria aprova solicitação de transferência com origem e destino',async()=>{
    const secretary={id:'s1',username:'secretaria',name:'Secretaria',email:'',role:'SECRETARIAT',profile:null}
    const request={id:'transfer-1',student_name:'Aluno Dois',student_ra:'RA2',source_room_name:'Sala Anterior',destination_room_name:'Sala de Projetos',source_professor_name:'Professor 2',destination_professor_name:'Professor 1',status:'PENDING',created_at:'2026-08-26T12:00:00Z'}
    let approved=false
    vi.spyOn(globalThis,'fetch').mockImplementation(async(input,init)=>{
      const url=String(input),method=init?.method??'GET'
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(secretary),{status:200})
      if(url.includes('/auth/csrf/'))return new Response(JSON.stringify({csrfToken:'token'}),{status:200})
      if(url.endsWith('/academic/room-transfer-requests/')&&method==='GET')return new Response(JSON.stringify([{...request,status:approved?'APPROVED':'PENDING'}]),{status:200})
      if(url.includes('/room-transfer-requests/transfer-1/approve/')&&method==='POST'){approved=true;return new Response(JSON.stringify({...request,status:'APPROVED'}),{status:200})}
      return new Response('{}',{status:403})
    })
    const user=userEvent.setup();render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await user.click(screen.getAllByRole('button',{name:'Administração'})[0])
    expect(await screen.findByText(/Sala Anterior/)).toBeInTheDocument()
    await user.click(await screen.findByRole('button',{name:'Aprovar'}))
    expect(await screen.findByRole('dialog',{name:'Aprovar transferência?'})).toHaveTextContent('Sala de Projetos')
    await user.type(screen.getByLabelText('Observação opcional'),'Transferência conferida')
    await user.click(screen.getByRole('button',{name:'Confirmar aprovação'}))
    expect(await screen.findByText('Transferência aprovada.')).toBeInTheDocument()
    expect(await screen.findByText('Aprovada')).toBeInTheDocument()
  })

  it('mantém administração restrita aos perfis autorizados',async()=>{
    const admin={id:'a1',username:'admin',name:'Admin Teste',email:'',role:'ADMIN',profile:null}
    vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
      const url=String(input)
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(admin),{status:200})
      if(url.includes('/auth/users/'))return new Response('[]',{status:200})
      return new Response('{}',{status:403})
    })
    render(<App/>);await screen.findByRole('heading',{name:'Início'})
    await userEvent.click(screen.getAllByRole('button',{name:'Administração'})[0])
    expect(await screen.findByRole('heading',{name:'Criar usuário'})).toBeInTheDocument()
  })

  it('apresenta estado vazio do acompanhamento do aluno',async()=>{
    vi.spyOn(globalThis,'fetch').mockImplementation(async input=>{
      const url=String(input)
      if(url.includes('/auth/session/'))return new Response(JSON.stringify(student),{status:200})
      if(url.endsWith('/projects/'))return new Response('[]',{status:200})
      return new Response('{}',{status:403})
    })
    render(<App/>);await screen.findByRole('heading',{name:'Início'})
    expect(screen.queryByRole('button',{name:'Acompanhamento'})).not.toBeInTheDocument()
  })
})
