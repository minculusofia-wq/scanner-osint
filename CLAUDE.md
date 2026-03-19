# Project Documentation (Auto-generated)

> This file is automatically updated by Claude Code hooks.
> Last updated: 2026-03-04 10:07:29

## Project Structure

```
/Users/anthony/Desktop/scanner osint
/Users/anthony/Desktop/scanner osint/.DS_Store
/Users/anthony/Desktop/scanner osint/frontend
/Users/anthony/Desktop/scanner osint/frontend/node_modules
/Users/anthony/Desktop/scanner osint/frontend/node_modules/.bin
/Users/anthony/Desktop/scanner osint/frontend/node_modules/@alloc
/Users/anthony/Desktop/scanner osint/frontend/node_modules/@emnapi
/Users/anthony/Desktop/scanner osint/frontend/node_modules/@types
/Users/anthony/Desktop/scanner osint/frontend/node_modules/call-bind
/Users/anthony/Desktop/scanner osint/frontend/node_modules/callsites
/Users/anthony/Desktop/scanner osint/frontend/node_modules/csstype
/Users/anthony/Desktop/scanner osint/frontend/node_modules/define-data-property
/Users/anthony/Desktop/scanner osint/frontend/node_modules/es-errors
/Users/anthony/Desktop/scanner osint/frontend/node_modules/escape-string-regexp
/Users/anthony/Desktop/scanner osint/frontend/node_modules/flatted
/Users/anthony/Desktop/scanner osint/frontend/node_modules/function.prototype.name
/Users/anthony/Desktop/scanner osint/frontend/node_modules/functions-have-names
/Users/anthony/Desktop/scanner osint/frontend/node_modules/globals
/Users/anthony/Desktop/scanner osint/frontend/node_modules/has-property-descriptors
/Users/anthony/Desktop/scanner osint/frontend/node_modules/has-proto
/Users/anthony/Desktop/scanner osint/frontend/node_modules/has-tostringtag
/Users/anthony/Desktop/scanner osint/frontend/node_modules/imurmurhash
/Users/anthony/Desktop/scanner osint/frontend/node_modules/is-array-buffer
/Users/anthony/Desktop/scanner osint/frontend/node_modules/is-bigint
/Users/anthony/Desktop/scanner osint/frontend/node_modules/is-typed-array
/Users/anthony/Desktop/scanner osint/frontend/node_modules/jiti
/Users/anthony/Desktop/scanner osint/frontend/node_modules/language-tags
/Users/anthony/Desktop/scanner osint/frontend/node_modules/loose-envify
/Users/anthony/Desktop/scanner osint/frontend/node_modules/math-intrinsics
/Users/anthony/Desktop/scanner osint/frontend/node_modules/ms
/Users/anthony/Desktop/scanner osint/frontend/node_modules/next
/Users/anthony/Desktop/scanner osint/frontend/node_modules/node-exports-info
/Users/anthony/Desktop/scanner osint/frontend/node_modules/possible-typed-array-names
/Users/anthony/Desktop/scanner osint/frontend/node_modules/prelude-ls
/Users/anthony/Desktop/scanner osint/frontend/node_modules/queue-microtask
/Users/anthony/Desktop/scanner osint/frontend/node_modules/react-is
/Users/anthony/Desktop/scanner osint/frontend/node_modules/reusify
/Users/anthony/Desktop/scanner osint/frontend/node_modules/shebang-regex
/Users/anthony/Desktop/scanner osint/frontend/node_modules/simple-swizzle
/Users/anthony/Desktop/scanner osint/frontend/node_modules/string.prototype.trimend
/Users/anthony/Desktop/scanner osint/frontend/node_modules/string.prototype.trimstart
/Users/anthony/Desktop/scanner osint/frontend/node_modules/strip-json-comments
/Users/anthony/Desktop/scanner osint/frontend/node_modules/styled-jsx
/Users/anthony/Desktop/scanner osint/frontend/node_modules/tailwind-merge
/Users/anthony/Desktop/scanner osint/frontend/node_modules/tapable
/Users/anthony/Desktop/scanner osint/frontend/node_modules/tinyglobby
/Users/anthony/Desktop/scanner osint/frontend/node_modules/ts-api-utils
/Users/anthony/Desktop/scanner osint/frontend/node_modules/tsconfig-paths
/Users/anthony/Desktop/scanner osint/frontend/node_modules/which-boxed-primitive
/Users/anthony/Desktop/scanner osint/frontend/postcss.config.mjs
```

## Tech Stack

## API Endpoints

### FastAPI Routes
```python
@router.get("/items/")
@router.get("/briefs/")
@router.post("/briefs/{brief_id}/dismiss")
@router.post("/collect")
@router.get("/stats")
@router.get("/config")
@router.put("/config")
@app.get("/health")
```

## Database

### SQLAlchemy Models
```python
class Settings(BaseSettings):
class Base(DeclarativeBase):
class OSINTConfigRecord(Base):
class IntelligenceBrief(Base):
class IntelligenceItem(Base):
class IntelligenceItemResponse(BaseModel):
class IntelligenceBriefResponse(BaseModel):
class OSINTConfig(BaseModel):
class IntelligenceStats(BaseModel):
class NASAFirmsCollector(BaseCollector):
class ACLEDCollector(BaseCollector):
class RedditCollector(BaseCollector):
class ShipTrackerCollector(BaseCollector):
class NewsDataCollector(BaseCollector):
class ADSBCollector(BaseCollector):
```

## Key Files


## Trading Bot Components

This appears to be a trading bot project. Key patterns detected:

- WebSocket connections for real-time data
- Position management
- Order execution
- Risk management
- Redis for caching/pub-sub
- PostgreSQL database
- Knowledge Graph (NetworkX) for entity correlation
- LLM-based Entity Extraction (Gemini)
- Predictions API for external trading bots

## Instructions for Claude

When working on this project:
- Check existing patterns before creating new files
- Follow the established code style
- Run tests if they exist before committing
- Update this documentation if you make structural changes

### Memory Management

When you make significant architectural decisions, discover pitfalls,
or establish new patterns, store them in memory using:
```
mcp__memory-service__store_memory with tags: "scanner osint,architecture,decision"
```
Use appropriate tags: architecture, decision, convention, pattern, pitfall, issue
This helps maintain project knowledge across sessions.

