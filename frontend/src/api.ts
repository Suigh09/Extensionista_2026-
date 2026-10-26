export type Role='STUDENT'|'PROFESSOR'|'SECRETARIAT'|'ADMIN'
export type AcademicItem={id:string;code:string;name:string}
export type ClassOfferingOption={id:string;label:string;subject_name?:string;offering_code?:string;term?:string;student_count?:number}
export type EnrollmentSummary={id:string;subject_code:string;subject_name:string;offering_code:string;term:string;professors:string[]}
export type ProfileProject={id:string;name:string;status:ProjectStatus;advisor?:string|null;evaluator?:string|null;members?:string[]}
export type RoomSummary={id:string;name:string;academic_identifier?:string;status:'ACTIVE'|'CLOSED';professor_name?:string;student_count?:number}
export type Expertise={id:string;kind:'DISCIPLINE'|'COMPETENCY';text:string;normalized_text?:string}
export type Profile={id:string;username:string;name:string;email:string;role:Role;profile:null|{ra?:string;cpf?:string;registration?:string;course?:AcademicItem|null;courses?:AcademicItem[];subjects?:AcademicItem[];current_term?:string|null;class_offering?:string|null;class_offering_label?:string|null;class_offerings?:ClassOfferingOption[];enrollments?:EnrollmentSummary[];projects?:ProfileProject[];advising_projects?:ProfileProject[];evaluating_projects?:ProfileProject[];active_room?:RoomSummary|null;expertise?:Expertise[]}}
export type NewUser={username:string;password:string;name:string;email?:string;role:Role;ra?:string;cpf?:string;registration?:string;course?:string}
export type Member={user_id:string;student_id:number;name:string;ra:string;joined_at:string}
export type ProjectGroup={id:string;name:string;class_offering:string;member_count:number;formation_status:'FORMING'|'FORMED'|'COMPLETE';members:Member[];responsible_professor_name:string|null;evaluator_name:string|null;leader?:number|null;leader_user_id?:string|null}
export type ProjectStatus='DRAFT'|'PENDING_APPROVAL'|'CHANGES_REQUESTED'|'APPROVED'|'COMPLETED'|'ARCHIVED'|'PAUSED'|'CANCELLED'
export type Project={id:string;name:string;about:string;class_offering:string;status:ProjectStatus;is_active:boolean;created_at:string;updated_at:string;created_by_name:string;submitted_at:string|null;reviewed_at:string|null;review_feedback:string;reviewed_by:string|null;group:ProjectGroup;groups?:ProjectGroup[];theme?:string|null;theme_snapshot?:{title?:string;description?:string};previous_status?:ProjectStatus;can_manage?:boolean;lifecycle?:{id:number;action:string;previous_status:string;new_status:string;reason:string;actor_name:string;created_at:string}[];cancellation_requests?:{id:string;reason:string;status:string;requested_by_name:string;decision_note:string;created_at:string;decided_at:string|null}[]}
export type Invitation={id:string;group:string;project_name:string;invitee_user_id:string;invitee_name:string;invitee_ra:string;status:'PENDING'|'ACCEPTED'|'DECLINED'|'CANCELLED';created_at:string;decided_at:string|null}
export type EligibleStudent={id:string;user:string;name:string;ra:string;course_name:string;class_code:string;term:string}
export type Attachment={id:string;original_name:string;content_type:string;size:number;download_url:string}
export type FollowUp={id:string;project:string;author_name:string;author_role:Role;text:string;kind:string;attachments:Attachment[];created_at:string}
export type Milestone={id:string;title:string;description:string;due_at:string;scope?:'PROJECTS'|'CLASS';requires_delivery:boolean;requires_approval:boolean;created_by_name:string;created_at?:string;assigned_at?:string;project_count?:number}
export type TimelineItem={id:string;event_type:'FOLLOW_UP';occurred_at:string;title:string;description:string;author_role:Role;attachments:Attachment[]}
export type CollaborationApplication={id:string;opportunity:string;candidate_group:string;candidate_group_name:string;candidate_project_name:string;candidate_class_label:string;candidate_member_count:number;message:string;status:'PENDING'|'ACCEPTED'|'DECLINED'|'CANCELLED';created_at:string;decided_at:string|null;is_mine:boolean}
export type CollaborationOpportunity={id:string;group:string;project_id:string;project_name:string;group_name:string;class_label:string;member_count:number;title:string;description:string;desired_skills:string[];status:'OPEN'|'MATCHED'|'CLOSED';created_at:string;updated_at:string;is_owner:boolean;applications:CollaborationApplication[]}
export type RoomStudent={id:string;name:string;ra:string;course_name?:string;active_room?:RoomSummary|null}
export type AcademicRoom=RoomSummary&{created_at?:string;closed_at?:string|null;students?:RoomStudent[];professor_name?:string}
export type PullStudentResult={action:'ADDED'|'TRANSFER_REQUESTED';detail?:string;transfer_request?:RoomTransferRequest}
export type RoomTransferRequest={id:string;student_name:string;student_ra:string;source_room_name:string;destination_room_name:string;source_professor_name:string;destination_professor_name:string;status:'PENDING'|'APPROVED'|'DECLINED'|'INVALIDATED';created_at:string;decided_at?:string|null;decision_note?:string}

