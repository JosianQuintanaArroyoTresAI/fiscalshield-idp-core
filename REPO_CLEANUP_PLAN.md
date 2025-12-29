# Repository Cleanup Plan

**Date:** December 29, 2025  
**Repository:** fiscalshield-idp-core

## Executive Summary

This repository contains **207+ markdown files** and numerous test scripts. Many are temporary development guides that are no longer needed but contain valuable knowledge. This plan categorizes files into: **DELETE**, **ARCHIVE**, **RELOCATE**, **KEEP**, and **UPDATE**.

---

## 🗑️ IMMEDIATE DELETIONS (No Archive Needed)

### Personal/Temporary Files (Root Directory)
- `jos_CV` - Personal CV file, should never be in a code repository
- `awscli.zip` - Temporary AWS CLI download (62MB!)
- `Invoices 101 page7.pdf` - Test/sample file
- `response.json` - API test response
- `test-payload.json` - Test data artifact
- `*.log` files: `deploy.log`, `deploy-fresh.log`, `publish-prod.log`

### Test Scripts (Root Directory) - Temporary Testing Tools
- `test_user_id_fix.py` - One-off fix verification script
- `test-invoice-routing.sh` - Manual routing verification
- `test-quickref.sh` - Quick reference card (content should be in docs)

### CloudWatch Log Dumps
- `cloudwatch_classification.md` - 4,110 lines of raw CloudWatch logs (no longer needed)

**Action:** Delete these files immediately. Add to `.gitignore` if not already covered.

```bash
# Immediate cleanup commands
rm jos_CV awscli.zip "Invoices 101 page7.pdf" response.json test-payload.json
rm *.log
rm test_user_id_fix.py test-invoice-routing.sh test-quickref.sh
rm cloudwatch_classification.md
```

---

## 📦 ARCHIVE TO docs/archive/ (Completed Development Guides)

These are detailed implementation guides that were useful during development but are now complete. They have **historical/knowledge value** and should be preserved.

### Invoice Extraction Implementation Journey
- **Root:** `invoice-extraction-refactor-guide.md` (1,592 lines)
  - **Why Archive:** Massive refactor guide from complex multi-path to simplified Claude approach
  - **Knowledge Value:** Shows before/after architecture, cost analysis, decision rationale
  - **New Location:** `docs/archive/invoice-extraction-refactor-guide.md`

### Chunking Strategy Analysis
- **Docs:** `docs/CHUNKING_ANALYSIS.md` (237 lines)
  - **Why Archive:** Analysis of character vs token confusion, overlap strategies
  - **Knowledge Value:** Shows why chunking strategy was changed
  - **New Location:** `docs/archive/chunking-analysis.md`

### Invoice Comparison Documentation  
- **Docs:** `docs/INVOICE_EXTRACTION_COMPARISON.md` (714 lines)
- **Docs:** `docs/PRIOR_LAMBDA_COMPARISON.md`
  - **Why Archive:** Comparison between previous project and IDP implementation
  - **Knowledge Value:** Migration rationale and architecture differences
  - **New Location:** `docs/archive/invoice-extraction-comparison.md`

### Boundary Detection Implementation
- **Docs:** `docs/LLM_BOUNDARY_DETECTION_IMPLEMENTATION.md`
  - **Why Archive:** Specific implementation guide for completed feature
  - **Knowledge Value:** LLM-based boundary detection approach
  - **New Location:** `docs/archive/llm-boundary-detection-implementation.md`

### Development Environment Fixes
- **Docs:** `docs/cline-terminal-integration-fix.md` (221 lines)
  - **Why Archive:** Specific fix for AI agent terminal integration issue
  - **Knowledge Value:** Shows how to configure bash prompts for Cline/AI agents
  - **New Location:** `docs/archive/cline-terminal-integration-fix.md`

### User Scoping Implementation  
- **Docs:** `docs/USER_SCOPED_TRACKING_IMPLEMENTATION.md`
  - **Why Archive:** Implementation guide for completed feature
  - **Knowledge Value:** Multi-tenant user scoping architecture
  - **New Location:** `docs/archive/user-scoped-tracking-implementation.md`

