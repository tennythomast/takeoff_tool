import '@testing-library/jest-dom';
import { agentInstructionService, ModelRoutingRule } from '../agent-instruction-service';
import * as authApi from '@/lib/auth/auth-api';

// Mock fetch
global.fetch = jest.fn() as jest.Mock;

// Mock auth headers
jest.mock('@/lib/auth/auth-api', () => ({
  getAuthHeaders: jest.fn().mockResolvedValue({ 'Authorization': 'Bearer test-token' })
}));

describe('AgentInstructionService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('generateInstructions', () => {
    it('should call the API with the correct parameters', async () => {
      // Mock successful API response
      const mockResponse = {
        ok: true,
        json: jest.fn().mockResolvedValue({
          instructions: 'Test instructions',
          suggestedConfiguration: {
            tools: ['web-search'],
            memory: { maxTokens: 2000, relevanceThreshold: 0.5 },
            responseStyle: { tone: 'professional', format: 'concise', creativity: 50 }
          }
        })
      };
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      // Test request
      const request = {
        name: 'Test Agent',
        primaryRole: 'Assistant',
        problemStatement: 'Help with testing',
        targetUsers: ['developers'],
        communicationStyle: 'Professional',
        outputFormat: 'Concise',
        qualityPreference: 2,
        capabilities: ['Web Browsing'],
        routingRule: ModelRoutingRule.BALANCED,
        additionalContext: 'This is a test'
      };

      // Call the service
      await agentInstructionService.generateInstructions(request);

      // Verify fetch was called with correct parameters
      expect(global.fetch).toHaveBeenCalledTimes(1);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('agent-instructions/generate/'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'Authorization': 'Bearer test-token'
          }),
          body: expect.any(String)
        })
      );

      // Verify the request body
      const callBody = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
      expect(callBody).toMatchObject({
        ...request,
        model: expect.any(String),
        enhancedPrompt: expect.any(String)
      });
    });

    it('should handle API errors and fall back to local generation', async () => {
      // Mock failed API response
      const mockResponse = {
        ok: false,
        json: jest.fn().mockResolvedValue({
          message: 'API error'
        })
      };
      (global.fetch as jest.Mock).mockResolvedValue(mockResponse);

      // Console spy
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();

      // Test request
      const request = {
        name: 'Test Agent',
        primaryRole: 'Assistant',
        problemStatement: 'Help with testing',
        targetUsers: ['developers'],
        communicationStyle: 'Professional',
        outputFormat: 'Concise',
        qualityPreference: 2,
        capabilities: ['Web Browsing'],
        routingRule: ModelRoutingRule.BALANCED
      };

      // Call the service
      const result = await agentInstructionService.generateInstructions(request);

      // Verify error handling
      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(consoleWarnSpy).toHaveBeenCalledWith('Falling back to local instruction generation');

      // Verify fallback result
      expect(result).toHaveProperty('instructions');
      expect(result).toHaveProperty('suggestedConfiguration');
      expect(result.suggestedConfiguration).toHaveProperty('tools');
      expect(result.suggestedConfiguration).toHaveProperty('memory');
      expect(result.suggestedConfiguration).toHaveProperty('responseStyle');
    });
  });

  describe('getModelForRoutingRule', () => {
    it('should return the correct model for each routing rule', () => {
      // Test private method using the public method
      const testCases = [
        { rule: ModelRoutingRule.BALANCED, expectedModelIncludes: 'gpt-4' },
        { rule: ModelRoutingRule.QUALITY, expectedModelIncludes: 'gpt-4-turbo' },
        { rule: ModelRoutingRule.SPEED, expectedModelIncludes: 'gpt-3.5' },
        { rule: ModelRoutingRule.COST, expectedModelIncludes: 'gpt-3.5' }
      ];

      for (const testCase of testCases) {
        // We'll test this indirectly by checking the API call
        (global.fetch as jest.Mock).mockClear();
        (global.fetch as jest.Mock).mockResolvedValue({
          ok: true,
          json: jest.fn().mockResolvedValue({})
        });

        // Call with the test case's routing rule
        agentInstructionService.generateInstructions({
          name: 'Test',
          primaryRole: 'Test',
          problemStatement: 'Test',
          targetUsers: ['test'],
          communicationStyle: 'Test',
          outputFormat: 'Test',
          qualityPreference: 2,
          capabilities: [],
          routingRule: testCase.rule
        });

        // Check that the model name is included in the payload
        expect(global.fetch).toHaveBeenCalled();
        const callBody = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
        expect(callBody.model).toContain(testCase.expectedModelIncludes);
      }
    });
  });
});