const API=import.meta.env.VITE_API_BASE_URL??`${window.location.protocol}//${window.location.hostname}:8000/api/v1`
let token=''
async function csrf(){if(!token){const response=await fetch(`${API}/auth/csrf/`,{credentials:'include'});token=(await response.json()).csrfToken}return token}
function errorMessage(body:unknown){if(body&&typeof body==='object'){const record=body as Record<string,unknown>;if(typeof record.detail==='string')return record.detail;const first=Object.values(record)[0];if(Array.isArray(first)&&typeof first[0]==='string')return first[0];if(typeof first==='string')return first}return'Não foi possível concluir a operação.'}
async function request<T>(path:string,init:RequestInit={}):Promise<T>{const headers=new Headers(init.headers);headers.set('Accept','application/json');if(init.method&&init.method!=='GET'){if(!(init.body instanceof FormData))headers.set('Content-Type','application/json');headers.set('X-CSRFToken',await csrf())}const response=await fetch(`${API}${path}`,{...init,headers,credentials:'include'});if(!response.ok){const body=await response.json().catch(()=>({}));throw new Error(errorMessage(body))}return response.status===204?undefined as T:response.json() as Promise<T>}

export const getSession=()=>request<Profile>('/auth/session/')
export async function login(identifier:string,password:string){const profile=await request<Profile>('/auth/login/',{method:'POST',body:JSON.stringify({identifier,password})});token='';return profile}
export async function logout(){await request<void>('/auth/logout/',{method:'POST'});token=''}
export const listUsers=()=>request<Profile[]>('/auth/users/')
export const listCourses=()=>request<AcademicItem[]>('/academic/courses/?is_active=true')
export const createUser=(user:NewUser)=>request<Profile>('/auth/users/',{method:'POST',body:JSON.stringify(user)})
export const listProjects=(query='')=>request<Project[]>(`/projects/?q=${encodeURIComponent(query)}`)
export const getProject=(projectId:string)=>request<Project>(`/projects/${projectId}/`)
export const createProject=(project:{name:string;about:string;theme:string;leader?:number;student_ids?:number[]})=>request<Project>('/projects/',{method:'POST',body:JSON.stringify(project)})
export const updateProject=(projectId:string,project:{name:string;about:string})=>request<Project>(`/projects/${projectId}/`,{method:'PATCH',body:JSON.stringify(project)})
export const submitProjectForApproval=(projectId:string)=>request<Project>(`/projects/${projectId}/submit/`,{method:'POST',body:'{}'})
export const approveProject=(projectId:string,feedback='')=>request<Project>(`/projects/${projectId}/approve/`,{method:'POST',body:JSON.stringify({feedback})})
export const requestProjectChanges=(projectId:string,feedback:string)=>request<Project>(`/projects/${projectId}/request-changes/`,{method:'POST',body:JSON.stringify({feedback})})
export const listEligibleStudents=(query:string,projectId='')=>request<EligibleStudent[]>(`/projects/eligible-students/?q=${encodeURIComponent(query)}&project=${encodeURIComponent(projectId)}`)
export const inviteStudent=(projectId:string,invitee:string)=>request<Invitation>(`/projects/${projectId}/invitations/`,{method:'POST',body:JSON.stringify({invitee})})
export const listProjectInvitations=(projectId:string)=>request<Invitation[]>(`/projects/${projectId}/invitations/`)
export const listMyInvitations=()=>request<Invitation[]>('/projects/invitations/mine/')
export const decideInvitation=(id:string,decision:'accept'|'decline'|'cancel',replaceActive=false)=>request<Invitation>(`/projects/invitations/${id}/${decision}/`,{method:'POST',body:JSON.stringify({replace_active:replaceActive})})
export const listFollowUps=(projectId:string)=>request<FollowUp[]>(`/projects/${projectId}/follow-ups/`)
export const createFollowUp=(projectId:string,data:FormData)=>request<FollowUp>(`/projects/${projectId}/follow-ups/`,{method:'POST',body:data})
export const attachmentUrl=(path:string)=>`${API}${path}`
export const listTimeline=(projectId:string)=>request<TimelineItem[]>(`/projects/${projectId}/timeline/`)
export const listProjectMilestones=(projectId:string)=>request<Milestone[]>(`/projects/${projectId}/milestones/`)
export const listProfessorProjects=()=>request<Project[]>('/projects/available-to-professor/')
export const listMilestones=()=>request<Milestone[]>('/projects/milestones/')
export const createMilestone=(data:{title:string;description:string;due_at:string;scope:'PROJECTS'|'CLASS';requires_delivery:boolean;requires_approval:boolean;class_offering?:string;project_ids?:string[]})=>request<Milestone>('/projects/milestones/',{method:'POST',body:JSON.stringify(data)})
export const listCollaborationOpportunities=(query='')=>request<CollaborationOpportunity[]>(`/projects/collaborations/opportunities/?q=${encodeURIComponent(query)}`)
export const createCollaborationOpportunity=(data:{group:string;title:string;description:string;desired_skills:string[]})=>request<CollaborationOpportunity>('/projects/collaborations/opportunities/',{method:'POST',body:JSON.stringify(data)})
export const applyToCollaboration=(opportunityId:string,data:{candidate_group:string;message:string})=>request<CollaborationApplication>(`/projects/collaborations/opportunities/${opportunityId}/applications/`,{method:'POST',body:JSON.stringify(data)})
export const decideCollaboration=(applicationId:string,decision:'accept'|'decline'|'cancel')=>request<CollaborationApplication>(`/projects/collaborations/applications/${applicationId}/${decision}/`,{method:'POST',body:'{}'})
export const listRooms=()=>request<AcademicRoom[]>('/academic/rooms/')
export const getRoom=(id:string)=>request<AcademicRoom>(`/academic/rooms/${id}/`)
export const createRoom=(data:{name:string;academic_identifier?:string})=>request<AcademicRoom>('/academic/rooms/',{method:'POST',body:JSON.stringify(data)})
export const closeRoom=(id:string)=>request<AcademicRoom>(`/academic/rooms/${id}/close/`,{method:'POST',body:'{}'})
export const listRoomStudents=(id:string)=>request<RoomStudent[]>(`/academic/rooms/${id}/students/`)
export const listAcademicEligibleStudents=(query:string)=>request<RoomStudent[]>(`/academic/eligible-students/?q=${encodeURIComponent(query)}`)
export const pullStudent=(roomId:string,studentId:string)=>request<PullStudentResult>(`/academic/rooms/${roomId}/pull-student/`,{method:'POST',body:JSON.stringify({student:studentId})})
export const listMyExpertise=()=>request<Expertise[]>('/academic/my-expertise/')
export const createExpertise=(data:{kind:Expertise['kind'];text:string})=>request<Expertise>('/academic/my-expertise/',{method:'POST',body:JSON.stringify(data)})
export const updateExpertise=(id:string,data:{text:string})=>request<Expertise>(`/academic/my-expertise/${id}/`,{method:'PATCH',body:JSON.stringify(data)})
export const deleteExpertise=(id:string)=>request<void>(`/academic/my-expertise/${id}/`,{method:'DELETE'})
export const listRoomTransferRequests=()=>request<RoomTransferRequest[]>('/academic/room-transfer-requests/')
export const decideRoomTransfer=(id:string,decision:'approve'|'decline',decision_note='')=>request<RoomTransferRequest>(`/academic/room-transfer-requests/${id}/${decision}/`,{method:'POST',body:JSON.stringify({decision_note})})

