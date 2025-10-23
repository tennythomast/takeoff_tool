# backend/modelhub/services/routing/router.py
"""
Enhanced intelligent model router with multi-entity support.
Handles routing for platform_chat, agent_session, workflow_execution, workspace_chat.
"""
import time
import logging
from typing import List, Dict, Optional, Tuple, Union
from decimal import Decimal
from channels.db import database_sync_to_async

from .types import (
    RoutingDecision, RequestContext, OptimizationStrategy, 
    ModelCandidate, EntityType, RoutingMetrics
)
from modelhub.models import Model, Provider, RoutingRule, RoutingRuleModel

logger = logging.getLogger(__name__)


class EnhancedModelRouter:
    """
    Enhanced routing engine with sub-50ms decisions and entity awareness.
    
    Features:
    - Entity-type specific routing logic
    - Database routing rules integration
    - Cost protection across entity types
    - Performance optimization per use case
    """
    
    def __init__(self):
        self.metrics = RoutingMetrics()
    
    async def route_request(
        self,
        organization,
        complexity_score: float,
        content_type: str,
        context: RequestContext,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> RoutingDecision:
        """
        Main routing logic with entity-aware intelligence.
        
        Args:
            organization: Organization instance
            complexity_score: Complexity score from analyzer
            content_type: Content type (code, business, etc.)
            context: Request context with entity information
            strategy: Optimization strategy
            
        Returns:
            RoutingDecision with selected model and metadata
        """
        start_time = time.time()
        
        logger.info(
            f"🎯 Starting entity-aware routing: "
            f"entity={context.entity_type}, "
            f"complexity={complexity_score:.2f}, "
            f"strategy={strategy.value}"
        )
        
        # Update metrics
        self.metrics.total_requests += 1
        if context.entity_type not in self.metrics.entity_type_breakdown:
            self.metrics.entity_type_breakdown[context.entity_type] = 0
        self.metrics.entity_type_breakdown[context.entity_type] += 1
        
        # Phase 1: Try database routing rules first
        try:
            rule_result = await self._get_routing_decision_from_rules(
                organization=organization,
                model_type=context.model_type,
                complexity_score=complexity_score,
                content_type=content_type,
                strategy=strategy,
                context=context
            )
            
            if rule_result:
                provider_slug, model_name, confidence = rule_result
                
                # Get cost estimation
                estimated_tokens = context.max_tokens
                model_info = await self._get_model_info(provider_slug, model_name)
                
                if model_info:
                    estimated_cost = self._calculate_estimated_cost(model_info, estimated_tokens)
                    decision_time = int((time.time() - start_time) * 1000)
                    
                    self.metrics.rule_based_decisions += 1
                    self._update_avg_decision_time(decision_time)
                    
                    logger.info(
                        f"✅ Rule-based routing: {provider_slug}:{model_name} "
                        f"(${estimated_cost:.6f}, {decision_time}ms, entity={context.entity_type})"
                    )
                    
                    return RoutingDecision(
                        selected_model=model_name,
                        selected_provider=provider_slug,
                        api_type="CHAT",
                        confidence_score=confidence,
                        reasoning=f"database_rule,entity={context.entity_type},complexity={complexity_score:.2f}",
                        estimated_cost=estimated_cost,
                        estimated_tokens=estimated_tokens,
                        complexity_score=complexity_score,
                        content_type=content_type,
                        fallback_chain=[],
                        decision_time_ms=decision_time,
                        session_sticky=False,
                        entity_type=context.entity_type,
                        organization_strategy=strategy.value
                    )
            
            logger.warning("⚠️ Database routing rules didn't find a match, using fallback logic")
            
        except Exception as e:
            logger.error(f"❌ Database routing failed: {e}, using fallback logic")
        
        # Phase 2: Fallback to legacy routing with entity awareness
        try:
            fallback_result = await self._fallback_routing_with_entity_awareness(
                organization=organization,
                complexity_score=complexity_score,
                content_type=content_type,
                context=context,
                strategy=strategy,
                start_time=start_time
            )
            
            self.metrics.fallback_decisions += 1
            return fallback_result
            
        except Exception as e:
            logger.error(f"❌ Fallback routing failed: {e}")
            
            # Emergency fallback
            decision_time = int((time.time() - start_time) * 1000)
            return RoutingDecision(
                selected_model="gpt-3.5-turbo",  # Safe default
                selected_provider="openai",
                api_type="CHAT",
                confidence_score=0.3,
                reasoning=f"emergency_fallback,entity={context.entity_type}",
                estimated_cost=Decimal('0.01'),
                estimated_tokens=context.max_tokens,
                complexity_score=complexity_score,
                content_type=content_type,
                fallback_chain=[],
                decision_time_ms=decision_time,
                entity_type=context.entity_type,
                organization_strategy=strategy.value
            )
    
    @database_sync_to_async
    def _get_routing_decision_from_rules(
        self,
        organization,
        model_type: str,
        complexity_score: float,
        content_type: str,
        strategy: OptimizationStrategy,
        context: RequestContext
    ) -> Optional[Tuple[str, str, float]]:
        """
        Use database routing rules with entity-aware logic.
        
        Entity types may influence rule selection and model preferences.
        """
        try:
            from ...models import RoutingRule
            
            logger.info(
                f"🔍 Looking for routing rules: "
                f"complexity={complexity_score:.2f}, "
                f"strategy={strategy.value}, "
                f"entity={context.entity_type} (entity-agnostic routing)"
            )
            
            # Get organization's default strategy if not provided
            org_strategy = None
            if hasattr(organization, 'default_optimization_strategy'):
                org_strategy = organization.default_optimization_strategy
                if org_strategy and org_strategy != strategy.value:
                    logger.info(f"Using org default strategy: {org_strategy} (overriding {strategy.value})")
                    strategy = OptimizationStrategy(org_strategy)
            
            # Find applicable routing rules
            applicable_rules = []
            
            # Get rules for this organization first, then system-wide rules
            rule_query = RoutingRule.objects.filter(
                model_type=model_type,
                is_active=True
            ).order_by('priority')
            
            # Prefer organization-specific rules
            org_rules = rule_query.filter(organization=organization)
            system_rules = rule_query.filter(organization__isnull=True)
            
            for rule in list(org_rules) + list(system_rules):
                if self._rule_matches_request(rule, complexity_score, content_type, strategy, context):
                    applicable_rules.append(rule)
                    logger.info(f"✅ Rule matches: {rule.name} (entity={context.entity_type})")
                    break  # Use first matching rule
            
            if not applicable_rules:
                logger.warning(f"⚠️ No routing rules matched for entity={context.entity_type}")
                return None
            
            # Use the selected rule
            selected_rule = applicable_rules[0]
            
            # Get models from the rule with their weights
            rule_models = selected_rule.routingrulemodel_set.all().select_related('model', 'model__provider')
            
            if not rule_models:
                logger.warning(f"⚠️ No models configured for rule: {selected_rule.name}")
                return None
            
            # Filter models based on entity-specific requirements
            suitable_models = []
            for rule_model in rule_models:
                if self._model_suitable_for_entity(rule_model.model, context):
                    suitable_models.append(rule_model)
            
            if not suitable_models:
                logger.warning(f"⚠️ No suitable models for entity type: {context.entity_type}")
                return None
            
            # Select model (for now, use first suitable model)
            # TODO: Implement proper weighted selection
            selected_rule_model = suitable_models[0]
            selected_model = selected_rule_model.model
            
            confidence = 0.9  # High confidence for rule-based decisions
            
            return (
                selected_model.provider.slug,
                selected_model.name,
                confidence
            )
            
        except Exception as e:
            logger.error(f"Error in rule-based routing: {e}")
            return None
    
    def _rule_matches_request(
        self,
        rule: RoutingRule,
        complexity_score: float,
        content_type: str,
        strategy: OptimizationStrategy,
        context: RequestContext
    ) -> bool:
        """Check if a routing rule matches the current request"""
        if not rule.conditions:
            return True
        
        for condition in rule.conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if not field or not operator:
                continue
            
            # Skip entity_type conditions - we're making routing entity-agnostic
            if field == 'entity_type':
                continue
            
            elif field == 'complexity_score' and complexity_score is not None:
                if not self._evaluate_condition(complexity_score, operator, value):
                    return False
            
            elif field == 'content_type' and content_type:
                if not self._evaluate_condition(content_type, operator, value):
                    return False
            
            elif field == 'optimization_strategy' and strategy:
                if not self._evaluate_condition(strategy.value, operator, value):
                    return False
        
        return True
    
    def _evaluate_condition(self, actual_value, operator: str, expected_value) -> bool:
        """
        Evaluate a routing rule condition.
        
        Args:
            actual_value: The actual value to compare
            operator: Comparison operator ('eq', 'gt', 'lt', 'gte', 'lte', 'in', 'contains')
            expected_value: The expected value to compare against
            
        Returns:
            bool: True if condition is met, False otherwise
        """
        try:
            if operator == 'eq':
                return actual_value == expected_value
            elif operator == 'gt':
                return float(actual_value) > float(expected_value)
            elif operator == 'lt':
                return float(actual_value) < float(expected_value)
            elif operator == 'gte':
                return float(actual_value) >= float(expected_value)
            elif operator == 'lte':
                return float(actual_value) <= float(expected_value)
            elif operator == 'in':
                # expected_value should be a list or comma-separated string
                if isinstance(expected_value, str):
                    expected_list = [item.strip() for item in expected_value.split(',')]
                else:
                    expected_list = expected_value
                return actual_value in expected_list
            elif operator == 'contains':
                return str(expected_value).lower() in str(actual_value).lower()
            else:
                logger.warning(f"Unknown operator in routing condition: {operator}")
                return False
        except (ValueError, TypeError) as e:
            logger.error(f"Error evaluating condition: {actual_value} {operator} {expected_value} - {e}")
            return False
    
    def _model_suitable_for_entity(self, model: Model, context: RequestContext) -> bool:
        """Check if a model is suitable for the given entity type"""
        # In entity-agnostic routing, all models are considered suitable for all entity types
        # We're ignoring entity-specific requirements
        return True
    
    def route_request_sync(
        self,
        organization,
        complexity_score: float,
        content_type: str,
        context: RequestContext,
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED
    ) -> RoutingDecision:
        """Synchronous version of route_request for testing"""
        import time
        start_time = time.time()
        model_type = "TEXT"  # Default model type
        
        # Get organization's default strategy if not provided
        if organization and hasattr(organization, 'default_optimization_strategy') and not strategy:
            strategy = OptimizationStrategy(organization.default_optimization_strategy)
        
        # Try to get a routing decision from rules
        routing_result = self._get_routing_decision_from_rules_sync(
            organization, model_type, complexity_score, content_type, strategy, context
        )
        
        if routing_result:
            provider_slug, model_name, confidence = routing_result
            model_info = self._get_model_info(provider_slug, model_name)
            estimated_cost = self._calculate_estimated_cost(model_info, context.max_tokens)
            
            decision_time = int((time.time() - start_time) * 1000)
            self._update_avg_decision_time(decision_time)
            
            return RoutingDecision(
                selected_model=model_name,
                selected_provider=provider_slug,
                api_type=model_info.get('api_type', 'CHAT'),
                confidence_score=confidence,
                reasoning=f"rule_match,entity={context.entity_type}",
                estimated_cost=estimated_cost,
                estimated_tokens=context.max_tokens,
                complexity_score=complexity_score,
                content_type=content_type,
                fallback_chain=[],
                decision_time_ms=decision_time,
                entity_type=context.entity_type,
                organization_strategy=strategy.value
            )
        
        # Fallback to hardcoded logic
        return self._fallback_routing_with_entity_awareness_sync(
            organization, complexity_score, content_type, context, strategy, start_time
        )
    
    def _get_routing_decision_from_rules_sync(
        self,
        organization,
        model_type: str,
        complexity_score: float,
        content_type: str,
        strategy: OptimizationStrategy,
        context: RequestContext
    ) -> Optional[Tuple[str, str, float]]:
        """Synchronous version of _get_routing_decision_from_rules"""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info(
                f"🔍 Looking for routing rules: "
                f"complexity={complexity_score:.2f}, "
                f"strategy={strategy.value}, "
                f"entity={context.entity_type} (entity-agnostic routing)"
            )
            
            # Get organization's default strategy if not provided
            if organization and hasattr(organization, 'default_optimization_strategy') and not strategy:
                strategy = OptimizationStrategy(organization.default_optimization_strategy)
            
            applicable_rules = []
            rule_query = RoutingRule.objects.filter(model_type=model_type, is_active=True).order_by('priority')
            
            if organization:
                org_rules = rule_query.filter(organization=organization)
                system_rules = rule_query.filter(organization__isnull=True)
                all_rules = list(org_rules) + list(system_rules)
            else:
                all_rules = list(rule_query.filter(organization__isnull=True))
            
            for rule in all_rules:
                if self._rule_matches_request(rule, complexity_score, content_type, strategy, context):
                    applicable_rules.append(rule)
                    logger.info(f"✅ Rule matched: {rule.name}")
                    break  # Use first matching rule based on priority
            
            if not applicable_rules:
                logger.info("❌ No matching rules found")
                return None
            
            selected_rule = applicable_rules[0]  # Use highest priority rule
            
            # Get models associated with the rule
            rule_models = selected_rule.routingrulemodel_set.all().select_related('model', 'model__provider')
            
            if not rule_models.exists():
                logger.warning(f"⚠️ No models configured for rule: {selected_rule.name}")
                return None
            
            # Filter models suitable for entity
            suitable_models = [rm for rm in rule_models if self._model_suitable_for_entity(rm.model, context)]
            
            if not suitable_models:
                logger.warning(f"⚠️ No suitable models for entity: {context.entity_type}")
                return None
            
            # Select model based on weights
            import random
            total_weight = sum(rm.weight for rm in suitable_models)
            rand_val = random.uniform(0, total_weight)
            
            current_weight = 0
            for rm in suitable_models:
                current_weight += rm.weight
                if rand_val <= current_weight:
                    selected_model = rm.model
                    provider_slug = selected_model.provider.slug
                    model_name = selected_model.name
                    confidence = 0.9  # High confidence for rule-based selection
                    
                    logger.info(f"✅ Selected {provider_slug}/{model_name} from rule {selected_rule.name}")
                    return provider_slug, model_name, confidence
            
            # Fallback to first model if weights don't add up correctly
            selected_model = suitable_models[0].model
            provider_slug = selected_model.provider.slug
            model_name = selected_model.name
            confidence = 0.8  # Slightly lower confidence for fallback selection
            
            logger.info(f"✅ Fallback selected {provider_slug}/{model_name} from rule {selected_rule.name}")
            return provider_slug, model_name, confidence
            
        except Exception as e:
            logger.error(f"❌ Error in rule-based routing: {e}")
            return None
    
    def _fallback_routing_with_entity_awareness_sync(
        self,
        organization,
        complexity_score: float,
        content_type: str,
        context: RequestContext,
        strategy: OptimizationStrategy,
        start_time: float
    ) -> RoutingDecision:
        """Synchronous version of _fallback_routing_with_entity_awareness"""
        import time
        import logging
        from decimal import Decimal
        logger = logging.getLogger(__name__)
        
        logger.info(f"⚠️ Using fallback routing for {context.entity_type}")
        
        # Emergency fallback
        decision_time = int((time.time() - start_time) * 1000)
        return RoutingDecision(
            selected_model="gpt-3.5-turbo",  # Safe default
            selected_provider="openai",
            api_type="CHAT",
            confidence_score=0.3,
            reasoning=f"emergency_fallback,entity={context.entity_type}",
            estimated_cost=Decimal('0.01'),
            estimated_tokens=context.max_tokens,
            complexity_score=complexity_score,
            content_type=content_type,
            fallback_chain=[],
            decision_time_ms=decision_time,
            entity_type=context.entity_type,
            organization_strategy=strategy.value
        )
        
    async def _fallback_routing_with_entity_awareness(
        self,
        organization,
        complexity_score: float,
        content_type: str,
        context: RequestContext,
        strategy: OptimizationStrategy,
        start_time: float
    ) -> RoutingDecision:
        """
        Fallback routing logic with entity type awareness.
        """
        
        # Get available models
        available_models = await self._get_available_models(organization, context.model_type)
        
        if not available_models:
            raise Exception("No available models found for organization")
        
        # Filter models for entity type
        suitable_models = []
        for model_dict in available_models:
            if self._model_dict_suitable_for_entity(model_dict, context):
                suitable_models.append(model_dict)
        
        if not suitable_models:
            # Fallback to any available model
            suitable_models = available_models
        
        # Score and select best model
        best_model = None
        best_score = -1
        
        for model in suitable_models:
            score = self._score_model_for_strategy(
                model, complexity_score, strategy, context.max_tokens, context.entity_type
            )
            
            if score > best_score:
                best_score = score
                best_model = model
        
        if not best_model:
            raise Exception("No suitable model found")
        
        # Calculate estimated cost
        estimated_cost = self._calculate_estimated_cost(best_model, context.max_tokens)
        decision_time = int((time.time() - start_time) * 1000)
        self._update_avg_decision_time(decision_time)
        
        return RoutingDecision(
            selected_model=best_model['model'],
            selected_provider=best_model['provider'],
            api_type=best_model['api_type'],
            confidence_score=best_score,
            reasoning=f"fallback_entity_aware,entity={context.entity_type},strategy={strategy.value}",
            estimated_cost=estimated_cost,
            estimated_tokens=context.max_tokens,
            complexity_score=complexity_score,
            content_type=content_type,
            fallback_chain=[],
            decision_time_ms=decision_time,
            entity_type=context.entity_type,
            organization_strategy=strategy.value,
            api_key_source=best_model.get('api_key_source')
        )
    
    def _model_dict_suitable_for_entity(self, model_dict: Dict, context: RequestContext) -> bool:
        """Check if model dictionary is suitable for entity type"""
        
        capabilities = model_dict.get('capabilities', [])
        
        # Entity-specific requirements
        if context.entity_type == EntityType.WORKFLOW_EXECUTION.value:
            return 'function_calling' in capabilities
        elif context.entity_type == EntityType.AGENT_SESSION.value:
            return 'advanced_reasoning' in capabilities
        elif context.entity_type == EntityType.RAG_QUERY.value:
            return model_dict.get('context_window', 0) >= 8000
        
        # Default: all models suitable
        return True
    
    def _score_model_for_strategy(
        self,
        model: Dict,
        complexity: float,
        strategy: OptimizationStrategy,
        estimated_tokens: int,
        entity_type: str
    ) -> float:
        """Score model based on strategy and entity type"""
        
        cost_per_request = self._calculate_estimated_cost(model, estimated_tokens)
        
        # Normalize factors (0.0 to 1.0, where 1.0 is best)
        cost_score = max(0, 1.0 - (float(cost_per_request) / 0.10))
        
        # Quality score based on capabilities and cost
        quality_indicators = len(model.get('capabilities', []))
        quality_score = min(1.0, (quality_indicators / 10.0) + (float(cost_per_request) / 0.05))
        
        # Performance score (cheaper models assumed faster)
        performance_score = max(0, 1.0 - (float(cost_per_request) / 0.08))
        
        # Entity-specific scoring adjustments
        entity_multiplier = 1.0
        if entity_type == EntityType.WORKFLOW_EXECUTION.value:
            # Workflows prioritize performance and function calling
            if 'function_calling' in model.get('capabilities', []):
                entity_multiplier = 1.2
        elif entity_type == EntityType.AGENT_SESSION.value:
            # Agents prioritize quality and reasoning
            if 'advanced_reasoning' in model.get('capabilities', []):
                entity_multiplier = 1.15
        
        # Strategy-based weighting
        if strategy == OptimizationStrategy.COST_FIRST:
            base_score = cost_score * 0.8 + quality_score * 0.1 + performance_score * 0.1
        elif strategy == OptimizationStrategy.QUALITY_FIRST:
            base_score = quality_score * 0.8 + cost_score * 0.1 + performance_score * 0.1
        elif strategy == OptimizationStrategy.PERFORMANCE_FIRST:
            base_score = performance_score * 0.8 + cost_score * 0.1 + quality_score * 0.1
        else:  # BALANCED
            base_score = cost_score * 0.4 + quality_score * 0.3 + performance_score * 0.3
        
        return base_score * entity_multiplier
    
    @database_sync_to_async
    def _get_available_models(self, organization, model_type: str = 'TEXT') -> List[Dict]:
        """Get available models for organization"""
        from ...models import Model, APIKey, Provider
        
        models = Model.objects.filter(
            status='ACTIVE',
            model_type=model_type,
            provider__status='ACTIVE'
        ).select_related('provider').order_by('cost_input')
        
        available_models = []
        
        for model in models:
            # Check API key availability
            api_key_info = self._check_api_key_availability(organization, model.provider)
            
            if api_key_info['available']:
                available_models.append({
                    'provider': model.provider.slug,
                    'model': model.name,
                    'api_type': model.get_preferred_api_type(),
                    'cost_input': float(model.cost_input),
                    'cost_output': float(model.cost_output),
                    'context_window': model.context_window,
                    'capabilities': model.capabilities,
                    'api_key': api_key_info['api_key'],
                    'api_key_source': api_key_info['source']
                })
        
        return available_models
    
    def _check_api_key_availability(self, organization, provider) -> Dict:
        """Check API key availability with cost protection"""
        from ...models import APIKey
        
        # Try organization key first
        if organization:
            api_key = APIKey.objects.filter(
                organization=organization,
                provider=provider,
                is_active=True
            ).first()
            
            if api_key and api_key.quota_status.get('status') != 'exceeded':
                return {
                    'available': True,
                    'api_key': api_key.key,
                    'source': 'org'
                }
        
        # Try Dataelan fallback key
        dataelan_key = APIKey.objects.filter(
            organization__isnull=True,
            provider=provider,
            is_active=True
        ).first()
        
        if dataelan_key and dataelan_key.quota_status.get('status') != 'exceeded':
            return {
                'available': True,
                'api_key': dataelan_key.key,
                'source': 'dataelan'
            }
        
        return {'available': False}
    
    @database_sync_to_async
    def _get_model_info(self, provider_slug: str, model_name: str) -> Optional[Dict]:
        """Get model information from database"""
        from ...models import Model
        
        try:
            model = Model.objects.select_related('provider').get(
                provider__slug=provider_slug,
                name=model_name,
                status='ACTIVE'
            )
            return {
                'provider': model.provider.slug,
                'model': model.name,
                'cost_input': float(model.cost_input),
                'cost_output': float(model.cost_output),
                'context_window': model.context_window,
                'capabilities': model.capabilities
            }
        except Model.DoesNotExist:
            return None
    
    def _calculate_estimated_cost(self, model_info: Dict, estimated_tokens: int) -> Decimal:
        """Calculate estimated cost for model usage"""
        input_tokens = estimated_tokens * 0.7  # Rough estimate
        output_tokens = estimated_tokens * 0.3
        
        cost = (
            (input_tokens / 1000 * model_info['cost_input']) +
            (output_tokens / 1000 * model_info['cost_output'])
        )
        return Decimal(str(cost))
    
    def _update_avg_decision_time(self, decision_time_ms: int):
        """Update average decision time metric"""
        total_decisions = (
            self.metrics.rule_based_decisions + 
            self.metrics.fallback_decisions + 
            self.metrics.session_sticky_decisions
        )
        
        if total_decisions > 0:
            current_avg = self.metrics.avg_decision_time_ms
            self.metrics.avg_decision_time_ms = (
                (current_avg * (total_decisions - 1) + decision_time_ms) / total_decisions
            )
    
    def get_routing_metrics(self) -> Dict:
        """Get routing performance metrics"""
        return {
            'total_requests': self.metrics.total_requests,
            'rule_based_decisions': self.metrics.rule_based_decisions,
            'fallback_decisions': self.metrics.fallback_decisions,
            'session_sticky_decisions': self.metrics.session_sticky_decisions,
            'rule_based_rate_percent': self.metrics.rule_based_rate,
            'stickiness_rate_percent': self.metrics.stickiness_rate,
            'avg_decision_time_ms': round(self.metrics.avg_decision_time_ms, 2),
            'entity_type_breakdown': self.metrics.entity_type_breakdown
        }