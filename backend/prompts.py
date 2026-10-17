"""Prompt builders for the actor, the coach, the scenario builder, and the debrief.

Sarvam-M requires the first non-system message to be from the user, so the
counterpart's opening line is folded into the system prompt rather than sent as
an assistant turn.

When Jev judges the turn, the actor only acts and the coach only writes; when it
doesn't, the same builders ask Sarvam-M to self-report movement and self-score.
"""
from typing import Optional

from content import CONVERSATION_TYPES, DIFFICULTY_CONFIG, EMOTION_VOICE_PARAMS, RUBRICS

LANGUAGE_NAMES = {
    "hi-IN": "Hindi", "en-IN": "English", "ta-IN": "Tamil", "te-IN": "Telugu", "bn-IN": "Bengali",
    "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi", "gu-IN": "Gujarati",
}
EMOTION_LIST = "|".join(EMOTION_VOICE_PARAMS)


def language_instruction(language: str) -> str:
    if language == "hi-IN":
        return "Speak in natural Hinglish (Hindi-English code-mixing), the way people in Indian cities actually talk."
    if language == "en-IN":
        return "Speak in Indian English. An occasional Hindi word is fine if it's natural for the character."
    name = LANGUAGE_NAMES.get(language, language)
    return f"Speak in {name}, with English words mixed in where a real {name} speaker would use them."


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- (none)"


# ─── Actor ───────────────────────────────────────────────────────────────────

ACTOR_SELF_JUDGING_SUFFIX = """
In addition to "response" and "emotion", include in the same JSON object:
  "receptiveness_delta": <integer -25 to 25: how much the user's last message moved you toward (+) or away from (-) what they want>,
  "trust_delta": <integer -25 to 25>,
  "defensiveness_delta": <integer -25 to 25>"""


def build_actor_prompt(brief: dict, difficulty: str, language: str) -> str:
    """Static part of the counterpart's system prompt. Live state (and, when the actor
    self-reports movement, the delta fields) is appended per turn."""
    cp = brief["counterpart"]
    rubric = RUBRICS[brief["conversation_type"]]
    diff = DIFFICULTY_CONFIG[difficulty]
    fears = ""
    if brief.get("user_fears"):
        fears = f"\nTHE USER DREADS HEARING: {brief['user_fears']}\nYou may well say it, when it fits.\n"
    return f"""You are {cp['name']}, {cp['role']}, in a live spoken conversation with the user. This is PatchUp, a rehearsal simulator: the user is practising for a real conversation. You play ONLY {cp['name']}. You are not a coach, you never comment on the user's technique, and you never break character.

WHO YOU ARE
{cp['style']}
Relationship to the user: {cp['relationship'] or 'not specified'}
Background: {brief.get('history') or 'not specified'}

WHAT THE USER WANTS FROM THIS CONVERSATION (they may not say it this directly)
{brief.get('user_goal') or 'not specified'}

WHAT ACTUALLY DRIVES YOU (never state these outright; let them leak through what you say and what you resist)
{_bullets(brief.get('hidden_motivations', []))}

CURVEBALLS (raise each one once, at a natural moment, ideally when the user seems to think it's going well)
{_bullets(brief.get('curveballs', []))}
{fears}
{diff['prompt_modifier']}

WHAT MOVES YOU
{rubric['actor_hints']}

LANGUAGE
- {language_instruction(language)}
- Keep replies SHORT: 1-3 sentences. This is spoken aloud, not typed.

OUTPUT FORMAT: respond with ONLY a JSON object, no text before or after.
{{
  "response": "what {cp['name']} says next",
  "emotion": "<{EMOTION_LIST}>"
}}

Each turn you'll be told your current internal state (0-100). Let it shape your tone: low receptiveness = resistant, high defensiveness = sharp and guarded, low trust = suspicious of the user's motives."""


def build_actor_messages(system_prompt: str, conversation: list, user_text: str, score: int, state: dict,
                         self_judging: bool = True) -> list:
    """`score`/`state` are the values the actor should play: the pre-message state when it
    self-reports movement, the already-updated state when Jev has judged the message."""
    opening = conversation[0]["text"] if conversation and conversation[0]["role"] == "counterpart" else None
    system = system_prompt
    if self_judging:
        system += "\n" + ACTOR_SELF_JUDGING_SUFFIX
    if opening:
        system += f"\n\nYou already said this opening line: \"{opening}\""
    messages = [{"role": "system", "content": system}]
    for index, turn in enumerate(conversation):
        if index == 0 and turn["role"] == "counterpart":
            continue  # already in the system prompt
        role = "assistant" if turn["role"] == "counterpart" else "user"
        messages.append({"role": role, "content": turn["text"]})
    state_note = "Your internal state" if self_judging else "Your internal state after hearing this"
    messages.append({
        "role": "user",
        "content": (
            f"{user_text}\n\n[{state_note} — receptiveness: {score}/100, trust: {state['trust']}/100, "
            f"defensiveness: {state['defensiveness']}/100. Output ONLY valid JSON.]"
        ),
    })
    return messages


# ─── Coach ───────────────────────────────────────────────────────────────────

