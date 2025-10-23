# Database Schema

## Core Models

### User
```python
class User(AbstractBaseUser, PermissionsMixin, SoftDeletableMixin):
    id = models.UUIDField(primary_key=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    default_org = models.ForeignKey('Organization', on_delete=models.SET_NULL)
    last_login_ip = models.GenericIPAddressField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Organization
```python
class Organization(SoftDeletableMixin):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    org_type = models.CharField(choices=[
        ('SOLO', 'Solo User'),
        ('TEAM', 'Team'),
        ('ENTERPRISE', 'Enterprise')
    ])
    api_key_strategy = models.CharField(choices=[
        ('DATAELAN', 'Use Dataelan API Keys'),
        ('BYOK', 'Bring Your Own Keys'),
        ('HYBRID', 'Mixed Strategy')
    ], default='DATAELAN')
```

## Project Models

### Project
```python
class Project(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField()
    organization = models.ForeignKey('Organization')
    owner = models.ForeignKey('User')
    collaborators = models.ManyToManyField('User', through='ProjectCollaborator')
    status = models.CharField(choices=['ACTIVE', 'ARCHIVED'])
    metadata = models.JSONField()
```

### ProjectCollaborator
```python
class ProjectCollaborator(BaseModel):
    project = models.ForeignKey('Project')
    user = models.ForeignKey('User')
    role = models.CharField(choices=['ADMIN', 'MEMBER'])
```

## Prompt Models

### PromptSession
```python
class PromptSession(BaseModel):
    title = models.CharField(max_length=255)
    description = models.TextField()
    project = models.ForeignKey('Project')
    creator = models.ForeignKey('User')
    model_type = models.CharField(choices=[
        'TEXT', 'CODE', 'IMAGE', 'VOICE', 'VIDEO'
    ])
    status = models.CharField(choices=[
        'DRAFT', 'ACTIVE', 'ARCHIVED'
    ])
    prompt = models.TextField()
    context = models.JSONField()
    response = models.JSONField()
    metadata = models.JSONField()
    cost = models.DecimalField()
```

### Prompt
```python
class Prompt(BaseModel):
    session = models.ForeignKey('PromptSession')
    user = models.ForeignKey('User')
    input_text = models.TextField()
    context = models.JSONField()
    metadata = models.JSONField()
```

### ModelExecutionLog
```python
class ModelExecutionLog(BaseModel):
    prompt = models.ForeignKey('Prompt')
    model_name = models.CharField(max_length=255)
    provider = models.CharField(choices=[
        'OPENAI', 'ANTHROPIC', 'GOOGLE', 'CUSTOM'
    ])
    response_type = models.CharField(choices=[
        'TEXT', 'CODE', 'IMAGE', 'VOICE', 'VIDEO'
    ])
    input = models.JSONField()
    output = models.JSONField()
    token_input = models.IntegerField()
    token_output = models.IntegerField()
    cost = models.DecimalField()
    status = models.CharField(choices=[
        'PENDING', 'SUCCESS', 'ERROR'
    ])
    error = models.TextField(null=True)
```

## ModelHub Models

### Provider
```python
class Provider(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    documentation_url = models.URLField(blank=True)
    status = models.CharField(choices=[
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('DEPRECATED', 'Deprecated')
    ])
    config = models.JSONField(default=dict)
```

### Model
```python
class Model(BaseModel):
    provider = models.ForeignKey('Provider', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    version = models.CharField(max_length=50)
    model_type = models.CharField(choices=[
        ('TEXT', 'Text'),
        ('CODE', 'Code'),
        ('IMAGE', 'Image'),
        ('VOICE', 'Voice'),
        ('VIDEO', 'Video')
    ])
    capabilities = models.JSONField(default=list)
    config = models.JSONField(default=dict)
    cost_input = models.DecimalField(max_digits=10, decimal_places=6)
    cost_output = models.DecimalField(max_digits=10, decimal_places=6)
    context_window = models.IntegerField()
    status = models.CharField(choices=[
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('DEPRECATED', 'Deprecated')
    ])
```

### APIKey
```python
class APIKey(BaseModel):
    organization = models.ForeignKey('Organization', null=True, blank=True)
    provider = models.ForeignKey('Provider', on_delete=models.CASCADE)
    label = models.CharField(max_length=255)
    key = EncryptedCharField(max_length=255)
    is_default = models.BooleanField(default=False)
    daily_quota = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    monthly_quota = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
```

### RoutingRule
```python
class RoutingRule(BaseModel):
    organization = models.ForeignKey('Organization', null=True, blank=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(100)])
    model_type = models.CharField(choices=[
        ('TEXT', 'Text'),
        ('CODE', 'Code'),
        ('IMAGE', 'Image'),
        ('VOICE', 'Voice'),
        ('VIDEO', 'Video')
    ])
    conditions = models.JSONField()
    models = models.ManyToManyField('Model', through='RoutingRuleModel')
```

### RoutingRuleModel
```python
class RoutingRuleModel(BaseModel):
    rule = models.ForeignKey('RoutingRule', on_delete=models.CASCADE)
    model = models.ForeignKey('Model', on_delete=models.CASCADE)
    weight = models.IntegerField(default=1)
    notes = models.TextField(blank=True)
    tags = models.JSONField(default=list)
```

### ModelMetrics
```python
class ModelMetrics(BaseModel):
    model = models.ForeignKey('Model', on_delete=models.CASCADE)
    organization = models.ForeignKey('Organization', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    latency_ms = models.IntegerField()
    tokens_input = models.IntegerField()
    tokens_output = models.IntegerField()
    cost = models.DecimalField(max_digits=10, decimal_places=6)
    status = models.CharField(choices=[
        ('SUCCESS', 'Success'),
        ('ERROR', 'Error'),
        ('TIMEOUT', 'Timeout')
    ])
    error_type = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
