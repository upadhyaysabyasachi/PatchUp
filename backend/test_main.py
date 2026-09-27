"""Offline regression tests: python3 -m unittest discover -s backend -v."""
import json
import os
import unittest
from unittest.mock import AsyncMock, patch

# Never initialize a real database client during test discovery.
with patch.dict(os.environ, {"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": ""}):
    import main


class ParsingTests(unittest.TestCase):
    def test_actor_wrappers_and_number_repair(self):
        payload = '{"response":"Cost: +20", "score_delta":+12}'
        for raw in (payload, f"```json\n{payload}\n```", f"Here it is: {payload} Done."):
            with self.subTest(raw=raw):
                parsed = main.parse_llm_json(raw)
                self.assertEqual(parsed["score_delta"], 12)
                self.assertEqual(parsed["response"], "Cost: +20")

    def test_actor_invalid_shapes_fall_back(self):
        for raw in ('[]', 'null', '42', '"hello"', '{broken', ''):
            with self.subTest(raw=raw):
                parsed = main.parse_llm_json(raw)
                self.assertIsInstance(parsed, dict)
                self.assertEqual(parsed["score_delta"], 0)

    def test_tips_wrappers(self):
        payload = '["Listen", "Be specific", "Agree next steps"]'
        for raw in (payload, f"```json\n{payload}\n```", f"Tips: {payload}"):
            self.assertEqual(main.parse_tips(raw), json.loads(payload))

    def test_invalid_tips(self):
        for raw in ('{}', '["one"]', '["one", null, "three"]', '["one", " ", "three"]'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                main.parse_tips(raw)


class ConversationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = patch.object(main, "supabase", None)
        self.db.start()
        main.memory_sessions.clear()
        self.session = {
            "id": "test", "persona_id": "priya", "scenario_id": next(iter(main.SCENARIOS)),
            "difficulty": "medium", "language": "en-IN", "current_score": 80,
            "status": "ongoing", "system_prompt": "Practice",
            "conversation": [{"role": "girlfriend", "text": "Opening", "score_delta": 0}],
        }
        main.memory_sessions["test"] = self.session

    def tearDown(self):
        main.memory_sessions.clear()
        self.db.stop()

    async def respond(self, payload):
        with patch.object(main, "sarvam_llm", AsyncMock(return_value=json.dumps(payload))) as llm, \
             patch.object(main, "sarvam_tts", AsyncMock(return_value="audio")):
            result = await main.process_user_message("test", "I understand")
            self.assertEqual(llm.call_args.args[0][1]["role"], "user")
            return result

    async def test_success_at_90_and_legacy_session(self):
        result = await self.respond({"response": "Thanks", "score_delta": 10})
        self.assertEqual(result.status, "patched_up")
        self.assertEqual(result.counterpart_text, "Thanks")
        self.assertEqual(result.model_dump()["girlfriend_text"], "Thanks")
        self.assertEqual(result.model_dump()["girlfriend_audio"], "audio")
        self.assertEqual(result.turn_number, 1)
        self.assertEqual([t["role"] for t in self.session["conversation"]],
                         ["counterpart", "user", "counterpart"])

    async def test_end_flags_cannot_override_score(self):
        result = await self.respond({"response": "Okay", "score_delta": 9,
                                     "should_end": True, "end_reason": "patched_up"})
        self.assertEqual(result.status, "ongoing")

    async def test_blocked_at_zero(self):
        self.session["current_score"] = 10
        result = await self.respond({"response": "Enough", "score_delta": -10})
        self.assertEqual(result.status, "blocked")

    async def test_invalid_fields_do_not_crash(self):
        result = await self.respond({"response": None, "score_delta": "n/a", "emotion": []})
        self.assertEqual(result.current_score, 80)
        self.assertEqual(result.emotion, "angry")

    async def test_debrief_ignores_opening_and_counts_legacy_roles(self):
        self.session["conversation"] += [
            {"role": "boyfriend", "text": "Sorry"},
            {"role": "girlfriend", "text": "Thanks", "score_delta": 10},
        ]
        with patch.object(main, "sarvam_llm", AsyncMock(return_value='```json\n["One", "Two", "Three"]\n```')), \
             patch.object(main, "db_record_stats") as stats:
            result = await main.end_session_endpoint("test")
        self.assertEqual(result.tips, ["One", "Two", "Three"])
        self.assertEqual(result.best_response, "Sorry")
        self.assertEqual(result.worst_response, "Sorry")
        self.assertEqual(result.total_turns, 1)
        self.assertEqual(stats.call_args.args[-2:], ("quit", 1))


if __name__ == "__main__":
    unittest.main()