**Action:**
```bash
# Create archive directory
mkdir -p docs/archive/completed-features

# Move completed implementation guides
mv invoice-extraction-refactor-guide.md docs/archive/
mv docs/CHUNKING_ANALYSIS.md docs/archive/chunking-analysis.md
mv docs/INVOICE_EXTRACTION_COMPARISON.md docs/archive/invoice-extraction-comparison.md
mv docs/PRIOR_LAMBDA_COMPARISON.md docs/archive/prior-lambda-comparison.md
mv docs/LLM_BOUNDARY_DETECTION_IMPLEMENTATION.md docs/archive/llm-boundary-detection-implementation.md
mv docs/cline-terminal-integration-fix.md docs/archive/cline-terminal-integration-fix.md
mv docs/USER_SCOPED_TRACKING_IMPLEMENTATION.md docs/archive/user-scoped-tracking-implementation.md
```

---

## 🔄 RELOCATE & CONSOLIDATE

### AI Agent Instructions
**Current:**
- `AI_AGENT_README.md` (root)
- `AmazonQ.md` (root)
- Scattered agent-specific docs in `docs/`

**Problem:** AI agent instructions are split across root and docs, making them hard to find.

**Recommendation:** Consolidate into `.github/AGENT_INSTRUCTIONS/`
```bash
mkdir -p .github/AGENT_INSTRUCTIONS
mv AI_AGENT_README.md .github/AGENT_INSTRUCTIONS/README.md
mv AmazonQ.md .github/AGENT_INSTRUCTIONS/AMAZON_Q.md
# Note: docs/DOCKER_LAMBDA_DEPLOYMENT.md is already referenced and in good place
```

**Update `.github/AGENT_INSTRUCTIONS/README.md`:**
- Add clear table of contents
- Reference DOCKER_LAMBDA_DEPLOYMENT.md location
- Link to other agent-specific documentation

### Memory Bank - Should This Be in Git?
**Current:** `memory-bank/` folder with 3 files
- `activeContext.md` - Current work status
- `projectbrief.md` - 847 lines of project architecture
- `publish-comparison-analysis.md`

**Question:** Is this for AI agent memory? If so, should it be version controlled?

**Recommendations:**
1. **If AI agent working memory:** Add to `.gitignore`
2. **If project documentation:** Move to `docs/project-overview/` and rename appropriately
3. **Hybrid approach:** Extract stable content (project architecture) to docs, gitignore the active context

### Business Documents  
**Current:**
- `idp_pitch_doc.md` (root, 826 lines) - Investor pitch document
- `unit_economics_word.md` (root, 102 lines) - Unit economics analysis

**Problem:** Business documents mixed with code repository

**Recommendation:** Move to dedicated folder
```bash
mkdir -p docs/business
mv idp_pitch_doc.md docs/business/taxradar-investor-pitch.md
mv unit_economics_word.md docs/business/unit-economics.md
```

### Quick Reference Guides - Consolidate
**Current:**
- `docs/INVOICE_EXTRACTION_QUICK_REF.md`
- `docs/cicd-quick-reference.md`
- `docs/data-collection-cicd-quick-ref.md`
- (test-quickref.sh content should be moved here)

**Recommendation:** Create a unified quick reference section
```bash
mkdir -p docs/quick-reference
mv docs/INVOICE_EXTRACTION_QUICK_REF.md docs/quick-reference/invoice-extraction.md
mv docs/cicd-quick-reference.md docs/quick-reference/cicd.md
mv docs/data-collection-cicd-quick-ref.md docs/quick-reference/data-collection-cicd.md
```

**Add:** `docs/quick-reference/README.md` with index of all quick refs

---

## ✅ KEEP & UPDATE

### Core Documentation (Root) - Keep As-Is
- `README.md` - Main project documentation ✅
- `CHANGELOG.md` - Version history ✅
- `CONTRIBUTING.md` - Contribution guidelines ✅
- `DEPLOYMENT.md` - Deployment instructions ✅
- `LICENSE` - Legal ✅
- `NOTICE` - Legal ✅
- `VERSION` - Version tracking ✅

### Essential Build/Deploy Scripts (Root) - Keep
- `Makefile` - Build automation ✅
- `publish.py` / `publish.sh` - Deployment ✅
- `deploy-pattern2-dev.sh` - Dev deployment ✅
- `activate-env.sh` - Environment activation ✅
- `reload_config_from_s3.py` - Config management ✅
- `template.yaml` - SAM template ✅

### Test Infrastructure (Root) - Keep But Review
- `run_tests.sh` - Main test runner ✅ KEEP
- `run_validation_tests.sh` - Validation tests ✅ KEEP
- `pytest.ini` - Pytest configuration ✅ KEEP

### Configuration Files (Root) - Keep
- `ruff.toml` - Linter config ✅
- `requirements-dev.txt` - Python deps ✅
- `Dockerfile.optimized` - Container config ✅
- `.gitignore` - Git config ✅ (needs update - see below)

