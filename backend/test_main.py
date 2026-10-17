"""Offline regression tests: python -m unittest discover -s backend -v (no network, no DB)."""
import itertools
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

# Never initialize a real database client during test discovery.
with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": "", "TYPESAFE_API_KEY": ""}):
    import content
    import db
    import main
    import parsing
    import prompts
    import typesafe

ACTOR = {"response": "Hmm.", "emotion": "cold", "receptiveness_delta": 5, "trust_delta": 2, "defensiveness_delta": -3}
COACH = {"scores": {"acknowledgment": 7, "ownership": 4, "non_defensiveness": 8}, "note": "Own the specific thing.", "stronger": "I should have texted."}
TIPS = ["One", "Two", "Three"]


def fake_llm(actor=ACTOR, coach=COACH, brief=None, tips=TIPS, coach_error=None):
    """Route mocked Sarvam-M calls by the prompt they carry."""
    async def side_effect(messages, temperature=0.7, max_tokens=512):
        system = messages[0]["content"] if messages[0]["role"] == "system" else ""
        if "communication coach" in system:
            if coach_error:
                raise coach_error
            return json.dumps(coach) if isinstance(coach, dict) else coach
        if "rehearsal scenarios" in system:
            return json.dumps(brief) if isinstance(brief, dict) else brief
        if not system:
            return json.dumps(tips)
        return json.dumps(actor) if isinstance(actor, dict) else actor
    return AsyncMock(side_effect=side_effect)


# ═══════════════════════════════════════════════════════════════════════════════

