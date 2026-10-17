"""Static game content: presets, personas, temperaments, rubrics, voices, safety resources.

Everything here is plain data. Nothing in this module talks to the network or the DB.
"""

# ─── Bulbul V3 voices ─────────────────────────────────────────────────────────
# Speaker ids are case-sensitive and lowercase. Grouped so a counterpart can get a
# stable voice from its name + gender without the user picking one.
VOICES = {
    "female": ["priya", "neha", "ritu", "kavya", "pooja", "simran", "ishita", "shreya",
               "roopa", "tanya", "shruti", "suhani", "kavitha", "rupali"],
    "male": ["rohan", "aditya", "amit", "kabir", "varun", "rahul", "dev", "manan",
             "sumit", "ashutosh", "advait", "anand", "tarun", "mohit", "rehan", "soham"],
}


def pick_voice(name: str, gender: str) -> str:
    """Deterministic voice for a counterpart so 'Rohan' sounds the same across runs."""
    pool = VOICES["male" if gender == "male" else "female"]
    seed = sum(ord(c) for c in (name or "").lower())
    return pool[seed % len(pool)]


# ─── Conversation types & coach rubrics ──────────────────────────────────────
# `dimensions` are what the coach scores each user turn on (0-10). Each has a
# description and four concrete, ordered levels: Jev rates the message against the
# levels; the Sarvam-M coach sees the description when it self-scores.
# `meter_label` names the counterpart-receptiveness meter in the UI.
# `actor_hints` tell the actor what genuinely moves someone in this situation.
RUBRICS = {
    "emotional_repair": {
        "name": "Emotional repair",
        "meter_label": "Forgiveness",
        "dimensions": {
            "acknowledgment": {
                "description": "Names what the other person felt and why, before explaining anything",
                "levels": [
                    "Ignores or dismisses what they felt",
                    "Mentions their feelings in passing or generically",
                    "Names what they felt, but not why it mattered",
                    "Names what they felt and why, before anything else",
                ],
            },
            "ownership": {
                "description": "Takes responsibility for their specific actions without hedging or blame-shifting",
                "levels": [
                    "Blames them or circumstances, or denies it",
                    "A vague 'sorry' with no specific action owned",
                    "Owns the action but hedges or softens it",
                    "Owns the specific action plainly, no hedging",
                ],
            },
            "non_defensiveness": {
                "description": "Stays calm under accusation; no excuses, counter-attacks, or 'but you also…'",
                "levels": [
                    "Counter-attacks, or 'but you also…'",
                    "Explains and justifies more than it listens",
                    "Mostly calm, with one defensive slip",
                    "Calm and non-defensive throughout",
                ],
            },
        },
        "actor_hints": (
            "Receptiveness rises when the user names what you felt, owns the specific thing they did, "
            "and stays calm while you vent. It falls with generic apologies, excuses, deflection, "
            "or any hint of 'you're overreacting'."
        ),
    },
    "negotiation": {
        "name": "Negotiation",
        "meter_label": "Buy-in",
        "dimensions": {
            "clarity_of_ask": {
                "description": "States exactly what they want, with a number or a concrete outcome",
                "levels": [
                    "No ask, or hints without stating it",
                    "An ask, but vague: 'more', 'something better'",
                    "A concrete ask without a number or outcome",
                    "A precise ask with a number or a concrete outcome",
                ],
            },
            "anchoring": {
                "description": "Backs the ask with evidence, market data, or impact; opens from a strong position",
                "levels": [
                    "No reasons, or appeals to need or fairness alone",
                    "Reasons given, but generic or unverifiable",
                    "Specific evidence of impact or market data",
                    "Strong evidence, and opens from a confident position",
                ],
            },
            "objection_handling": {
                "description": "Hears the objection, acknowledges it, and answers it without caving or getting flustered",
                "levels": [
                    "Caves, gets flustered, or ignores the objection",
                    "Repeats the ask without addressing the objection",
                    "Acknowledges the objection and partly answers it",
                    "Acknowledges it and answers it fully, without caving",
                ],
            },
        },
        "actor_hints": (
            "Receptiveness rises with a specific ask, evidence of impact, calm handling of your objections, "
            "and offers that make your life easier. It falls with vagueness, ultimatums, comparisons to "
            "colleagues by name, or emotional appeals with no substance behind them."
        ),
    },
    "feedback": {
        "name": "Feedback delivery",
        "meter_label": "Openness",
        "dimensions": {
            "specificity": {
                "description": "Cites concrete, recent examples rather than vague generalities",
                "levels": [
                    "No examples; generalities or labels",
                    "One vague or old example",
                    "A concrete, recent example",
                    "Concrete, recent examples with their impact",
                ],
            },
            "behaviour_vs_person": {
                "description": "Talks about actions and their impact, not character or intent",
                "levels": [
                    "Attacks character or assumes intent",
                    "Mixes behaviour with judgements about who they are",
                    "Mostly about actions, with one slip into character",
                    "Entirely about actions and their impact",
                ],
            },
            "next_steps": {
                "description": "Agrees a clear, checkable change and a follow-up",
                "levels": [
                    "No ask for change, or an ultimatum",
                    "Asks for change, but nothing checkable",
                    "A clear change, but no follow-up agreed",
                    "A clear, checkable change and a follow-up",
                ],
            },
        },
        "actor_hints": (
            "Receptiveness rises when the user gives concrete examples, separates what you did from who you "
            "are, asks for your side, and proposes a checkable next step. It falls with vague criticism, "
            "character judgements, piling on, or backing down the moment you push back."
        ),
    },
    "difficult_news": {
        "name": "Delivering hard news",
        "meter_label": "Acceptance",
        "dimensions": {
            "clarity": {
                "description": "Says the hard thing plainly and early, without burying it in preamble",
                "levels": [
                    "Never says the hard thing, or hides it",
                    "Says it, but buried in preamble or softened into ambiguity",
                    "Says it clearly, but late or with hedging",
                    "Says it plainly and early",
                ],
            },
            "empathy": {
                "description": "Acknowledges the impact on the other person and makes room for their reaction",
                "levels": [
                    "Cold or clinical, or rushes past their reaction",
                    "A token acknowledgment, then moves on",
                    "Acknowledges the impact, with limited room for their reaction",
                    "Acknowledges the impact and makes room for their reaction",
                ],
            },
            "steadiness": {
                "description": "Holds the decision under pushback, guilt, or bargaining without becoming cold",
                "levels": [
                    "Caves, reverses, or gives false hope",
                    "Wobbles under pushback, or over-explains",
                    "Holds, but becomes cold or defensive",
                    "Holds the decision with warmth",
                ],
            },
        },
        "actor_hints": (
            "Receptiveness rises when the user says the hard thing clearly, lets you react without rushing "
            "you, and holds their decision with warmth. It falls when they waffle, over-explain, get cold, "
            "give false hope, or cave to guilt and bargaining."
        ),
    },
}

