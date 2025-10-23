# Getting Started with Dataelan

## Prerequisites

- Python 3.9+
- PostgreSQL 13+
- Docker (optional)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/dataelan.git
cd dataelan
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Run the development server:
```bash
python manage.py runserver
```

## Key Concepts

### Organizations
- Every user belongs to at least one organization
- Organizations can be SOLO, TEAM, or ENTERPRISE
- Users get a personal organization on signup

### Projects
- Projects belong to organizations
- Projects can have multiple collaborators
- Each project can contain multiple prompt sessions

### Prompt Sessions
- Sessions are collections of related prompts
- Support different model types (TEXT, CODE, IMAGE, VOICE, VIDEO)
- Track execution costs and performance

### Model Hub
- Centralized management of LLM providers and models
- API key management with multiple strategies:
  - DATAELAN: Use platform's managed keys
  - BYOK: Use your own provider keys
  - HYBRID: Mix of both approaches
- Intelligent model routing based on:
  - Model capabilities
  - Cost constraints
  - Performance requirements
  - Custom conditions
- Comprehensive metrics tracking

## Setting Up Model Hub

1. Configure providers:
```bash
# Access Django admin interface
open http://localhost:8000/admin/modelhub/provider/

# Add common providers
python manage.py loaddata modelhub/fixtures/providers.json
```

2. Add API keys:
```python
# Via Django admin or API
from modelhub.models import Provider, APIKey

# For Dataelan-managed keys (system-wide)
APIKey.objects.create(
    provider=provider,
    label='Production',
    key='your-api-key',
    is_default=True
)

# For organization-specific keys
APIKey.objects.create(
    organization=org,
    provider=provider,
    label='Team API Key',
    key='your-api-key',
    daily_quota=100.00  # Optional spending limit
)
```

3. Configure routing rules:
```python
from modelhub.models import RoutingRule, Model

# Create a rule for handling code generation
rule = RoutingRule.objects.create(
    name='Code Generation Priority',
    model_type='CODE',
    priority=1,
    conditions={
        'max_cost': 0.05,  # per 1K tokens
        'min_context_window': 8000
    }
)

# Add models to the rule with weights
rule.routingrulemodel_set.create(
    model=Model.objects.get(name='gpt-4'),
    weight=70,
    tags=['primary', 'high-quality']
)
rule.routingrulemodel_set.create(
    model=Model.objects.get(name='claude-2'),
    weight=30,
    tags=['fallback', 'cost-effective']
)
```

### Model Execution
- Automatic provider selection based on routing rules
- Cost logging and quota management
- Performance metrics tracking
- Response transformation into structured actions
