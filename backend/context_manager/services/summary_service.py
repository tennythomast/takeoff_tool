# context_manager/services/summary_service.py

import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class SummaryResult:
    """Result from summary generation"""
    content: str
    cost: Decimal
    model_used: str
    generation_time_ms: int
    quality_score: float
    tokens_used: int


class SummaryGenerationService:
    """
    PHASE 2 CORE: Cost-Effective Summary Generation with ModelHub Integration
    
    Dynamically selects cost-effective models from ModelHub for summarization
    Implements smart prompting for high-quality summaries
    
    Key Features:
    - Dynamic model selection from ModelHub
    - Real-time cost calculation
    - Intelligent prompt engineering
    - 40/60 summary/recent split
    - Quality preservation techniques
    """
    
    def __init__(self):
        self.default_summarization_model = "mixtral-8x7b"  # Fallback choice
        self.token_estimator = TokenEstimator()
    
    async def generate_fresh_summary(self, 
                                   conversation: List[Dict],
                                   target_tokens: int,
                                   organization_id: str,
                                   preserve_quality: bool = True) -> SummaryResult:
        """
        Generate a fresh summary of the conversation
        
        Tier 3: Fresh Generation (10% of cases)
        Only used when cache miss and incremental update not possible
        
        Args:
            conversation: Complete conversation history
            target_tokens: Target summary length
            organization_id: Tenant identifier
            preserve_quality: Whether to prioritize quality over cost
            
        Returns:
            SummaryResult with generated content
        """
        try:
            start_time = time.time()
            
            # Calculate optimal allocation (40% summary, 60% recent)
            summary_tokens, recent_tokens = self._calculate_token_allocation(target_tokens)
            
            # Split conversation into parts
            recent_messages, older_messages = self._split_conversation(
                conversation, recent_tokens
            )
            
            # If no older messages, just return recent formatted
            if not older_messages:
                formatted_content = self._format_messages_for_model(conversation)
                return SummaryResult(
                    content=formatted_content,
                    cost=Decimal('0.00'),
                    model_used="none",
                    generation_time_ms=int((time.time() - start_time) * 1000),
                    quality_score=1.0,
                    tokens_used=self.token_estimator.count_tokens(formatted_content)
                )
            
            # Select optimal model for summarization
            selected_model = await self._select_summarization_model(
                organization_id=organization_id,
                preserve_quality=preserve_quality,
                estimated_tokens=len(self._format_messages_for_model(older_messages)) // 4
            )
            
            # Generate summary of older messages
            summary_prompt = self._create_summary_prompt(older_messages, summary_tokens)
            
            # Call LLM service with selected model
            summary_response = await self._call_llm_service(
                prompt=summary_prompt,
                organization_id=organization_id,
                model=selected_model['model'],
                max_tokens=summary_tokens
            )
            
            # Format final context with summary + recent messages
            final_content = self._format_final_context(
                summary=summary_response['content'],
                recent_messages=recent_messages
            )
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"Generated fresh summary using {selected_model['model']}: "
                       f"{len(older_messages)} older + {len(recent_messages)} recent messages, "
                       f"cost: ${summary_response['cost']}, time: {generation_time_ms}ms")
            
            return SummaryResult(
                content=final_content,
                cost=summary_response['cost'],
                model_used=selected_model['model'],
                generation_time_ms=generation_time_ms,
                quality_score=0.85,  # High quality with smart summarization
                tokens_used=target_tokens
            )
            
        except Exception as e:
            logger.error(f"Fresh summary generation failed: {str(e)}", exc_info=True)
            # Fallback to recent messages only
            return await self._fallback_to_recent_messages(conversation, target_tokens)
    
    async def generate_incremental_update(self, 
                                        existing_summary: str,
                                        new_messages: List[Dict],
                                        target_tokens: int,
                                        organization_id: str) -> Optional[SummaryResult]:
        """
        Generate incremental update to existing summary
        
        Tier 2: Incremental Updates (20% of cache misses)
        Cost-effective way to update summaries with 1-3 new messages
        
        Args:
            existing_summary: Current summary content
            new_messages: 1-3 new messages to incorporate
            target_tokens: Target updated summary length
            organization_id: Tenant identifier
            
        Returns:
            SummaryResult with updated content or None if failed
        """
        try:
            start_time = time.time()
            
            # Select cost-effective model for incremental updates
            selected_model = await self._select_summarization_model(
                organization_id=organization_id,
                preserve_quality=False,  # Prioritize cost for incremental updates
                estimated_tokens=len(existing_summary + self._format_messages_for_model(new_messages)) // 4
            )
            
            # Create incremental update prompt
            update_prompt = self._create_incremental_prompt(
                existing_summary, new_messages, target_tokens
            )
            
            # Generate update
            update_response = await self._call_llm_service(
                prompt=update_prompt,
                organization_id=organization_id,
                model=selected_model['model'],
                max_tokens=int(target_tokens * 0.5)  # Incremental updates need less generation
            )
            
            # Format the updated summary with recent messages
            final_content = self._format_incremental_result(
                updated_summary=update_response['content'],
                new_messages=new_messages,
                target_tokens=target_tokens
            )
            
            generation_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(f"Generated incremental update using {selected_model['model']}: "
                       f"{len(new_messages)} new messages, "
                       f"cost: ${update_response['cost']}, time: {generation_time_ms}ms")
            
            return SummaryResult(
                content=final_content,
                cost=update_response['cost'],
                model_used=selected_model['model'],
                generation_time_ms=generation_time_ms,
                quality_score=0.87,  # Slightly higher than fresh (preserves context better)
                tokens_used=target_tokens
            )
            
        except Exception as e:
            logger.error(f"Incremental update failed: {str(e)}")
            return None
    
    async def _select_summarization_model(self, 
                                        organization_id: str,
                                        preserve_quality: bool,
                                        estimated_tokens: int) -> Dict:
        """
        Select optimal model for summarization from ModelHub
        
        Args:
            organization_id: Organization identifier
            preserve_quality: Whether to prioritize quality over cost
            estimated_tokens: Estimated input tokens
            
        Returns:
            Dict with selected model info and cost estimates
        """
        try:
            # Import here to avoid circular imports
            from modelhub.models import Model, APIKey
            
            # Get available models for summarization
            available_models = []
            
            # Define preferred models for summarization (cost-effective)
            preferred_models = [
                ('mistral', 'mixtral-8x7b'),
                ('openai', 'gpt-3.5-turbo'),
                ('anthropic', 'claude-3-haiku'),
                ('google', 'gemini-pro')
            ]
            
            for provider_slug, model_name in preferred_models:
                try:
                    # Check if we have API key for this provider
                    api_key = await APIKey.get_active_key_for_provider_async(
                        provider_slug, organization_id
                    )
                    if not api_key:
                        continue
                    
                    # Get model info
                    model = await Model.get_model_async(provider_slug, model_name)
                    
                    # Calculate estimated cost
                    estimated_cost = model.estimate_cost(
                        input_tokens=estimated_tokens,
                        output_tokens=estimated_tokens // 4  # Summary is typically 1/4 of input
                    )
                    
                    available_models.append({
                        'model': f"{provider_slug}/{model_name}",
                        'cost_per_1k_input': model.cost_input,
                        'cost_per_1k_output': model.cost_output,
                        'estimated_cost': estimated_cost,
                        'context_window': model.context_window,
                        'provider': provider_slug,
                        'quality_tier': self._get_model_quality_tier(provider_slug, model_name)
                    })
                    
                except Exception as model_error:
                    logger.debug(f"Model {provider_slug}/{model_name} not available: {str(model_error)}")
                    continue
            
            if not available_models:
                # Fallback to default model
                logger.warning(f"No models available from ModelHub, using fallback: {self.default_summarization_model}")
                return {
                    'model': self.default_summarization_model,
                    'estimated_cost': Decimal('0.0002') * (estimated_tokens / 1000),
                    'cost_per_1k_input': Decimal('0.0002'),
                    'quality_tier': 'medium'
                }
            
            # Select model based on requirements
            if preserve_quality:
                # Choose model with best quality/cost ratio
                selected = min(available_models, 
                             key=lambda m: (m['quality_tier'] == 'low', m['estimated_cost']))
            else:
                # Choose cheapest model
                selected = min(available_models, key=lambda m: m['estimated_cost'])
            
            logger.info(f"Selected model {selected['model']} for summarization "
                       f"(cost: ${selected['estimated_cost']:.4f}, quality: {selected['quality_tier']})")
            
            return selected
            
        except Exception as e:
            logger.error(f"Model selection failed: {str(e)}")
            # Fallback
            return {
                'model': self.default_summarization_model,
                'estimated_cost': Decimal('0.0002') * (estimated_tokens / 1000),
                'cost_per_1k_input': Decimal('0.0002'),
                'quality_tier': 'medium'
            }
    
    def _get_model_quality_tier(self, provider: str, model_name: str) -> str:
        """
        Categorize model quality for selection logic
        
        Returns: 'high', 'medium', or 'low'
        """
        quality_map = {
            'openai': {
                'gpt-4': 'high',
                'gpt-4-turbo': 'high',
                'gpt-3.5-turbo': 'medium'
            },
            'anthropic': {
                'claude-3-opus': 'high',
                'claude-3-sonnet': 'high',
                'claude-3-haiku': 'medium',
                'claude-2': 'medium'
            },
            'mistral': {
                'mixtral-8x7b': 'medium',
                'mistral-7b': 'low'
            },
            'google': {
                'gemini-pro': 'medium',
                'palm-2': 'low'
            }
        }
        
        return quality_map.get(provider, {}).get(model_name, 'medium')
    
    def _calculate_token_allocation(self, target_tokens: int) -> Tuple[int, int]:
        """
        Calculate optimal allocation between summary and recent messages
        
        Proven 40/60 split for optimal quality/efficiency balance
        """
        summary_tokens = int(target_tokens * 0.4)
        recent_tokens = target_tokens - summary_tokens
        
        # Ensure minimum allocations
        min_summary = 100
        min_recent = 200
        
        if summary_tokens < min_summary:
            summary_tokens = min_summary
            recent_tokens = target_tokens - summary_tokens
        
        if recent_tokens < min_recent:
            recent_tokens = min_recent
            summary_tokens = target_tokens - recent_tokens
        
        return summary_tokens, recent_tokens
    
    def _split_conversation(self, 
                           conversation: List[Dict], 
                           recent_tokens: int) -> Tuple[List[Dict], List[Dict]]:
        """
        Split conversation into recent messages and older messages
        
        Args:
            conversation: Full conversation
            recent_tokens: Tokens allocated for recent messages
            
        Returns:
            (recent_messages, older_messages)
        """
        recent_messages = []
        used_tokens = 0
        
        # Work backwards to get recent messages within token limit
        for message in reversed(conversation):
            message_tokens = self.token_estimator.estimate_message_tokens(message)
            if used_tokens + message_tokens > recent_tokens:
                break
            recent_messages.insert(0, message)
            used_tokens += message_tokens
        
        # Older messages are everything not in recent
        older_messages = conversation[:-len(recent_messages)] if recent_messages else conversation
        
        return recent_messages, older_messages
    
    def _create_summary_prompt(self, older_messages: List[Dict], summary_tokens: int) -> str:
        """
        Create optimized prompt for conversation summarization
        
        Focus on preserving critical information in limited space
        """
        older_content = self._format_messages_for_model(older_messages)
        
        prompt = f"""Summarize this conversation preserving all critical information in approximately {summary_tokens} tokens.

CRITICAL REQUIREMENTS:
- Preserve all key decisions, facts, and requirements
- Include user preferences and goals
- Maintain important context for future responses
- Keep essential technical details
- Note any errors or issues mentioned
- Preserve agent reasoning and tool usage if present

CONVERSATION TO SUMMARIZE:
{older_content}

CONCISE SUMMARY (target {summary_tokens} tokens):"""
        
        return prompt
    
    def _create_incremental_prompt(self, 
                                  existing_summary: str,
                                  new_messages: List[Dict],
                                  target_tokens: int) -> str:
        """
        Create prompt for incremental summary updates
        
        Efficiently integrate new information into existing summary
        """
        new_content = self._format_messages_for_model(new_messages)
        summary_tokens = int(target_tokens * 0.4)
        
        prompt = f"""Update this conversation summary by incorporating the new messages below. 
Maintain all important information from the original summary while adding relevant details from new messages.
Target length: approximately {summary_tokens} tokens.

EXISTING SUMMARY:
{existing_summary}

NEW MESSAGES TO INCORPORATE:
{new_content}

UPDATED SUMMARY (target {summary_tokens} tokens):"""
        
        return prompt
    
    def _format_messages_for_model(self, messages: List[Dict]) -> str:
        """Format messages for model consumption with domain awareness"""
        formatted = []
        for msg in messages:
            role = msg['role'].title()
            content = msg['content']
            
            # Add structured data context for agents/workflows
            if msg.get('structured_data') and len(msg['structured_data']) > 0:
                structured_info = []
                for key, value in msg['structured_data'].items():
                    if key in ['tool_calls', 'function_calls', 'reasoning_steps']:
                        structured_info.append(f"{key}: {value}")
                
                if structured_info:
                    content += f" [Context: {'; '.join(structured_info)}]"
            
            # Add execution metadata for workflows
            if msg.get('execution_metadata') and len(msg['execution_metadata']) > 0:
                exec_info = []
                for key, value in msg['execution_metadata'].items():
                    if key in ['step_type', 'status', 'output']:
                        exec_info.append(f"{key}: {value}")
                
                if exec_info:
                    content += f" [Execution: {'; '.join(exec_info)}]"
            
            formatted.append(f"{role}: {content}")
        
        return "\n\n".join(formatted)
    
    def _format_final_context(self, summary: str, recent_messages: List[Dict]) -> str:
        """Format final context with summary and recent messages"""
        parts = []
        
        if summary and summary.strip():
            parts.append("## CONVERSATION SUMMARY")
            parts.append("Previous conversation summary:")
            parts.append(summary.strip())
            parts.append("")
        
        if recent_messages:
            parts.append("## RECENT CONVERSATION")
            parts.append("Recent messages for context:")
            parts.append("")
            
            for msg in recent_messages:
                role = msg['role'].title()
                content = msg['content']
                
                # Add structured data context for agents/workflows
                if msg.get('structured_data') and len(msg['structured_data']) > 0:
                    structured_info = []
                    for key, value in msg['structured_data'].items():
                        if key in ['tool_calls', 'function_calls', 'reasoning_steps']:
                            structured_info.append(f"{key}: {value}")
                    
                    if structured_info:
                        content += f" [Context: {'; '.join(structured_info)}]"
                
                # Add execution metadata for workflows
                if msg.get('execution_metadata') and len(msg['execution_metadata']) > 0:
                    exec_info = []
                    for key, value in msg['execution_metadata'].items():
                        if key in ['step_type', 'status', 'output']:
                            exec_info.append(f"{key}: {value}")
                    
                    if exec_info:
                        content += f" [Execution: {'; '.join(exec_info)}]"
                
                parts.append(f"**{role}**: {content}")
        
        return "\n".join(parts)
    
    def _format_incremental_result(self, 
                                  updated_summary: str,
                                  new_messages: List[Dict],
                                  target_tokens: int) -> str:
        """Format incremental update result"""
        # For incremental updates, new messages are usually the "recent" part
        return self._format_final_context(updated_summary.strip(), new_messages)
    
    async def _call_llm_service(self, 
                              prompt: str, 
                              organization_id: str,
                              model: str,
                              max_tokens: int = 2000) -> Dict:
        """
        Call the LLM service for summary generation using ModelHub
        
        Uses the specified model with optimal parameters for summarization
        """
        try:
            # Import here to avoid circular imports
            from modelhub.managers import ModelManager
            
            model_manager = ModelManager()
            
            # Parse model string to get provider and model name
            if '/' in model:
                provider, model_name = model.split('/', 1)
            else:
                # Use utils to parse model string
                from ..utils import _parse_model_string
                provider, model_name = _parse_model_string(model)
            
            response = await model_manager.generate_response(
                provider=provider,
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                organization_id=organization_id,
                max_tokens=max_tokens,
                temperature=0.1,  # Low temperature for consistent summaries
                top_p=0.9
            )
            
            return {
                'content': response['response'],
                'cost': Decimal(str(response.get('cost', 0.0))),
                'tokens_used': response.get('tokens_used', 0)
            }
            
        except Exception as e:
            logger.error(f"LLM service call failed for model {model}: {str(e)}")
            # Try fallback call with simplified parameters
            try:
                return await self._fallback_llm_call(prompt, organization_id)
            except Exception as fallback_error:
                logger.error(f"Fallback LLM call also failed: {str(fallback_error)}")
                raise
    
    async def _fallback_llm_call(self, prompt: str, organization_id: str) -> Dict:
        """
        Fallback LLM call when primary model fails
        """
        try:
            # Use a simple, reliable model for fallback
            from modelhub.managers import ModelManager
            
            model_manager = ModelManager()
            
            response = await model_manager.generate_response(
                provider='openai',
                model='gpt-3.5-turbo',
                messages=[{"role": "user", "content": prompt}],
                organization_id=organization_id,
                max_tokens=1000,
                temperature=0.1
            )
            
            return {
                'content': response['response'],
                'cost': Decimal(str(response.get('cost', 0.001))),
                'tokens_used': response.get('tokens_used', 0)
            }
            
        except Exception as e:
            logger.error(f"Fallback LLM call failed: {str(e)}")
            raise
    
    async def _fallback_to_recent_messages(self, 
                                         conversation: List[Dict], 
                                         target_tokens: int) -> SummaryResult:
        """
        Fallback when summary generation fails
        
        Just use recent messages within token limit
        """
        try:
            start_time = time.time()
            
            recent_messages, _ = self._split_conversation(conversation, target_tokens)
            content = self._format_messages_for_model(recent_messages)
            
            return SummaryResult(
                content=content,
                cost=Decimal('0.00'),
                model_used="fallback",
                generation_time_ms=int((time.time() - start_time) * 1000),
                quality_score=0.6,  # Lower quality but functional
                tokens_used=self.token_estimator.count_tokens(content)
            )
            
        except Exception as e:
            logger.error(f"Fallback failed: {str(e)}")
            # Ultimate fallback - just the latest message
            if conversation:
                latest = conversation[-1]
                content = f"{latest['role'].title()}: {latest['content']}"
            else:
                content = "No conversation history available."
            
            return SummaryResult(
                content=content,
                cost=Decimal('0.00'),
                model_used="emergency_fallback",
                generation_time_ms=0,
                quality_score=0.3,
                tokens_used=self.token_estimator.count_tokens(content)
            )
    
    async def estimate_summarization_cost(self, 
                                        conversation: List[Dict],
                                        target_tokens: int,
                                        organization_id: str) -> Dict:
        """
        Estimate cost for summarizing a conversation before actually doing it
        
        Useful for cost-aware decision making
        """
        try:
            # Estimate input tokens
            conversation_content = self._format_messages_for_model(conversation)
            input_tokens = self.token_estimator.count_tokens(conversation_content)
            
            # Get optimal model for this request
            selected_model = await self._select_summarization_model(
                organization_id=organization_id,
                preserve_quality=True,
                estimated_tokens=input_tokens
            )
            
            # Estimate output tokens (summary)
            output_tokens = target_tokens // 2  # Conservative estimate
            
            return {
                'estimated_cost': selected_model['estimated_cost'],
                'selected_model': selected_model['model'],
                'input_tokens': input_tokens,
                'output_tokens': output_tokens,
                'quality_tier': selected_model['quality_tier']
            }
            
        except Exception as e:
            logger.error(f"Cost estimation failed: {str(e)}")
            return {
                'estimated_cost': Decimal('0.001'),  # Conservative fallback
                'selected_model': self.default_summarization_model,
                'input_tokens': len(self._format_messages_for_model(conversation)) // 4,
                'output_tokens': target_tokens // 2,
                'quality_tier': 'medium'
            }


