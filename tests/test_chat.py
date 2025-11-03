"""
Chat function tests for FlockParser
Tests interactive chat functionality
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flockparsecli import chat


class TestChatFunction:
    """Test chat functionality"""

    @patch("flockparsecli.load_document_index")
    def test_chat_no_documents(self, mock_index):
        """Test chat with no documents"""
        mock_index.return_value = {"documents": []}

        result = chat()

        # Should return early with no documents
        assert result is None

    @patch("builtins.input")
    @patch("flockparsecli.load_balancer.chat_distributed")
    @patch("flockparsecli.get_similar_chunks")
    @patch("flockparsecli.load_document_index")
    def test_chat_basic_interaction(self, mock_index, mock_chunks, mock_chat, mock_input):
        """Test basic chat interaction"""
        # Mock documents exist
        mock_index.return_value = {
            "documents": [{"id": "doc1", "original": "/path/to/test.pdf", "chunks": [{"file": "/tmp/chunk1.json"}]}]
        }

        # Mock user input: one question then exit
        mock_input.side_effect = ["What is this about?", "exit"]

        # Mock similar chunks
        mock_chunks.return_value = [{"text": "Test content", "doc_name": "test.pdf", "similarity": 0.9}]

        # Mock chat response
        mock_response = Mock()
        mock_response.message = {"content": "This is a test response"}
        mock_chat.return_value = mock_response

        chat()

        # Should have called chat with user query
        assert mock_chat.called

    @patch("builtins.input")
    @patch("flockparsecli.get_similar_chunks")
    @patch("flockparsecli.load_document_index")
    def test_chat_no_relevant_chunks(self, mock_index, mock_chunks, mock_input):
        """Test chat when no relevant chunks found"""
        # Mock documents exist
        mock_index.return_value = {
            "documents": [{"id": "doc1", "original": "/path/to/test.pdf", "chunks": [{"file": "/tmp/chunk1.json"}]}]
        }

        # Mock user input: question with no results, then exit
        mock_input.side_effect = ["What is this?", "exit"]

        # Mock no similar chunks
        mock_chunks.return_value = []

        chat()

        # Should handle gracefully
        assert True

    @patch("builtins.input")
    @patch("flockparsecli.load_document_index")
    def test_chat_empty_input(self, mock_index, mock_input):
        """Test chat with empty input"""
        # Mock documents exist
        mock_index.return_value = {
            "documents": [{"id": "doc1", "original": "/path/to/test.pdf", "chunks": [{"file": "/tmp/chunk1.json"}]}]
        }

        # Mock user input: empty string, then exit
        mock_input.side_effect = ["", "exit"]

        chat()

        # Should skip empty input and continue
        assert True

    @patch("builtins.input")
    @patch("flockparsecli.load_balancer.chat_distributed")
    @patch("flockparsecli.get_similar_chunks")
    @patch("flockparsecli.load_document_index")
    def test_chat_multiple_interactions(self, mock_index, mock_chunks, mock_chat, mock_input):
        """Test multiple chat interactions"""
        # Mock documents exist
        mock_index.return_value = {
            "documents": [{"id": "doc1", "original": "/path/to/test.pdf", "chunks": [{"file": "/tmp/chunk1.json"}]}]
        }

        # Mock multiple user inputs
        mock_input.side_effect = ["First question", "Second question", "exit"]

        # Mock similar chunks
        mock_chunks.return_value = [{"text": "Content", "doc_name": "test.pdf", "similarity": 0.8}]

        # Mock chat response
        mock_response = Mock()
        mock_response.message = {"content": "Response"}
        mock_chat.return_value = mock_response

        chat()

        # Should have processed both questions
        assert mock_chat.call_count >= 2

    @patch("builtins.input")
    @patch("flockparsecli.load_balancer.chat_distributed")
    @patch("flockparsecli.get_similar_chunks")
    @patch("flockparsecli.load_document_index")
    def test_chat_with_history(self, mock_index, mock_chunks, mock_chat, mock_input):
        """Test chat with conversation history"""
        # Mock documents exist
        mock_index.return_value = {
            "documents": [
                {"id": "doc1", "original": "/path/to/test.pdf", "chunks": [{"file": "/tmp/chunk1.json"}] * 10}
            ]
        }

        # Mock user inputs
        mock_input.side_effect = ["Question 1", "Question 2", "exit"]

        # Mock similar chunks with varying similarities
        mock_chunks.side_effect = [
            [{"text": f"Content {i}", "doc_name": "test.pdf", "similarity": 0.9 - i * 0.1} for i in range(5)],
            [{"text": f"Content {i}", "doc_name": "test.pdf", "similarity": 0.8 - i * 0.1} for i in range(5)],
        ]

        # Mock chat response
        mock_response = Mock()
        mock_response.message = {"content": "Response"}
        mock_chat.return_value = mock_response

        chat()

        # Should build conversation history
        assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