export type ProjectTheme={id:string;room:string;room_name:string;title:string;description:string;is_open:boolean;max_projects:number|null;project_count:number}
export const listThemes=()=>request<ProjectTheme[]>('/projects/themes/')
export const saveTheme=(data:{room:string;title:string;description:string;max_projects:number|null})=>request<ProjectTheme>('/projects/themes/',{method:'POST',body:JSON.stringify(data)})
export const updateTheme=(id:string,data:Partial<Pick<ProjectTheme,'title'|'description'|'is_open'|'max_projects'>>)=>request<ProjectTheme>(`/projects/themes/${id}/`,{method:'PATCH',body:JSON.stringify(data)})
export const searchThemeStudents=(id:string,q:string)=>request<EligibleStudent[]>(`/projects/themes/${id}/students/?q=${encodeURIComponent(q)}`)
export const projectTransition=(id:string,action:string,reason:string)=>request<Project>(`/projects/${id}/lifecycle/`,{method:'POST',body:JSON.stringify({action,reason})})
export const assignProjectStudent=(id:string,student_id:number,make_leader=false)=>request<Project>(`/projects/${id}/assign-student/`,{method:'POST',body:JSON.stringify({student_id,make_leader})})
export const listInstitutionalProjects=()=>request<Project[]>('/projects/institutional/')

