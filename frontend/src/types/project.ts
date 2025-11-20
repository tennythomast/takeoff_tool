export type ProjectStatus = 'ACTIVE' | 'ARCHIVED' | 'COMPLETED' | 'ON_HOLD'
export type ProjectType = 'FIXED_PRICE' | 'TIME_AND_MATERIALS' | 'RETAINER' | 'OTHER'

export interface Project {
    id: string
    title: string
    description: string
    client_name: string
    client_email: string
    client_phone: string
    client_company: string
    project_type: ProjectType
    project_type_display: string
    budget: string | null
    location: string
    tags: string[]
    organization: string
    organization_name: string
    owner: string
    owner_email: string
    owner_name: string
    status: ProjectStatus
    status_display: string
    created_at: string
    updated_at: string
    started_at: string | null
    deadline: string | null
    metadata: Record<string, any>
}

export interface ProjectCollaborator {
    id: string
    user: string
    user_email: string
    user_name: string
    role: 'ADMIN' | 'EDITOR' | 'VIEWER'
    created_at: string
    metadata: Record<string, any>
}
