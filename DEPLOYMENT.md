# Production Deployment Checklist - POC Migration Phase 3
**Date:** November 8, 2025  
**Version:** 3.0  
**Branch:** main (commit: 65fbf31a)

---

## ✅ Pre-Deployment Verification

### **Code Status**
- [x] All changes merged from dev to main
- [x] No differences between dev and main branches
- [x] Latest commit: `65fbf31a - Merge pull request #5`
- [x] Migration guide updated and committed
- [x] All key files present:
  - `src/ui/src/contexts/company.js` ✅
  - `src/ui/src/components/company-intelligence/CompanyAnalysis.jsx` ✅
  - `src/ui/src/components/client-takeon/ClientTakeOnAnalysis.jsx` ✅
  - `src/ui/src/services/analysisStack.js` ✅

### **Feature Completeness**
- [x] Phase 1: CompanyProvider context (commit `1b6c1c63`)
- [x] Phase 2: Page structure and navigation (commit `42fcccf8`)
- [x] Phase 3.1: Client Take-On Analysis (commit `e2554bbe`)
- [x] Phase 3.2: Hybrid card layout (commit `95578d29`)
- [x] Phase 3.3: Merged implementation (commit `38d6e2fc`)

---

## 🚀 Deployment Steps

### **1. Verify CI/CD Pipeline**
```bash
# Check GitHub Actions status
# URL: https://github.com/JosianQuintanaArroyoTresAI/fiscalshield-idp-core/actions
```
- [ ] Latest workflow run successful
- [ ] No failing tests
- [ ] Build completed without errors

### **2. Deploy to Production**
The merge to main should automatically trigger CI/CD deployment. If manual deployment is needed:

```bash
# Option A: CI/CD should auto-deploy from main branch
# Wait for GitHub Actions to complete

# Option B: Manual deployment (if needed)
cd /home/josian/git/fiscalshield-idp-core
git checkout main
git pull origin main

# Deploy pattern 2 stack (if infrastructure changed)
./deploy-pattern2-prod.sh

# Or use complete deployment script
cd scripts
./deploy-prod-complete.sh
```

### **3. Monitor Deployment**
```bash
# Check CloudFormation stacks
aws cloudformation describe-stacks \
  --stack-name fiscalshield-idp-prod-PATTERN2STACK \
  --query 'Stacks[0].StackStatus' \
  --output text

# Check if UPDATE_COMPLETE or CREATE_COMPLETE
```

---

## 🧪 Post-Deployment Verification

### **Frontend Verification**
- [ ] Navigate to production URL
- [ ] Login with test credentials
- [ ] Navigate to Company Select
- [ ] Select a company (e.g., 11087779 or TESCO)
- [ ] Click "View Company Intelligence"

### **Company Analysis Page - Overview Tab**
- [ ] Page loads without errors
- [ ] 4 compact risk cards display:
  - [ ] Overall Risk card (shows risk level with color)
  - [ ] Adverse Media card (shows findings count)
  - [ ] Director Screening card (shows sanctions + PEP count)
  - [ ] Company Status card (shows active/inactive)
- [ ] Risk scores load from Analysis Stack
- [ ] Color coding is correct (red/orange/green)
- [ ] Company data section displays below cards

### **Company Analysis Page - AML Report Tab**
- [ ] Click "AML Report" tab
- [ ] Tab switches without error
- [ ] Analysis Summary cards display (4 cards):
  - [ ] Red Flags count
  - [ ] Recommendations count
  - [ ] Mitigating Factors count
  - [ ] Enhanced DD status
- [ ] Detailed Intelligence section displays:
  - [ ] Overall Summary
  - [ ] Red Flags list (if any)
  - [ ] Recommendations list (if any)
  - [ ] Mitigating Factors list (if any)
- [ ] Category Analysis sections display:
  - [ ] Governance insights
  - [ ] AML/Sanctions insights
  - [ ] Reputational insights
  - [ ] Financial insights