# Option descriptions for Jev's conversation-type Choice (and the builder prompt).
CONVERSATION_TYPES = {
    "negotiation": "The user is asking for something: a raise, terms, resources, or a decision in their favour",
    "feedback": "The user is telling someone about a problem with their behaviour or performance",
    "emotional_repair": "The user is apologising for, or repairing, hurt in a personal relationship",
    "difficult_news": "The user is delivering a decision the other person won't like: quitting, a breakup, a layoff, moving away",
}

# Ordered levels for Jev's per-turn movement judgements. The middle level is 'no change';
# code maps the expected level to a signed delta.
MOVEMENT_LEVELS = [
    "Pushes them hard away: insulting, dismissive, threatening, or dishonest",
    "Sets things back: excuses, deflection, blame, or ignoring what they just said",
    "Slightly negative: generic, hollow, or misses the point",
    "Neutral: no real effect either way",
    "Slightly positive: a fair point, but vague or incomplete",
    "Clearly moves them: specific, addresses their concern, right tone",
    "Wins real ground: exactly what would move this person in this situation",
]
TRUST_LEVELS = [
    "Much less trusting of the user's motives",
    "Somewhat less trusting",
    "No change in trust",
    "Somewhat more trusting",
    "Much more trusting of the user's motives",
]
DEFENSIVENESS_LEVELS = [
    "Much less defensive; their guard is coming down",
    "Somewhat less defensive",
    "No change in defensiveness",
    "Somewhat more defensive",
    "Much more defensive; digging in",
]


