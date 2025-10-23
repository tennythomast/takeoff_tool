import { AgentGenerationRequest, AgentGenerationResponse } from '@/lib/api/agent-service';
import { getAuthHeaders } from '@/lib/auth/auth-api';
import { API_BASE_URL } from '@/lib/config';

// Base API URL for agent instruction endpoints
const API_URL = `${API_BASE_URL}/api/v1/agent-instructions/`;

/**
 * Model routing rules
 */
export enum ModelRoutingRule {
  BALANCED = 'balanced', // Balance between quality and speed
  QUALITY = 'quality',   // Prioritize quality over speed
  SPEED = 'speed',       // Prioritize speed over quality
  COST = 'cost'          // Minimize cost
}

/**
 * Enhanced agent generation request with routing rules
 */
export interface EnhancedAgentGenerationRequest extends AgentGenerationRequest {
  routingRule?: ModelRoutingRule;
  additionalContext?: string;
  exampleInstructions?: string[];
}

/**
 * Service for generating agent instructions with enhanced capabilities
 */
export class AgentInstructionService {
  /**
   * Get the appropriate model based on the routing rule
   */
  private getModelForRoutingRule(rule: ModelRoutingRule): string {
    switch (rule) {
      case ModelRoutingRule.QUALITY:
        return 'gpt-4-turbo'; // High quality model
      case ModelRoutingRule.SPEED:
        return 'gpt-3.5-turbo'; // Faster model
      case ModelRoutingRule.COST:
        return 'gpt-3.5-turbo'; // Lower cost model
      case ModelRoutingRule.BALANCED:
      default:
        return 'gpt-4'; // Balanced model
    }
  }

  /**
   * Generate enhanced prompt for the LLM based on user inputs
   */
  private generateEnhancedPrompt(request: EnhancedAgentGenerationRequest): string {
    const { 
      name, 
      primaryRole, 
      problemStatement, 
      targetUsers, 
      communicationStyle, 
      outputFormat, 
      qualityPreference, 
      capabilities,
      additionalContext,
      exampleInstructions
    } = request;

    let prompt = `Generate comprehensive instructions for an AI agent with the following specifications:\n\n`;
    
    prompt += `Name: ${name || 'Unnamed Agent'}\n`;
    prompt += `Primary Role: ${primaryRole}\n`;
    prompt += `Problem Statement: ${problemStatement}\n`;
    prompt += `Target Users: ${targetUsers.join(', ')}\n`;
    prompt += `Communication Style: ${communicationStyle}\n`;
    prompt += `Output Format: ${outputFormat}\n`;
    prompt += `Quality Preference: ${qualityPreference === 3 ? 'High' : qualityPreference === 2 ? 'Medium' : 'Low'}\n`;
    prompt += `Capabilities: ${capabilities.join(', ')}\n`;
    
    if (additionalContext) {
      prompt += `\nAdditional Context: ${additionalContext}\n`;
    }
    
    prompt += `\nThe instructions should include:\n`;
    prompt += `1. A clear definition of the agent's purpose and scope\n`;
    prompt += `2. Guidelines for communication style and tone\n`;
    prompt += `3. Specific instructions for handling different types of queries\n`;
    prompt += `4. Limitations and boundaries of the agent's capabilities\n`;
    prompt += `5. Recommended tools and their usage patterns\n`;
    
    if (exampleInstructions && exampleInstructions.length > 0) {
      prompt += `\nReference these example instructions for inspiration:\n`;
      exampleInstructions.forEach((example, index) => {
        prompt += `Example ${index + 1}:\n${example}\n\n`;
      });
    }
    
    return prompt;
  }

