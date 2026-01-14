"""Tests for prompt builder"""
import pytest
from br_llm_client import PromptBuilder, BR_PROMPTS


class TestPromptBuilder:
    """Tests for PromptBuilder"""
    
    def test_get_template(self):
        builder = PromptBuilder()
        template = builder.get_template("expense_qualification")
        
        assert template is not None
        assert template.name == "expense_qualification"
    
    def test_get_unknown_template(self):
        builder = PromptBuilder()
        template = builder.get_template("nonexistent")
        
        assert template is None
    
    def test_build_expense_qualification(self):
        builder = PromptBuilder()
        
        system, user = builder.build_expense_qualification(
            description="Zakup serwera",
            amount=15000,
            vendor="Dell",
            category="equipment",
            date="2025-01-10",
        )
        
        assert "ekspert" in system.lower() or "b+r" in system.lower()
        assert "15000" in user
        assert "Dell" in user
        assert "serwer" in user.lower()
    
    def test_build_document_review(self):
        builder = PromptBuilder()
        
        system, user = builder.build_document_review(
            document_content="# Test Document\n\nContent here",
            document_type="project_card",
            year=2025,
        )
        
        assert "Test Document" in user
        assert "project_card" in user
        assert "2025" in user
    
    def test_build_nexus_explanation(self):
        builder = PromptBuilder()
        
        system, user = builder.build_nexus_explanation(
            a=50000,
            b=10000,
            c=5000,
            d=0,
            nexus=0.95,
        )
        
        assert "50000" in user
        assert "10000" in user
        assert "0.95" in user
        assert "Nexus" in user


class TestBRPrompts:
    """Tests for BR_PROMPTS dictionary"""
    
    def test_all_prompts_have_required_fields(self):
        for name, template in BR_PROMPTS.items():
            assert template.name == name
            assert template.system_prompt
            assert template.user_prompt_template
    
    def test_expense_qualification_exists(self):
        assert "expense_qualification" in BR_PROMPTS
    
    def test_document_review_exists(self):
        assert "document_review" in BR_PROMPTS
    
    def test_nexus_explanation_exists(self):
        assert "nexus_explanation" in BR_PROMPTS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
