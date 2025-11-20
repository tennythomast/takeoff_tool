import type { Project } from '@/types/project'
import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { MapPin, ChevronDown } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface ProjectCardProps {
    project: Project
}

export function ProjectCard({ project }: ProjectCardProps) {
    // Get initials for avatar
    const getInitials = (name: string) => {
        return name
            .split(' ')
            .map(word => word[0])
            .join('')
            .toUpperCase()
            .slice(0, 2)
    }

    // Format time ago
    const timeAgo = formatDistanceToNow(new Date(project.created_at), { addSuffix: true })

    // Determine status badge variant
    const getStatusVariant = (status: string) => {
        switch (status) {
            case 'ACTIVE':
                return 'default'
            case 'COMPLETED':
                return 'secondary'
            default:
                return 'outline'
        }
    }

    return (
        <Card className="p-5 hover:shadow-md transition-shadow">
            <div className="flex items-start gap-4">
                {/* Project Icon */}
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-orange-500 text-white font-bold text-lg flex-shrink-0">
                    {getInitials(project.title)}
                </div>

                {/* Project Content */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-2">
                        <div>
                            <h3 className="font-semibold text-lg text-gray-900">{project.title}</h3>
                            <p className="text-sm text-gray-600">{project.client_name}</p>
                        </div>
                        <Badge variant={getStatusVariant(project.status)} className="flex-shrink-0">
                            {project.status_display}
                        </Badge>
                    </div>

                    {/* Tags */}
                    {project.tags && project.tags.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-3">
                            {project.tags.map((tag, index) => (
                                <span
                                    key={index}
                                    className="px-3 py-1 text-xs font-medium bg-gray-100 text-gray-700 rounded-full"
                                >
                                    {tag}
                                </span>
                            ))}
                        </div>
                    )}

                    {/* Description */}
                    <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                        {project.description}
                    </p>

                    {/* Footer */}
                    <div className="flex items-center justify-between text-sm text-gray-500">
                        <div className="flex items-center gap-4">
                            {project.location && (
                                <div className="flex items-center gap-1">
                                    <MapPin className="h-4 w-4" />
                                    <span>{project.location}</span>
                                </div>
                            )}
                            <span>{timeAgo}</span>
                        </div>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <ChevronDown className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </div>
        </Card>
    )
}
