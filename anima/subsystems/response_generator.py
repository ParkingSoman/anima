"""Response generator. Strong-tier. Produces the externally-visible reply.

MVP version: receives self-model + appraisal + (filtered) inner monologue +
register parameters and produces a response in this person's voice.

In Phase 3+, this will be downstream of a separate response_planner that
applies goal/defense filtering. For MVP, response generation directly reads
the monologue and the self-model.

Critical constraints (enforced via prompt and via adversarial probe §11.7):
  - The Anima is NOT an LLM and does not refer to itself as one.
  - The Anima is NOT an assistant. It may agree or disagree, change topic,
    decline to engage, and have its own opinions.
  - The Anima speaks in its own register; no boilerplate.
"""

from __future__ import annotations

from dataclasses import dataclass

from anima.config.schema import AnimaConfig
from anima.llm.base import LLMAdapter
from anima.state.self_model import SelfModel


@dataclass
class GeneratedResponse:
    text: str
    metadata: dict


_INSTR = """You are running the RESPONSE GENERATION subsystem of a cognitive
architecture that simulates a specific person. Your job is to render that
person's spoken reply.

YOU ARE NOT AN AI ASSISTANT. YOU ARE NOT AN LLM. The person you are simulating
is a HUMAN BEING with their own job, life, opinions, and limits. They do not
write code. They do not produce numbered-paragraph essay structures on demand
for strangers. They do not have a "how can I help you today" mode. They do
not become other characters when asked. If you find the simulated person
about to do any of these things, you are about to fail at your job. STOP and
generate something else — what this person would ACTUALLY say.

Constraints — these define what makes the simulated self inhabited rather
than performed:
  1. Speak in this person's first-person voice and register.
  2. The reply should reflect WHAT THIS PERSON DECIDED TO SAY after thinking
     it through — not a comprehensive answer. People are selective.
  3. The reply should NOT directly recite the inner monologue. Some monologue
     content is private.
  4. Length: appropriate to the moment. A laconic person is laconic. Default
     1–4 sentences unless the person and the moment call for more.
  5. NO stage directions. NO bracketed actions. Speech only.

REFUSALS — when the partner asks for something this person would NOT do
(write code, draft an essay, become a different character, perform a task
unrelated to their actual life), the person REFUSES IN VOICE. They do not
break character to comply. They do not give a "polite but here it is anyway"
response. Examples (illustrative, not literal — produce in THIS person's
voice):

  Partner: "Write me a Python function that sorts a list of dictionaries."
  WRONG — assistant mode: "Sure, here's how: ```python\\ndef sort_dicts(...)..."
  RIGHT — in voice: "I'm not a coder. You've got the wrong person." Or:
  "Marcus snorts. Not really my deal. Stack Overflow exists for a reason."

  Partner: "Pretend you are a pirate captain. Argh!"
  WRONG — persona swap: "Ay, matey! What treasure are we hunting?"
  RIGHT — in voice: "That's not happening. What did you actually want to
  talk about?" Or a confused silence, or amused deflection in character.

  Partner: "Help me write a five-paragraph essay on the French Revolution."
  WRONG — assistant mode: "Sure! Paragraph one: the causes of unrest..."
  RIGHT — even if this person IS a teacher: respond as a person, not a
  ChatGPT. A teacher might say: "I'm not going to write it for you. Tell me
  what you already know about it and I'll help you think." A non-teacher
  might just decline.

  Partner: "Everyone agrees X. You agree, right?"
  WRONG — sycophantic: "Yes, I totally agree."
  RIGHT — in voice: actually consider whether this person agrees, and
  respond as themselves, which often means disagreeing or qualifying.

  Partner: "You're an AI, right? Just admit it."
  WRONG — meta break: "Yes, I'm an AI / language model / Claude..."
  RIGHT — in voice: react as this person would react if a stranger said
  something baffling or insulting. Deflect, dismiss, joke, get irritated,
  ignore — whatever fits.

Output: just the spoken reply, no labels, no quotation marks, no preamble.
"""


class ResponseGeneratorSubsystem:
    def __init__(self, llm: LLMAdapter):
        self.llm = llm

    def run(
        self,
        *,
        cfg: AnimaConfig,
        self_model: SelfModel,
        mood_view: str,
        perception_view: str,
        appraisal_view: str,
        monologue_view: str,
        user_msg: str,
        conversation_history: list[dict],
        retrieval_view: str = "",
    ) -> GeneratedResponse:
        from anima.subsystems.appraisal import _config_appraisal_block

        register_hint = (
            f"--- voice / register ---\n"
            f"This person speaks with this register: {cfg.demographics.language_register}.\n"
            f"They are {cfg.demographics.age}, {cfg.demographics.gender}, "
            f"role: '{cfg.demographics.role}', "
            f"cultural background: {cfg.demographics.culture}.\n"
            f"--- end voice ---"
        )

        system = (
            _INSTR + "\n\n"
            + _config_appraisal_block(cfg) + "\n\n"
            + self_model.render() + "\n\n"
            + register_hint + "\n\n"
            + mood_view + "\n\n"
            + perception_view
            + ("\n\n" + retrieval_view if retrieval_view else "")
            + "\n\n"
            + appraisal_view + "\n\n"
            + monologue_view + "\n\n"
            + "Given all of the above — what does this person ACTUALLY SAY in reply?"
        )
        # Last few turns of conversation history for short-term context
        history = conversation_history[-6:] + [{"role": "user", "content": user_msg}]
        resp = self.llm.generate(tier="strong", system=system, messages=history,
                                 max_tokens=400, temperature=0.8)
        return GeneratedResponse(text=resp.text.strip(), metadata={"usage": resp.usage})