### Documentation That Should Stay Active

#### Architecture & Design (docs/)
- `docs/architecture.md` ✅
- `docs/deployment-architecture.md` ✅
- `docs/pattern-1.md`, `docs/pattern-2.md`, `docs/pattern-3.md` ✅
- `docs/well-architected.md` ✅

#### Operational Guides (docs/)
- `docs/configuration.md` ✅
- `docs/monitoring.md` ✅
- `docs/troubleshooting.md` ✅
- `docs/deployment.md` ✅
- `docs/development-workflow.md` ✅

#### Feature Documentation (docs/)
- `docs/classification.md` ✅
- `docs/extraction.md` ✅
- `docs/evaluation.md` ✅
- `docs/human-review.md` ✅
- `docs/knowledge-base.md` ✅
- `docs/web-ui.md` ✅

#### CI/CD Documentation (docs/cicd/)
- `docs/CI_CD_DEPLOYMENT_ORDER.md` ✅
- `docs/cicd-improvements-summary.md` ✅
- `docs/cicd-troubleshooting.md` ✅
- `docs/DOCKER_LAMBDA_DEPLOYMENT.md` ✅ (referenced by AI agents)

#### Testing Documentation (docs/)
- `docs/testing-best-practices.md` ✅
- `docs/RUNNING_USER_SCOPING_TESTS.md` ✅

#### API & Integration Docs (docs/)
- `docs/companies-house-api.md` ✅
- `docs/post-processing-lambda-hook.md` ✅
- `docs/idp-cli.md` ✅

---

## 📝 UPDATE NEEDED

### 1. Update .gitignore
Add these patterns to prevent future accumulation:
```bash
# Personal files
jos_CV
*_CV
*.cv

# Large downloads
*.zip
awscli.zip

# Temporary test files
response.json
test-payload.json
test-*.json

# Log files (if not already covered)
*.log

# Test PDFs in root
*.pdf

# AI agent memory (if applicable)
memory-bank/activeContext.md
```

### 2. Update README.md Documentation Links
After reorganization, update `README.md` to reflect new documentation structure:
- Add link to `docs/archive/` for historical implementation guides
- Add link to `docs/quick-reference/` for quick reference section
- Add link to `docs/business/` for business documentation
- Update links to relocated AI agent instructions

### 3. Create Archive README
Create `docs/archive/README.md`:
```markdown
# Archived Documentation

This directory contains implementation guides and analysis documents from completed features and refactors. While no longer actively maintained, they provide valuable historical context and decision rationale.

## Contents

### Invoice Extraction Journey
- [invoice-extraction-refactor-guide.md](invoice-extraction-refactor-guide.md) - Major architecture refactor (1,592 lines)
- [invoice-extraction-comparison.md](invoice-extraction-comparison.md) - Previous vs current comparison
- [chunking-analysis.md](chunking-analysis.md) - Chunking strategy evolution
- [llm-boundary-detection-implementation.md](llm-boundary-detection-implementation.md) - Boundary detection approach

### Completed Features
- [user-scoped-tracking-implementation.md](user-scoped-tracking-implementation.md) - Multi-tenant implementation

### Development Environment
- [cline-terminal-integration-fix.md](cline-terminal-integration-fix.md) - AI agent terminal configuration

## When to Consult This Archive
- Understanding why certain architectural decisions were made
- Learning from previous implementation approaches
- Debugging issues related to legacy code patterns
- Onboarding new team members to project history
```

### 4. Create Quick Reference Index
Create `docs/quick-reference/README.md`:
```markdown
# Quick Reference Guides

Fast access to common commands and workflows.

## Available Guides
- [Invoice Extraction Quick Ref](invoice-extraction.md)
- [CI/CD Quick Ref](cicd.md)
- [Data Collection CI/CD Quick Ref](data-collection-cicd.md)
- [Testing Commands](../testing-best-practices.md) (see Testing section)

## Usage
These guides are designed for quick copy-paste operations during development and operations.
```

---

## 📊 SUMMARY METRICS

### Files to Delete: 12
- Personal files: 1
- Temporary files: 4
- Test scripts: 3
- Log files: 3
- Raw log dumps: 1

### Files to Archive: 7
- Implementation guides: 5
- Analysis documents: 2

### Files to Relocate: 8
- AI agent instructions: 2
- Memory bank files: 3 (decision needed)
- Business docs: 2
- Quick reference guides: 3

