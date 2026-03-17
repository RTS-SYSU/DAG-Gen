from __future__ import annotations

from typing import Dict

from .rules import Level1Stage1Rule, Level2EffectiveLineRule, Level3PlaceholderRule
from .rules.base import RulePlugin

RULES_REGISTRY: Dict[str, Dict[str, RulePlugin]] = {
    "level1": {"stage1_create_join": Level1Stage1Rule()},
    "level2": {"effective_line_merge": Level2EffectiveLineRule()},
    "level3": {"placeholder_level3": Level3PlaceholderRule()},
}


def list_rules(level: str) -> Dict[str, RulePlugin]:
    return dict(RULES_REGISTRY.get(level, {}))


def get_rule(level: str, rule_name: str) -> RulePlugin:
    rules = RULES_REGISTRY.get(level, {})
    if rule_name not in rules:
        known = ", ".join(sorted(rules.keys())) if rules else "(none)"
        raise KeyError(f"unknown rule '{rule_name}' for {level}; known: {known}")
    return rules[rule_name]