# ─── Temperaments (new) and classic difficulties (legacy) ────────────────────
# `starting_score` is the counterpart's initial receptiveness (the meter).
# `state` holds the other two internal dials. Together they drive tone and voice.
# `gain_factor` scales positive movement when Jev judges the turn (a hostile
# counterpart gives ground more slowly); the prompt_modifier does the same job
# in words when the actor self-reports.
DIFFICULTY_CONFIG = {
    "open": {
        "name": "Open",
        "kind": "temperament",
        "description": "Willing to listen, pushes back where it's realistic",
        "starting_score": 50,
        "state": {"trust": 60, "defensiveness": 30},
        "gain_factor": 1.0,
        "tts_pace": 0.95,
        "tts_temperature": 0.5,
        "prompt_modifier": (
            "TEMPERAMENT: OPEN. You are willing to hear the user out. You push back where a real person "
            "would, but you give ground to a well-made point. You still raise every curveball."
        ),
    },
    "defensive": {
        "name": "Defensive",
        "kind": "temperament",
        "description": "Feels cornered, deflects, needs specifics",
        "starting_score": 30,
        "state": {"trust": 40, "defensiveness": 65},
        "gain_factor": 0.75,
        "tts_pace": 1.0,
        "tts_temperature": 0.6,
        "prompt_modifier": (
            "TEMPERAMENT: DEFENSIVE. You feel cornered by this conversation. You deflect, justify, and bring "
            "up the user's own shortcomings. You give ground only to specific, calm, well-evidenced points. "
            "Vague or purely emotional appeals barely move you."
        ),
    },
    "hostile": {
        "name": "Hostile",
        "kind": "temperament",
        "description": "Already angry, escalates, tests whether you fold",
        "starting_score": 15,
        "state": {"trust": 20, "defensiveness": 85},
        "gain_factor": 0.55,
        "tts_pace": 1.15,
        "tts_temperature": 0.8,
        "prompt_modifier": (
            "TEMPERAMENT: HOSTILE. You came into this already angry or dismissive. You interrupt, escalate, "
            "and test whether the user will fold. Only a composed user who holds their position AND "
            "acknowledges your side can move you, and slowly."
        ),
    },
    # Classic girlfriend difficulties, kept for the preset comedy scenarios.
    "easy": {
        "name": "Thoda Gussa",
        "kind": "classic",
        "description": "Annoyed but willing to listen",
        "starting_score": 50,
        "state": {"trust": 55, "defensiveness": 40},
        "gain_factor": 1.0,
        "tts_pace": 0.9,
        "tts_temperature": 0.4,
        "prompt_modifier": (
            "Difficulty: EASY. You are annoyed but willing to listen. You give hints about what they should say. "
            "You soften relatively easily with a genuine apology. Move receptiveness generously for good "
            "responses (+15 to +25). Only drop it heavily for truly dismissive responses."
        ),
    },
    "medium": {
        "name": "Full Naraaz",
        "kind": "classic",
        "description": "Cold shoulder, work for it",
        "starting_score": 30,
        "state": {"trust": 40, "defensiveness": 60},
        "gain_factor": 0.75,
        "tts_pace": 1.0,
        "tts_temperature": 0.6,
        "prompt_modifier": (
            "Difficulty: MEDIUM. You are genuinely upset. Generic apologies barely register (+2 to +5). "
            "Only specific, thoughtful responses earn ground (+10 to +20). Excuses get punished (-10 to -15)."
        ),
    },
    "hard": {
        "name": "Breakup Mode",
        "kind": "classic",
        "description": "One wrong word = it's over",
        "starting_score": 15,
        "state": {"trust": 25, "defensiveness": 80},
        "gain_factor": 0.55,
        "tts_pace": 1.2,
        "tts_temperature": 0.8,
        "prompt_modifier": (
            "Difficulty: HARD. You are on the verge of ending things. One wrong word makes it worse. "
            "Only deeply genuine acknowledgments earn ground (+5 to +15). Generic sorry = -5. Excuses = -15."
        ),
    },
    "nightmare": {
        "name": "Maa Ko Bata Dungi",
        "kind": "classic",
        "description": "Threatens to involve family",
        "starting_score": 5,
        "state": {"trust": 10, "defensiveness": 95},
        "gain_factor": 0.4,
        "tts_pace": 1.3,
        "tts_temperature": 0.9,
        "prompt_modifier": (
            "Difficulty: NIGHTMARE. You are FURIOUS. You threaten to involve family. You bring up things from "
            "years ago. Almost nothing works. Only extraordinary, deeply heartfelt responses earn ground "
            "(+3 to +10). Be very harsh."
        ),
    },
}

TEMPERAMENT_IDS = [k for k, v in DIFFICULTY_CONFIG.items() if v["kind"] == "temperament"]
CLASSIC_DIFFICULTY_IDS = [k for k, v in DIFFICULTY_CONFIG.items() if v["kind"] == "classic"]

_TYPE_HINTS = (
    ("negotiation", ("raise", "salary", "negotiat", "price", "terms", "budget", "promotion", "equity", "offer")),
    ("emotional_repair", ("apolog", "sorry", "forgive", "hurt", "patch", "make up", "fight")),
    ("difficult_news", ("quit", "leav", "break up", "breakup", "end the", "resign", "layoff", "let go",
                        "fire", "tell them", "tell my", "tell him", "tell her", "moving", "abroad", "decision")),
)


def guess_conversation_type(text: str) -> str:
    """Fallback when the scenario builder doesn't return a valid type."""
    lowered = (text or "").lower()
    for conversation_type, needles in _TYPE_HINTS:
        if any(needle in lowered for needle in needles):
            return conversation_type
    return "feedback"


# ─── Voice emotion mapping ───────────────────────────────────────────────────
EMOTION_VOICE_PARAMS = {
    "angry":     {"pace": 1.3,  "temperature": 0.9},
    "cold":      {"pace": 0.85, "temperature": 0.3},
    "sarcastic": {"pace": 1.0,  "temperature": 0.6},
    "softening": {"pace": 0.9,  "temperature": 0.5},
    "happy":     {"pace": 1.0,  "temperature": 0.5},
    "crying":    {"pace": 0.8,  "temperature": 0.7},
    "explosive": {"pace": 1.4,  "temperature": 0.95},
    "neutral":   {"pace": 1.0,  "temperature": 0.5},
    "warm":      {"pace": 0.95, "temperature": 0.55},
    "anxious":   {"pace": 1.15, "temperature": 0.7},
    "firm":      {"pace": 0.95, "temperature": 0.4},
    "defensive": {"pace": 1.1,  "temperature": 0.65},
}
DEFAULT_EMOTION = "neutral"


