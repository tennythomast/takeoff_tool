# Agent Instruction Service

## Overview

The Agent Instruction Service enhances the Smart Agent Builder by providing intelligent routing of LLM model selection and generating detailed instructions for agents based on user inputs. This service sits between the frontend and backend, adding additional context and optimizing the agent generation process.

## Features

- **Model Routing**: Intelligently selects the appropriate LLM model based on routing rules (balanced, quality, speed, cost)
- **Enhanced Prompts**: Generates comprehensive prompts with additional context for better agent instructions
- **Fallback Generation**: Provides local instruction generation if the backend API is unavailable
- **Optimized Configuration**: Suggests tools, memory settings, and response styles based on agent purpose

## Usage

```typescript
import { agentInstructionService, ModelRoutingRule } from '@/lib/services/agent-instruction-service';

// Create an enhanced request
const request = {
  name: "Customer Support Agent",
  primaryRole: "Customer Support",
  problemStatement: "Help users troubleshoot product issues",
  targetUsers: ["customers", "support staff"],
  communicationStyle: "Professional",
  outputFormat: "Concise",
  qualityPreference: 2,
  capabilities: ["Knowledge Base Access", "Document Processing"],
  routingRule: ModelRoutingRule.BALANCED,
  additionalContext: "This agent should focus on quick resolution of customer issues"
};

// Generate instructions
const response = await agentInstructionService.generateInstructions(request);

// Use the generated instructions and configuration
console.log(response.instructions);
console.log(response.suggestedConfiguration);
```

## Model Routing Rules

The service supports four routing rules for selecting the appropriate LLM model:

1. **BALANCED**: Default option that balances quality and speed (uses gpt-4)
2. **QUALITY**: Prioritizes high-quality, detailed instructions (uses gpt-4-turbo)
3. **SPEED**: Prioritizes faster response times (uses gpt-3.5-turbo)
4. **COST**: Minimizes token usage and cost (uses gpt-3.5-turbo with optimized settings)

## Integration with Backend

The service calls the backend API endpoint `/api/v1/agent-instructions/generate/` to generate instructions. If the backend is unavailable, it falls back to local generation to ensure the agent creation process is not interrupted.

## Testing

Unit tests are available in the `__tests__` directory. Run them with:

```bash
npm test
```

## Future Improvements

- Add support for more LLM models and providers
- Implement caching of similar instruction requests
- Add analytics to track which models perform best for different agent types
- Support for fine-tuning models based on user feedback