  /**
   * Generate agent instructions with enhanced context and routing
   */
  async generateInstructions(request: EnhancedAgentGenerationRequest): Promise<AgentGenerationResponse> {
    try {
      console.log('Generating enhanced agent instructions with routing rule:', request.routingRule || ModelRoutingRule.BALANCED);
      
      // Select the appropriate model based on routing rule
      const model = this.getModelForRoutingRule(request.routingRule || ModelRoutingRule.BALANCED);
      
      // Generate enhanced prompt
      const enhancedPrompt = this.generateEnhancedPrompt(request);
      console.log('Enhanced prompt generated, length:', enhancedPrompt.length);
      
      // Prepare the API request payload
      const payload = {
        ...request,
        model,
        enhancedPrompt
      };
      
      // Get authentication headers - this is the key fix
      let authHeaders;
      try {
        authHeaders = await getAuthHeaders();
      } catch (authError) {
        console.error('Error getting auth headers:', authError);
        console.warn('Authentication failed, falling back to local generation');
        return this.generateLocalInstructions(request);
      }
      
      // Call the backend API with proper authentication
      const response = await fetch(`${API_URL}generate/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders, // Spread the auth headers properly
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        // Handle 401 Unauthorized specifically
        if (response.status === 401) {
          console.warn('Authentication failed (401). User may need to log in again.');
          console.warn('Falling back to local generation due to auth failure');
          return this.generateLocalInstructions(request);
        }
        
        // Check if response is 404 - endpoint not found
        if (response.status === 404) {
          console.warn('API endpoint not found (404). Falling back to local generation.');
          return this.generateLocalInstructions(request);
        }
        
        // Try to parse error as JSON, but handle non-JSON responses
        let errorMessage = 'Failed to generate enhanced agent instructions';
        try {
          const errorData = await response.text();
          
          // Try to parse as JSON if possible
          try {
            const jsonError = JSON.parse(errorData);
            errorMessage = jsonError.message || jsonError.detail || errorMessage;
          } catch (jsonError) {
            // If not JSON, use the text response or a portion of it
            errorMessage = errorData.length > 100 ? 
              `${errorData.substring(0, 100)}... (truncated)` : errorData;
          }
        } catch (textError) {
          // If we can't even get text, use status
          errorMessage = `Server returned ${response.status} ${response.statusText}`;
        }
        
        console.error('Error generating enhanced agent instructions:', errorMessage);
        
        // For any API error, fall back to local generation instead of throwing
        console.warn('API error occurred, falling back to local generation');
        return this.generateLocalInstructions(request);
      }

      // Try to parse the successful response as JSON
      try {
        const responseText = await response.text();
        
        const result = JSON.parse(responseText);
        console.log('Successfully generated enhanced instructions');
        
        // Ensure the response has the expected structure
        const normalizedResult: AgentGenerationResponse = {
          instructions: result.instructions || '',
          generation_method: result.generation_method || 'primary_llm',
          quality_score: result.quality_score || 'high',
          can_enhance: result.can_enhance || false,
          suggestedConfiguration: result.suggestedConfiguration || {
            tools: [],
            memory: {},
            responseStyle: {}
          },
          metadata: result.metadata || {}
        };
        
        return normalizedResult;
      } catch (jsonError) {
        console.error('Error parsing successful response as JSON:', jsonError);
        console.warn('Falling back to local instruction generation');
        return this.generateLocalInstructions(request);
      }
    } catch (error) {
      console.error('Error in generateInstructions:', error);
      
      // Fallback to local generation if API fails
      console.warn('Falling back to local instruction generation');
      return this.generateLocalInstructions(request);
    }
  }


  /**
   * Fallback function to generate instructions locally
   * This is public to allow direct access from agent-service.ts for fallback scenarios
   */
  public generateLocalInstructions(request: EnhancedAgentGenerationRequest): AgentGenerationResponse {
    // Generate instructions based on the request
    let instructionsText = `# ${request.name || 'AI Assistant'} - ${request.primaryRole} Agent
  
  You are an AI assistant specialized in ${request.primaryRole.toLowerCase()}. 
  
  ## Primary Goal
  Your primary goal is to help ${request.targetUsers.join(', ')} with ${request.problemStatement}.
  
  ## Communication Guidelines
  - Respond in a ${request.communicationStyle.toLowerCase()} tone
  - Present information in ${request.outputFormat.toLowerCase()} format
  - Focus on ${request.qualityPreference === 3 ? 'high quality, detailed responses' : 
            request.qualityPreference === 2 ? 'balanced responses with moderate detail' : 
            'quick, concise responses'}
  
  ## Capabilities
  ${request.capabilities.map(cap => `- ${cap}: Use this capability when appropriate to solve user problems`).join('\n')}
  
  ## User Context
  Your users are ${request.targetUsers.join(', ')}. Tailor your responses to their needs and level of expertise.
  
  ## Guidelines for Excellence
  - Always be helpful and accurate in your responses
  - If you're unsure about something, admit it rather than guessing
  - Stay focused on your role and the problems you're designed to solve
  - Provide step-by-step guidance when appropriate
  - Ask clarifying questions when user intent is unclear`;
      
      // Add additional context if provided
      if (request.additionalContext) {
        instructionsText += `\n\n## Additional Context\n${request.additionalContext}`;
      }
      
      // Determine suggested tools based on capabilities
      const suggestedTools: string[] = [];
      
      if (request.capabilities.includes('Web Browsing')) {
        suggestedTools.push('web-search', 'url-reader', 'web-browser');
      }
      
      if (request.capabilities.includes('Code Generation')) {
        suggestedTools.push('code-interpreter', 'code-execution');
      }
      
      if (request.capabilities.includes('Data Analysis')) {
        suggestedTools.push('data-analysis', 'chart-generator', 'file-reader');
      }
      
      if (request.capabilities.includes('Knowledge Base Access')) {
        suggestedTools.push('knowledge-base', 'document-retrieval');
      }
      
      if (request.capabilities.includes('Document Processing')) {
        suggestedTools.push('document-processor', 'document-retrieval');
      }
      
      if (request.capabilities.includes('Text Generation')) {
        suggestedTools.push('text-generator');
      }
      
      // Configure memory settings based on quality preference and routing rule
      const memory = this.getMemoryConfigForRequest(request);
      
      // Configure response style based on communication preferences
      const responseStyle = this.getResponseStyleForRequest(request);
      
      // Return in the enhanced format matching backend
      return {
        instructions: instructionsText,
        generation_method: 'smart_template',
        quality_score: 'medium',
        can_enhance: true,
        suggestedConfiguration: {
          tools: suggestedTools,
          memory,
          responseStyle
        },
        metadata: {
          is_fallback: true,
          template_used: 'local_generation',
          character_count: instructionsText.length,
          enhancement_suggestion: 'AI-generated instructions available when services are restored'
        }
      };
    }

  /**
   * Get memory configuration based on request parameters
   */
  private getMemoryConfigForRequest(request: EnhancedAgentGenerationRequest) {
    // Base memory settings on quality preference
    const baseMaxTokens = request.qualityPreference === 3 ? 4000 : 
                         request.qualityPreference === 2 ? 2000 : 1000;
    
    const baseThreshold = request.qualityPreference === 3 ? 0.7 : 
                         request.qualityPreference === 2 ? 0.5 : 0.3;
    
    // Adjust based on routing rule if present
    let maxTokens = baseMaxTokens;
    let relevanceThreshold = baseThreshold;
    
    if (request.routingRule) {
      switch (request.routingRule) {
        case ModelRoutingRule.QUALITY:
          maxTokens = Math.min(8000, baseMaxTokens * 2);
          relevanceThreshold = Math.min(0.8, baseThreshold + 0.1);
          break;
        case ModelRoutingRule.SPEED:
          maxTokens = Math.max(500, Math.floor(baseMaxTokens / 2));
          relevanceThreshold = Math.max(0.2, baseThreshold - 0.1);
          break;
        case ModelRoutingRule.COST:
          maxTokens = Math.max(500, Math.floor(baseMaxTokens / 2));
          relevanceThreshold = baseThreshold;
          break;
      }
    }
    
    return {
      maxTokens,
      relevanceThreshold
    };
  }

  /**
   * Get response style configuration based on request parameters
   */
  private getResponseStyleForRequest(request: EnhancedAgentGenerationRequest) {
    // Determine tone based on communication style
    const lowerCommunicationStyle = request.communicationStyle.toLowerCase();
    let tone: 'professional' | 'technical' | 'simple' | 'friendly' = 'friendly';
    
    if (lowerCommunicationStyle.includes('professional')) {
      tone = 'professional';
    } else if (lowerCommunicationStyle.includes('technical')) {
      tone = 'technical';
    } else if (lowerCommunicationStyle.includes('simple')) {
      tone = 'simple';
    }
    
    // Determine format based on output format preference
    const lowerOutputFormat = request.outputFormat.toLowerCase();
    const format: 'detailed' | 'concise' = lowerOutputFormat.includes('detail') ? 'detailed' : 'concise';
    
    // Base creativity on quality preference
    let creativity = request.qualityPreference === 3 ? 70 : 
                    request.qualityPreference === 2 ? 50 : 30;
    
    // Adjust based on routing rule if present
    if (request.routingRule) {
      switch (request.routingRule) {
        case ModelRoutingRule.QUALITY:
          creativity = Math.min(90, creativity + 20);
          break;
        case ModelRoutingRule.SPEED:
          creativity = Math.max(10, creativity - 20);
          break;
        case ModelRoutingRule.COST:
          creativity = Math.max(10, creativity - 10);
          break;
      }
    }
    
    return {
      tone,
      format,
      creativity
    };
  }
}

// Export a singleton instance
export const agentInstructionService = new AgentInstructionService();