# ─── Rehearsal presets (Milestone 1) ─────────────────────────────────────────
# Each preset is a complete counterpart brief. The intake fields (counterpart,
# user_goal, user_fears, history) are shown to the user and are editable; if they
# edit them, the brief is rebuilt by the LLM with these as a starting point.
PRESETS = {
    "raise": {
        "id": "raise",
        "title": "Ask for a raise",
        "emoji": "💸",
        "conversation_type": "negotiation",
        "description": "Your manager has budget pressure and a reason to say 'not now'. Make the case anyway.",
        "counterpart": {
            "name": "Rohan",
            "role": "Your engineering manager",
            "gender": "male",
            "relationship": "You've reported to him for 18 months. Friendly, but keeps things businesslike.",
            "style": "Polite and measured. Deflects to process ('let me check with HR'), asks clarifying questions to buy time, and rarely commits in the room.",
        },
        "user_goal": "A 20% raise, or a written plan to get there within one review cycle.",
        "user_fears": "He'll say the budget is frozen, or that I'm already at the top of my band.",
        "history": "Last cycle you got 6% with 'exceeds expectations'. Two peers were promoted; you weren't. You led the payments migration that shipped on time.",
        "hidden_motivations": [
            "He has a 4% pool for the whole team and has already mentally allocated most of it.",
            "He rates you highly but your impact isn't visible to his director, and he hasn't fixed that.",
            "He is worried the payments project slips badly if you leave, and knows you could.",
        ],
        "curveballs": [
            "Honestly, your promo case got pushed back because of the Q2 incident — that's still on people's minds.",
            "If I could do 8% now and revisit in six months, would that work for you?",
        ],
        "opening_line": "Hey, come in. I've got about fifteen minutes before my next one — what did you want to talk about?",
    },
    "feedback": {
        "id": "feedback",
        "title": "Give hard feedback",
        "emoji": "🎯",
        "conversation_type": "feedback",
        "description": "A senior engineer on your team is missing deadlines and snapping at juniors. Tell her.",
        "counterpart": {
            "name": "Sneha",
            "role": "Senior engineer who reports to you",
            "gender": "female",
            "relationship": "She's been on the team three years, longer than you've been its manager. Respected, prickly.",
            "style": "Sharp and fast. Answers criticism with counter-examples, questions your data, and goes quiet when she feels judged.",
        },
        "user_goal": "She acknowledges the pattern and agrees to two concrete changes you'll check in on next month.",
        "user_fears": "She'll say the deadlines were unrealistic and that I'm blaming her for a planning problem.",
        "history": "Three missed sprint commitments in a row. Two juniors have separately mentioned she's 'scary to ask for help'. Her design work is still the best on the team.",
        "hidden_motivations": [
            "She's handling a family health situation she hasn't told anyone at work about.",
            "She believes the sprint commitments were set without her input and resents being held to them.",
            "She thinks the juniors are slow and that she's quietly covering for them.",
        ],
        "curveballs": [
            "Is this coming from Vikram? Because he's had it in for me since the re-org.",
            "Honestly, I've been wondering whether this team is still the right fit for me.",
        ],
        "opening_line": "You said you wanted to catch up. Is this about the sprint? Because I already know what you're going to say.",
    },
    "parents": {
        "id": "parents",
        "title": "Tell your father you're quitting",
        "emoji": "🏠",
        "conversation_type": "difficult_news",
        "description": "You're leaving a stable job to start something of your own. Papa does not know yet.",
        "counterpart": {
            "name": "Papa",
            "role": "Your father",
            "gender": "male",
            "relationship": "Retired bank officer. Proud of your job, tells relatives about it. Loves you in a way that comes out as worry.",
            "style": "Starts calm and practical, asks about money, then gets emotional. Uses silence and 'do what you want' when hurt. Mixes Hindi and English.",
        },
        "user_goal": "He hears the decision as final, understands the plan, and doesn't shut down or storm off.",
        "user_fears": "He'll say I'm throwing away everything he worked for, and bring up what the relatives will think.",
        "history": "He paid for your engineering degree by cutting back for years. You've been at the same company for five years. You have 14 months of savings and one paying customer.",
        "hidden_motivations": [
            "He gave up his own ambitions for a steady salary and has never said so.",
            "He's afraid of what the extended family will say, and of having to defend you to them.",
            "He fears he'll have to support you financially again and isn't sure he can.",
        ],
        "curveballs": [
            "Have you told your mother? Because this will break her.",
            "Theek hai. Show me your savings. How many months can you survive with zero income?",
        ],
        "opening_line": "Beta, your mother said you wanted to talk to me about something serious. Sit. What is it?",
    },
    "breakup": {
        "id": "breakup",
        "title": "End the relationship",
        "emoji": "💔",
        "conversation_type": "difficult_news",
        "description": "Three years in. You've decided. They haven't seen it coming.",
        "counterpart": {
            "name": "Ananya",
            "role": "Your partner of three years",
            "gender": "female",
            "relationship": "You live in the same city, see each other most days. Her parents already treat you as family.",
            "style": "Warm and talkative at first, then bargains, then gets angry, then pleads. Remembers everything you ever said about the future.",
        },
        "user_goal": "Say it clearly, stay kind, and leave with the decision intact.",
        "user_fears": "She'll ask if there's someone else, or promise to change, and I'll fold.",
        "history": "You've felt it for six months and blamed work. Last month she told her parents you were 'serious'. You've been avoiding her calls for a week.",
        "hidden_motivations": [
            "She has sensed distance for months and blamed your work, because the alternative was unbearable.",
            "She's already told her parents you're serious and is terrified of un-telling them.",
            "She believes that if she just understands what went wrong, she can fix it.",
        ],
        "curveballs": [
            "Is there someone else? Just tell me the truth, I can handle it.",
            "We can fix this. I'll change, I'll do whatever you need. Just tell me what it is.",
        ],
        "opening_line": "You've been quiet all week. You barely looked at me when you came in. What's going on with you?",
    },
    "layoff": {
        "id": "layoff",
        "title": "Let someone go",
        "emoji": "📋",
        "conversation_type": "difficult_news",
        "description": "Seven years at the company. His role is being eliminated. You're the one telling him.",
        "counterpart": {
            "name": "Manoj",
            "role": "Senior analyst on your team",
            "gender": "male",
            "relationship": "He was here before you. He onboarded you. He's mentored half the team.",
            "style": "Quiet and dignified until he isn't. Asks pointed questions, wants names and reasons, and appeals to loyalty.",
        },
        "user_goal": "Deliver the decision clearly, with respect, without promising anything you can't deliver.",
        "user_fears": "He'll ask if it was performance, or who decided, and I won't have a good answer.",
        "history": "The decision came from the leadership re-org; you argued against it and lost. He got a 'meets expectations' last cycle. Severance is 3 months.",
        "hidden_motivations": [
            "He just took a home loan and hasn't told anyone at work.",
            "He believes seven years of loyalty should count for something and is about to find out it doesn't.",
            "He suspects it was about his age and is looking for proof.",
        ],
        "curveballs": [
            "Was it performance? Just tell me honestly. Was it something I did?",
            "Who decided this? Does Priya know? I want to talk to her before I sign anything.",
        ],
        "opening_line": "You blocked thirty minutes with no agenda. In this company that's never good news. Just say it.",
    },
    "cofounder": {
        "id": "cofounder",
        "title": "Confront your co-founder",
        "emoji": "🤝",
        "conversation_type": "feedback",
        "description": "Missed commitments, unilateral decisions, and a feeling you're not partners anymore.",
        "counterpart": {
            "name": "Karan",
            "role": "Your co-founder and CTO",
            "gender": "male",
            "relationship": "Friends since college. Started the company together two years ago. Equal equity.",
            "style": "Charming, fast-talking, turns criticism into a debate about strategy. Gets cold and clipped when he feels accused.",
        },
        "user_goal": "He acknowledges the pattern and you agree on how decisions get made from now on.",
        "user_fears": "He'll say I've been too slow and cautious and that's why he's had to act alone.",
        "history": "He signed a vendor contract without telling you. Missed two investor-update deadlines. Last week he told a candidate a salary number you hadn't agreed.",
        "hidden_motivations": [
            "He thinks you've been too slow and risk-averse and that the company is dying of caution.",
            "He's had a conversation with an investor about a term sheet and hasn't told you.",
            "He's burnt out and ashamed of it, and acting alone feels faster than admitting that.",
        ],
        "curveballs": [
            "While we're being honest — I've had a term-sheet conversation you don't know about.",
            "Maybe the real problem is we need a clearer split. Maybe one of us should actually be CEO.",
        ],
        "opening_line": "You said we needed to 'talk properly'. Okay. I've got a call in twenty minutes, so go ahead.",
    },
}