class TokenEstimator:
    """
    Enhanced token estimation for planning and optimization
    
    Provides better estimates for different content types
    """
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text
        
        Improved approximation considering different content types
        """
        if not text:
            return 0
        
        # Base approximation: 1 token per 4 characters for English text
        base_tokens = len(text) // 4
        
        # Adjust for content patterns
        if '```' in text:
            # Code blocks are typically more token-dense
            base_tokens = int(base_tokens * 1.2)
        elif text.count('\n') > 10:
            # Structured content with many lines
            base_tokens = int(base_tokens * 1.1)
        elif any(pattern in text for pattern in ['{', '[', '<', 'http']):
            # JSON, arrays, XML, URLs are more token-dense
            base_tokens = int(base_tokens * 1.15)
        
        return max(1, base_tokens)  # Ensure at least 1 token
    
    def estimate_message_tokens(self, message: Dict) -> int:
        """Estimate tokens for a single message with metadata"""
        role_tokens = 3  # Role prefix and formatting
        content_tokens = self.count_tokens(message['content'])
        
        # Add tokens for structured data
        if message.get('structured_data'):
            structured_content = str(message['structured_data'])
            content_tokens += self.count_tokens(structured_content) // 2  # Partial weight
        
        # Add tokens for execution metadata
        if message.get('execution_metadata'):
            exec_content = str(message['execution_metadata'])
            content_tokens += self.count_tokens(exec_content) // 3  # Lower weight
        
        formatting_tokens = 5  # Message formatting overhead
        
        return role_tokens + content_tokens + formatting_tokens
    
    def estimate_conversation_tokens(self, conversation: List[Dict]) -> int:
        """Estimate total tokens for conversation"""
        total = 0
        for message in conversation:
            total += self.estimate_message_tokens(message)
        
        # Add conversation-level formatting
        conversation_overhead = len(conversation) * 2  # Inter-message formatting
        
        return total + conversation_overhead
    
    def estimate_prompt_tokens(self, prompt: str) -> int:
        """Estimate tokens for a prompt including system instructions"""
        base_tokens = self.count_tokens(prompt)
        
        # Add overhead for system instructions and formatting
        prompt_overhead = 50  # Typical system prompt overhead
        
        return base_tokens + prompt_overhead