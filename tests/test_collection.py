"""Collection Layer Tests (Person 1: Raghav)"""
import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# GitHub Agent Tests
# ---------------------------------------------------------------------------


class TestSearchGithubRepos:
    """Tests for search_github_repos tool function."""

    def test_search_github_repos_returns_repo_list(self):
        """search_github_repos returns dict with 'repos' key containing list of dicts."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "owner/repo1",
                    "html_url": "https://github.com/owner/repo1",
                    "stargazers_count": 1000,
                    "language": "Python",
                    "topics": ["ml", "ai"],
                    "fork": False,
                    "created_at": "2023-01-01T00:00:00Z",
                },
                {
                    "full_name": "owner/repo2",
                    "html_url": "https://github.com/owner/repo2",
                    "stargazers_count": 500,
                    "language": "JavaScript",
                    "topics": [],
                    "fork": False,
                    "created_at": "2023-06-01T00:00:00Z",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
                from src.agents.collection.github_agent import search_github_repos

                result = asyncio.run(
                    search_github_repos("machine learning", language="python", min_stars=50)
                )

        assert "repos" in result
        assert isinstance(result["repos"], list)
        assert len(result["repos"]) == 2

    def test_search_github_repos_each_repo_has_required_keys(self):
        """Each repo dict in search results has required keys."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "full_name": "owner/repo1",
                    "html_url": "https://github.com/owner/repo1",
                    "stargazers_count": 1000,
                    "language": "Python",
                    "topics": ["ml"],
                    "fork": False,
                    "created_at": "2023-01-01T00:00:00Z",
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("requests.get", return_value=mock_response):
            with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
                from src.agents.collection.github_agent import search_github_repos

                result = asyncio.run(search_github_repos("machine learning"))

        repo = result["repos"][0]
        required_keys = {"name", "url", "stars", "language", "topics", "is_fork", "created_at"}
        assert required_keys.issubset(set(repo.keys()))