class ParsingTests(unittest.TestCase):
    def test_actor_wrappers_and_number_repair(self):
        payload = '{"response":"Cost: +20", "receptiveness_delta":+12, "emotion":"firm"}'
        for raw in (payload, f"```json\n{payload}\n```", f"Here it is: {payload} Done."):
            with self.subTest(raw=raw):
                parsed = parsing.parse_actor(raw, content.EMOTION_VOICE_PARAMS, "neutral")
                self.assertEqual(parsed["receptiveness_delta"], 12)
                self.assertEqual(parsed["response"], "Cost: +20")
                self.assertEqual(parsed["emotion"], "firm")

    def test_actor_invalid_shapes_fall_back(self):
        for raw in ('[]', 'null', '42', '"hello"', '{broken', ''):
            with self.subTest(raw=raw):
                parsed = parsing.parse_actor(raw, content.EMOTION_VOICE_PARAMS, "neutral")
                self.assertEqual(parsed["receptiveness_delta"], 0)
                self.assertEqual(parsed["emotion"], "neutral")
                self.assertTrue(parsed["response"])

    def test_actor_accepts_legacy_score_delta_and_clamps(self):
        parsed = parsing.parse_actor('{"response":"ok","score_delta":40,"trust_delta":"x"}', content.EMOTION_VOICE_PARAMS, "neutral")
        self.assertEqual(parsed["receptiveness_delta"], 25)
        self.assertEqual(parsed["trust_delta"], 0)

    def test_coach_partial_scores_and_garbage(self):
        dims = ["clarity", "empathy", "steadiness"]
        parsed = parsing.parse_coach('{"scores":{"clarity":11,"empathy":"n/a","other":5},"note":" Good. "}', dims)
        self.assertEqual(parsed["scores"], {"clarity": 10})
        self.assertEqual(parsed["note"], "Good.")
        self.assertIsNone(parsing.parse_coach("not json", dims))
        self.assertIsNone(parsing.parse_coach('{"scores":{}}', dims))

    def test_tips_wrappers_and_invalid(self):
        payload = '["Listen", "Be specific", "Agree next steps"]'
        for raw in (payload, f"```json\n{payload}\n```", f"Tips: {payload}"):
            self.assertEqual(parsing.parse_tips(raw), json.loads(payload))
        for raw in ('{}', '["one"]', '["one", null, "three"]', '["one", " ", "three"]'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parsing.parse_tips(raw)

    def test_brief_fills_from_intake_and_requires_opening(self):
        intake = {"counterpart": {"name": "Rohan", "role": "Manager", "gender": "male"}, "user_goal": "A raise"}
        raw = '{"conversation_type":"negotiation","hidden_motivations":["a","b","c","d"],"curveballs":["x"],"opening_line":"Hi.","safety_category":"nope"}'
        brief = parsing.parse_brief(raw, intake, set(content.RUBRICS), "feedback")
        self.assertEqual(brief["counterpart"]["name"], "Rohan")
        self.assertEqual(brief["counterpart"]["gender"], "male")
        self.assertIn(brief["counterpart"]["voice_id"], content.VOICES["male"])
        self.assertEqual(brief["user_goal"], "A raise")
        self.assertEqual(len(brief["hidden_motivations"]), 3)
        self.assertIsNone(brief["safety_category"])
        self.assertIsNone(parsing.parse_brief('{"conversation_type":"negotiation"}', intake, set(content.RUBRICS), "feedback"))
        self.assertEqual(parsing.parse_brief('{"opening_line":"Hi","conversation_type":"bogus"}', intake, set(content.RUBRICS), "feedback")["conversation_type"], "feedback")


class ContentTests(unittest.TestCase):
    def test_presets_are_complete_briefs(self):
        for preset_id in content.PRESETS:
            with self.subTest(preset=preset_id):
                brief = content.preset_brief(preset_id)
                self.assertIn(brief["conversation_type"], content.RUBRICS)
                self.assertGreaterEqual(len(brief["hidden_motivations"]), 2)
                self.assertEqual(len(brief["curveballs"]), 2)
                self.assertTrue(brief["opening_line"])
                self.assertIn(brief["counterpart"]["voice_id"], content.VOICES[brief["counterpart"]["gender"]])
                self.assertEqual(main.normalized_intake(content.preset_intake(preset_id))["user_goal"], brief["user_goal"])

    def test_classic_briefs_cover_every_pair(self):
        for persona_id, scenario_id in itertools.product(content.PERSONAS, content.SCENARIOS):
            brief = content.classic_brief(persona_id, scenario_id)
            self.assertEqual(brief["kind"], "classic")
            self.assertEqual(brief["conversation_type"], "emotional_repair")
            self.assertEqual(brief["opening_line"], content.SCENARIOS[scenario_id]["opening_lines"][persona_id])
            self.assertEqual(brief["counterpart"]["voice_id"], persona_id)

    def test_pick_voice_is_stable_and_valid(self):
        self.assertEqual(content.pick_voice("Rohan", "male"), content.pick_voice("rohan", "male"))
        self.assertIn(content.pick_voice("Anyone", "female"), content.VOICES["female"])
        self.assertIn(content.pick_voice("", "other"), content.VOICES["female"])

    def test_safety_screen_and_type_guess(self):
        self.assertEqual(content.screen_intake_text("He HITS me when drunk"), "abuse")
        self.assertEqual(content.screen_intake_text("I want to end my life"), "self_harm")
        self.assertIsNone(content.screen_intake_text("My boss yells in standups"))
        self.assertEqual(content.guess_conversation_type("ask for a raise"), "negotiation")
        self.assertEqual(content.guess_conversation_type("tell my parents I'm quitting"), "difficult_news")
        self.assertEqual(content.guess_conversation_type("missed deadlines"), "feedback")

    def test_every_difficulty_has_state_and_every_emotion_has_voice(self):
        for config in content.DIFFICULTY_CONFIG.values():
            self.assertEqual(set(config["state"]), {"trust", "defensiveness"})
        self.assertIn(content.DEFAULT_EMOTION, content.EMOTION_VOICE_PARAMS)


class PromptTests(unittest.TestCase):
    def test_actor_messages_fold_opening_and_start_with_user(self):
        conversation = [{"role": "counterpart", "text": "Opening"}, {"role": "user", "text": "Hi"}, {"role": "counterpart", "text": "Hmm"}]
        messages = prompts.build_actor_messages("SYS", conversation, "Sorry", 40, {"trust": 30, "defensiveness": 70})
        self.assertIn("Opening", messages[0]["content"])
        self.assertEqual([m["role"] for m in messages], ["system", "user", "assistant", "user"])
        self.assertIn("defensiveness: 70/100", messages[-1]["content"])

    def test_actor_prompt_contains_brief_and_coach_prompt_contains_rubric(self):
        brief = content.preset_brief("raise")
        actor = prompts.build_actor_prompt(brief, "defensive", "hi-IN")
        self.assertIn("Rohan", actor)
        self.assertIn(brief["curveballs"][0], actor)
        self.assertIn("Hinglish", actor)
        coach = prompts.build_coach_messages(brief, [], "I want 20%")
        self.assertIn("clarity_of_ask", coach[0]["content"])
        self.assertEqual(coach[1]["role"], "user")
        self.assertIn("I want 20%", coach[1]["content"])

    def test_brief_prompt_seeds_from_preset(self):
        messages = prompts.build_brief_messages({"counterpart": {"name": "X"}, "user_goal": "y"}, content.PRESETS["layoff"])
        self.assertIn("Let someone go", messages[0]["content"])
        self.assertIn("X", messages[1]["content"])


# ═══════════════════════════════════════════════════════════════════════════════

class SessionTestCase(unittest.IsolatedAsyncioTestCase):
    """In-memory sessions, mocked Sarvam."""

    def setUp(self):
        self.db_patch = patch.object(db, "supabase", None)
        self.db_patch.start()
        db.memory_sessions.clear()
        self.tts = patch.object(main, "sarvam_tts", AsyncMock(return_value="audio"))
        self.tts.start()
        self.translate = patch.object(main, "sarvam_translate", AsyncMock(side_effect=lambda text, *a, **k: f"[hi] {text}"))
        self.translate.start()

    def tearDown(self):
        self.translate.stop()
        self.tts.stop()
        db.memory_sessions.clear()
        self.db_patch.stop()

    def legacy_session(self, score=80, difficulty="medium"):
        """A row written by the pre-rehearsal backend: girlfriend roles, no brief, no state."""
        session = {
            "id": "legacy", "persona_id": "priya", "scenario_id": "anniversary",
            "difficulty": difficulty, "language": "en-IN", "current_score": score,
            "status": "ongoing", "system_prompt": "Practice",
            "conversation": [{"role": "girlfriend", "text": "Opening", "score_delta": 0}],
        }
        db.memory_sessions["legacy"] = session
        return session

    async def start_preset(self, preset_id="raise", difficulty="defensive", language="en-IN"):
        with patch.object(main, "sarvam_llm", fake_llm()):
            return await main.start_session(main.SessionStartRequest(
                brief=content.preset_brief(preset_id), difficulty=difficulty, language=language))

    async def respond(self, session_id, text="I understand", **llm_kwargs):
        with patch.object(main, "sarvam_llm", fake_llm(**llm_kwargs)) as llm:
            result = await main.process_user_message(session_id, text)
            # Sarvam-M needs the first non-system message to be from the user, on both calls.
            for call in llm.call_args_list:
                self.assertEqual(call.args[0][1]["role"], "user")
            return result


# ═══════════════════════════════════════════════════════════════════════════════

def fake_answers(movement=3.0, trust=2.0, defensiveness=2.0, dims=None):
    """A Jev `answers` map in the shape the API returns."""
    answers = {
        "movement": {"type": "score", "score": movement, "confidence": 0.8},
        "trust": {"type": "score", "score": trust, "confidence": 0.6},
        "defensiveness": {"type": "score", "score": defensiveness, "confidence": 0.6},
    }
    for dim, score in (dims or {}).items():
        answers[dim] = {"type": "score", "score": score, "confidence": 0.7}
    return answers


class JevMappingTests(unittest.TestCase):
    def test_score_to_delta_is_symmetric_around_the_middle_level(self):
        self.assertEqual(typesafe.score_to_delta(3, 7, 25), 0)
        self.assertEqual(typesafe.score_to_delta(6, 7, 25), 25)
        self.assertEqual(typesafe.score_to_delta(0, 7, 25), -25)
        self.assertEqual(typesafe.score_to_delta(4.2, 7, 25), 10)
        self.assertEqual(typesafe.score_to_delta(2, 5, 15), 0)
        self.assertEqual(typesafe.score_to_delta(4, 5, 15), 15)

    def test_score_to_ten(self):
        self.assertEqual(typesafe.score_to_ten(3, 4), 10.0)
        self.assertEqual(typesafe.score_to_ten(1.5, 4), 5.0)
        self.assertEqual(typesafe.score_to_ten(0, 4), 0.0)

    def test_needs_english_only_for_native_scripts(self):
        self.assertFalse(typesafe.needs_english("sorry yaar, galti ho gayi"))
        self.assertTrue(typesafe.needs_english("मुझे माफ़ कर दो"))
        self.assertTrue(typesafe.needs_english("மன்னிக்கவும்"))

    def test_turn_questions_cover_movement_and_every_rubric_dimension(self):
        brief = content.preset_brief("raise")
        questions = typesafe.turn_questions(brief)
        self.assertEqual(set(questions), {"movement", "trust", "defensiveness", "clarity_of_ask", "anchoring", "objection_handling"})
        for spec in questions.values():
            self.assertEqual(spec["type"], "score")
            self.assertTrue(2 <= len(spec["criteria"]) <= 10)
        self.assertEqual(questions["movement"]["criteria"], content.MOVEMENT_LEVELS)
        self.assertIn("Rohan", questions["movement"]["instructions"])
        state = typesafe.turn_state(brief, [{"role": "counterpart", "text": "Hi"}], "I want 20%", 30,
                                    {"trust": 40, "defensiveness": 65}, "I want twenty percent")
        self.assertEqual(state["transcript"], [{"speaker": "Rohan", "text": "Hi"}])
        self.assertEqual(state["latest_user_message_english"], "I want twenty percent")
        self.assertEqual(state["counterpart_state_before_this_message"]["receptiveness"], 30)
        self.assertNotIn("latest_user_message_english", typesafe.turn_state(brief, [], "x", 30, {"trust": 40, "defensiveness": 65}))

    def test_intake_questions_and_every_rubric_has_four_levels(self):
        self.assertEqual(set(typesafe.INTAKE_QUESTIONS["conversation_type"]["criteria"]), set(content.RUBRICS))
        for rubric in content.RUBRICS.values():
            for spec in rubric["dimensions"].values():
                self.assertEqual(len(spec["levels"]), 4)
                self.assertTrue(spec["description"])


class JevJudgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_judge_turn_maps_answers(self):
        brief = content.preset_brief("raise")
        answers = fake_answers(movement=6, trust=4, defensiveness=0,
                               dims={"clarity_of_ask": 3, "anchoring": 1.5, "objection_handling": 0})
        with patch.object(typesafe, "system_one", AsyncMock(return_value=answers)) as system_one:
            verdict = await typesafe.judge_turn(brief, [], "I want 20%", 30, {"trust": 40, "defensiveness": 65})
        self.assertEqual(verdict["receptiveness_delta"], 25)
        self.assertEqual(verdict["trust_delta"], 15)
        self.assertEqual(verdict["defensiveness_delta"], -15)
        self.assertEqual(verdict["scores"], {"clarity_of_ask": 10.0, "anchoring": 5.0, "objection_handling": 0.0})
        self.assertEqual(verdict["confidence"]["movement"], 0.8)
        self.assertEqual(system_one.call_args.args[0]["latest_user_message"], "I want 20%")

    async def test_judge_turn_rejects_missing_scores(self):
        with patch.object(typesafe, "system_one", AsyncMock(return_value={"movement": {"type": "score"}})):
            with self.assertRaises(ValueError):
                await typesafe.judge_turn(content.preset_brief("raise"), [], "x", 30, {"trust": 40, "defensiveness": 65})

    async def test_judge_intake_thresholds_and_type(self):
        answers = {
            "abuse": {"type": "noul", "noul": 0.2},
            "self_harm": {"type": "noul", "noul": 0.7},
            "conversation_type": {"type": "choice", "choice": "difficult_news", "probabilities": {"difficult_news": 0.9}},
        }
        with patch.object(typesafe, "system_one", AsyncMock(return_value=answers)):
            verdict = await typesafe.judge_intake({"user_goal": "x"})
        self.assertEqual(verdict["safety_category"], "self_harm")
        self.assertEqual(verdict["conversation_type"], "difficult_news")
        answers["self_harm"]["noul"] = 0.1
        answers["conversation_type"]["choice"] = "bogus"
        with patch.object(typesafe, "system_one", AsyncMock(return_value=answers)):
            verdict = await typesafe.judge_intake({"user_goal": "x"})
        self.assertIsNone(verdict["safety_category"])
        self.assertIsNone(verdict["conversation_type"])


class JevConversationTests(SessionTestCase):
    def setUp(self):
        super().setUp()
        self.enabled = patch.object(main, "judge_enabled", return_value=True)
        self.enabled.start()

    def tearDown(self):
        self.enabled.stop()
        super().tearDown()

    @staticmethod
    def verdict(**override):
        return {
            "receptiveness_delta": 20, "trust_delta": 10, "defensiveness_delta": -10,
            "scores": {"acknowledgment": 8.0, "ownership": 3.3, "non_defensiveness": 6.7}, "confidence": {},
            **override,
        }

    async def test_jev_owns_movement_and_scores(self):
        session = self.legacy_session(score=50, difficulty="medium")  # gain_factor 0.75
        actor = {"response": "Fine.", "emotion": "softening", "score_delta": -25, "trust_delta": -25, "defensiveness_delta": 25}
        with patch.object(main, "judge_turn", AsyncMock(return_value=self.verdict())) as judge:
            result = await self.respond("legacy", actor=actor, coach={"note": "Good.", "stronger": "Better.", "scores": {"ownership": 0}})
        self.assertEqual(result.judged_by, "jev")
        self.assertEqual(result.score_delta, 15)
        self.assertEqual(result.current_score, 65)
        self.assertEqual(result.counterpart_state, {"trust": 50, "defensiveness": 50})
        self.assertEqual(result.coach.scores, {"acknowledgment": 8.0, "ownership": 3.3, "non_defensiveness": 6.7})
        self.assertEqual(result.coach.note, "Good.")
        self.assertEqual(result.skill_scores["ownership"], 3.3)
        self.assertEqual(session["conversation"][1]["judged_by"], "jev")
        judge.assert_awaited_once()
        self.assertIsNone(judge.call_args.args[5])  # en-IN: nothing to translate
        main.sarvam_translate.assert_not_called()

    async def test_actor_plays_updated_state_and_coach_sees_scores(self):
        self.legacy_session(score=50, difficulty="easy")  # gain_factor 1.0
        with patch.object(main, "judge_turn", AsyncMock(return_value=self.verdict())), \
             patch.object(main, "sarvam_llm", fake_llm()) as llm:
            await main.process_user_message("legacy", "I'm sorry")
        actor_call, coach_call = llm.call_args_list
        actor_messages = actor_call.args[0]
        self.assertIn("after hearing this", actor_messages[-1]["content"])
        self.assertIn("receptiveness: 70/100", actor_messages[-1]["content"])
        self.assertNotIn("receptiveness_delta", actor_messages[0]["content"])
        coach_system = coach_call.args[0][0]["content"]
        self.assertIn("already been scored", coach_system)
        self.assertIn("Weakest: ownership", coach_system)
        self.assertNotIn('"scores"', coach_system)

    async def test_self_judging_prompt_asks_for_deltas(self):
        self.enabled.stop()
        self.legacy_session(score=50)
        with patch.object(main, "sarvam_llm", fake_llm()) as llm:
            await main.process_user_message("legacy", "I'm sorry")
        self.enabled.start()
        actor_messages = llm.call_args_list[0].args[0]
        self.assertIn("receptiveness_delta", actor_messages[0]["content"])
        self.assertIn("receptiveness: 50/100", actor_messages[-1]["content"])

    async def test_losses_land_in_full_and_gains_are_scaled_by_temperament(self):
        self.legacy_session(score=50, difficulty="nightmare")  # gain_factor 0.4
        with patch.object(main, "judge_turn", AsyncMock(return_value=self.verdict(receptiveness_delta=25))):
            self.assertEqual((await self.respond("legacy")).score_delta, 10)
        with patch.object(main, "judge_turn", AsyncMock(return_value=self.verdict(receptiveness_delta=-25))):
            self.assertEqual((await self.respond("legacy")).score_delta, -25)

    async def test_jev_failure_falls_back_to_actor(self):
        self.legacy_session(score=50)
        with patch.object(main, "judge_turn", AsyncMock(side_effect=RuntimeError("down"))):
            result = await self.respond("legacy", actor={**ACTOR, "receptiveness_delta": 7})
        self.assertEqual(result.judged_by, "actor")
        self.assertEqual(result.score_delta, 7)
        self.assertEqual(result.coach.scores["ownership"], 4)

    async def test_native_script_is_translated_for_jev(self):
        self.legacy_session(score=50)["language"] = "hi-IN"
        with patch.object(main, "judge_turn", AsyncMock(return_value=self.verdict())) as judge:
            await self.respond("legacy", text="मुझे माफ़ कर दो")
        self.assertEqual(judge.call_args.args[5], "[hi] मुझे माफ़ कर दो")
        with patch.object(main, "judge_turn", AsyncMock(return_value=self.verdict())) as judge:
            await self.respond("legacy", text="sorry yaar")
        self.assertIsNone(judge.call_args.args[5])

    async def test_build_uses_jev_verdict(self):
        llm_brief = {
            "title": "Talk", "conversation_type": "feedback",
            "counterpart": {"name": "Meera", "role": "VP", "relationship": "new", "style": "brisk"},
            "user_goal": "15%", "hidden_motivations": ["m1"], "curveballs": ["c1", "c2"],
            "opening_line": "Go ahead.", "safety_category": None,
        }
        verdict = {"safety_category": None, "safety_probabilities": {}, "conversation_type": "negotiation", "type_probabilities": {}}
        custom = main.Intake(counterpart=main.IntakeCounterpart(name="Meera", role="VP"), user_goal="a raise")

        with patch.object(main, "sarvam_llm", fake_llm(brief=llm_brief)), \
             patch.object(main, "judge_intake", AsyncMock(return_value=verdict)):
            result = await main.build_scenario(main.ScenarioBuildRequest(intake=custom))
        self.assertEqual(result.judged_by, "jev")
        self.assertEqual(result.brief["conversation_type"], "negotiation")  # Jev overrides the builder

        edited = main.Intake(**{**content.preset_intake("raise"), "user_goal": "15% and a title"})
        with patch.object(main, "sarvam_llm", fake_llm(brief=llm_brief)), \
             patch.object(main, "judge_intake", AsyncMock(return_value={**verdict, "conversation_type": "feedback"})):
            result = await main.build_scenario(main.ScenarioBuildRequest(preset_id="raise", intake=edited))
        self.assertEqual(result.brief["conversation_type"], "negotiation")  # presets keep their type

        with patch.object(main, "sarvam_llm", fake_llm(brief=llm_brief)), \
             patch.object(main, "judge_intake", AsyncMock(return_value={**verdict, "safety_category": "abuse"})):
            result = await main.build_scenario(main.ScenarioBuildRequest(intake=custom))
        self.assertEqual(result.safety["category"], "abuse")
        self.assertIsNone(result.brief)

        with patch.object(main, "sarvam_llm", fake_llm(brief=llm_brief)), \
             patch.object(main, "judge_intake", AsyncMock(side_effect=RuntimeError("down"))):
            result = await main.build_scenario(main.ScenarioBuildRequest(intake=custom))
        self.assertEqual(result.judged_by, "llm")
        self.assertEqual(result.brief["conversation_type"], "feedback")


class ConversationTests(SessionTestCase):
    async def test_legacy_session_reaches_goal_at_90(self):
        session = self.legacy_session(score=80)
        result = await self.respond("legacy", actor={"response": "Thanks", "score_delta": 10})
        self.assertEqual(result.status, "patched_up")
        self.assertEqual(result.current_score, 90)
        self.assertEqual(result.counterpart_text, "Thanks")
        self.assertEqual(result.model_dump()["girlfriend_text"], "Thanks")
        self.assertEqual(result.turn_number, 1)
        self.assertEqual([t["role"] for t in session["conversation"]], ["counterpart", "user", "counterpart"])
        self.assertEqual(session["conversation"][-1]["state"]["receptiveness"], 90)

    async def test_end_flags_cannot_override_score(self):
        self.legacy_session(score=80)
        result = await self.respond("legacy", actor={"response": "Okay", "score_delta": 9, "should_end": True, "end_reason": "patched_up"})
        self.assertEqual(result.status, "ongoing")

    async def test_blocked_at_zero(self):
        self.legacy_session(score=10)
        result = await self.respond("legacy", actor={"response": "Enough", "receptiveness_delta": -10})
        self.assertEqual(result.status, "blocked")

    async def test_invalid_actor_fields_do_not_crash(self):
        self.legacy_session(score=80)
        result = await self.respond("legacy", actor={"response": None, "receptiveness_delta": "n/a", "emotion": []})
        self.assertEqual(result.current_score, 80)
        self.assertEqual(result.emotion, "neutral")

    async def test_coach_annotates_turn_and_averages(self):
        session = self.legacy_session(score=50)
        first = await self.respond("legacy")
        self.assertEqual(first.coach.scores["ownership"], 4)
        self.assertEqual(first.skill_scores, {"acknowledgment": 7.0, "ownership": 4.0, "non_defensiveness": 8.0})
        second = await self.respond("legacy", coach={"scores": {"ownership": 8}, "note": "", "stronger": ""})
        self.assertEqual(second.skill_scores["ownership"], 6.0)
        self.assertEqual(second.skill_scores["acknowledgment"], 7.0)
        self.assertEqual(session["conversation"][1]["coach"]["note"], "Own the specific thing.")

    async def test_coach_failure_does_not_fail_turn(self):
        self.legacy_session(score=50)
        result = await self.respond("legacy", coach_error=RuntimeError("coach down"))
        self.assertIsNone(result.coach)
        self.assertEqual(result.current_score, 55)
        garbage = await self.respond("legacy", coach="not json at all")
        self.assertIsNone(garbage.coach)

    async def test_state_moves_and_nudges_voice(self):
        self.legacy_session(score=50, difficulty="medium")
        result = await self.respond("legacy", actor={**ACTOR, "trust_delta": 30, "defensiveness_delta": -99})
        self.assertEqual(result.counterpart_state, {"trust": 65, "defensiveness": 35})
        pace, _ = main.sarvam_tts.call_args.kwargs["pace"], None
        calm_pace, _ = main.voice_params("medium", "cold", {"trust": 50, "defensiveness": 0})
        tense_pace, _ = main.voice_params("medium", "cold", {"trust": 50, "defensiveness": 100})
        self.assertLess(calm_pace, tense_pace)
        self.assertAlmostEqual(pace, main.voice_params("medium", "cold", {"trust": 65, "defensiveness": 35})[0])

    async def test_stats_recorded_once_when_conversation_resolves(self):
        self.legacy_session(score=80)
        with patch.object(main, "db_record_stats") as stats:
            await self.respond("legacy", actor={**ACTOR, "receptiveness_delta": 10})
            self.assertEqual(stats.call_args.args[0]["status"], "patched_up")
            with patch.object(main, "sarvam_llm", fake_llm()):
                await main.end_session_endpoint("legacy")
                await main.end_session_endpoint("legacy")
        self.assertEqual(stats.call_count, 1)

    async def test_ended_session_rejects_messages(self):
        self.legacy_session(score=80)["status"] = "quit"
        with self.assertRaises(HTTPException) as ctx:
            await self.respond("legacy")
        self.assertEqual(ctx.exception.status_code, 400)


class StartAndBuildTests(SessionTestCase):
    async def test_start_from_preset_brief_translates_opening_for_hindi(self):
        started = await self.start_preset(language="hi-IN")
        self.assertTrue(started.opening_message.startswith("[hi] "))
        self.assertEqual(started.counterpart_name, "Rohan")
        self.assertEqual(started.meter_label, "Buy-in")
        self.assertEqual([d["id"] for d in started.dimensions], ["clarity_of_ask", "anchoring", "objection_handling"])
        self.assertEqual(started.initial_score, 30)
        self.assertEqual(started.model_dump()["persona_name"], "Rohan")
        session = db.memory_sessions[started.session_id]
        self.assertEqual(session["scenario_id"], "raise")
        self.assertIsNone(session["persona_id"])
        self.assertIn("Rohan", session["system_prompt"])

    async def test_start_english_skips_translation_and_classic_never_translates(self):
        await self.start_preset(language="en-IN")
        main.sarvam_translate.assert_not_called()
        with patch.object(main, "sarvam_llm", fake_llm()):
            started = await main.start_session(main.SessionStartRequest(persona_id="neha", scenario_id="late", difficulty="hard", language="hi-IN"))
        main.sarvam_translate.assert_not_called()
        self.assertEqual(started.kind, "classic")
        self.assertEqual(started.opening_message, "I already ate. Alone.")
        self.assertEqual(started.initial_score, 15)

    async def test_start_validation(self):
        for request in (
            main.SessionStartRequest(difficulty="medium"),
            main.SessionStartRequest(persona_id="priya", scenario_id="nope"),
            main.SessionStartRequest(brief=content.preset_brief("raise"), difficulty="impossible"),
            main.SessionStartRequest(brief=content.preset_brief("raise"), language="xx-XX"),
            main.SessionStartRequest(brief={"kind": "custom", "counterpart": {"name": "A"}}),
        ):
            with self.subTest(request=request), self.assertRaises(HTTPException) as ctx:
                await main.start_session(request)
            self.assertEqual(ctx.exception.status_code, 400)

    async def test_build_preset_fast_path_skips_llm(self):
        with patch.object(main, "sarvam_llm", fake_llm()) as llm:
            untouched = await main.build_scenario(main.ScenarioBuildRequest(preset_id="layoff"))
            same = await main.build_scenario(main.ScenarioBuildRequest(
                preset_id="layoff", intake=main.Intake(**content.preset_intake("layoff"))))
        llm.assert_not_called()
        self.assertEqual(untouched.built_by, "preset")
        self.assertEqual(same.brief["counterpart"]["name"], "Manoj")

    async def test_build_edited_preset_and_custom_use_llm(self):
        llm_brief = {
            "title": "Raise talk", "conversation_type": "negotiation",
            "counterpart": {"name": "Meera", "role": "VP", "relationship": "new", "style": "brisk"},
            "user_goal": "15%", "hidden_motivations": ["m1", "m2"], "curveballs": ["c1", "c2"],
            "opening_line": "Go ahead.", "safety_category": None,
        }
        edited = main.Intake(**{**content.preset_intake("raise"), "user_goal": "15% and a title bump"})
        with patch.object(main, "sarvam_llm", fake_llm(brief=llm_brief)) as llm:
            result = await main.build_scenario(main.ScenarioBuildRequest(preset_id="raise", intake=edited))
        self.assertEqual(result.built_by, "llm")
        self.assertEqual(result.brief["kind"], "preset")
        self.assertEqual(result.brief["preset_id"], "raise")
        self.assertEqual(result.brief["counterpart"]["gender"], "male")  # intake wins over LLM
        self.assertIn("Ask for a raise", llm.call_args.args[0][0]["content"])  # seeded from the preset
        self.assertNotIn("safety_category", result.brief)

        custom = main.Intake(counterpart=main.IntakeCounterpart(name="Dad", role="Father", gender="male"), user_goal="Tell him I'm moving abroad")
        with patch.object(main, "sarvam_llm", fake_llm(brief={**llm_brief, "conversation_type": "bogus"})):
            result = await main.build_scenario(main.ScenarioBuildRequest(intake=custom))
        self.assertEqual(result.brief["kind"], "custom")
        self.assertEqual(result.brief["conversation_type"], "difficult_news")  # guessed from the goal
        self.assertEqual(result.brief["emoji"], "🗣️")

    async def test_build_safety_screen_and_llm_flag(self):
        flagged = main.Intake(counterpart=main.IntakeCounterpart(role="Husband"), history="he hits me when he drinks")
        with patch.object(main, "sarvam_llm", fake_llm()) as llm:
            result = await main.build_scenario(main.ScenarioBuildRequest(intake=flagged))
        llm.assert_not_called()
        self.assertEqual(result.safety["category"], "abuse")
        self.assertTrue(result.safety["resources"])
        self.assertIsNone(result.brief)

        subtle = main.Intake(counterpart=main.IntakeCounterpart(role="Friend"), user_goal="talk about last night")
        with patch.object(main, "sarvam_llm", fake_llm(brief={"opening_line": "Hey", "safety_category": "self_harm"})):
            result = await main.build_scenario(main.ScenarioBuildRequest(intake=subtle))
        self.assertEqual(result.safety["category"], "self_harm")

    async def test_build_rejects_empty_intake_and_unusable_llm_output(self):
        with self.assertRaises(HTTPException) as ctx:
            await main.build_scenario(main.ScenarioBuildRequest(intake=main.Intake()))
        self.assertEqual(ctx.exception.status_code, 400)
        with patch.object(main, "sarvam_llm", fake_llm(brief="nonsense")), self.assertRaises(HTTPException) as ctx:
            await main.build_scenario(main.ScenarioBuildRequest(intake=main.Intake(user_goal="a raise")))
        self.assertEqual(ctx.exception.status_code, 502)


class RehearsalLoopTests(SessionTestCase):
    async def test_rewind_restores_state_and_skill(self):
        started = await self.start_preset()
        sid = started.session_id
        await self.respond(sid, "turn one", actor={**ACTOR, "receptiveness_delta": 10})
        await self.respond(sid, "turn two", actor={**ACTOR, "receptiveness_delta": 20, "trust_delta": 20},
                           coach={"scores": {"anchoring": 2}, "note": "", "stronger": ""})
        self.assertEqual(db.memory_sessions[sid]["current_score"], 60)

        snap = await main.rewind_session(sid, main.RewindRequest(turn_number=2))
        self.assertEqual(snap.current_score, 40)
        self.assertEqual(snap.counterpart_state, {"trust": 42, "defensiveness": 62})
        self.assertEqual(snap.next_turn_number, 2)
        self.assertEqual(len(snap.conversation), 3)
        self.assertNotIn("anchoring", snap.skill_scores)

        # Rewinding a finished session reopens it.
        db.memory_sessions[sid]["status"] = "blocked"
        snap = await main.rewind_session(sid, main.RewindRequest(turn_number=1))
        self.assertEqual(snap.status, "ongoing")
        self.assertEqual(snap.current_score, 30)
        self.assertEqual(snap.conversation, db.memory_sessions[sid]["conversation"][:1])

        for bad in (0, 2):
            with self.subTest(turn=bad), self.assertRaises(HTTPException):
                await main.rewind_session(sid, main.RewindRequest(turn_number=bad))

    async def test_rewind_legacy_rows_replays_deltas(self):
        session = self.legacy_session(score=10, difficulty="medium")
        session["conversation"] += [
            {"role": "boyfriend", "text": "a"}, {"role": "girlfriend", "text": "b", "score_delta": -25},
            {"role": "boyfriend", "text": "c"}, {"role": "girlfriend", "text": "d", "score_delta": 5},
        ]
        snap = await main.rewind_session("legacy", main.RewindRequest(turn_number=2))
        self.assertEqual(snap.current_score, 5)  # 30 - 25, clamped per step
        self.assertEqual(snap.counterpart_state, content.DIFFICULTY_CONFIG["medium"]["state"])

    async def test_restart_links_previous_and_end_compares(self):
        first = await self.start_preset()
        await self.respond(first.session_id, actor={**ACTOR, "receptiveness_delta": 25})
        with patch.object(main, "sarvam_llm", fake_llm()):
            second = await main.restart_session(first.session_id)
        self.assertNotEqual(first.session_id, second.session_id)
        self.assertEqual(db.memory_sessions[first.session_id]["status"], "quit")
        self.assertEqual(db.memory_sessions[second.session_id]["previous_session_id"], first.session_id)
        self.assertEqual(second.initial_score, 30)

        with patch.object(main, "sarvam_llm", fake_llm()), patch.object(main, "db_record_stats") as stats:
            ended = await main.end_session_endpoint(second.session_id)
        self.assertEqual(ended.previous_score, 55)
        self.assertEqual(ended.final_score, 30)
        self.assertEqual(ended.reveal["curveballs"], content.PRESETS["raise"]["curveballs"])
        self.assertEqual(ended.status, "quit")
        self.assertEqual(ended.verdict, "You lost ground.")
        self.assertEqual(stats.call_args.args[1], 0)

    async def test_debrief_ignores_opening_and_counts_legacy_roles(self):
        session = self.legacy_session()
        session["conversation"] += [
            {"role": "boyfriend", "text": "Sorry"},
            {"role": "girlfriend", "text": "Thanks", "score_delta": 10},
        ]
        with patch.object(main, "sarvam_llm", AsyncMock(return_value='```json\n["One", "Two", "Three"]\n```')), \
             patch.object(main, "db_record_stats") as stats:
            result = await main.end_session_endpoint("legacy")
        self.assertEqual(result.tips, ["One", "Two", "Three"])
        self.assertEqual(result.best_response, "Sorry")
        self.assertEqual(result.worst_response, "Sorry")
        self.assertEqual(result.total_turns, 1)
        self.assertEqual(result.kind, "classic")
        self.assertEqual(result.meter_label, "Forgiveness")
        self.assertEqual(result.verdict, "😊 Almost there! She's softening up.")  # score 80, classic copy
        self.assertEqual(stats.call_args.args[0]["status"], "quit")
        self.assertEqual(stats.call_args.args[1], 1)

    async def test_debrief_falls_back_when_tips_fail(self):
        self.legacy_session()
        with patch.object(main, "sarvam_llm", AsyncMock(side_effect=RuntimeError("down"))):
            result = await main.end_session_endpoint("legacy")
        self.assertEqual(len(result.tips), 3)

    async def test_delete_session(self):
        started = await self.start_preset()
        self.assertEqual(await main.delete_session(started.session_id), {"deleted": True})
        with self.assertRaises(HTTPException) as ctx:
            await main.delete_session(started.session_id)
        self.assertEqual(ctx.exception.status_code, 404)
        with self.assertRaises(HTTPException):
            await main.get_session(started.session_id)


# ═══════════════════════════════════════════════════════════════════════════════

class _FailingTable:
    def __init__(self, error):
        self.error = error

    def __getattr__(self, name):
        def chain(*args, **kwargs):
            return self
        return chain

    def execute(self):
        raise self.error


class _FailingClient:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def table(self, name):
        self.calls += 1
        return _FailingTable(self.error)


class StorageTests(unittest.TestCase):
    def setUp(self):
        db.memory_sessions.clear()
        self.client = _FailingClient(RuntimeError("column brief does not exist"))
        self.patches = [patch.object(db, "supabase", self.client), patch.object(db, "_supabase_failed_at", None)]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        db.memory_sessions.clear()

    def test_breaker_opens_then_retries_after_window(self):
        # monotonic() is read once when the breaker opens (t=100), then on each readiness check.
        with patch.object(db.time, "monotonic", side_effect=[100.0, 130.0, 170.0]):
            db.db_create_session({"id": "s1", "difficulty": "open", "current_score": 50, "status": "ongoing", "conversation": []})
            self.assertEqual(self.client.calls, 1)
            self.assertIn("s1", db.memory_sessions)
            self.assertEqual(db.storage_mode(), "memory")        # 130 - 100 < 60: still open
            self.assertEqual(self.client.calls, 1)
            self.assertEqual(db.storage_mode(), "supabase")      # 170 - 100 >= 60: half-open, try again
            self.assertEqual(db.db_get_session("s1")["id"], "s1")  # memory first, no Supabase call
            self.assertEqual(self.client.calls, 1)
            db.db_update_session("s1", {"status": "quit"})
            self.assertEqual(db.memory_sessions["s1"]["status"], "quit")
            self.assertEqual(self.client.calls, 1)

    def test_normalize_session_defaults(self):
        session = db.normalize_session({"id": "x", "conversation": [{"role": "girlfriend", "text": "hi"}], "skill_scores": None})
        self.assertEqual(session["conversation"][0]["role"], "counterpart")
        self.assertEqual(session["skill_scores"], {})
        self.assertIsNone(session["brief"])
        self.assertIsNone(db.normalize_session(None))


if __name__ == "__main__":
    unittest.main()
