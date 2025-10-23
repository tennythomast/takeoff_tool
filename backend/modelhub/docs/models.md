# Models

The following models are defined in the `modelhub` app. These enable provider registration, model cataloging, secure API key storage, routing logic, and performance tracking.

## Provider
Model for LLM providers (e.g., OpenAI, Anthropic).
- **Fields:**
  - `name`: Name of the provider (unique)
  - `slug`: Slug for the provider (unique)
  - `description`: Optional description
  - `website`: Provider website
  - `documentation_url`: Link to provider docs
  - `status`: Active/Inactive/Deprecated
  - `config`: Provider-specific configuration (JSON)

## Model
Represents an AI model from a provider.
- **Fields:**
  - `provider`: ForeignKey to Provider
  - `name`: Model name
  - `version`: Version string
  - `model_type`: Text/Code/Image/Voice/Video
  - `capabilities`: List of capabilities (JSON)
  - `config`: Model-specific config (JSON)
  - `cost_input`: Cost per 1K input tokens (USD)
  - `cost_output`: Cost per 1K output tokens (USD)
  - `context_window`: Max context tokens
  - `status`: Active/Inactive/Deprecated

## APIKey
Stores encrypted API keys for providers and organizations.
- **Fields:**
  - `organization`: ForeignKey to core.Organization (nullable)
  - `provider`: ForeignKey to Provider
  - `label`: Label for the API key
  - `key`: Encrypted API key
  - `is_default`: Is this the default key?
  - `is_active`: Is this key active?
  - `daily_quota`/`monthly_quota`: Spending limits (USD)
  - `last_used_at`: Last usage timestamp

## RoutingRule
Defines rules for routing requests to models.
- **Fields:**
  - `organization`: ForeignKey to core.Organization (nullable)
  - `name`: Rule name
  - `description`: Description
  - `priority`: 1 (highest) to 100 (lowest)
  - `model_type`: Text/Code/Image/Voice/Video
  - `conditions`: JSON conditions for rule
  - `models`: ManyToMany to Model (through RoutingRuleModel)

## RoutingRuleModel
Through model for RoutingRule and Model with weights.
- **Fields:**
  - `rule`: ForeignKey to RoutingRule
  - `model`: ForeignKey to Model
  - `weight`: Relative selection weight
  - `notes`: Optional notes
  - `tags`: List of tags (JSON)

## ModelMetrics
Tracks model performance metrics.
- **Fields:**
  - `model`: ForeignKey to Model
  - `organization`: ForeignKey to core.Organization (nullable)
  - `api_key`: ForeignKey to APIKey (nullable)
  - `timestamp`: Auto timestamp
  - `latency_ms`: Response time (ms)
  - `tokens_input`/`tokens_output`: Token counts
  - `cost`: Cost of request
  - `status`: Success/Error/Timeout
  - `error_type`/`error_message`: Error details

---

Each model includes validation, string representations, and utility methods for dashboard, usage, and cost summaries.
