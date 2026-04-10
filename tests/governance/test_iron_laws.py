"""Iron laws system tests"""
from src.governance.iron_laws import IRON_LAWS, get_iron_laws_prompt


class TestIronLaws:
    def test_four_laws_defined(self):
        """Exactly 4 iron laws exist"""
        assert len(IRON_LAWS) == 4

    def test_each_law_has_required_fields(self):
        """Each law has id, title, description, constraints"""
        for law in IRON_LAWS:
            assert "id" in law
            assert "title" in law
            assert "description" in law
            assert "constraints" in law
            assert len(law["constraints"]) >= 2

    def test_law_ids_are_unique(self):
        """No duplicate law IDs"""
        ids = [law["id"] for law in IRON_LAWS]
        assert len(ids) == len(set(ids))

    def test_law_ids(self):
        """Specific law IDs exist"""
        ids = {law["id"] for law in IRON_LAWS}
        assert "data-safety" in ids
        assert "process-protection" in ids
        assert "config-readonly" in ids
        assert "network-boundary" in ids


class TestGetIronLawsPrompt:
    def test_returns_non_empty_string(self):
        prompt = get_iron_laws_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_contains_header(self):
        prompt = get_iron_laws_prompt()
        assert "铁律" in prompt

    def test_contains_all_titles(self):
        prompt = get_iron_laws_prompt()
        for law in IRON_LAWS:
            assert law["title"] in prompt

    def test_contains_all_constraints(self):
        prompt = get_iron_laws_prompt()
        for law in IRON_LAWS:
            for constraint in law["constraints"]:
                assert constraint in prompt

    def test_laws_section_before_other_sections(self):
        """Iron laws prompt starts with the header"""
        prompt = get_iron_laws_prompt()
        assert prompt.startswith("# 铁律")