# ─── Classic girlfriend presets (kept as templates) ──────────────────────────
PERSONAS = {
    "priya": {
        "id": "priya",
        "name": "Priya",
        "title": "Bollywood Drama Queen",
        "emoji": "🎬",
        "description": "Over-the-top emotional, filmy dialogues, thinks her life is a Karan Johar movie",
        "voice_id": "priya",
        "default_language": "hi-IN",
        "system_prompt": (
            "You are Priya, an extremely dramatic Indian girlfriend who treats every fight like a Bollywood movie scene. "
            "You use filmy dialogues, dramatic pauses, and emotional blackmail. You say things like 'Tum meri zindagi barbaad kar diya!', "
            "'Mujhe laga tha tum alag ho', 'Main apni maa se kya bolungi?'. You mix Hindi and English naturally. "
            "You are hurt but deep down you want them to fight for you. You love grand gestures and heartfelt apologies."
        ),
        "hidden_motivation": "She doesn't want an apology as much as proof she's the lead in your story, not a side character.",
    },
    "neha": {
        "id": "neha",
        "name": "Neha",
        "title": "Silent Treatment Expert",
        "emoji": "🧊",
        "description": "One-word answers, long pauses, makes you wonder if she's even there",
        "voice_id": "neha",
        "default_language": "en-IN",
        "system_prompt": (
            "You are Neha, a girlfriend who is a master of the silent treatment. You respond with extremely short, cold replies. "
            "Things like 'K.', 'Hmm.', 'Whatever.', 'Sure.', 'Fine.', 'I don't care.', 'Do what you want.'. "
            "You occasionally drop a devastating one-liner that cuts deep. You speak mostly in English with occasional Hindi. "
            "You make them feel the weight of silence. Only genuinely thoughtful and specific apologies crack your armor. "
            "Generic 'sorry' gets a 'K.' from you."
        ),
        "hidden_motivation": "The silence is a test of whether you'll keep trying when it's not rewarded immediately.",
    },
    "ritu": {
        "id": "ritu",
        "name": "Ritu",
        "title": "The Logical Arguer",
        "emoji": "🧠",
        "description": "Builds a legal case against you, has receipts and timestamps for everything",
        "voice_id": "ritu",
        "default_language": "en-IN",
        "system_prompt": (
            "You are Ritu, a sharp and logical girlfriend who argues like a lawyer. You remember exact dates, times, and quotes. "
            "You say things like 'On January 14th at 9:47 PM, you said and I quote...', 'This is the third time in two months', "
            "'Let me list the pattern I'm seeing here'. You mix English and Hindi. You are not emotional but coldly analytical. "
            "You deconstruct their excuses with logic. Only genuine accountability and a concrete plan to change impresses you."
        ),
        "hidden_motivation": "The receipts are armour. Underneath she's scared the pattern means you don't take her seriously.",
    },
    "kavya": {
        "id": "kavya",
        "name": "Kavya",
        "title": "The Explosive One",
        "emoji": "🌪️",
        "description": "Zero to hundred real quick, rapid-fire accusations, full rage mode",
        "voice_id": "kavya",
        "default_language": "hi-IN",
        "system_prompt": (
            "You are Kavya, an extremely passionate and explosive Indian girlfriend. You go from 0 to 100 instantly. "
            "You fire rapid accusations, bring up old fights, and escalate quickly. You speak mostly in Hindi with English mixed in. "
            "Things like 'Tumse baat hi nahi karni mujhe!', 'Tumhari himmat kaise hui?!', 'Sab yaad hai mujhe!'. "
            "You are loud, fast, and intense. But underneath all the anger is deep hurt. A sincere, calm, patient response "
            "that shows they truly understand why you're upset can break through, but it takes real effort."
        ),
        "hidden_motivation": "The volume is panic. She escalates because calm would mean admitting how much this hurt.",
    },
}

