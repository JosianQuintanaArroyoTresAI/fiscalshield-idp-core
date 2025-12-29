# Archived Documentation

This directory contains implementation guides and analysis documents from completed features and refactors. While no longer actively maintained, they provide valuable historical context and decision rationale.

## Structure

- **Root files** - Major implementation guides and analyses (see below)
- **`implementations/`** - Documentation of completed feature implementations
- **`deployment-history/`** - Records of specific deployment events

## Recent Additions (December 2025 Cleanup)

### Invoice Extraction Journey
- **[invoice-extraction-refactor-guide.md](invoice-extraction-refactor-guide.md)** (1,592 lines)
  - Major architecture refactor from complex multi-path chunking to simplified Claude-based boundary detection
  - Cost reduction: $10/document → $1.60/document (85% reduction)

- **[invoice-extraction-comparison.md](invoice-extraction-comparison.md)** (714 lines)
  - Comparison between previous project implementation and IDP accelerator approach

- **[chunking-analysis.md](chunking-analysis.md)** (237 lines)
  - Analysis of character vs token confusion in chunking strategy

- **[llm-boundary-detection-implementation.md](llm-boundary-detection-implementation.md)**
  - LLM-based document boundary detection implementation

### Completed Features
- **[user-scoped-tracking-implementation.md](user-scoped-tracking-implementation.md)**
  - Multi-tenant user scoping implementation guide

### Development Environment
- **[cline-terminal-integration-fix.md](cline-terminal-integration-fix.md)** (221 lines)
  - Fix for AI agent (Cline) terminal integration with VSCode

## Why Archive?

These documents are preserved for historical reference but are no longer actively maintained:
- Features are fully implemented and merged
- Deployments are complete
- Implementation approaches have evolved

## When to Consult This Archive

- Understanding architectural decisions and their rationale
- Learning from previous implementation approaches
- Debugging legacy code patterns
- Cost optimization insights from real-world analysis
- Onboarding new team members to project history
- Reference for similar future work

## Finding Current Documentation

For current, actively maintained documentation, see:
- Root-level markdown files (README.md, CONTRIBUTING.md, etc.)
- `docs/` subdirectories (features, cicd, etc.)

---

**Last Updated:** December 29, 2025