### Total Cleanup Impact
- **Space saved:** ~62MB (mainly awscli.zip)
- **Line count reduced from root:** ~4,000+ lines moved to organized locations
- **Markdown files organized:** ~15 files better categorized
- **Repository clarity:** Significantly improved

---

## 🚀 EXECUTION PLAN

### Phase 1: Immediate Cleanup (Low Risk)
```bash
# Delete temporary files
rm jos_CV awscli.zip "Invoices 101 page7.pdf" response.json test-payload.json
rm deploy.log deploy-fresh.log publish-prod.log
rm test_user_id_fix.py test-invoice-routing.sh test-quickref.sh
rm cloudwatch_classification.md
```

### Phase 2: Archive Creation
```bash
# Create archive structure
mkdir -p docs/archive
mkdir -p docs/quick-reference
mkdir -p docs/business

# Move completed guides to archive
mv invoice-extraction-refactor-guide.md docs/archive/
mv docs/CHUNKING_ANALYSIS.md docs/archive/chunking-analysis.md
mv docs/INVOICE_EXTRACTION_COMPARISON.md docs/archive/invoice-extraction-comparison.md
mv docs/PRIOR_LAMBDA_COMPARISON.md docs/archive/prior-lambda-comparison.md
mv docs/LLM_BOUNDARY_DETECTION_IMPLEMENTATION.md docs/archive/llm-boundary-detection-implementation.md
mv docs/cline-terminal-integration-fix.md docs/archive/cline-terminal-integration-fix.md
mv docs/USER_SCOPED_TRACKING_IMPLEMENTATION.md docs/archive/user-scoped-tracking-implementation.md
```

### Phase 3: Reorganization
```bash
# Relocate AI agent instructions
mkdir -p .github/AGENT_INSTRUCTIONS
mv AI_AGENT_README.md .github/AGENT_INSTRUCTIONS/README.md
mv AmazonQ.md .github/AGENT_INSTRUCTIONS/AMAZON_Q.md

# Move business documents
mv idp_pitch_doc.md docs/business/taxradar-investor-pitch.md
mv unit_economics_word.md docs/business/unit-economics.md

# Consolidate quick references
mv docs/INVOICE_EXTRACTION_QUICK_REF.md docs/quick-reference/invoice-extraction.md
mv docs/cicd-quick-reference.md docs/quick-reference/cicd.md
mv docs/data-collection-cicd-quick-ref.md docs/quick-reference/data-collection-cicd.md
```

### Phase 4: Update Documentation
1. Update `.gitignore` with new patterns
2. Create `docs/archive/README.md`
3. Create `docs/quick-reference/README.md`
4. Create `docs/business/README.md`
5. Update `.github/AGENT_INSTRUCTIONS/README.md`
6. Update main `README.md` with new structure

### Phase 5: Decision on Memory Bank
**Options:**
1. **Add to .gitignore:** If it's AI agent working memory
2. **Extract & Move:** Split stable content to docs, gitignore active context
3. **Keep as-is:** If it's intended to be version controlled

**Recommendation:** Option 2 - Extract `projectbrief.md` content into proper docs, gitignore `activeContext.md`

---

## ⚠️ BEFORE EXECUTING

1. **Commit current state:** `git add -A && git commit -m "Snapshot before cleanup"`
2. **Create cleanup branch:** `git checkout -b repo-cleanup-2025`
3. **Review file contents:** Spot-check archived files to ensure no critical info is lost
4. **Test builds:** Ensure cleanup doesn't break build/deploy processes
5. **Update CI/CD:** Check if any CI/CD pipelines reference moved files

---

## 🎯 SUCCESS CRITERIA

- [ ] Root directory contains only essential code, config, and current docs
- [ ] All historical implementation guides preserved in `docs/archive/`
- [ ] AI agent instructions consolidated in `.github/AGENT_INSTRUCTIONS/`
- [ ] Business documents organized in `docs/business/`
- [ ] Quick references consolidated in `docs/quick-reference/`
- [ ] Personal files and large temporary files removed
- [ ] `.gitignore` updated to prevent recurrence
- [ ] All documentation links updated
- [ ] Build and deployment still work
- [ ] README.md reflects new organization

---

## 📞 NEXT STEPS

Would you like me to:
1. **Execute Phase 1** (immediate cleanup - very low risk)?
2. **Start with Phase 2** (create archive structure)?
3. **Review specific files** before making decisions?
4. **Help you decide on memory-bank** folder handling?
5. **Create the updated .gitignore** file?

Let me know which phase you'd like to tackle first, and I'll execute it for you!
