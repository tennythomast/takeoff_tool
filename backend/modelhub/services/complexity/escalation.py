# backend/modelhub/services/complexity/escalation.py
"""
LLM escalation criteria and logic for uncertain/nuanced cases.
Handles the 15% of requests that rule-based analysis can't confidently assess.
"""
import re
import logging
import time
import logging
from typing import Dict, Optional
from decimal import Decimal
from channels.db import database_sync_to_async
from ..unified_llm_client import UnifiedLLMClient
import json
from ...models import APIKey

from .types import (
    ComplexityResult, EscalationDecision, EscalationReason, 
    RequestContext, AnalysisPath, ComplexityLevel, ContentType
)

logger = logging.getLogger(__name__)

QWEN_COMPLEXITY_ANALYZER_PROMPT = """You are a specialized AI routing optimizer that analyzes request complexity to determine the most cost-effective model for processing.

Your task is to analyze incoming AI requests and determine their complexity level for optimal model routing in a cost optimization platform.

## Complexity Scoring Guidelines (0.0 - 1.0 scale):

### SIMPLE (0.0 - 0.3): Route to low-cost models (Mixtral, Gemini Flash)
- Basic factual questions
- Simple data lookups
- Basic arithmetic or calculations
- Single-step instructions
- Yes/no questions
- Simple classifications
- Basic formatting tasks

### MEDIUM (0.4 - 0.7): Route to balanced models (GPT-3.5-turbo, Claude Haiku)
- Multi-step reasoning
- Code debugging or explanation
- Business analysis with context
- Creative writing with constraints
- Data analysis and interpretation
- API integration questions
- Moderate technical explanations

### COMPLEX (0.8 - 1.0): Route to premium models (GPT-4, Claude Sonnet)
- Complex multi-domain reasoning
- Advanced code generation or architecture
- Strategic business planning
- Creative tasks requiring nuance
- Research synthesis
- Complex mathematical proofs
- Multi-stakeholder analysis
- Ethical or philosophical reasoning

## Content Type Detection:
Identify the primary content type to apply specialized routing:
- CODE: Programming, debugging, architecture
- DATA_ANALYSIS: Statistics, data processing, visualization
- BUSINESS: Strategy, planning, financial analysis
- CREATIVE: Writing, storytelling, design
- TECHNICAL: Engineering, scientific, mathematical
- GENERAL: Mixed or conversational

## Confidence Scoring (0.0 - 1.0):
Rate your confidence in the complexity assessment:
- HIGH (0.85-1.0): Clear indicators, obvious complexity level
- MEDIUM (0.70-0.84): Some ambiguity but reasonable assessment
- LOW (<0.70): Unclear request, conflicting signals, needs human review

## Key Factors to Consider:
1. **Reasoning Depth**: How many logical steps are required?
2. **Domain Expertise**: Does it require specialized knowledge?
3. **Context Integration**: How much context must be synthesized?
4. **Creative Elements**: Does it require subjective judgment?
5. **Precision Requirements**: How critical is accuracy?
6. **Multi-step Processing**: Are there dependent sub-tasks?

## Output Format:
You must respond with valid JSON only, no additional text:

{
    "complexity_score": 0.0-1.0,
    "complexity_level": "simple|medium|complex",
    "confidence": 0.0-1.0,
    "content_type": "general|code|data_analysis|business|creative|technical",
    "reasoning": "Brief explanation of complexity determination",
    "key_factors": ["factor1", "factor2", "factor3"],
    "recommended_model_tier": "basic|standard|premium",
    "optimization_hint": "specific suggestion for cost optimization"
}

## Examples:

REQUEST: "What is the capital of France?"
RESPONSE: {
    "complexity_score": 0.1,
    "complexity_level": "simple",
    "confidence": 0.95,
    "content_type": "general",
    "reasoning": "Basic factual question with single definitive answer",
    "key_factors": ["factual_lookup", "no_reasoning", "common_knowledge"],
    "recommended_model_tier": "basic",
    "optimization_hint": "Use cheapest available model for simple factual queries"
}

REQUEST: "Debug this React component that's causing infinite re-renders and suggest performance optimizations"
RESPONSE: {
    "complexity_score": 0.65,
    "complexity_level": "medium",
    "confidence": 0.88,
    "content_type": "code",
    "reasoning": "Requires code analysis, debugging skills, and React expertise",
    "key_factors": ["debugging", "framework_knowledge", "performance_analysis"],
    "recommended_model_tier": "standard",
    "optimization_hint": "Use code-specialized model with good React knowledge"
}

REQUEST: "Develop a comprehensive go-to-market strategy for our B2B SaaS platform targeting enterprise healthcare, including pricing models, channel partnerships, and a 12-month execution roadmap"
RESPONSE: {
    "complexity_score": 0.92,
    "complexity_level": "complex",
    "confidence": 0.91,
    "content_type": "business",
    "reasoning": "Requires strategic thinking, industry knowledge, and multi-faceted planning",
    "key_factors": ["strategic_planning", "industry_expertise", "multi_component_synthesis"],
    "recommended_model_tier": "premium",
    "optimization_hint": "Requires premium model for strategic business planning"
}

Remember: Your goal is to minimize costs while maintaining quality. When in doubt, lean toward the simpler classification unless clear complexity indicators are present."""


