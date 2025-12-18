"""Synthesis app tests."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestLLMService:
    """Test LLM service."""

    def test_generate_response(self, mock_openai_client, mock_settings):
        """Test response generation."""
        with patch("openai.OpenAI", return_value=mock_openai_client):
            from apps.synthesis.services.pipeline import LLMService

            service = LLMService(api_key="test-key")
            text, tokens = service.generate(
                system_prompt="You are helpful", user_prompt="What is your experience?"
            )

            assert "Generated response" in text
            assert tokens > 0


class TestPromptBuilder:
    """Test prompt builder."""

    def test_build_system_prompt(self):
        """Test system prompt building."""
        from apps.synthesis.services.pipeline import PromptBuilder

        builder = PromptBuilder()
        prompt = builder.build_system_prompt()

        assert "portfolio" in prompt.lower() or "helpful" in prompt.lower()

    def test_build_user_prompt(self, mock_retrieval_result):
        """Test user prompt building."""
        from apps.synthesis.services.pipeline import PromptBuilder

        builder = PromptBuilder()
        context_text = "I have 5 years of Python experience"
        prompt = builder.build_user_prompt(query="What is your experience?", context=context_text)

        assert "What is your experience?" in prompt


class TestSynthesisPipeline:
    """Test full synthesis pipeline."""

    def test_prompt_builder(self, mock_retrieval_result):
        """Test prompt building in pipeline."""
        from apps.synthesis.services.pipeline import SynthesisPipeline, PromptBuilder

        builder = PromptBuilder()
        system_prompt = builder.build_system_prompt()
        user_prompt = builder.build_user_prompt(
            query="What is your experience?", context="I have 5 years of Python experience"
        )

        assert system_prompt is not None
        assert "helpful" in system_prompt.lower()
        assert user_prompt is not None
        assert "What is your experience?" in user_prompt