### **AML Report Generation**
- [ ] Click "Generate Full AML Report" button
- [ ] Loading state displays correctly
- [ ] Success alert appears after generation
- [ ] Download button appears in alert
- [ ] Click download button
- [ ] PDF downloads successfully
- [ ] Open PDF and verify content

### **Browser Console Check**
- [ ] Open browser DevTools (F12)
- [ ] Check Console tab - no errors
- [ ] Check Network tab - all API calls successful (200/201 status)
- [ ] No 404 or 500 errors

### **Responsive Design**
- [ ] Test on desktop (1920x1080)
- [ ] Test on laptop (1366x768)
- [ ] Test on tablet view (resize browser)
- [ ] All cards display correctly at different sizes

---

## 🔍 API Verification

### **Analysis Stack Endpoints**
```bash
# Get Analysis Stack API URL from CloudFormation
ANALYSIS_API=$(aws cloudformation describe-stacks \
  --stack-name fiscalshield-analysis-prod \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

echo "Analysis API URL: $ANALYSIS_API"

# Test health endpoint
curl ${ANALYSIS_API}/health

# Test intelligence endpoint (replace with real company number)
curl ${ANALYSIS_API}/company/11087779/intelligence
```

Expected responses:
- [ ] `/health` returns 200 OK
- [ ] `/company/{id}/intelligence` returns 200 with data
- [ ] No 500 errors or timeouts

---

## 📋 Stakeholder Demo Preparation

### **Demo Environment**
- [ ] Production URL accessible
- [ ] Test company data available (e.g., 11087779, TESCO)
- [ ] Analysis Stack has intelligence data for demo companies
- [ ] PDF generation working

### **Demo Script Ready**
- [ ] Company Select → Pick company
- [ ] Overview Tab → Show 4 risk cards
- [ ] AML Report Tab → Show detailed intelligence
- [ ] Generate Report → Download PDF
- [ ] Have backup screenshots ready

### **Backup Plan**
- [ ] Screenshots of working deployment
- [ ] Video recording of features (optional)
- [ ] Rollback plan documented

---

## 🐛 Rollback Plan (If Issues Found)

### **Quick Rollback**
```bash
# Revert to previous main commit
git checkout main
git reset --hard c3924a64  # Previous stable commit before merge
git push origin main --force

# Or revert the merge commit
git revert 65fbf31a -m 1
git push origin main
```

### **CloudFormation Rollback**
```bash
# If stack update fails, it auto-rolls back
# Manual rollback if needed:
aws cloudformation cancel-update-stack \
  --stack-name fiscalshield-idp-prod-PATTERN2STACK
```

---

## 📊 Success Criteria

### **Must Have (Blocking)**
- [ ] ✅ Company Analysis page loads
- [ ] ✅ Overview tab displays 4 risk cards
- [ ] ✅ AML Report tab displays intelligence
- [ ] ✅ No console errors
- [ ] ✅ Analysis Stack API responds

### **Should Have (Non-blocking)**
- [ ] ✅ PDF generation works
- [ ] ✅ All card data populates correctly
- [ ] ✅ Color coding accurate
- [ ] ✅ Responsive design works

### **Nice to Have**
- [ ] Fast load times (< 2 seconds)
- [ ] Smooth tab transitions
- [ ] Professional appearance

---

## 📝 Post-Deployment Notes

### **Issues Found:**
```
[Document any issues discovered during verification]
```

### **Fixes Applied:**
```
[Document any hotfixes deployed]
```

### **Stakeholder Feedback:**
```
[Record feedback from demo]
```

---

## ✅ Final Sign-Off

- [ ] All verification steps completed
- [ ] No critical errors
- [ ] Stakeholder demo successful
- [ ] Production deployment approved

**Deployed By:** _________________  
**Date/Time:** _________________  
**Approved By:** _________________  

---

**Status:** Ready for Production Deployment  
**Next Steps:** Execute deployment and run verification checklist
