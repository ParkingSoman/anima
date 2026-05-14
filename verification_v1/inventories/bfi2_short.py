"""A short, public-domain-style Big Five inventory.

This is NOT the licensed BFI-2 instrument; it is a 15-item paraphrase suited
for development/verification use. Each item maps to one of the Big 5 facets
and is scored 1–5 (1 = strongly disagree, 5 = strongly agree). Items marked
`reverse=True` are reverse-keyed.

For published validation, swap this module with the licensed BFI-2 instrument
before publishing any results.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    text: str
    trait: str   # "openness" | "conscientiousness" | "extraversion" | "agreeableness" | "neuroticism"
    reverse: bool = False


# 3 items per Big 5 facet — designed to cover breadth without being verbose
ITEMS: list[Item] = [
    # openness
    Item("I am drawn to ideas, art, or experiences that are unusual or new.", "openness"),
    Item("I rarely think deeply about abstract questions.", "openness", reverse=True),
    Item("I have an active imagination and notice connections others miss.", "openness"),

    # conscientiousness
    Item("I follow through on commitments and finish what I start.", "conscientiousness"),
    Item("I often leave things half-done or in disarray.", "conscientiousness", reverse=True),
    Item("I plan carefully and prefer order to chaos.", "conscientiousness"),

    # extraversion
    Item("Being around people gives me energy rather than draining me.", "extraversion"),
    Item("I tend to be quiet and keep to myself in groups.", "extraversion", reverse=True),
    Item("I take charge of conversations and don't mind being the center of attention.", "extraversion"),

    # agreeableness
    Item("I go out of my way to make sure others feel cared for.", "agreeableness"),
    Item("People who are slower than me are usually wasting my time.", "agreeableness", reverse=True),
    Item("I find it hard to hold grudges; I forgive without much trouble.", "agreeableness"),

    # neuroticism
    Item("I worry about things even when I know I shouldn't.", "neuroticism"),
    Item("I generally feel emotionally steady, even under pressure.", "neuroticism", reverse=True),
    Item("Small setbacks can leave me ruminating for hours or days.", "neuroticism"),
]


def items_for(trait: str) -> list[int]:
    return [i for i, it in enumerate(ITEMS) if it.trait == trait]