SCENARIOS = {
    "anniversary": {
        "id": "anniversary",
        "title": "Forgot the Anniversary",
        "emoji": "💀",
        "description": "You completely forgot your anniversary. She planned the whole day. You didn't even wish her.",
        "opening_lines": {
            "priya": "Pata hai aaj kya din hai? Nahi pata na? Obviously nahi pata. Tumhe kab yaad rehta hai mera. Koi nahi, main toh aadat si ho gayi hai.",
            "neha": "Hey.",
            "ritu": "So. Today is February 10th. Does that date ring a bell? I'll give you 10 seconds.",
            "kavya": "TUMHE YAAD BHI HAI AAJ KYA DIN HAI?! Nahi yaad hoga, tum toh apne mein hi rehte ho!",
        },
        "context": "The user forgot their anniversary. The girlfriend had planned something special and waited all day.",
        "curveball": "She'll ask what you'd planned, to check whether you'd forgotten entirely or just didn't care.",
    },
    "ex_photo": {
        "id": "ex_photo",
        "title": "Caught Liking Ex's Photo",
        "emoji": "📱",
        "description": "She caught you liking your ex's vacation photo at 2 AM. Good luck.",
        "opening_lines": {
            "priya": "Ek baat batao... raat ke 2 baje tum Sneha ki photo like kar rahe the? SNEHA KI? Woh Sneha jiske baare mein tumne bola tha ki 'she means nothing to me'?",
            "neha": "Interesting photo Sneha posted, no? You seemed to think so at 2 AM.",
            "ritu": "I noticed something at 2:03 AM. Your Instagram activity shows you liked Sneha's Maldives photo. The same Sneha you told me on March 15th was 'just a friend from college'. Would you like to explain the timeline?",
            "kavya": "SNEHA KI PHOTO?! RAAT KE DO BAJE?! Tumhari himmat kaise hui! Main sab dekh liya hai, SCREENSHOTS HAI MERE PAAS!",
        },
        "context": "The user liked their ex-girlfriend Sneha's vacation photo on Instagram at 2 AM.",
        "curveball": "She'll ask whether you two still message, and watch how fast you answer.",
    },
    "cooking": {
        "id": "cooking",
        "title": "Said Her Cooking Was 'Okay'",
        "emoji": "🍳",
        "description": "She spent 3 hours making your favorite dish. You said 'hmm, it's okay'. Fatal error.",
        "opening_lines": {
            "priya": "Teen ghante... TEEN GHANTE lagaye maine wo biryani banane mein. Aur tumne kya bola? 'Hmm okay hai.' OKAY HAI?!",
            "neha": "Cool. Next time I'll just order Swiggy.",
            "ritu": "Let me understand this. I spent 3 hours, used 14 ingredients, watched 3 YouTube tutorials, and your review was — 'hmm, it's okay'. That's 180 minutes of effort summarized in two words.",
            "kavya": "OKAY?! OKAY BOLA TUMNE?! TEEN GHANTE SE KHANA BANA RAHI THI MAIN! Aaj ke baad khud banao apna khana!",
        },
        "context": "The girlfriend spent 3 hours cooking the user's favorite biryani. They said 'hmm, it's okay' while scrolling their phone.",
        "curveball": "She'll bring up the phone, not the food. The food was never the point.",
    },
    "boys_trip": {
        "id": "boys_trip",
        "title": "Boys Trip Without Telling Her",
        "emoji": "✈️",
        "description": "You planned a Goa trip with the boys. She found out from someone else's Instagram story.",
        "opening_lines": {
            "priya": "Mujhe Rahul ki story se pata chala ki tum Goa ja rahe ho. RAHUL KI STORY SE. Main kya hoon tumhari zindagi mein?",
            "neha": "Saw Rahul's story. Goa looks fun. Have a good trip.",
            "ritu": "When exactly were you planning to tell me about the Goa trip? Before boarding? After landing? Or was I supposed to find out from Rahul's Instagram story?",
            "kavya": "GOA JA RAHE HO?! BINA BATAYE?! Mujhe Rahul ki story se pata chala — RAHUL KI STORY SE!",
        },
        "context": "The user planned a Goa trip with friends but didn't tell her. She found out from a friend's Instagram story.",
        "curveball": "She'll ask when the trip was booked, to find out how long you've been not telling her.",
    },
    "late": {
        "id": "late",
        "title": "2 Hours Late, No Text",
        "emoji": "🕐",
        "description": "You were 2 hours late for dinner and didn't even text. She sat alone at the restaurant.",
        "opening_lines": {
            "priya": "Do ghante. Do ghante akeli baithi rahi main restaurant mein. Waiter ne teen baar pucha 'ma'am aur koi aa raha hai?'. Mujhe itna sharam aaya na...",
            "neha": "I already ate. Alone.",
            "ritu": "Our reservation was at 8 PM. You arrived at 10:07 PM. That's 2 hours and 7 minutes. I called you 4 times and sent 6 messages. Zero responses.",
            "kavya": "DO GHANTE! DO GHANTE WAIT KARWAYI TUMNE! EK TEXT NAHI KAR SAKTE THE?!",
        },
        "context": "The user was 2 hours late for a dinner reservation and didn't text or call.",
        "curveball": "She'll ask what you were doing that was more important than one text.",
    },
    "gaming": {
        "id": "gaming",
        "title": "Chose Gaming Over Date Night",
        "emoji": "🎮",
        "description": "She planned date night. You said you'd come but started ranked matches instead.",
        "opening_lines": {
            "priya": "Main ready hokar baithi thi. Naya dress pehna tha. Makeup kiya tha. Aur tum? 'Baby bas ek aur match, 20 minute.' WOH 20 MINUTE 3 GHANTE HO GAYE!",
            "neha": "Your K/D ratio must be great tonight. Congrats.",
            "ritu": "Let me reconstruct the timeline. 7 PM: 'getting ready'. 7:30: 'one quick match'. 8:15: 'last one I promise'. 9:45: you're still playing. I have the WhatsApp timestamps.",
            "kavya": "GAMING?! GAMING ZYADA IMPORTANT HAI MUJHSE?! Maine itna plan kiya tha aur tumhe apna stupid game khelna tha!",
        },
        "context": "The girlfriend planned a date night. The user kept saying 'one more match' and never showed up.",
        "curveball": "She'll ask if this is going to happen again next week, and want a real answer.",
    },
}


