Check if the shared Pydantic schemas are defined and valid.

Read src/models/schemas.py and verify:
1. All 5 models exist: RepoData, NewsItem, RAGContext, AnalystHypothesis, SynthesisReport
2. All required fields are present per REQUIREMENTS.md SCHEMA-01 through SCHEMA-05
3. Pydantic v2 syntax is used (not v1 validators)
4. Models are importable (no syntax errors)

Report what's missing or broken. If all good, confirm schemas are ready for both layers to build against.
