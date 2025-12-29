# 🤖 AI Agent Instructions

This directory contains critical instructions for AI agents working on this codebase.

## Quick Start

### Pattern 2 Deployment (MOST IMPORTANT!)

**📖 [DOCKER_LAMBDA_DEPLOYMENT.md](../../docs/DOCKER_LAMBDA_DEPLOYMENT.md)**

Before making Pattern 2 code changes, READ THIS! Contains:
- Why code changes don't deploy automatically
- The correct deployment workflow
- Common mistakes that waste hours
- Real examples from production debugging

**TL;DR for Pattern 2 code changes:**
```bash
source activate-env.sh
python publish.py fiscalshield-templates fiscalshield/dev eu-central-1 --clean-build --lint off
./deploy-pattern2-dev.sh
```

### Development Guidelines

**📖 [AMAZON_Q.md](AMAZON_Q.md)**

Essential Python and testing best practices:
- Python formatting and linting with Ruff
- Pytest organization (unit vs integration tests)
- Test annotations and markers
- Code quality standards

## Additional Resources

### Technical Documentation
- [Main README](../../README.md) - Project overview
- [Development Workflow](../../docs/development-workflow.md) - Day-to-day development
- [Testing Best Practices](../../docs/testing-best-practices.md) - Comprehensive test guide

### Quick References
- [Quick Reference Guides](../../docs/quick-reference/) - Common commands and workflows
- [CI/CD Quick Ref](../../docs/quick-reference/cicd.md) - Build and deploy commands

### Architecture
- [Architecture Docs](../../docs/architecture.md) - System design
- [Pattern 2 Documentation](../../docs/pattern-2.md) - Pattern 2 specifics

## Note for AI Agents

These instructions are specifically curated to help AI assistants avoid common pitfalls and follow project conventions. Always check these before:
- Making deployment changes
- Running tests
- Modifying CI/CD workflows
- Implementing new features

---

*Last Updated: December 29, 2025*
