# Organizations

Organizations in Dataelan provide a way to group users and manage access to projects and resources.

## Organization Types

### SOLO
- Personal organization created automatically on user signup
- Single user
- Limited features
- Basic rate limits

### TEAM
- Multiple users
- Team collaboration features
- Shared projects
- Higher rate limits
- Team billing

### ENTERPRISE
- Advanced team features
- Custom rate limits
- Priority support
- Advanced analytics
- Custom integrations
- SSO support

## Features

### User Management
- Organization owners can invite users
- Role-based access control
- User groups
- Activity tracking

### Project Management
- Create and manage projects
- Set project permissions
- Project templates
- Resource quotas

### API Key Management
- Three strategies for managing LLM provider API keys:
  1. **DATAELAN** (default): Use Dataelan's managed API keys
     - Simplified setup
     - Automatic key rotation
     - Usage monitoring included
     - Cost optimization built-in
  2. **BYOK** (Bring Your Own Keys):
     - Full control over API keys
     - Direct billing relationship with providers
     - Custom rate limits
     - Enhanced security and compliance
  3. **HYBRID**:
     - Mix of Dataelan and own keys
     - Fallback support
     - Load balancing across keys
     - Flexible cost management

### Billing
- Usage tracking per API key
- Cost allocation by project
- Budget controls and quotas
- Invoice management
- Daily and monthly spending limits

### Security
- IP allowlisting
- Audit logs
- Security policies
- Data retention controls

## Best Practices

1. **Organization Structure**
   - Keep projects organized by team or department
   - Use clear naming conventions
   - Document project ownership

2. **Access Control**
   - Follow principle of least privilege
   - Regular access reviews
   - Remove inactive users

3. **Resource Management**
   - Monitor usage and costs
   - Set budget alerts
   - Clean up unused resources

4. **Compliance**
   - Regular security reviews
   - Data classification
   - Policy enforcement