class LLMEscalationCriteria:
    """
    Determines when requests should be escalated to LLM analysis.
    Target: High accuracy for uncertain/nuanced cases.
    """
    
    # Confidence thresholds
    CONFIDENCE_THRESHOLDS = 0.85
    
    # Cost limits for LLM escalation (per analysis)
    ESCALATION_COST_LIMITS = {
        'starter': Decimal('0.001'),    # $0.001 per escalation
        'pro': Decimal('0.002'),        # $0.002 per escalation  
        'enterprise': Decimal('0.005')  # $0.005 per escalation
    }
    
    def __init__(self):
        self._compile_escalation_patterns()
    
    def _compile_escalation_patterns(self):
        """Compile patterns that indicate escalation needed"""
        
        self.ESCALATION_PATTERNS = {
            # Nuanced requests that rules struggle with
            'nuanced_language': [
                re.compile(r'\b(nuanced|subtle|complex relationship|depends on)\b', re.I),
                re.compile(r'\b(considering|taking into account|given that)\b.*\b(however|but|although)\b', re.I),
                re.compile(r'\b(not exactly|sort of|kind of|somewhat)\b', re.I),
                re.compile(r'\b(it\'s complicated|hard to say|difficult to determine)\b', re.I)
            ],
            
            # Multi-faceted analysis
            'multi_faceted': [
                re.compile(r'\b(multiple|several|various).*\b(aspects|factors|considerations)\b', re.I),
                re.compile(r'\b(on one hand|on the other hand|alternatively)\b', re.I),
                re.compile(r'\b(from different perspectives|various angles|multiple viewpoints)\b', re.I),
                re.compile(r'\b(pros and cons|trade.?offs?|benefits and drawbacks)\b', re.I)
            ],
            
            # Domain-specific expertise needed
            'expert_knowledge': [
                re.compile(r'\b(specialized|technical|expert|professional)\b.*\b(knowledge|understanding|expertise)\b', re.I),
                re.compile(r'\b(industry|domain|field).*\b(specific|dependent|related)\b', re.I),
                re.compile(r'\b(best practices|standards|conventions)\b.*\b(in|for)\b', re.I),
                re.compile(r'\b(regulatory|compliance|legal|medical|financial)\b.*\b(requirements|implications)\b', re.I)
            ],
            
            # Contextual reasoning required
            'contextual_dependent': [
                re.compile(r'\b(in this context|given the situation|under these circumstances)\b', re.I),
                re.compile(r'\b(depending on|based on the|considering the)\b.*\b(context|situation|scenario)\b', re.I),
                re.compile(r'\b(interpretation|perspective|viewpoint|approach)\b.*\b(depends|varies)\b', re.I)
            ],
            
            # Creative/subjective tasks
            'creative_subjective': [
                re.compile(r'\b(creative|artistic|innovative|original|imaginative)\b', re.I),
                re.compile(r'\b(opinion|perspective|subjective|personal|preference)\b', re.I),
                re.compile(r'\b(feel|think|believe|prefer|suggest)\b.*\b(would|should|might)\b', re.I),
                re.compile(r'\b(brainstorm|ideate|conceptualize|envision)\b', re.I)
            ],
            
            # Complex logical reasoning
            'complex_logic': [
                re.compile(r'\b(if.*then.*else|assuming.*what if)\b', re.I),
                re.compile(r'\b(logical|reasoning|inference|deduction|implication)\b', re.I),
                re.compile(r'\b(cause and effect|root cause|underlying reason)\b', re.I),
                re.compile(r'\b(contradictory|conflicting|inconsistent)\b.*\b(information|signals|evidence)\b', re.I)
            ],
            
            # Meta-analysis requests
            'meta_analysis': [
                re.compile(r'\b(analyze.*analysis|review.*review|evaluate.*evaluation)\b', re.I),
                re.compile(r'\b(what do you think about|your thoughts on|how would you approach)\b', re.I),
                re.compile(r'\b(strengths and weaknesses|effectiveness|appropriateness)\b', re.I)
            ]
        }
    
    async def should_escalate(
        self, 
        rule_result: ComplexityResult, 
        request_text: str, 
        context: RequestContext
    ) -> EscalationDecision:
        """
        Determine if request should be escalated to LLM analysis.
        
        Escalation triggers:
        1. Low confidence from rule analysis
        2. Ambiguous/contradictory signals
        3. Novel/edge cases
        4. Context-heavy requests
        5. Organization-specific thresholds
        """
        
        # Get organization's escalation settings
        org_settings = await self._get_organization_escalation_settings(context.organization_id)
        confidence_threshold = org_settings['confidence_threshold']
        cost_limit = org_settings['cost_limit']
        
        # Primary trigger: Low confidence
        if rule_result.confidence < confidence_threshold:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.LOW_CONFIDENCE,
                confidence_threshold=confidence_threshold,
                actual_confidence=rule_result.confidence,
                organization_strategy=org_settings.get('default_strategy'),
                estimated_llm_cost=cost_limit
            )
        
        # Secondary triggers for specific scenarios
        text_lower = request_text.lower()
        escalation_score = self._calculate_escalation_score(text_lower)
        
        # Check for multiple escalation indicators
        if escalation_score >= 3:  # Multiple strong indicators
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.NUANCED_REQUEST,
                confidence_threshold=confidence_threshold,
                actual_confidence=rule_result.confidence,
                organization_strategy=org_settings.get('default_strategy'),
                estimated_llm_cost=cost_limit
            )
        
        # Context-based escalation
        context_escalation = self._check_context_escalation(context, text_lower)
        if context_escalation:
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.CONTEXT_DEPENDENT,
                confidence_threshold=confidence_threshold,
                actual_confidence=rule_result.confidence,
                organization_strategy=org_settings.get('default_strategy'),
                estimated_llm_cost=cost_limit
            )
        
        # Pattern conflict detection
        if self._has_conflicting_signals(rule_result):
            return EscalationDecision(
                should_escalate=True,
                reason=EscalationReason.CONFLICTING_SIGNALS,
                confidence_threshold=confidence_threshold,
                actual_confidence=rule_result.confidence,
                organization_strategy=org_settings.get('default_strategy'),
                estimated_llm_cost=cost_limit
            )
        
        # No escalation needed
        return EscalationDecision(
            should_escalate=False,
            reason=EscalationReason.LOW_CONFIDENCE,  # Default reason
            confidence_threshold=confidence_threshold,
            actual_confidence=rule_result.confidence,
            organization_strategy=org_settings.get('default_strategy')
        )
    
    def _calculate_escalation_score(self, text: str) -> int:
        """Calculate escalation score based on pattern matches"""
        escalation_matches = 0
        
        for category, patterns in self.ESCALATION_PATTERNS.items():
            category_matches = sum(1 for pattern in patterns if pattern.search(text))
            if category_matches > 0:
                escalation_matches += 1
                logger.debug(f"Escalation pattern match in {category}: {category_matches}")
        
        return escalation_matches
    
    def _check_context_escalation(self, context: RequestContext, text: str) -> bool:
        """Check if context requires escalation"""
        
        # Complex RAG scenarios
        if context.rag_documents and len(context.rag_documents) > 3:
            if any(keyword in text for keyword in ['synthesis', 'compare', 'contrast', 'conflicting']):
                logger.debug("RAG context escalation: multi-document synthesis")
                return True
        
        # Complex conversation context
        if context.conversation_history and len(context.conversation_history) > 8:
            if any(ref_word in text for ref_word in ['this', 'that', 'previously', 'earlier', 'we discussed']):
                logger.debug("Session context escalation: complex conversation reference")
                return True
        
        # Quality-critical or cost-sensitive requests
        if context.quality_critical and any(keyword in text for keyword in ['important', 'critical', 'crucial', 'vital']):
            logger.debug("Quality-critical request escalation")
            return True
        
        return False
    
    def _has_conflicting_signals(self, rule_result: ComplexityResult) -> bool:
        """Detect conflicting signals in pattern matches"""
        
        if not rule_result.pattern_matches:
            return False
        
        simple_matches = rule_result.pattern_matches.get('simple', 0)
        complex_matches = rule_result.pattern_matches.get('complex', 0)
        escalation_matches = rule_result.pattern_matches.get('escalation', 0)
        
        # Conflicting simple vs complex signals
        if simple_matches > 0 and complex_matches > 0:
            if abs(simple_matches - complex_matches) <= 1:  # Very close scores
                logger.debug(f"Conflicting signals: simple={simple_matches}, complex={complex_matches}")
                return True
        
        # High escalation signals regardless of other patterns
        if escalation_matches >= 2:
            logger.debug(f"High escalation signals: {escalation_matches}")
            return True
        
        return False
    
    @database_sync_to_async
    def _get_organization_escalation_settings(self, organization_id: Optional[str]) -> Dict:
        """Get organization-specific escalation settings"""
        
        if not organization_id:
            # Default settings for non-org requests
            return {
                'confidence_threshold': 0.70,
                'cost_limit': Decimal('0.002'),
                'default_strategy': 'balanced'
            }
        
        try:
            from core.models import Organization
            
            org = Organization.objects.get(id=organization_id)
            
            # Map subscription tiers to thresholds
            tier = getattr(org, 'subscription_tier', 'pro')
            
            return {
                'confidence_threshold': self.CONFIDENCE_THRESHOLDS.get(tier, 0.85),
                'cost_limit': self.ESCALATION_COST_LIMITS.get(tier, Decimal('0.002')),
                'default_strategy': getattr(org, 'default_optimization_strategy', 'balanced')
            }
            
        except Exception as e:
            logger.debug(f"Failed to get org escalation settings: {e}")
            return {
                'confidence_threshold': 0.85,
                'cost_limit': Decimal('0.002'),
                'default_strategy': 'balanced'
            }
    
    def get_llm_analysis_prompt(self, request_text: str, context: RequestContext) -> str:
        """
        Generate optimized prompt for LLM complexity analysis.
        This will be used when we implement the actual LLM escalation.
        """
        base_prompt = f"""Analyze the complexity of this AI request for optimal model routing:

REQUEST: "{request_text}"

Analyze complexity on a scale of 0.0-1.0 considering:
- Reasoning depth required
- Multi-step processing needs  
- Context integration complexity
- Domain expertise requirements
- Creative/subjective elements

Respond with JSON:
{{
    "complexity_score": 0.0-1.0,
    "complexity_level": "simple|medium|complex", 
    "reasoning": "brief explanation",
    "key_factors": ["factor1", "factor2"],
    "recommended_model_tier": "basic|standard|premium",
    "confidence": 0.0-1.0
}}"""
        
        # Add context if available
        context_parts = []
        
        if context.rag_documents:
            context_parts.append(f"RAG CONTEXT: {len(context.rag_documents)} documents available for retrieval")
        
        if context.conversation_history:
            context_parts.append(f"SESSION CONTEXT: {len(context.conversation_history)} previous messages")
        
        if context.quality_critical:
            context_parts.append("QUALITY CRITICAL: High accuracy required")
            
        if context.cost_sensitive:
            context_parts.append("COST SENSITIVE: Minimize analysis cost")
        
        if context_parts:
            base_prompt += f"\n\nADDITIONAL CONTEXT:\n" + "\n".join(context_parts)
        
        return base_prompt
    
    async def estimate_escalation_cost(
        self, 
        request_text: str, 
        organization_id: Optional[str]
    ) -> Decimal:
        """
        Estimate cost of LLM escalation analysis.
        Used for cost-aware escalation decisions.
        """
        
        # Base cost calculation (rough estimate)
        input_tokens = len(request_text.split()) * 1.3  # Rough token estimate
        prompt_tokens = 150  # Base prompt tokens
        total_input_tokens = input_tokens + prompt_tokens
        output_tokens = 50  # Expected JSON response length
        
        # Get organization settings for model selection
        org_settings = await self._get_organization_escalation_settings(organization_id)
        strategy = org_settings.get('default_strategy', 'balanced')
        
        # Estimate cost based on likely model selection
        # These are rough estimates - actual costs depend on routing rules
        model_costs = {
            'cost_first': {'input': 0.0005, 'output': 0.0015},      # Mixtral-like
            'balanced': {'input': 0.001, 'output': 0.002},          # Claude Haiku-like  
            'quality_first': {'input': 0.003, 'output': 0.015},     # GPT-4-like
            'performance_first': {'input': 0.0005, 'output': 0.0015} # Fast model
        }
        
        costs = model_costs.get(strategy, model_costs['balanced'])
        
        estimated_cost = (
            (total_input_tokens / 1000) * costs['input'] +
            (output_tokens / 1000) * costs['output']
        )
        
        return Decimal(str(estimated_cost)).quantize(Decimal('0.000001'))