export type DeliveryStatus='SUBMITTED'|'APPROVED'|'CHANGES_REQUESTED'
export type Delivery={id:string;project:string;group:string;group_name:string;version:number;title_snapshot:string;about_snapshot:string;notes:string;original_name:string;content_type:string;size:number;status:DeliveryStatus;submitted_by_name:string;submitted_at:string;review_feedback:string;reviewed_by_name:string|null;reviewed_at:string|null;download_url:string}
export type Forwarding={project:string;project_name:string;snapshot:Record<string,{delivery_id:string;version:number}>;observations:string;required_competencies:string;forwarded_by_name:string;forwarded_at:string}
export const listDeliveries=(projectId:string)=>request<Delivery[]>(`/projects/${projectId}/deliveries/`)
export const submitDelivery=(projectId:string,data:FormData)=>request<Delivery>(`/projects/${projectId}/deliveries/`,{method:'POST',body:data})
export const reviewDelivery=(deliveryId:string,decision:'APPROVED'|'CHANGES_REQUESTED',feedback='')=>request<Delivery>(`/projects/deliveries/${deliveryId}/review/`,{method:'POST',body:JSON.stringify({decision,feedback})})
export const deliveryDownloadUrl=(path:string)=>attachmentUrl(path)
export const getForwarding=(projectId:string)=>request<Forwarding>(`/projects/${projectId}/forward/`)
export const forwardProject=(projectId:string,data:{observations:string;required_competencies:string})=>request<Forwarding>(`/projects/${projectId}/forward/`,{method:'POST',body:JSON.stringify(data)})
export const listForwarded=()=>request<Forwarding[]>('/projects/forwarded/')

