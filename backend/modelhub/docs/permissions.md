# Permissions

All endpoints in the `modelhub` app require authentication and leverage Django REST Framework's permissions system.

## Roles & Access
- **Authenticated User**: Can view and interact with providers, models, API keys, routing rules, and metrics within their organization.
- **Organization Admin/Owner**: Can create, update, and delete resources for their organization (e.g., models, API keys, routing rules).
- **System Admin (Superuser)**: Can manage all resources system-wide, including system-level API keys and routing rules.

## Access Rules
- **JWT Authentication**: All API requests require a valid JWT token in the `Authorization` header.
- **Object-Level Permissions**: Most viewsets restrict modification (create/update/delete) to users with admin or owner roles for the relevant organization.
- **Read-Only for Non-Admins**: Non-admin users may have read-only access to some endpoints, depending on organization settings.
- **API Key Security**: API keys are encrypted at rest. Only users with appropriate permissions can view or manage keys for their organization.
- **Quota Enforcement**: API key usage is monitored and enforced based on daily/monthly quotas and key status.

## Example Permission Classes
```python
permission_classes = [permissions.IsAuthenticated]
```

- Some endpoints may implement custom permission classes for more granular control (e.g., only organization owners can delete keys).

---

For more details, see the `permission_classes` in each ViewSet and the project's authentication documentation.
