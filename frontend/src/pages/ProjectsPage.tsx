import { useState, useEffect } from 'react'
import type { Project } from '@/types/project'
import { projectApi } from '@/services/projectApi'
import { ProjectCard } from '@/components/ProjectCard'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Link } from 'react-router-dom'

export default function ProjectsPage() {
    const [projects, setProjects] = useState<Project[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        fetchProjects()
    }, [])

    const fetchProjects = async () => {
        try {
            setLoading(true)
            const data = await projectApi.getProjects()
            setProjects(data)
            setError(null)
        } catch (err) {
            setError('Failed to load projects')
            console.error('Error fetching projects:', err)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <Skeleton className="h-8 w-64" />
                    <Skeleton className="h-6 w-32" />
                </div>
                {[1, 2, 3].map((i) => (
                    <Skeleton key={i} className="h-40 w-full" />
                ))}
            </div>
        )
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center py-12">
                <p className="text-red-500 mb-4">{error}</p>
                <Button onClick={fetchProjects}>Try Again</Button>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">Your Recent Projects</h1>
                <Link to="/projects/all" className="text-sm text-gray-600 hover:text-gray-900">
                    See all Project
                </Link>
            </div>

            {/* Projects List */}
            {projects.length === 0 ? (
                <div className="text-center py-12">
                    <p className="text-gray-500 mb-4">No projects yet</p>
                    <Button>Create Your First Project</Button>
                </div>
            ) : (
                <div className="space-y-4">
                    {projects.map((project) => (
                        <ProjectCard key={project.id} project={project} />
                    ))}
                </div>
            )}
        </div>
    )
}