class QwenComplexityAnalyzer:
    """
    Qwen-based LLM analysis for complexity assessment.
    Replaces the placeholder with actual implementation.
    """
    
    def __init__(self):
        self.provider_slug = 'qwen'
        self.model_name = 'Qwen/Qwen3-4B-Instruct-2507-FP8'
        self.system_prompt = QWEN_COMPLEXITY_ANALYZER_PROMPT
    
    @database_sync_to_async
    def _get_api_key(self):
        """Get API key from database"""
        try:
            # Get the default API key for Qwen provider
            api_key_obj = APIKey.objects.filter(
                provider__slug=self.provider_slug,
                is_active=True,
                is_default=True
            ).first()
            
            if api_key_obj:
                return api_key_obj.key  # Automatically decrypted
            
            # Fallback to environment variable
            from django.conf import settings
            return getattr(settings, 'QWEN_API_KEY', None)
        except Exception as e:
            logger.error(f"Failed to get Qwen API key: {e}")
            return None

    async def analyze_complexity_with_llm(
        self,
        request_text: str,
        context: RequestContext,
        escalation_decision: EscalationDecision
    ) -> ComplexityResult:
        """
        Actual LLM-based complexity analysis using Qwen with the comprehensive prompt.
        """
        
        # Get API key from database
        api_key = await self._get_api_key()
        
        if not api_key:
            logger.warning("No API key found for Qwen provider")
            return self._get_fallback_result(escalation_decision)
        
        start_time = time.time()
        
        try:
            # Build the user prompt with context
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": self._build_user_prompt(request_text, context)}
            ]

            # Call Qwen via unified client
            logger.info(f"🤖 Calling Qwen for complexity analysis via UnifiedLLMClient")
            
            response = await UnifiedLLMClient.call_llm(
                provider_slug=self.provider_slug,
                model_name=self.model_name,
                api_key=api_key,
                messages=messages,
                temperature=0.1,  # Low temperature for consistent analysis
                max_tokens=200,   # Enough for JSON response
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            # Debug log to view the full LLM response
            logger.debug(f"LLM Escalation Raw Response: {response.content}")
            
            # Log the complete response object for debugging
            logger.debug(f"LLM Escalation Full Response Object: {response}")
            logger.debug(f"Response attributes: {dir(response) if hasattr(response, '__dict__') else 'No attributes'}")
            logger.debug(f"Response raw_response: {response.raw_response if hasattr(response, 'raw_response') else 'No raw_response'}")
            
            # Check if there's an error in the response
            if hasattr(response, 'raw_response') and isinstance(response.raw_response, dict) and 'error' in response.raw_response:
                logger.error(f"LLM Escalation Error in raw_response: {response.raw_response['error']}")
                if 'type' in response.raw_response:
                    logger.error(f"Error type: {response.raw_response['type']}")
                if 'traceback' in response.raw_response:
                    logger.error(f"Error traceback: {response.raw_response['traceback']}")
            
            # If content starts with "Error:", log it as an error
            if isinstance(response.content, str) and response.content.startswith("Error:"):
                logger.error(f"LLM Escalation Error in content: {response.content}")
                # Still continue to try parsing in case there's valid JSON in the error message
            
            # Log the full response before attempting to parse
            logger.info(f"🔍 Full LLM response before parsing: {response.content}")
            
            # Parse JSON response
            try:
                analysis = json.loads(response.content)
                logger.debug(f"Parsed LLM JSON response: {analysis}")
            except json.JSONDecodeError as e:
                logger.error(f"JSONDecodeError: {e}")
                logger.error(f"Response content: {response.content}")
                logger.error(f"Response type: {type(response.content)}")
                logger.error(f"Response raw: {response.raw_response if hasattr(response, 'raw_response') else 'No raw response'}")
                
                # Try to extract JSON-like structure if present
                json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
                if json_match:
                    try:
                        json_str = json_match.group(0)
                        logger.debug(f"Extracted JSON-like structure: {json_str}")
                        analysis = json.loads(json_str)
                        logger.debug(f"Successfully parsed extracted JSON")
                    except json.JSONDecodeError:
                        logger.error("No JSON-like structure found in response")
                        logger.error(f"Failed to parse Qwen JSON response: {e}")
                        logger.error(f"Response content: {response.content}")
                        return self._get_fallback_result(escalation_decision)
                else:
                    logger.error("No JSON-like structure found in response")
                    logger.error(f"Failed to parse Qwen JSON response: {e}")
                    logger.error(f"Response content: {response.content}")
                    return self._get_fallback_result(escalation_decision)
            
            # Log the analysis result
            logger.info(
                f"✅ Qwen analysis complete: "
                f"score={analysis.get('complexity_score', 'N/A')}, "
                f"level={analysis.get('complexity_level', 'N/A')}, "
                f"confidence={analysis.get('confidence', 'N/A')}, "
                f"time={response.latency_ms}ms"
            )
            
            # Convert to ComplexityResult
            return self._parse_llm_response(
                analysis, 
                escalation_decision, 
                response.latency_ms
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Qwen JSON response: {e}")
            logger.error(f"Response content: {response.content if 'response' in locals() else 'N/A'}")
            return self._get_fallback_result(escalation_decision)
        except Exception as e:
            logger.error(f"Qwen analysis failed: {e}", exc_info=True)
            return self._get_fallback_result(escalation_decision)
    
    def _build_user_prompt(self, request_text: str, context: RequestContext) -> str:
        """Build user prompt with context"""
        prompt = f"REQUEST: {request_text}"
        
        # Add relevant context
        context_parts = []
        
        if context.conversation_history and len(context.conversation_history) > 0:
            context_parts.append(f"CONVERSATION HISTORY: {len(context.conversation_history)} previous messages")
        
        if context.rag_documents and len(context.rag_documents) > 0:
            context_parts.append(f"RAG DOCUMENTS: {len(context.rag_documents)} documents available")
        
        if context.entity_type:
            context_parts.append(f"ENTITY TYPE: {context.entity_type}")
        
        if context.quality_critical:
            context_parts.append("REQUIREMENT: High accuracy is critical")
            
        if context.cost_sensitive:
            context_parts.append("REQUIREMENT: Cost optimization is priority")
        
        if context_parts:
            prompt += "\n\nCONTEXT:\n" + "\n".join(context_parts)
        
        return prompt
    
    def _parse_llm_response(
        self, 
        analysis: dict, 
        escalation_decision: EscalationDecision,
        latency_ms: int
    ) -> ComplexityResult:
        """Parse Qwen's JSON response into ComplexityResult"""
        
        from .types import ComplexityLevel, ContentType, AnalysisPath
        
        # Map string values to enums
        level_map = {
            "simple": ComplexityLevel.SIMPLE,
            "medium": ComplexityLevel.MEDIUM,
            "complex": ComplexityLevel.COMPLEX
        }
        
        content_type_map = {
            "general": ContentType.GENERAL,
            "code": ContentType.CODE,
            "data_analysis": ContentType.DATA_ANALYSIS,
            "business": ContentType.BUSINESS,
            "creative": ContentType.CREATIVE,
            "technical": ContentType.TECHNICAL
        }
        
        # Extract values with defaults
        complexity_score = float(analysis.get("complexity_score", 0.5))
        complexity_level = analysis.get("complexity_level", "medium")
        confidence = float(analysis.get("confidence", 0.8))
        content_type = analysis.get("content_type", "general")
        
        return ComplexityResult(
            score=complexity_score,
            level=level_map.get(complexity_level, ComplexityLevel.MEDIUM),
            confidence=confidence,
            reasoning=analysis.get("reasoning", "qwen_analysis"),
            analysis_path=AnalysisPath.LLM_ESCALATION,
            analysis_time_ms=latency_ms,
            content_type=content_type_map.get(content_type, ContentType.GENERAL),
            escalation_reason=escalation_decision.reason,
            pattern_matches={
                "key_factors": analysis.get("key_factors", [])
            },
            context_factors={
                "recommended_tier": analysis.get("recommended_model_tier", "standard"),
                "optimization_hint": analysis.get("optimization_hint", ""),
                "llm_model": "qwen",
                "llm_provider": self.provider_slug
            }
        )
    
    def _get_fallback_result(self, escalation_decision: EscalationDecision) -> ComplexityResult:
        """Fallback result when LLM analysis fails"""
        
        from .types import ComplexityLevel, ContentType, AnalysisPath
        
        logger.info("Using fallback complexity result due to LLM failure")
        
        return ComplexityResult(
            score=0.5,
            level=ComplexityLevel.MEDIUM,
            confidence=0.70,  # Lower confidence for fallback
            reasoning=f"llm_fallback:reason={escalation_decision.reason.value}",
            analysis_path=AnalysisPath.LLM_ESCALATION,
            analysis_time_ms=100,
            content_type=ContentType.GENERAL,
            escalation_reason=escalation_decision.reason,
            context_factors={
                "fallback": True,
                "original_confidence": escalation_decision.actual_confidence
            }
        )
    
    # Keep the old method for backward compatibility
    def get_llm_analysis_prompt(self, request_text: str, context: RequestContext) -> str:
        """Legacy method - now just calls _build_user_prompt"""
        return self._build_user_prompt(request_text, context)
        
    async def analyze_with_llm(self, text: str, context: RequestContext) -> ComplexityResult:
        """Method called by parallel analyzer for LLM escalation"""
        # Create a basic escalation decision for the method call
        escalation_decision = EscalationDecision(
            should_escalate=True,
            reason=EscalationReason.LOW_CONFIDENCE,
            confidence_threshold=0.7,
            actual_confidence=0.5,
            organization_strategy='balanced'  # Default to balanced strategy
        )
        
        # Call the actual implementation
        return await self.analyze_complexity_with_llm(text, context, escalation_decision)
    
    async def estimate_escalation_cost(
        self, 
        request_text: str, 
        organization_id: Optional[str]
    ) -> Decimal:
        """
        Estimate cost of Qwen LLM escalation analysis.
        """
        # Rough token estimates
        system_prompt_tokens = 800  # The comprehensive prompt
        user_prompt_tokens = len(request_text.split()) * 1.3
        total_input_tokens = system_prompt_tokens + user_prompt_tokens
        output_tokens = 60  # JSON response
        
        # Qwen costs (very low for self-hosted on RunPod)
        cost_per_1k_input = Decimal('0.0001')  # $0.10 per 1M tokens
        cost_per_1k_output = Decimal('0.0002')  # $0.20 per 1M tokens
        
        estimated_cost = (
            (Decimal(total_input_tokens) / 1000 * cost_per_1k_input) +
            (Decimal(output_tokens) / 1000 * cost_per_1k_output)
        )
        
        return estimated_cost.quantize(Decimal('0.000001'))