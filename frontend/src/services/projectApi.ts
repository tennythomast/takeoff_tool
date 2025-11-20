import type { Project } from '@/types/project'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

// Get auth token from localStorage
const getAuthToken = (): string | null => {
    return localStorage.getItem('access_token')
}

// Create headers with auth
const getHeaders = (): HeadersInit => {
    const token = getAuthToken()
    return {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
    }
}

export const projectApi = {
    // Get all projects
    getProjects: async (): Promise<Project[]> => {
        const response = await fetch(`${API_URL}/projects/`, {
            headers: getHeaders(),
        })

        if (!response.ok) {
            throw new Error('Failed to fetch projects')
        }

        return response.json()
    },

    // Get single project
    getProject: async (id: string): Promise<Project> => {
        const response = await fetch(`${API_URL}/projects/${id}/`, {
            headers: getHeaders(),
        })

        if (!response.ok) {
            throw new Error('Failed to fetch project')
        }

        return response.json()
    },

    // Create project
    createProject: async (data: Partial<Project>): Promise<Project> => {
        const response = await fetch(`${API_URL}/projects/`, {
            method: 'POST',
            headers: getHeaders(),
            body: JSON.stringify(data),
        })

        if (!response.ok) {
            throw new Error('Failed to create project')
        }

        return response.json()
    },

    // Update project
    updateProject: async (id: string, data: Partial<Project>): Promise<Project> => {
        const response = await fetch(`${API_URL}/projects/${id}/`, {
            method: 'PATCH',
            headers: getHeaders(),
            body: JSON.stringify(data),
        })

        if (!response.ok) {
            throw new Error('Failed to update project')
        }

        return response.json()
    },

    // Delete project
    deleteProject: async (id: string): Promise<void> => {
        const response = await fetch(`${API_URL}/projects/${id}/`, {
            method: 'DELETE',
            headers: getHeaders(),
        })

        if (!response.ok) {
            throw new Error('Failed to delete project')
        }
    },

    // Archive project
    archiveProject: async (id: string): Promise<Project> => {
        const response = await fetch(`${API_URL}/projects/${id}/archive/`, {
            method: 'POST',
            headers: getHeaders(),
        })

        if (!response.ok) {
            throw new Error('Failed to archive project')
        }

        return response.json()
    },

    // Complete project
    completeProject: async (id: string): Promise<Project> => {
        const response = await fetch(`${API_URL}/projects/${id}/complete/`, {
            method: 'POST',
            headers: getHeaders(),
        })

        if (!response.ok) {
            throw new Error('Failed to complete project')
        }

        return response.json()
    },

    // Reactivate project
    reactivateProject: async (id: string): Promise<Project> => {
        const response = await fetch(`${API_URL}/projects/${id}/reactivate/`, {
            method: 'POST',
            headers: getHeaders(),
        })

        if (!response.ok) {
            throw new Error('Failed to reactivate project')
        }

        return response.json()
    },
}
