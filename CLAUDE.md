# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**dss-mas** (Decision Support System - Multi-Agent System) is a Python-based multi-agent system for business intelligence. Autonomous agents use LLM tools to analyze data and support decision-making.

## Environment Setup

```bash
# Create and activate virtual environment
python -m venv .venv
.venv/Scripts/activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

Configuration is via `.env` file with:
- `GIGACHAT_API_KEY`, `GIGACHAT_CLIENT_SECRET`, `GIGACHAT_CLIENT_ID` — GigaChat (primary LLM provider)
- Optional: OpenAI, DeepSeek, Ollama credentials

## Running

```bash
python src/main.py
```

No test framework is configured. There is no build step.

## Architecture

### Tech Stack
- **LangGraph** — graph-based agent workflow/state machine (primary orchestration layer)
- **LangChain** — LLM abstraction, prompt templates, chain composition
- **LLM Providers** — GigaChat (Russian LLM, primary), OpenAI, DeepSeek, Ollama (local)
- **Starlette + Uvicorn** — ASGI web layer (if serving agents over HTTP)
- **SQLAlchemy** — persistence/checkpointing
- **Pydantic** — data validation and state modeling

### Agent Pattern

Agents are implemented as LangGraph `StateGraph` state machines:

1. **State** — typed dict (`TypedDict`) defining input/output fields passed between nodes
2. **Nodes** — `async` functions that receive state, call an LLM via `ainvoke()`, and return updated state fields
3. **Edges** — sequential or conditional transitions between nodes
4. **Entry/Exit** — configured via `set_entry_point()` / `set_finish_point()`

All agent methods are `async`; use `asyncio.run()` at the entry point.

### Prompt Design
- Use `PromptTemplate` with explicit variable substitution
- Structure prompts for deterministic outputs (enums, JSON) with normalization/fallback logic for unexpected LLM responses
- Include closest-match heuristics when LLM output doesn't exactly match expected values

### Enum Classification
Use Python `Enum` classes for classification categories. Normalize LLM responses against enum values; include fallback when output is ambiguous.

### Logging
Custom `Logger` class (wraps `logging`) with dual output: file (`app.log`) + stdout.

## Key Conventions
- Source code lives in `src/`
- `.env` holds credentials — never commit real keys
- Async-first: all LLM calls use `async/await`