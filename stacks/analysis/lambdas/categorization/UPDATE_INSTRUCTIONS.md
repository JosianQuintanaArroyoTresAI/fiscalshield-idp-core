# High-Risk Countries List - Update Instructions

## Update Schedule

**Frequency**: 3 times per year  
**Months**: February, June, October  
**After**: FATF publishes quarterly updates

## Update Process

### Step 1: Check FATF Website
Visit: https://www.fatf-gafi.org/en/countries/high-risk-and-other-monitored-jurisdictions.html

Look for:
- **High-Risk Jurisdictions** (Call for Action) - Black List
- **Jurisdictions under Increased Monitoring** - Grey List

### Step 2: Check UK Sanctions
Visit: https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets

Download the latest consolidated list to check for new country-level sanctions.

### Step 3: Update the JSON File

Edit `high_risk_countries.json`:

```bash
cd stacks/analysis/lambdas/categorization/
nano high_risk_countries.json
```

**What to update**:

1. **Update metadata** (top of file):
   ```json
   "version": "2025-06-01",
   "last_updated": "2025-06-01",
   "next_update_due": "2025-10-01"
   ```

2. **Add new countries** (if any):
   ```json
   "ABC": {
     "name": "New Country Name",
     "iso3": "ABC",
     "iso2": "AB",
     "risk_level": "HIGH",
     "risk_score": 85,
     "sources": ["FATF"],
     "category": "FATF Increased Monitoring"
   }
   ```

3. **Remove countries** (if FATF removed them from lists)

4. **Update risk levels** (if country moved between categories)

### Step 4: Deploy

```bash
cd /home/josian/git/fiscalshield-idp-core
git add stacks/analysis/lambdas/categorization/high_risk_countries.json
git commit -m "chore: Update FATF high-risk countries list (June 2025)"
git push origin dev
```

GitHub Actions will automatically deploy to the categorization Lambda.

### Step 5: Verify

After deployment:
1. Upload a test bank statement with transactions to a high-risk country
2. Check that `GeographicRiskFlag` is set correctly in DynamoDB
3. Verify risk score appears in frontend

## Risk Level Guidelines

| Level | Score | Examples | Action |
|-------|-------|----------|--------|
| **CRITICAL** | 95-100 | North Korea, Iran, Syria | Block or senior approval |
| **HIGH** | 75-94 | Russia, Belarus, Myanmar | Enhanced monitoring |
| **MEDIUM** | 50-74 | FATF Grey List countries | Standard monitoring |
| **LOW** | 0-49 | All other countries | Standard processing |

## Country Code Formats

The system accepts multiple formats:
- **ISO 3166-1 alpha-2**: `US`, `GB`, `FR` (2 letters)
- **ISO 3166-1 alpha-3**: `USA`, `GBR`, `FRA` (3 letters)
- **Full names**: `USA`, `UK`, `UNITED KINGDOM`

The lookup will try to match any of these formats.

## Troubleshooting

**Q: Lambda not picking up new list?**
- Lambda uses cold start caching. Wait 5-10 minutes or force refresh by updating environment variable.

**Q: Country code not matching?**
- Check if extracted code matches ISO standard (e.g., `GB` vs `UK`)
- Add common aliases in the code if needed

**Q: Forgot to update?**
- Check `next_update_due` field in JSON
- Set calendar reminder for Feb 1, June 1, Oct 1

## Automation (Future Enhancement)

To automate FATF list checking:

1. Create Lambda: `check-fatf-updates`
2. EventBridge cron: `0 0 1 2,6,10 ? *` (1st of Feb, Jun, Oct)
3. SNS notification when FATF publishes updates
4. Manual review and commit still required (regulatory compliance)

## References

- FATF Official: https://www.fatf-gafi.org/
- UK Sanctions: https://www.gov.uk/government/publications/financial-sanctions-consolidated-list-of-targets
- US OFAC: https://sanctionssearch.ofac.treas.gov/
- EU Sanctions: https://www.sanctionsmap.eu/