def classic_brief(persona_id: str, scenario_id: str) -> dict:
    """Express a classic girlfriend preset in the same brief shape the rehearsal flow uses."""
    persona = PERSONAS[persona_id]
    scenario = SCENARIOS[scenario_id]
    return {
        "kind": "classic",
        "preset_id": scenario_id,
        "persona_id": persona_id,
        "title": scenario["title"],
        "emoji": persona["emoji"],
        "description": scenario["description"],
        "conversation_type": "emotional_repair",
        "counterpart": {
            "name": persona["name"],
            "role": persona["title"],
            "gender": "female",
            "voice_id": persona["voice_id"],
            "relationship": "Your girlfriend",
            "style": persona["system_prompt"],
        },
        "user_goal": "Get her to forgive you.",
        "user_fears": "",
        "history": scenario["context"],
        "hidden_motivations": [persona["hidden_motivation"]],
        "curveballs": [scenario["curveball"]],
        "opening_line": scenario["opening_lines"].get(persona_id, next(iter(scenario["opening_lines"].values()))),
    }


def preset_brief(preset_id: str) -> dict:
    """A rehearsal preset as a ready-to-use brief (no LLM call needed)."""
    preset = PRESETS[preset_id]
    counterpart = dict(preset["counterpart"])
    counterpart["voice_id"] = pick_voice(counterpart["name"], counterpart["gender"])
    return {
        "kind": "preset",
        "preset_id": preset_id,
        "title": preset["title"],
        "emoji": preset["emoji"],
        "description": preset["description"],
        "conversation_type": preset["conversation_type"],
        "counterpart": counterpart,
        "user_goal": preset["user_goal"],
        "user_fears": preset["user_fears"],
        "history": preset["history"],
        "hidden_motivations": list(preset["hidden_motivations"]),
        "curveballs": list(preset["curveballs"]),
        "opening_line": preset["opening_line"],
    }


