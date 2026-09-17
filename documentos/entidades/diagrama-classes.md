# Diagrama de Classes de Domínio

O diagrama apresenta as principais entidades implementadas até a Sprint 4.7. Campos técnicos e
métodos triviais foram omitidos para preservar legibilidade.

```mermaid
classDiagram
  class User {
    +UUID id
    +string username
    +string email
    +Role role
  }
  class StudentProfile {
    +string ra
    +string cpf_hash
    +string cpf_last4
  }
  class ProfessorProfile {
    +string registration
  }
  class Course {
    +UUID id
    +string code
    +string name
    +bool is_active
  }
  class Subject {
    +UUID id
    +string code
    +string name
    +int workload_hours
  }
  class ClassOffering {
    +UUID id
    +string term
    +string code
    +bool is_active
  }
  class Enrollment {
    +UUID id
    +bool is_active
    +datetime enrolled_at
  }
  class AcademicRoom {
    +UUID id
    +string name
    +string academic_identifier
    +RoomStatus status
    +datetime closed_at
  }
  class RoomMembership {
    +UUID id
    +bool is_active
    +datetime joined_at
    +datetime left_at
  }
  class RoomTransferRequest {
    +UUID id
    +TransferStatus status
    +datetime decided_at
    +string decision_note
  }
  class ProfessorExpertise {
    +UUID id
    +ExpertiseKind kind
    +string text
    +string normalized_text
  }
  class Project {
    +UUID id
    +string name
    +text about
    +ProjectStatus status
    +bool is_active
    +text review_feedback
  }
  class ProjectGroup {
    +UUID id
    +string name
    +bool is_active
  }
  class GroupMember {
    +bool is_active
    +datetime joined_at
  }
  class GroupInvitation {
    +UUID id
    +InvitationStatus status
    +datetime decided_at
  }
  class FollowUp {
    +UUID id
    +text text
    +string kind
    +datetime created_at
  }
  class FollowUpAttachment {
    +UUID id
    +string original_name
    +string content_type
    +int size
  }
  class Milestone {
    +UUID id
    +string title
    +datetime due_at
    +MilestoneScope scope
    +bool requires_delivery
    +bool requires_approval
  }
  class ProjectMilestone {
    +datetime assigned_at
  }
  class CollaborationOpportunity {
    +UUID id
    +string title
    +text description
    +json desired_skills
    +OpportunityStatus status
  }
  class CollaborationApplication {
    +UUID id
    +text message
    +ApplicationStatus status
  }
  class AuditEvent {
    +UUID id
    +string action
    +string object_type
    +string object_id
    +json changed_fields
  }

  User "1" --> "0..1" StudentProfile
  User "1" --> "0..1" ProfessorProfile
  Course "1" <-- "0..*" StudentProfile
  Subject "1" <-- "0..*" ClassOffering
  StudentProfile "1" --> "0..*" Enrollment
  ClassOffering "1" --> "0..*" Enrollment
  ProfessorProfile "0..*" -- "0..*" Course
  ProfessorProfile "0..*" -- "0..*" Subject
  ProfessorProfile "0..*" -- "0..*" ClassOffering
  ProfessorProfile "1" --> "0..*" AcademicRoom : responsavel
  AcademicRoom "1" --> "0..*" RoomMembership
  StudentProfile "1" --> "0..*" RoomMembership
  StudentProfile "1" --> "0..*" RoomTransferRequest
  AcademicRoom "1" --> "0..*" RoomTransferRequest : origem
  AcademicRoom "1" --> "0..*" RoomTransferRequest : destino
  ProfessorProfile "1" --> "0..*" ProfessorExpertise
  ClassOffering "1" --> "0..*" Project
  AcademicRoom "0..1" --> "0..*" Project : sala_origem
  User "1" --> "0..*" Project : criador
  Project "1" --> "1..2" ProjectGroup
  ProjectGroup "1" --> "0..4" GroupMember
  StudentProfile "1" --> "0..*" GroupMember
  ProjectGroup "1" --> "0..*" GroupInvitation
  StudentProfile "1" --> "0..*" GroupInvitation : convidado
  Project "1" --> "0..*" FollowUp
  User "1" --> "0..*" FollowUp : autor
  FollowUp "1" --> "0..*" FollowUpAttachment
  ProfessorProfile "1" --> "0..*" Milestone : criador
  Milestone "1" --> "0..*" ProjectMilestone
  Project "1" --> "0..*" ProjectMilestone
  ProjectGroup "1" --> "0..*" CollaborationOpportunity
  CollaborationOpportunity "1" --> "0..*" CollaborationApplication
  ProjectGroup "1" --> "0..*" CollaborationApplication : candidato
  User "0..1" --> "0..*" AuditEvent : ator
```

## Restrições estruturais importantes

- Um aluno possui no máximo um `RoomMembership` ativo.
- Um aluno possui no máximo uma `RoomTransferRequest` pendente.
- Convite pendente é único por grupo e convidado.
- O grupo mantém entre 2 e 4 integrantes quando formado; durante a composição pode conter apenas o criador.
- O projeto interdisciplinar possui no máximo dois grupos no MVP.
- Chaves externas críticas usam `PROTECT` para preservar o histórico acadêmico.
- `cpf_hash` é uma impressão criptográfica; o CPF integral não é persistido no perfil.