export type NotificationItem={id:string;kind:string;title:string;body:string;project:string|null;project_name:string|null;is_read:boolean;read_at:string|null;created_at:string}
export const listNotifications=()=>request<NotificationItem[]>('/auth/notifications/')
export const markNotificationRead=(id:string)=>request<NotificationItem>(`/auth/notifications/${id}/read/`,{method:'POST',body:'{}'})
export const markAllNotificationsRead=()=>request<void>('/auth/notifications/read-all/',{method:'POST',body:'{}'})

export type EvaluationRecommendation={professor_profile_id:string;name:string;matched:Record<string,string[]>;match_count:number;load:number}
export type EvaluationGroup={group_id:string;group_name:string;responsible_professor_name:string|null;evaluator_profile_id:string|null;evaluator_name:string|null}
export type AssignmentRecord={id:string;group:string;group_name:string;evaluator:string;evaluator_name:string;recommended:{professor_profile_id:string;name:string;match_count:number;load:number}[];justification:string;decided_by_name:string;decided_at:string}
export type RecommendationResponse={keywords:string[];recommendations:EvaluationRecommendation[];groups:EvaluationGroup[];history:AssignmentRecord[]}
export type SearchedProfessor={id:string;name:string;registration:string}
export const recommendEvaluators=(projectId:string)=>request<RecommendationResponse>(`/projects/${projectId}/evaluator-recommendations/`)
export const designateEvaluator=(groupId:string,data:{professor:string;justification:string})=>request<AssignmentRecord>(`/projects/groups/${groupId}/designate-evaluator/`,{method:'POST',body:JSON.stringify(data)})
export const searchProfessors=(q:string)=>request<SearchedProfessor[]>(`/academic/professors/search/?q=${encodeURIComponent(q)}`)

export type Criterion={id:string;name:string;description:string;position:number}
export type Rubric={id:string;title:string;criteria:Criterion[];created_at:string;updated_at:string}
export type GradeItem={criterion:string;criterion_name:string;value:string}
export type GradeSubmission={id:string;group:string;rubric:string;rubric_title:string;author_name:string;comment:string;concluded:boolean;created_at:string;items:GradeItem[]}
export type GroupGrades={average:string|null;submissions:GradeSubmission[]}
export type IndividualGrade={id:string;student:string;student_name:string;group:string;value:string;comment:string;author_name:string;created_at:string}
export const listRubrics=()=>request<Rubric[]>('/projects/rubrics/')
export const createRubric=(data:{title:string;criteria:{name:string;description:string}[]})=>request<Rubric>('/projects/rubrics/',{method:'POST',body:JSON.stringify(data)})
export const updateRubricTitle=(id:string,title:string)=>request<Rubric>(`/projects/rubrics/${id}/`,{method:'PATCH',body:JSON.stringify({title})})
export const deleteRubric=(id:string)=>request<void>(`/projects/rubrics/${id}/`,{method:'DELETE'})
export const addCriterion=(rubricId:string,data:{name:string;description:string})=>request<Criterion>(`/projects/rubrics/${rubricId}/criteria/`,{method:'POST',body:JSON.stringify(data)})
export const deleteCriterion=(id:string)=>request<void>(`/projects/criteria/${id}/`,{method:'DELETE'})
export const usableRubrics=(projectId:string)=>request<Rubric[]>(`/projects/${projectId}/usable-rubrics/`)
export const groupGrades=(groupId:string)=>request<GroupGrades>(`/projects/groups/${groupId}/grades/`)
export const submitGrades=(groupId:string,data:{rubric:string;comment:string;items:{criterion:string;value:string}[]})=>request<GradeSubmission&{average:string}>(`/projects/groups/${groupId}/grades/`,{method:'POST',body:JSON.stringify(data)})
export const concludeEvaluation=(groupId:string)=>request<GradeSubmission>(`/projects/groups/${groupId}/conclude/`,{method:'POST',body:'{}'})
export const individualGrades=(studentId:string)=>request<{current:IndividualGrade|null;history:IndividualGrade[]}>(`/academic/students/${studentId}/individual-grade/`)
export const gradeIndividual=(studentId:string,data:{value:string;comment:string})=>request<IndividualGrade>(`/academic/students/${studentId}/individual-grade/`,{method:'POST',body:JSON.stringify(data)})