class TestFetchRepoDetails:
    """Tests for fetch_repo_details tool function."""

    def test_fetch_repo_details_star_velocity_clamped(self):
        """fetch_repo_details returns star_velocity clamped to [-1.0, 1.0]."""
        # Recent 100 stargazers all within last 30 days (high velocity)
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        recent_time = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        stargazers_response = MagicMock()
        stargazers_response.status_code = 200
        stargazers_response.json.return_value = [
            {"starred_at": recent_time, "user": {"login": f"user{i}"}}
            for i in range(100)
        ]
        stargazers_response.raise_for_status = MagicMock()

        repo_response = MagicMock()
        repo_response.status_code = 200
        repo_response.json.return_value = {
            "stargazers_count": 50,  # total stars less than recent = velocity > 1 before clamp
            "open_issues_count": 10,
        }
        repo_response.raise_for_status = MagicMock()

        # commit_activity 202 then success
        commit_activity_response = MagicMock()
        commit_activity_response.status_code = 200
        commit_activity_response.json.return_value = [
            {"total": 5, "week": 1700000000, "days": [1, 0, 1, 2, 1, 0, 0]}
            for _ in range(4)
        ]
        commit_activity_response.raise_for_status = MagicMock()

        contributors_response = MagicMock()
        contributors_response.status_code = 200
        contributors_response.json.return_value = [{"author": {"login": "user1"}}] * 5
        contributors_response.raise_for_status = MagicMock()

        call_count = [0]

        def mock_get(url, **kwargs):
            call_count[0] += 1
            if "stargazers" in url:
                return stargazers_response
            elif "stats/commit_activity" in url:
                return commit_activity_response
            elif "stats/contributors" in url:
                return contributors_response
            else:
                return repo_response

        with patch("requests.get", side_effect=mock_get):
            with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
                from src.agents.collection.github_agent import fetch_repo_details

                result = asyncio.run(fetch_repo_details("owner", "repo"))

        assert "star_velocity" in result
        assert -1.0 <= result["star_velocity"] <= 1.0

    def test_fetch_repo_details_returns_required_keys(self):
        """fetch_repo_details returns dict with all required keys."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=15)
        recent_time = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        stargazers_response = MagicMock()
        stargazers_response.status_code = 200
        stargazers_response.json.return_value = [
            {"starred_at": recent_time, "user": {"login": "user1"}}
        ]
        stargazers_response.raise_for_status = MagicMock()

        repo_response = MagicMock()
        repo_response.status_code = 200
        repo_response.json.return_value = {
            "stargazers_count": 1000,
            "open_issues_count": 42,
        }
        repo_response.raise_for_status = MagicMock()

        commit_activity_response = MagicMock()
        commit_activity_response.status_code = 200
        commit_activity_response.json.return_value = [
            {"total": 10, "week": 1700000000, "days": [1, 2, 1, 2, 1, 2, 1]}
            for _ in range(4)
        ]
        commit_activity_response.raise_for_status = MagicMock()

        contributors_response = MagicMock()
        contributors_response.status_code = 200
        contributors_response.json.return_value = [{"author": {"login": f"user{i}"}} for i in range(10)]
        contributors_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if "stargazers" in url:
                return stargazers_response
            elif "stats/commit_activity" in url:
                return commit_activity_response
            elif "stats/contributors" in url:
                return contributors_response
            else:
                return repo_response

        with patch("requests.get", side_effect=mock_get):
            with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
                from src.agents.collection.github_agent import fetch_repo_details

                result = asyncio.run(fetch_repo_details("owner", "repo"))

        required_keys = {"star_velocity", "commits", "contributors", "issues"}
        assert required_keys.issubset(set(result.keys()))

    def test_fetch_repo_details_handles_202_retry(self):
        """fetch_repo_details retries when GitHub returns 202 for stats endpoints."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=15)
        recent_time = cutoff.strftime("%Y-%m-%dT%H:%M:%SZ")

        stargazers_response = MagicMock()
        stargazers_response.status_code = 200
        stargazers_response.json.return_value = [
            {"starred_at": recent_time, "user": {"login": "user1"}}
        ]
        stargazers_response.raise_for_status = MagicMock()

        repo_response = MagicMock()
        repo_response.status_code = 200
        repo_response.json.return_value = {"stargazers_count": 1000, "open_issues_count": 5}
        repo_response.raise_for_status = MagicMock()

        # First call to commit_activity returns 202, second returns 200
        commit_202 = MagicMock()
        commit_202.status_code = 202
        commit_202.json.return_value = {}
        commit_202.raise_for_status = MagicMock()

        commit_200 = MagicMock()
        commit_200.status_code = 200
        commit_200.json.return_value = [
            {"total": 8, "week": 1700000000, "days": [1, 1, 1, 1, 1, 1, 2]}
            for _ in range(4)
        ]
        commit_200.raise_for_status = MagicMock()

        contributors_response = MagicMock()
        contributors_response.status_code = 200
        contributors_response.json.return_value = [{"author": {"login": "user1"}}] * 3
        contributors_response.raise_for_status = MagicMock()

        commit_call_count = [0]

        def mock_get(url, **kwargs):
            if "stargazers" in url:
                return stargazers_response
            elif "stats/commit_activity" in url:
                commit_call_count[0] += 1
                if commit_call_count[0] == 1:
                    return commit_202
                return commit_200
            elif "stats/contributors" in url:
                return contributors_response
            else:
                return repo_response

        with patch("requests.get", side_effect=mock_get):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
                    from src.agents.collection.github_agent import fetch_repo_details

                    result = asyncio.run(fetch_repo_details("owner", "repo"))

        # Should have retried at least once
        assert commit_call_count[0] >= 2
        assert "commits" in result


class TestGithubAgentInstance:
    """Tests for github_agent LlmAgent instance."""

    def test_github_agent_is_llm_agent(self):
        """github_agent is an LlmAgent instance with correct name."""
        from google.adk.agents.llm_agent import LlmAgent

        with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
            from src.agents.collection.github_agent import github_agent

        assert isinstance(github_agent, LlmAgent)
        assert github_agent.name == "github_agent"

    def test_github_agent_has_output_key(self):
        """github_agent has output_key set to 'github_results'."""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}):
            from src.agents.collection.github_agent import github_agent

        assert github_agent.output_key == "github_results"


# ---------------------------------------------------------------------------
# HN+Tavily Agent Tests
# ---------------------------------------------------------------------------