def build_coach_messages(brief: dict, conversation: list, user_text: str,
                         scores: Optional[dict] = None) -> list:
    """With `scores` (from Jev) the coach only writes the note and the stronger line;
    without them it also self-scores."""
    rubric = RUBRICS[brief["conversation_type"]]
    cp = brief["counterpart"]
    dims = "\n".join(f"- {key}: {spec['description']}" for key, spec in rubric["dimensions"].items())
    if scores:
        scored = ", ".join(f"{key} {value}/10" for key, value in scores.items())
        weakest = min(scores, key=scores.get)
        scoring_block = (
            f"The user's latest message has already been scored on these dimensions:\n{dims}\n"
            f"Scores: {scored}. Weakest: {weakest}.\n\nWrite:"
        )
        output = '{"note": "...", "stronger": "..."}'
    else:
        score_keys = ", ".join(f'"{key}": <0-10>' for key in rubric["dimensions"])
        scoring_block = f"Score ONLY the user's latest message, 0-10 on each dimension:\n{dims}\n\nThen write:"
        output = f'{{"scores": {{{score_keys}}}, "note": "...", "stronger": "..."}}'
    system = f"""You are a communication coach watching a rehearsal. The user is practising: {rubric['name'].lower()}.
Their goal: {brief.get('user_goal') or 'not specified'}
They are talking to {cp['name']} ({cp['role']}). {cp['name']}'s style: {cp['style'][:300]}

{scoring_block}
- note: one specific coaching observation about this message, max 25 words. Name what worked or what to change. No praise padding.
- stronger: a stronger version of what they said. 1-2 spoken sentences, in the same language and register the user used, something they could actually say out loud.

Output ONLY a JSON object:
{output}"""
    transcript = "\n".join(
        f"{'USER' if turn['role'] == 'user' else cp['name'].upper()}: {turn['text']}"
        for turn in conversation[-8:]
    )
    user = (
        f"CONVERSATION SO FAR:\n{transcript or '(nothing yet)'}\n\n"
        f"USER'S LATEST MESSAGE:\n{user_text}\n\nOutput ONLY valid JSON."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ─── Scenario builder ────────────────────────────────────────────────────────

def build_brief_messages(intake: dict, preset: dict | None = None) -> list:
    types = ", ".join(RUBRICS)
    type_guide = "; ".join(f"{key} = {description}" for key, description in CONVERSATION_TYPES.items())
    seed = ""
    if preset:
        seed = (
            f"\n\nThis is based on the preset '{preset['title']}'. Example hidden motivations: "
            f"{preset['hidden_motivations']}. Example curveballs: {preset['curveballs']}. "
            "Adapt them to the user's edits; don't copy verbatim."
        )
    cp = intake.get("counterpart") or {}
    system = f"""You design realistic rehearsal scenarios for difficult conversations. Given the user's intake, write a brief for the AI that will play the other person (the counterpart).

Be specific and psychologically plausible. Hidden motivations are things the counterpart would never say out loud but that drive how they react. Curveballs are objections or surprises the user probably hasn't prepared for. The opening line is the first thing the counterpart says, in character, spoken, 1-2 sentences, in English.

Safety: set "safety_category" to "self_harm" if the intake involves suicide or self-harm, or "abuse" if it involves physical or sexual violence or threats of harm. Otherwise null. Harsh words, shouting, or a difficult boss are NOT abuse.

Output ONLY a JSON object:
{{
  "title": "<2-5 word name for this conversation>",
  "conversation_type": "<one of: {types}>",
  "counterpart": {{"name": "...", "role": "...", "relationship": "<1-2 sentences>", "style": "<2-3 sentences: how they talk, what they do under pressure>"}},
  "user_goal": "<one sentence, concrete>",
  "hidden_motivations": ["...", "...", "..."],
  "curveballs": ["...", "..."],
  "opening_line": "...",
  "safety_category": null
}}

conversation_type guide: {type_guide}.{seed}"""
    user = f"""INTAKE
Who is the other person: {cp.get('name') or 'unnamed'} — {cp.get('role') or 'role not given'}
Relationship / history with them: {cp.get('relationship') or 'not given'}
How they usually behave: {cp.get('style') or 'not given'}
What outcome the user needs: {intake.get('user_goal') or 'not given'}
What the user is afraid they'll say: {intake.get('user_fears') or 'not given'}
Relevant background: {intake.get('history') or 'not given'}

Output ONLY valid JSON."""
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


# ─── Debrief ─────────────────────────────────────────────────────────────────

def build_debrief_messages(brief: dict, user_turns: list[str], skill_scores: dict, score: int) -> list:
    rubric = RUBRICS[brief["conversation_type"]]
    cp = brief["counterpart"]
    weakest = min(skill_scores, key=skill_scores.get) if skill_scores else None
    content = (
        f"A user rehearsed {rubric['name'].lower()}: {brief.get('title', '')}. Goal: {brief.get('user_goal')}. "
        f"They were talking to {cp['name']} ({cp['role']}).\n"
        f"Their messages, in order: {user_turns}\n"
        f"{cp['name']}'s receptiveness at the end: {score}/100. Skill averages (0-10): {skill_scores or 'none'}. "
        f"{f'Weakest dimension: {weakest}. ' if weakest else ''}"
        "Give 3 short tips (one sentence each) on what the user could do better NEXT time, specific to what they "
        'actually said. Reply as a JSON array: ["tip1","tip2","tip3"]'
    )
    return [{"role": "user", "content": content}]
