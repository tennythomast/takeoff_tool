import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from core.models import Organization, User, Membership
from workspaces.models import Workspace, WorkspaceCollaborator


class Command(BaseCommand):
    help = 'Creates example construction project workspaces for takeoff tool'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of workspaces to create'
        )
        parser.add_argument(
            '--organization',
            type=str,
            help='Organization slug to create workspaces for (default: first active org)'
        )

    def handle(self, *args, **options):
        count = options['count']
        org_slug = options.get('organization')

        # Get organization
        if org_slug:
            try:
                organization = Organization.objects.get(slug=org_slug, is_active=True)
            except Organization.DoesNotExist:
                self.stderr.write(self.style.ERROR(f'Organization with slug "{org_slug}" not found or inactive'))
                return
        else:
            organization = Organization.objects.filter(is_active=True).first()
            if not organization:
                self.stderr.write(self.style.ERROR('No active organizations found'))
                return

        # Get users from the organization
        members = User.objects.filter(
            memberships__organization=organization,
            is_active=True
        ).distinct()

        if not members:
            self.stderr.write(self.style.ERROR(f'No active users found in organization "{organization.name}"'))
            return

        # Get owner (preferably) or admin
        owner = members.filter(memberships__organization=organization, 
                              memberships__role=Membership.Role.OWNER).first()
        if not owner:
            owner = members.filter(memberships__organization=organization, 
                                  memberships__role=Membership.Role.ADMIN).first()
        if not owner:
            owner = members.first()

        self.stdout.write(self.style.SUCCESS(
            f'Creating example construction project workspaces for organization "{organization.name}" with owner "{owner.email}"'
        ))

        with transaction.atomic():
            # Create construction project workspaces
            self._create_construction_project_workspaces(organization, owner, members, count)

        self.stdout.write(self.style.SUCCESS('Successfully created example construction project workspaces'))

    def _create_construction_project_workspaces(self, organization, owner, members, count):
        """Create construction project workspaces for takeoff"""
        self.stdout.write('Creating construction project workspaces...')
        
        workspace_names = [
            'Commercial Office Building - Downtown',
            'Residential High-Rise - Waterfront',
            'Hospital Expansion - North Wing',
            'Shopping Mall Renovation - Westside',
            'University Campus - Science Building',
            'Hotel & Convention Center',
            'Industrial Warehouse Complex',
            'Public Library Renovation',
            'Mixed-Use Development - Eastside',
            'Elementary School Construction'
        ]
        
        project_types = [
            'Commercial', 
            'Residential', 
            'Healthcare', 
            'Retail', 
            'Educational',
            'Hospitality',
            'Industrial',
            'Public',
            'Mixed-Use',
            'Infrastructure'
        ]
        
        construction_phases = [
            'Pre-Construction',
            'Foundation',
            'Framing',
            'Mechanical/Electrical/Plumbing',
            'Interior Finishes',
            'Exterior Finishes',
            'Final Inspection'
        ]
        
        material_types = [
            'Concrete',
            'Steel',
            'Wood',
            'Glass',
            'Masonry',
            'Drywall',
            'Roofing',
            'Flooring',
            'Insulation',
            'Plumbing Fixtures',
            'Electrical Components',
            'HVAC Equipment'
        ]
        
        for i in range(min(count, len(workspace_names))):
            name = workspace_names[i]
            project_type = project_types[i % len(project_types)]
            status = random.choice([Workspace.Status.ACTIVE, Workspace.Status.ACTIVE, 
                                   Workspace.Status.COMPLETED])
            
            # Create workspace
            workspace = Workspace.objects.create(
                name=name,
                description=f'Takeoff and estimation workspace for {name} construction project',
                organization=organization,
                owner=owner,
                status=status,
                workspace_type=Workspace.WorkspaceType.PROJECT,
                metadata={
                    'project_type': project_type,
                    'construction_phase': random.choice(construction_phases),
                    'square_footage': random.randint(10000, 500000),
                    'floors': random.randint(1, 50),
                    'estimated_cost': f'${random.randint(1, 100)}M',
                    'location': f'{random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"])}',
                    'materials': random.sample(material_types, k=random.randint(3, 6)),
                    'start_date': (timezone.now() - timedelta(days=random.randint(30, 180))).strftime('%Y-%m-%d'),
                    'completion_date': (timezone.now() + timedelta(days=random.randint(90, 720))).strftime('%Y-%m-%d'),
                    'tags': ['construction', 'takeoff', 'estimation', project_type.lower()]
                }
            )
            
            # Add collaborators
            self._add_collaborators(workspace, members, owner, max_collaborators=4)
            
            self.stdout.write(f'  - Created workspace: {workspace.name} ({workspace.status})')

    def _add_collaborators(self, workspace, members, owner, max_collaborators=3):
        """Add random collaborators to a workspace"""
        # Filter out the owner from potential collaborators
        potential_collaborators = [m for m in members if m.id != owner.id]
        
        if not potential_collaborators:
            return
            
        # Select random number of collaborators
        num_collaborators = min(len(potential_collaborators), random.randint(1, max_collaborators))
        collaborators = random.sample(potential_collaborators, num_collaborators)
        
        # Add collaborators with different roles
        roles = [WorkspaceCollaborator.Role.ADMIN, WorkspaceCollaborator.Role.EDITOR, 
                WorkspaceCollaborator.Role.VIEWER]
        
        for collaborator in collaborators:
            role = random.choice(roles)
            WorkspaceCollaborator.objects.create(
                workspace=workspace,
                user=collaborator,
                role=role,
                metadata={
                    'added_by': owner.email,
                    'added_at': timezone.now().isoformat(),
                    'last_active': (timezone.now() - timedelta(days=random.randint(0, 30))).isoformat(),
                    'position': random.choice(['Project Manager', 'Architect', 'Engineer', 'Estimator', 'Contractor', 'Subcontractor', 'Owner Representative']),
                    'department': random.choice(['Construction', 'Design', 'Estimation', 'Project Management', 'Finance'])
                }
            )
