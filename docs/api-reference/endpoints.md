# API Endpoints

## Authentication

### Register User
```http
POST /api/auth/register/
```
Create a new user account with a personal organization.

### Login
```http
POST /api/auth/login/
```
Authenticate user and get JWT token.

### Refresh Token
```http
POST /api/auth/token/refresh/
```
Get new access token using refresh token.

## Organizations

### List Organizations
```http
GET /api/organizations/
```
List organizations the user belongs to.

### Create Organization
```http
POST /api/organizations/
```
Create a new organization.

### Update Organization
```http
PATCH /api/organizations/{id}/
```
Update organization details.

## Projects

### List Projects
```http
GET /api/projects/
```
List projects in user's organization.

### Create Project
```http
POST /api/projects/
```
Create a new project.

### Project Detail
```http
GET /api/projects/{id}/
```
Get project details.

### Update Project
```http
PATCH /api/projects/{id}/
```
Update project details.

### Delete Project
```http
DELETE /api/projects/{id}/
```
Archive a project.

### List Project Collaborators
```http
GET /api/projects/{id}/collaborators/
```
List project collaborators.

### Add Collaborator
```http
POST /api/projects/{id}/collaborators/
```
Add a collaborator to the project.

## Prompt Sessions

### List Sessions
```http
GET /api/projects/{project_id}/sessions/
```
List prompt sessions in a project.

### Create Session
```http
POST /api/projects/{project_id}/sessions/
```
Create a new prompt session.

### Session Detail
```http
GET /api/projects/{project_id}/sessions/{id}/
```
Get session details.

### Update Session
```http
PATCH /api/projects/{project_id}/sessions/{id}/
```
Update session details.

## Prompts

### List Prompts
```http
GET /api/projects/{project_id}/sessions/{session_id}/prompts/
```
List prompts in a session.

### Create Prompt
```http
POST /api/projects/{project_id}/sessions/{session_id}/prompts/
```
Create a new prompt.

### Execute Prompt
```http
POST /api/projects/{project_id}/sessions/{session_id}/prompts/{id}/execute/
```
Execute a prompt with specified model.

### Prompt Detail
```http
GET /api/projects/{project_id}/sessions/{session_id}/prompts/{id}/
```
Get prompt details.

## Model Execution Logs

### List Execution Logs
```http
GET /api/projects/{project_id}/sessions/{session_id}/prompts/{prompt_id}/executions/
```
List execution logs for a prompt.

### Get Execution Log
```http
GET /api/projects/{project_id}/sessions/{session_id}/prompts/{prompt_id}/executions/{id}/
```
Get execution log details.
