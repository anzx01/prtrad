from services.tagging.contracts import TagDefinitionInput, TagRuleInput, TagRuleVersionCreateInput
from services.tagging.classifier import MarketAutoClassificationService, get_market_auto_classification_service
from services.tagging.service import TaggingRuleService, get_tagging_rule_service

__all__ = [
    "TagDefinitionInput",
    "TagRuleInput",
    "TagRuleVersionCreateInput",
    "MarketAutoClassificationService",
    "get_market_auto_classification_service",
    "TaggingRuleService",
    "get_tagging_rule_service",
]
