"""Tests for Worklist routing upgrade (A5)."""
import pytest
from unittest.mock import MagicMock, patch
from src.collaboration.a2a_controller import A2AController, parse_a2a_mentions


class TestParseA2aMentions:
    def test_single_mention(self):
        result = parse_a2a_mentions("@opus help me", {"opus", "sonnet"})
        assert result == ["opus"]

    def test_multiple_mentions(self):
        result = parse_a2a_mentions("@opus and @sonnet please", {"opus", "sonnet"})
        assert "opus" in result
        assert "sonnet" in result

    def test_no_mentions(self):
        result = parse_a2a_mentions("no mentions here", {"opus", "sonnet"})
        assert result == []

    def test_unknown_mention_ignored(self):
        result = parse_a2a_mentions("@unknown_cat help", {"opus", "sonnet"})
        assert result == []

    def test_duplicate_mention_deduplicated(self):
        result = parse_a2a_mentions("@opus @opus help", {"opus"})
        assert len(result) == 1

    def test_mixed_known_and_unknown(self):
        result = parse_a2a_mentions("@opus @unknown @sonnet", {"opus", "sonnet"})
        assert set(result) == {"opus", "sonnet"}

    def test_empty_content(self):
        result = parse_a2a_mentions("", {"opus"})
        assert result == []

    def test_empty_cat_ids(self):
        result = parse_a2a_mentions("@opus help", set())
        assert result == []

    def test_mention_at_end_of_sentence(self):
        result = parse_a2a_mentions("I need help from @opus.", {"opus"})
        assert result == ["opus"]

    def test_mention_with_punctuation(self):
        result = parse_a2a_mentions("@opus, @sonnet!", {"opus", "sonnet"})
        assert set(result) == {"opus", "sonnet"}


def make_mock_agent(breed_id, name="TestCat"):
    agent = MagicMock()
    agent["breed_id"] = breed_id
    agent["name"] = name
    agent["service"] = MagicMock()
    return agent


def make_controller(agents=None):
    if agents is None:
        agents = []
    controller = A2AController(
        agents=agents,
        session_chain=None,
        dag_executor=None,
        template_factory=None,
        memory_service=None,
    )
    return controller