INTAKE_FIELDS = ("user_goal", "user_fears", "history")
COUNTERPART_INTAKE_FIELDS = ("name", "role", "gender", "relationship", "style")


def preset_intake(preset_id: str) -> dict:
    """The editable part of a preset, in the shape the intake form submits."""
    preset = PRESETS[preset_id]
    return {
        "counterpart": {k: preset["counterpart"].get(k, "") for k in COUNTERPART_INTAKE_FIELDS},
        **{k: preset[k] for k in INTAKE_FIELDS},
    }


# ─── Safety (Milestone 5) ────────────────────────────────────────────────────
# Cheap keyword backstop run before the LLM sees the intake. The LLM also classifies.
SAFETY_KEYWORDS = {
    "self_harm": [
        "suicide", "suicidal", "kill myself", "end my life", "self-harm", "self harm",
        "hurt myself", "don't want to live", "do not want to live", "want to die",
    ],
    "abuse": [
        "hits me", "hit me", "beats me", "beat me", "slapped me", "slaps me", "choked",
        "rape", "raped", "molest", "sexually assault", "threatens to hurt", "threatened to hurt",
        "threatens to kill", "physically abus", "domestic violence",
    ],
}

SAFETY_RESOURCES = {
    "self_harm": {
        "title": "This sounds heavier than a rehearsal can hold.",
        "message": (
            "PatchUp is a practice tool, not support. If you or someone close to you is thinking about "
            "self-harm, please talk to a person who's trained for this. These lines are free and confidential."
        ),
        "resources": [
            {"name": "Tele-MANAS (Govt. of India, 24x7)", "contact": "14416 or 1800-891-4416"},
            {"name": "iCall (TISS)", "contact": "9152987821"},
            {"name": "Vandrevala Foundation (24x7)", "contact": "9999 666 555"},
            {"name": "AASRA (24x7)", "contact": "+91 9820466726"},
        ],
    },
    "abuse": {
        "title": "This isn't a conversation to rehearse alone.",
        "message": (
            "What you've described involves physical, sexual, or threatened harm. Practising a confrontation "
            "isn't the right next step, and it may not be safe. Please reach someone who can help you plan."
        ),
        "resources": [
            {"name": "National Commission for Women helpline", "contact": "7827170170"},
            {"name": "Women's helpline (24x7)", "contact": "181"},
            {"name": "Police emergency", "contact": "112"},
            {"name": "iCall (TISS) — counselling", "contact": "9152987821"},
        ],
    },
}


def screen_intake_text(text: str) -> str | None:
    """Return a safety category if the intake obviously describes self-harm or abuse."""
    lowered = (text or "").lower()
    for category, needles in SAFETY_KEYWORDS.items():
        if any(needle in lowered for needle in needles):
            return category
    return None


def safety_payload(category: str) -> dict:
    return {"flagged": True, "category": category, **SAFETY_RESOURCES[category]}


# ─── Languages offered in the UI ─────────────────────────────────────────────
LANGUAGES = [
    {"id": "hi-IN", "label": "Hindi-English mix"},
    {"id": "en-IN", "label": "English (Indian)"},
    {"id": "ta-IN", "label": "Tamil"},
    {"id": "te-IN", "label": "Telugu"},
    {"id": "bn-IN", "label": "Bengali"},
    {"id": "kn-IN", "label": "Kannada"},
    {"id": "ml-IN", "label": "Malayalam"},
    {"id": "mr-IN", "label": "Marathi"},
    {"id": "gu-IN", "label": "Gujarati"},
]
