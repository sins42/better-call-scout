Review an agent file for correctness and consistency with the project design.

Usage: /review-agent src/agents/collection/github_agent.py

Read the specified agent file, then check:
1. Imports are correct for Google ADK patterns
2. Pydantic models from src/models/schemas.py are used (not ad-hoc dicts)
3. Async patterns are correct
4. Error handling exists for external API calls
5. Output conforms to the expected schema type
6. Docstring is present and accurate

Point out specific issues with line references. If clean, confirm it's ready.