class TestFetchHnTopStories:
    """Tests for fetch_hn_top_stories tool function."""

    def test_fetch_hn_top_stories_returns_stories(self):
        """fetch_hn_top_stories returns dict with 'stories' key."""
        topstories_response = MagicMock()
        topstories_response.status_code = 200
        topstories_response.json.return_value = [1, 2, 3, 4, 5]
        topstories_response.raise_for_status = MagicMock()

        story_response = MagicMock()
        story_response.status_code = 200
        story_response.json.return_value = {
            "id": 1,
            "type": "story",
            "title": "Test Story",
            "url": "https://example.com",
            "score": 100,
            "time": 1700000000,
            "by": "testuser",
        }
        story_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if "topstories" in url:
                return topstories_response
            return story_response

        with patch("requests.get", side_effect=mock_get):
            from src.agents.collection.hn_tavily_agent import fetch_hn_top_stories

            result = asyncio.run(fetch_hn_top_stories(limit=5))

        assert "stories" in result
        assert isinstance(result["stories"], list)

    def test_fetch_hn_top_stories_each_story_has_required_keys(self):
        """Each story dict has required keys: title, url, score, time, by."""
        topstories_response = MagicMock()
        topstories_response.status_code = 200
        topstories_response.json.return_value = [42]
        topstories_response.raise_for_status = MagicMock()

        story_response = MagicMock()
        story_response.status_code = 200
        story_response.json.return_value = {
            "id": 42,
            "type": "story",
            "title": "Test Story",
            "url": "https://example.com",
            "score": 200,
            "time": 1700000000,
            "by": "user123",
        }
        story_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if "topstories" in url:
                return topstories_response
            return story_response

        with patch("requests.get", side_effect=mock_get):
            from src.agents.collection.hn_tavily_agent import fetch_hn_top_stories

            result = asyncio.run(fetch_hn_top_stories(limit=1))

        assert len(result["stories"]) >= 1
        story = result["stories"][0]
        required_keys = {"title", "url", "score", "time", "by"}
        assert required_keys.issubset(set(story.keys()))

    def test_fetch_hn_top_stories_concurrent_fetch(self):
        """HN stories are fetched concurrently using asyncio.gather."""
        import inspect
        import src.agents.collection.hn_tavily_agent as module

        source = inspect.getsource(module.fetch_hn_top_stories)
        assert "asyncio.gather" in source, "fetch_hn_top_stories must use asyncio.gather for concurrent fetching"

    def test_fetch_hn_top_stories_url_fallback(self):
        """Stories without url use HN item URL fallback."""
        topstories_response = MagicMock()
        topstories_response.status_code = 200
        topstories_response.json.return_value = [99]
        topstories_response.raise_for_status = MagicMock()

        story_response = MagicMock()
        story_response.status_code = 200
        story_response.json.return_value = {
            "id": 99,
            "type": "story",
            "title": "Ask HN: No URL post",
            # No "url" key — should fall back
            "score": 50,
            "time": 1700000000,
            "by": "poster",
        }
        story_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if "topstories" in url:
                return topstories_response
            return story_response

        with patch("requests.get", side_effect=mock_get):
            from src.agents.collection.hn_tavily_agent import fetch_hn_top_stories

            result = asyncio.run(fetch_hn_top_stories(limit=1))

        assert len(result["stories"]) >= 1
        assert "ycombinator.com/item?id=99" in result["stories"][0]["url"]