class TestWorklistSerialExecute:
    @pytest.mark.asyncio
    async def test_basic_serial_execution(self):
        """Agents execute in order when no mentions."""
        a1 = make_mock_agent("opus", "Opus")
        a2 = make_mock_agent("sonnet", "Sonnet")
        ctrl = make_controller([a1, a2])

        thread = MagicMock()
        thread.messages = []
        thread.add_message = MagicMock()

        responses = []

        async def _agen(*args, **kwargs):
            for resp in [
                MagicMock(content="response from opus", targetCats=None),
                MagicMock(content="response from sonnet", targetCats=None),
            ]:
                yield resp

        mock_call = MagicMock(side_effect=_agen)
        with patch.object(ctrl, "_call_cat", mock_call):
            async for r in ctrl._serial_execute("hello", thread):
                responses.append(r)

        assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_mentions_extend_worklist(self):
        """@mentions in response extend the worklist."""
        a1 = make_mock_agent("opus", "Opus")
        a2 = make_mock_agent("sonnet", "Sonnet")
        a3 = make_mock_agent("haiku", "Haiku")
        ctrl = make_controller([a1, a2, a3])

        thread = MagicMock()
        thread.messages = []
        thread.add_message = MagicMock()

        # opus mentions @haiku
        r1 = MagicMock(content="@haiku please review", targetCats=None)
        # sonnet responds
        r2 = MagicMock(content="done from sonnet", targetCats=None)
        # haiku responds (was added via mention)
        r3 = MagicMock(content="done", targetCats=None)

        async def _agen(*args, **kwargs):
            for resp in [r1, r2, r3]:
                yield resp

        mock_call = MagicMock(side_effect=_agen)
        with patch.object(ctrl, "_call_cat", mock_call):
            responses = []
            async for r in ctrl._serial_execute("hello", thread):
                responses.append(r)

        # All 3 agents called: opus, sonnet (initial worklist), haiku (via mention)
        assert mock_call.call_count == 3

    @pytest.mark.asyncio
    async def test_worklist_depth_limited(self):
        """Worklist respects max_depth to prevent infinite chains."""
        a1 = make_mock_agent("opus", "Opus")
        a2 = make_mock_agent("sonnet", "Sonnet")
        ctrl = make_controller([a1, a2])

        thread = MagicMock()
        thread.messages = []
        thread.add_message = MagicMock()

        # Each response mentions the other cat, creating a potential infinite loop
        async def _agen(*args, **kwargs):
            breed_id = args[2]
            other = "sonnet" if breed_id == "opus" else "opus"
            yield MagicMock(content=f"@{other} ping", targetCats=None)

        mock_call = MagicMock(side_effect=_agen)
        with patch.object(ctrl, "_call_cat", mock_call):
            responses = []
            async for r in ctrl._serial_execute("hello", thread):
                responses.append(r)

        # Should not loop infinitely; total calls should be bounded
        assert mock_call.call_count <= 10  # reasonable upper bound

    @pytest.mark.asyncio
    async def test_deduplication_prevents_reexecution(self):
        """Already-executed cats are not re-added to worklist."""
        a1 = make_mock_agent("opus", "Opus")
        a2 = make_mock_agent("sonnet", "Sonnet")
        ctrl = make_controller([a1, a2])

        thread = MagicMock()
        thread.messages = []
        thread.add_message = MagicMock()

        # opus mentions @opus (itself) -- should be ignored
        r1 = MagicMock(content="@opus self-ref @sonnet cross-ref", targetCats=None)
        r2 = MagicMock(content="done", targetCats=None)
        r3 = MagicMock(content="done again", targetCats=None)

        async def _agen(*args, **kwargs):
            for resp in [r1, r2, r3]:
                yield resp

        mock_call = MagicMock(side_effect=_agen)
        with patch.object(ctrl, "_call_cat", mock_call):
            responses = []
            async for r in ctrl._serial_execute("hello", thread):
                responses.append(r)

        # opus should not be called again; sonnet called once
        # Total: opus (initial) + sonnet (initial or mentioned) = 2
        assert mock_call.call_count == 2

    @pytest.mark.asyncio
    async def test_fairness_gate_with_user_queue(self):
        """Fairness gate: don't append new cats if user messages are queued."""
        # Set up agents: opus has targetCats (in initial worklist), sonnet does not
        a1 = {"breed_id": "opus", "name": "Opus", "service": MagicMock(), "targetCats": ["opus"]}
        a2 = {"breed_id": "sonnet", "name": "Sonnet", "service": MagicMock()}
        ctrl = make_controller([a1, a2])

        thread = MagicMock()
        thread.messages = []
        thread.add_message = MagicMock()

        # Simulate user messages queued
        ctrl._user_queue_has_pending = MagicMock(return_value=True)

        # opus mentions @sonnet, but fairness gate should block adding sonnet
        r1 = MagicMock(content="@sonnet please help", targetCats=None)

        async def _agen(*args, **kwargs):
            for resp in [r1]:
                yield resp

        mock_call = MagicMock(side_effect=_agen)
        with patch.object(ctrl, "_call_cat", mock_call):
            responses = []
            async for r in ctrl._serial_execute("hello", thread):
                responses.append(r)

        # sonnet should NOT have been appended to worklist due to fairness gate
        # Only opus (initial worklist) runs
        assert mock_call.call_count == 1

    @pytest.mark.asyncio
    async def test_empty_agents_list(self):
        """Empty agent list produces no responses."""
        ctrl = make_controller([])
        thread = MagicMock()
        thread.messages = []
        thread.add_message = MagicMock()

        responses = []
        async for r in ctrl._serial_execute("hello", thread):
            responses.append(r)

        assert responses == []