export type ShowcaseStatus='PENDING'|'SCHEDULED'|'PRESENTED'|'ABSENT'|'CANCELLED'
export type ShowcaseEntry={id:string;group:string;group_name:string;project_id:string;project_name:string;date:string;location:string;status:ShowcaseStatus;decided_by:string|null;decided_by_name:string|null;notes:string;is_evaluator:boolean;created_at:string;updated_at:string}
export type ShowcaseEntryCreate={group:string;date:string;location:string}
export const listShowcaseEntries=()=>request<ShowcaseEntry[]>('/projects/showcase/')
export const createShowcaseEntry=(data:ShowcaseEntryCreate)=>request<ShowcaseEntry>('/projects/showcase/',{method:'POST',body:JSON.stringify(data)})
export const recordPresence=(entryId:string,status:'PRESENTED'|'ABSENT',notes='')=>request<ShowcaseEntry>(`/projects/showcase/${entryId}/`,{method:'POST',body:JSON.stringify({status,notes})})
export const cancelShowcaseEntry=(entryId:string,reason='')=>request<ShowcaseEntry>(`/projects/showcase/${entryId}/`,{method:'DELETE',body:JSON.stringify({reason})})

export type PublicationDocumentStatus='PENDING'|'APPROVED'|'REJECTED'
export type PublicationDocument={id:string;project:string;project_name:string;version:number;original_name:string;content_type:string;size:number;status:PublicationDocumentStatus;review:string|null;reviewed_by_name:string|null;reviewed_at:string|null;consent_given:boolean;consent_at:string|null;consent_by_name:string|null;generated_by_name:string;download_url:string;created_at:string}
export type PublicationDocumentCreate={project:string;consent_given:boolean}
export const listPublicationDocuments=(projectId:string)=>request<PublicationDocument[]>(`/projects/${projectId}/publication-documents/`)
export const createPublicationDocument=(data:{project:string;file:File;consent_given:boolean})=>{const form=new FormData();form.append('pdf',data.file);if(data.consent_given)form.append('consent_given','true');return request<PublicationDocument>(`/projects/${data.project}/publication-documents/`,{method:'POST',body:form})}
export const reviewPublicationDocument=(documentId:string,status:'APPROVED'|'REJECTED',review='')=>request<PublicationDocument>(`/projects/publication-documents/${documentId}/review/`,{method:'POST',body:JSON.stringify({status,review})})
export const publicationDocumentDownloadUrl=(documentId:string)=>`${API}/projects/publication-documents/${documentId}/download/`

export type Publication={id:string;project:string;project_name:string;document:string;document_version:number;document_status:string;published_at:string|null;withdrawn_at:string|null;withdrawal_reason:string|null;withdrawn_by_name:string|null;is_published:boolean;created_at:string;updated_at:string}
export type PublicationCreate={project:string;document:string}
export type PublicationWithdraw={reason:string}
export const listPublications=()=>request<Publication[]>('/projects/publications/')
export const publishProject=(data:PublicationCreate)=>request<Publication>('/projects/publications/',{method:'POST',body:JSON.stringify(data)})
export const withdrawPublication=(publicationId:string,reason='')=>request<Publication>(`/projects/publications/${publicationId}/withdraw/`,{method:'POST',body:JSON.stringify({reason})})

export type AcervoItem={id:string;project_name:string;document_version:number;published_at:string;created_at:string}
export const listAcervo=(q='')=>request<AcervoItem[]>(`/projects/acervo/?q=${encodeURIComponent(q)}`)
