"""Tests for skills tools"""
from iribot.tools.skills import UseSkillTool


class TestUseSkillTool:
    """Tests for UseSkillTool"""

    def test_use_main_skill(self, tmp_path, monkeypatch):
        """Test using a main skill"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        python_skill = skills_dir / "python"
        python_skill.mkdir()
        content = "# Python Development\n\nBest practices for Python."
        (python_skill / "SKILL.md").write_text(content)

        monkeypatch.setattr("iribot.tools.skills.SKILLS_DIR", skills_dir)

        tool = UseSkillTool()
        result = tool.execute(skill_id="python")

        assert result["success"] is True
        assert result["skill_id"] == "python"
        assert result["content"] == content

    def test_use_sub_skill_as_file(self, tmp_path, monkeypatch):
        """Test using a sub-skill stored as a file"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        python_skill = skills_dir / "python"
        python_skill.mkdir()
        (python_skill / "SKILL.md").write_text("# Python")

        sub_content = "# Debugging\n\nDebug techniques."
        (python_skill / "debugging.md").write_text(sub_content)

        monkeypatch.setattr("iribot.tools.skills.SKILLS_DIR", skills_dir)

        tool = UseSkillTool()
        result = tool.execute(skill_id="python/debugging")

        assert result["success"] is True
        assert result["content"] == sub_content

    def test_use_sub_skill_as_directory(self, tmp_path, monkeypatch):
        """Test using a sub-skill stored as a directory with SKILL.md"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        python_skill = skills_dir / "python"
        python_skill.mkdir()

        debugging_dir = python_skill / "debugging"
        debugging_dir.mkdir()
        sub_content = "# Debugging Guide"
        (debugging_dir / "SKILL.md").write_text(sub_content)

        monkeypatch.setattr("iribot.tools.skills.SKILLS_DIR", skills_dir)

        tool = UseSkillTool()
        result = tool.execute(skill_id="python/debugging")

        assert result["success"] is True
        assert result["content"] == sub_content

    def test_use_nonexistent_skill(self, tmp_path, monkeypatch):
        """Test using a skill that doesn't exist"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()

        monkeypatch.setattr("iribot.tools.skills.SKILLS_DIR", skills_dir)

        tool = UseSkillTool()
        result = tool.execute(skill_id="nonexistent")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_use_skill_no_directory(self, tmp_path, monkeypatch):
        """Test using a skill when skills directory doesn't exist"""
        skills_dir = tmp_path / "nonexistent"

        monkeypatch.setattr("iribot.tools.skills.SKILLS_DIR", skills_dir)

        tool = UseSkillTool()
        result = tool.execute(skill_id="python")

        assert result["success"] is False
        assert "not found" in result["error"]