class TestSearchTavilyNews:
    """Tests for search_tavily_news tool function."""

    def test_search_tavily_news_returns_results(self):
        """search_tavily_news returns dict with 'results' key."""
        mock_search_response = {
            "results": [
                {
                    "title": "AI Funding News",
                    "url": "https://techcrunch.com/ai-funding",
                    "content": "Major funding round announced...",
                    "score": 0.95,
                    "published_date": "2024-01-15",
                }
            ]
        }

        with patch(
            "src.agents.collection.hn_tavily_agent.AsyncTavilyClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_search_response)
            mock_client_cls.return_value = mock_client

            with patch.dict(os.environ, {"TAVILY_API_KEY": "fake_key"}):
                from src.agents.collection.hn_tavily_agent import search_tavily_news

                result = asyncio.run(search_tavily_news("AI funding"))

        assert "results" in result
        assert isinstance(result["results"], list)
        assert len(result["results"]) >= 1

    def test_search_tavily_news_each_result_has_required_keys(self):
        """Each news result has required keys: title, url, content, score, published_date."""
        mock_search_response = {
            "results": [
                {
                    "title": "Test Article",
                    "url": "https://example.com/article",
                    "content": "Article content here...",
                    "score": 0.85,
                    "published_date": "2024-03-01",
                }
            ]
        }

        with patch(
            "src.agents.collection.hn_tavily_agent.AsyncTavilyClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(return_value=mock_search_response)
            mock_client_cls.return_value = mock_client

            with patch.dict(os.environ, {"TAVILY_API_KEY": "fake_key"}):
                from src.agents.collection.hn_tavily_agent import search_tavily_news

                result = asyncio.run(search_tavily_news("test query"))

        result_item = result["results"][0]
        required_keys = {"title", "url", "content", "score", "published_date"}
        assert required_keys.issubset(set(result_item.keys()))

    def test_search_tavily_news_fallback_no_key(self):
        """When TAVILY_API_KEY is missing, returns HN-only fallback."""
        env_without_tavily = {k: v for k, v in os.environ.items() if k != "TAVILY_API_KEY"}

        with patch.dict(os.environ, env_without_tavily, clear=True):
            from src.agents.collection.hn_tavily_agent import search_tavily_news

            result = asyncio.run(search_tavily_news("AI funding"))

        assert result == {"results": [], "fallback": True}

    def test_search_tavily_news_fallback_on_error(self):
        """When Tavily raises an exception, returns fallback result."""
        with patch(
            "src.agents.collection.hn_tavily_agent.AsyncTavilyClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.search = AsyncMock(side_effect=Exception("Quota exhausted"))
            mock_client_cls.return_value = mock_client

            with patch.dict(os.environ, {"TAVILY_API_KEY": "fake_key"}):
                from src.agents.collection.hn_tavily_agent import search_tavily_news

                result = asyncio.run(search_tavily_news("AI funding"))

        assert result["results"] == []
        assert result["fallback"] is True
        assert "error" in result


class TestHnTavilyAgentInstance:
    """Tests for hn_tavily_agent LlmAgent instance."""

    def test_hn_tavily_agent_is_llm_agent(self):
        """hn_tavily_agent is an LlmAgent instance with correct name."""
        from google.adk.agents.llm_agent import LlmAgent

        from src.agents.collection.hn_tavily_agent import hn_tavily_agent

        assert isinstance(hn_tavily_agent, LlmAgent)
        assert hn_tavily_agent.name == "hn_tavily_agent"

    def test_hn_tavily_agent_has_output_key(self):
        """hn_tavily_agent has output_key set to 'hn_tavily_results'."""
        from src.agents.collection.hn_tavily_agent import hn_tavily_agent

        assert hn_tavily_agent.output_key == "hn_tavily_results"


# ---------------------------------------------------------------------------
# RAG Ingestion Tests
# ---------------------------------------------------------------------------


class TestGetChromaCollection:
    """Tests for get_chroma_collection."""

    def test_get_chroma_collection_returns_collection(self):
        """get_chroma_collection returns a ChromaDB collection with SentenceTransformerEmbeddingFunction."""
        mock_collection = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_embedding_fn = MagicMock()

        with patch("chromadb.PersistentClient", return_value=mock_client):
            with patch(
                "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction",
                return_value=mock_embedding_fn,
            ):
                from src.rag.ingestion import get_chroma_collection

                result = get_chroma_collection()

        assert result is mock_collection
        mock_client.get_or_create_collection.assert_called_once()


class TestChunkText:
    """Tests for chunk_text."""

    def test_chunk_text_returns_list_of_strings(self):
        """chunk_text returns a list of non-empty string chunks."""
        from src.rag.ingestion import chunk_text

        text = "a" * 1200
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert isinstance(chunks, list)
        assert all(isinstance(c, str) for c in chunks)
        assert all(len(c) > 0 for c in chunks)

    def test_chunk_text_respects_chunk_size(self):
        """chunk_text produces chunks no larger than chunk_size."""
        from src.rag.ingestion import chunk_text

        text = "x" * 2000
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert all(len(c) <= 500 for c in chunks)

    def test_chunk_text_short_text_returns_single_chunk(self):
        """chunk_text returns a single chunk for text shorter than chunk_size."""
        from src.rag.ingestion import chunk_text

        text = "short text"
        chunks = chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_empty_string_returns_empty_list(self):
        """chunk_text returns empty list for empty string."""
        from src.rag.ingestion import chunk_text

        chunks = chunk_text("", chunk_size=500, overlap=50)
        assert chunks == []


class TestIngestHnStories:
    """Tests for ingest_hn_stories."""

    def test_ingest_hn_stories_calls_chroma_add(self):
        """ingest_hn_stories fetches HN stories and adds documents to ChromaDB."""
        mock_collection = MagicMock()
        mock_collection.add = MagicMock()
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        top_stories_response = MagicMock()
        top_stories_response.json.return_value = [1, 2]
        top_stories_response.raise_for_status = MagicMock()

        story_response = MagicMock()
        story_response.json.return_value = {
            "id": 1,
            "type": "story",
            "title": "Test Story",
            "url": "https://example.com/story",
            "text": "Some story text content here.",
            "time": 1700000000,
        }
        story_response.raise_for_status = MagicMock()

        def mock_get(url, **kwargs):
            if "topstories" in url:
                return top_stories_response
            return story_response

        with patch("chromadb.PersistentClient", return_value=mock_client):
            with patch(
                "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
            ):
                with patch("requests.get", side_effect=mock_get):
                    from src.rag.ingestion import ingest_hn_stories

                    count = asyncio.run(ingest_hn_stories(limit=2))

        assert isinstance(count, int)
        assert count >= 0
        mock_collection.add.assert_called()

    def test_ingest_hn_stories_uses_deterministic_ids(self):
        """ingest_hn_stories uses hashlib.sha256 for deterministic document IDs."""
        import inspect
        import src.rag.ingestion as module

        source = inspect.getsource(module)
        assert "hashlib.sha256" in source


# ---------------------------------------------------------------------------
# RAG Retrieval Tests
# ---------------------------------------------------------------------------


class TestQueryCorpus:
    """Tests for query_corpus."""

    def test_query_corpus_returns_list_of_dicts(self):
        """query_corpus returns a list of dicts with text, source, metadata keys."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["chunk text 1", "chunk text 2"]],
            "ids": [["id1", "id2"]],
            "metadatas": [[{"source_type": "hackernews"}, {"source_type": "hackernews"}]],
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with patch("chromadb.PersistentClient", return_value=mock_client):
            with patch(
                "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
            ):
                from src.rag.retrieval import query_corpus

                results = query_corpus("machine learning", n_results=5)

        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert "text" in r
            assert "source" in r
            assert "metadata" in r

    def test_query_corpus_empty_collection_returns_empty_list(self):
        """query_corpus handles empty collection gracefully."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [[]],
            "ids": [[]],
            "metadatas": [[]],
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with patch("chromadb.PersistentClient", return_value=mock_client):
            with patch(
                "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
            ):
                from src.rag.retrieval import query_corpus

                results = query_corpus("machine learning", n_results=5)

        assert results == []

    def test_async_query_corpus_returns_same_shape(self):
        """async_query_corpus wraps query_corpus and returns same shape."""
        mock_collection = MagicMock()
        mock_collection.query.return_value = {
            "documents": [["text chunk"]],
            "ids": [["doc-id-1"]],
            "metadatas": [[{"source_type": "hackernews"}]],
        }
        mock_client = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_collection

        with patch("chromadb.PersistentClient", return_value=mock_client):
            with patch(
                "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
            ):
                from src.rag.retrieval import async_query_corpus

                results = asyncio.run(async_query_corpus("AI tools", n_results=3))

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["text"] == "text chunk"
        assert results[0]["source"] == "doc-id-1"


# ---------------------------------------------------------------------------
# RAG Agent Tests
# ---------------------------------------------------------------------------


class TestRagAgentInstance:
    """Tests for rag_agent LlmAgent instance."""

    def test_rag_agent_is_llm_agent(self):
        """rag_agent is an LlmAgent instance with correct name and output_key."""
        from google.adk.agents.llm_agent import LlmAgent

        with patch("chromadb.PersistentClient"):
            with patch(
                "chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"
            ):
                from src.agents.collection.rag_agent import rag_agent

        assert isinstance(rag_agent, LlmAgent)
        assert rag_agent.name == "rag_agent"
        assert rag_agent.output_key == "rag_results"


class TestQueryRagCorpus:
    """Tests for query_rag_corpus tool function."""

    def test_query_rag_corpus_returns_chunks_dict(self):
        """query_rag_corpus returns dict with 'chunks' key containing list of chunk dicts."""
        mock_chunks = [
            {"text": "AI text", "source": "id1", "metadata": {"source_type": "hackernews"}},
        ]

        with patch("src.rag.retrieval.query_corpus", return_value=mock_chunks):
            from src.agents.collection.rag_agent import query_rag_corpus

            result = asyncio.run(query_rag_corpus("machine learning", n_results=5))

        assert "chunks" in result
        assert isinstance(result["chunks"], list)
        assert result["chunks"][0]["text"] == "AI text"


# ---------------------------------------------------------------------------
# Critic Agent Tests
# ---------------------------------------------------------------------------


class TestHeuristicFilter:
    """Tests for heuristic_filter tool function."""

    def _make_repo(
        self,
        *,
        is_fork: bool = False,
        commits: int = 25,
        contributors: int = 5,
        age_days: int = 60,
    ) -> dict:
        """Helper to build a minimal repo dict for filter tests."""
        from datetime import datetime, timedelta, timezone

        created_at = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
        return {
            "name": "owner/repo",
            "url": "https://github.com/owner/repo",
            "stars": 1000,
            "star_velocity": 0.1,
            "commits": commits,
            "contributors": contributors,
            "issues": 10,
            "topics": [],
            "language": "Python",
            "is_fork": is_fork,
            "created_at": created_at,
        }

    def test_heuristic_filter_rejects_forks(self):
        """Repo with is_fork=True is always rejected even with high activity."""
        import json
        from src.agents.critic_agent import heuristic_filter

        repo = self._make_repo(is_fork=True, commits=100, contributors=10, age_days=90)
        result = asyncio.run(heuristic_filter(json.dumps([repo])))

        assert len(result["rejected"]) == 1
        assert len(result["passed"]) == 0

    def test_heuristic_filter_passes_strong_repos(self):
        """Repo with commits>20, contributors>3, age>30d is passed heuristically."""
        import json
        from src.agents.critic_agent import heuristic_filter

        repo = self._make_repo(commits=25, contributors=5, age_days=60)
        result = asyncio.run(heuristic_filter(json.dumps([repo])))

        assert len(result["passed"]) == 1
        assert len(result["rejected"]) == 0
        assert len(result["borderline"]) == 0

    def test_heuristic_filter_borderline_repos(self):
        """Repo with commits=10 (5-20 range) goes to borderline."""
        import json
        from src.agents.critic_agent import heuristic_filter

        repo = self._make_repo(commits=10, contributors=2, age_days=20)
        result = asyncio.run(heuristic_filter(json.dumps([repo])))

        assert len(result["borderline"]) == 1
        assert len(result["passed"]) == 0
        assert len(result["rejected"]) == 0

    def test_heuristic_filter_rejects_low_activity(self):
        """Repo with commits<5 or contributors<1 is rejected heuristically."""
        import json
        from src.agents.critic_agent import heuristic_filter

        repo = self._make_repo(commits=2, contributors=0, age_days=90)
        result = asyncio.run(heuristic_filter(json.dumps([repo])))

        assert len(result["rejected"]) == 1
        assert len(result["passed"]) == 0


class TestCriticAgentInstance:
    """Tests for critic_agent LlmAgent instance."""

    def test_critic_agent_is_llm_agent(self):
        """critic_agent is an LlmAgent instance with name='critic_agent' and output_key='filtered_repos'."""
        from google.adk.agents.llm_agent import LlmAgent
        from src.agents.critic_agent import critic_agent

        assert isinstance(critic_agent, LlmAgent)
        assert critic_agent.name == "critic_agent"
        assert critic_agent.output_key == "filtered_repos"
