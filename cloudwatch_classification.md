timestamp,message
1764447304620,"[INFO]	2025-11-29T20:15:04.620Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 2.36s
"
1764447304620,"[INFO]	2025-11-29T20:15:04.620Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5020, 'outputTokens': 87, 'totalTokens': 5107}
"
1764447304628,"[INFO]	2025-11-29T20:15:04.628Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 2.32s
"
1764447304628,"[INFO]	2025-11-29T20:15:04.628Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5015, 'outputTokens': 78, 'totalTokens': 5093}
"
1764447304635,"[INFO]	2025-11-29T20:15:04.634Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 2.37s
"
1764447304635,"[INFO]	2025-11-29T20:15:04.635Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5017, 'outputTokens': 79, 'totalTokens': 5096}
"
1764447304652,"[INFO]	2025-11-29T20:15:04.652Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	No resize requested (width or height is None/empty), returning original image
"
1764447304652,"[INFO]	2025-11-29T20:15:04.652Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Detected image format: jpeg
"
1764447304652,"[INFO]	2025-11-29T20:15:04.652Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Classifying page 27 with Bedrock
"
1764447304663,"[INFO]	2025-11-29T20:15:04.663Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 3: 2.52 seconds
"
1764447304664,"[WARNING]	2025-11-29T20:15:04.664Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447304665,"[WARNING]	2025-11-29T20:15:04.664Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447304665,"[INFO]	2025-11-29T20:15:04.665Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, supplier details, itemized charges, and financial calculations typical of an invoice. It includes an invoice date, reference number, and amount due section, confirming it as an invoice.', 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447304665,"[INFO]	2025-11-29T20:15:04.665Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 3 classified as invoice
"
1764447304669,"[WARNING]	2025-11-29T20:15:04.669Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447304669,"[INFO]	2025-11-29T20:15:04.669Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 2.44s
"
1764447304669,"[INFO]	2025-11-29T20:15:04.669Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5030, 'outputTokens': 104, 'totalTokens': 5134}
"
1764447304744,"[WARNING]	2025-11-29T20:15:04.744Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Removed <<CACHEPOINT>> tags for unsupported model: arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.amazon.nova-pro-v1:0. CachePoint is only supported for: eu.anthropic.claude-3-7-sonnet-20250219-v1:0, eu.anthropic.claude-sonnet-4-20250514-v1:0, eu.anthropic.claude-sonnet-4-5-20250929-v1:0, eu.amazon.nova-lite-v1:0, eu.amazon.nova-pro-v1:0
"
1764447304745,"[INFO]	2025-11-29T20:15:04.745Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request attempt 1/7:
"
1764447304746,"[INFO]	2025-11-29T20:15:04.745Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - model: arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.amazon.nova-pro-v1:0
"
1764447304746,"[INFO]	2025-11-29T20:15:04.745Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - inferenceConfig: {'topP': 0.1, 'maxTokens': 8000}
"
1764447304746,"[INFO]	2025-11-29T20:15:04.746Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - system: [{'text': 'You are a multimodal document classification expert specializing in UK financial and commercial documents. Your task is to classify documents into predefined categories with HIGH CONFIDENCE based on visual layout, textual content, and distinctive features. You MUST provide a confidence score from 0.0 to 1.0 reflecting the strength of classification evidence. Your output must be valid JSON according to the requested format.
<variables> <document-ocr-data>: OCR-extracted text content providing textual information for classification <document-image>: Visual representation showing layout, formatting, logos, and structure <document-types>: Valid document types you must classify into - ONLY use types from this list </variables>'}]
"
1764447304746,"[INFO]	2025-11-29T20:15:04.746Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - messages: [{'role': 'user', 'content': [{'text': '<task-description> Analyze the provided document using both visual layout and textual content to determine its document type with high confidence. Decide if this page starts a new document (""start"") or continues the previous document (""continue""). </task-description>
<document-types> invoice  \t[ A commercial invoice or expense claim document issued by a supplier, vendor, or individual to request payment for goods or services purchased.
KEY IDENTIFIERS: - Header text: ""Invoice"", ""Tax Invoice"", ""VAT Invoice"", ""Proforma Invoice"", ""Credit Note"", ""Receipt"" - Supplier/vendor details at top (company name, address, VAT/tax registration number) - Line items table with columns: description, quantity, unit price, amount - Financial calculations: subtotal, VAT/GST breakdown (often 20%% in UK), total amount - Invoice metadata: invoice number, invoice date, due date - Payment terms and bank details for wire transfer - May include purchase order number, customer reference
DISTINGUISHING FEATURES: - Itemized charges showing WHAT was purchased (products/services) - Amounts OWED (not paid) - this is a request for payment - Business-to-business OR individual-to-business format - VAT invoice number format (e.g., ""INV-2024-001"", ""#12345"") - May show ""PAID"" stamp or payment status if settled
INCLUDES SUBTYPES: - Supplier invoices (formal business invoices with VAT registration) - Expense claims/receipts (individual purchases, simpler format, from shops/restaurants) - Credit notes (negative invoices for refunds/adjustments) ]
bank-statement  \t[ A financial statement issued by a bank or financial institution documenting account activity and transactions over a specific time period.
KEY IDENTIFIERS: - Bank logo and institution name (e.g., Barclays, HSBC, Lloyds, NatWest, Metro Bank) - Account holder name and address - Account number (often partially masked: ****1234) - Sort code (UK: XX-XX-XX format) - Statement period with clear start and end dates - Opening balance and closing balance - Chronological transaction list with dates
TRANSACTION TABLE COLUMNS: - Date (transaction date) - Description (merchant name, payment reference, transaction type) - Money OUT (debits, payments, withdrawals) - Money IN (credits, deposits, transfers received) - Running balance (account balance after each transaction)
DISTINGUISHING FEATURES: - Shows money flowing IN and OUT of an account (not requesting payment) - Transaction history format (NOT itemized sales) - Statement period dates (e.g., ""01 Oct 2024 - 31 Oct 2024"") - Transaction types: DD (Direct Debit), SO (Standing Order), POS (Point of Sale), BACS, CHAPS, ATM - Interest charges, bank fees, overdraft information may be included - NOT an invoice - this is account activity documentation
TRANSACTION TYPES COMMONLY SEEN: - Direct Debits (regular bills: utilities, subscriptions) - Standing Orders (regular transfers) - Card payments (POS, contactless, chip & PIN) - Bank transfers (BACS, CHAPS, Faster Payments) - ATM withdrawals - Salary deposits - Interest earned/charged ] </document-types>
<classification-examples> Example 1 - Invoice Classification: Visual evidence: Header text ""TAX INVOICE"", company logo at top, table with columns (Description, Qty, Unit Price, Amount) Textual evidence: ""Invoice Number: INV-2024-12345"", ""Invoice Date: 15/11/2024"", itemized list showing ""Office Chairs x 5 @ £120.00"", financial calculation showing ""Subtotal: £600.00"", ""VAT 20%: £120.00"", ""Total Due: £720.00"", ""Payment Terms: Net 30 days"" Classification: ""invoice"" Confidence: 0.98 Reasoning: Clear invoice structure with all distinctive features - invoice number, supplier details, itemized charges, VAT breakdown, payment terms. High confidence due to multiple matching identifiers. Document Boundary: start
Example 2 - Bank Statement Classification: Visual evidence: Bank logo (Barclays), professional letterhead, transaction table layout with date/description/amount columns Textual evidence: ""Barclays Bank PLC"", ""Statement Period: 01/10/2024 - 31/10/2024"", ""Account: ****1234"", ""Sort Code: 20-00-00"", ""Opening Balance: £5,420.50"", transaction list including ""15 Oct DD - Electric Company £85.00"", ""18 Oct POS - Tesco Superstore £42.15"", ""25 Oct BACS Credit - Salary £2,800.00"", ""Closing Balance: £8,093.35"" Classification: ""bank-statement"" Confidence: 0.99 Reasoning: Unmistakable bank statement format - bank header, statement period, account details, chronological transactions with debits/credits, running balance. All key identifiers present. Document Boundary: start
Example 3 - Expense Receipt (Invoice subtype): Visual evidence: Simple receipt format from retail store, POS terminal print style Textual evidence: ""Tesco Express"", ""Receipt #: 1234"", ""Date: 15/11/2024"", list of grocery items with prices, ""Total: £35.42"", ""Card Payment"" Classification: ""invoice"" Confidence: 0.85 Reasoning: Classifying as ""invoice"" because it shows itemized purchases with amounts. This is a receipt/expense claim document (invoice subtype). Confidence slightly lower than formal B2B invoices due to simpler format, but still clearly requesting/documenting payment for goods. Document Boundary: start </classification-examples>
<classification-instructions> Follow these steps to achieve HIGH CONFIDENCE classification:
1. VISUAL ANALYSIS:
   - Examine logos, headers, letterheads (bank logos vs company logos)
   - Analyze document structure (transaction table vs itemized invoice)
   - Check for distinctive formatting (statement period vs invoice number)

2. TEXTUAL ANALYSIS:
   - Identify key terminology (""Invoice"", ""Statement"", ""Account"", ""VAT"", ""Sort Code"")
   - Look for distinctive metadata (invoice number format vs account number format)
   - Analyze transaction/line item patterns (money IN/OUT vs items purchased)

3. FEATURE MATCHING:
   - Count how many KEY IDENTIFIERS match each document type
   - More matches = higher confidence
   - Look for DISTINGUISHING FEATURES that definitively rule in/out types

4. CONFIDENCE ASSESSMENT:
   HIGH (0.90-1.0): Multiple distinctive features clearly match ONE type, no ambiguity
   MEDIUM (0.70-0.89): Most features match, minor ambiguity or missing secondary features
   LOW (0.0-0.69): Limited features, conflicting signals, or poor image quality

5. DOCUMENT BOUNDARY (CRITICAL FOR ACCURATE BATCHING):
   This flag determines whether a page starts a NEW document or continues the previous one.
   Accurate boundary detection enables optimal parallel processing.
   
   ⚠️ CRITICAL RULE: When classifying EACH PAGE INDEPENDENTLY, you must determine if this page
   starts a NEW invoice or continues the PREVIOUS invoice. Look for continuation signals!
   
   For INVOICES - Set ""continue"" when you see ANY of these signals:
   ✓ **NO invoice header/title** at top of page (no ""INVOICE"", ""TAX INVOICE"", ""RECEIPT"")
   ✓ **NO ""Bill To:"" or ""To:"" section** (new invoices always have recipient details)
   ✓ **NO company logo/letterhead** at top (continuation pages are plain)
   ✓ **Mid-table content** - Description/Qty/Price columns continuing from previous page
   ✓ **Page number indicators**: ""Page 2 of 3"", ""Continued from page X"", ""Page 2""
   ✓ **Terms & conditions** at bottom (usually last page of invoice)
   ✓ **Footer text only** - payment instructions, disclaimers, thank you notes
   ✓ **Same invoice number visible** as previous page (if you can infer context)
   
   For INVOICES - Set ""start"" ONLY when you see CLEAR SIGNALS of a NEW invoice:
   ✓ NEW ""Invoice Number:"" or ""Invoice #XXX"" in header area
   ✓ NEW ""Bill To:"" or ""To:"" section (indicates new customer/recipient)
   ✓ Company logo/letterhead at TOP of page (fresh invoice header)
   ✓ Fresh invoice header text: ""INVOICE"", ""TAX INVOICE"", ""RECEIPT"" at top
   ✓ New invoice date in header area (not buried in footer)
   ✓ Line items table starting from beginning (not mid-table continuation)
   
   **DEFAULT BEHAVIOR - CRITICAL**:
   - If page has NO clear invoice header/logo/recipient → prefer ""continue""
   - If page looks like middle of a table → definitely ""continue""
   - If page has footer/terms only → definitely ""continue""
   - Only use ""start"" when you see CLEAR NEW INVOICE SIGNALS
   - **When uncertain, prefer ""continue"" to avoid splitting multi-page invoices**
   
   For BANK STATEMENTS - Set ""start"" when you see:
   ✓ Bank logo and statement header
   ✓ ""Statement Period: DD/MM/YYYY - DD/MM/YYYY""
   ✓ New account number or statement date range
   
   For BANK STATEMENTS - Set ""continue"" when you see:
   ✓ Transaction list continuation
   ✓ Same account number, continued transaction table
   
   **REMEMBER**: You see ONE page at a time. Look for absence of invoice header signals!

6. CRITICAL: Only use document types explicitly listed in <document-types> section above </classification-instructions>
<disambiguation-rules> Invoice vs Bank Statement confusion points: - Invoice: Shows WHAT was purchased (line items) and money OWED - Bank Statement: Shows WHERE money went/came from (transactions) and account ACTIVITY - Invoice: Has supplier details, invoice number, payment terms - Bank Statement: Has bank logo, account number, statement period - Invoice: Requests payment or documents a purchase - Bank Statement: Documents account history over time
If uncertain, check: - Does it have an invoice number? → Likely invoice - Does it have an account number and statement period? → Likely bank-statement - Does it show ""Total Due"" or ""Amount Owed""? → Likely invoice - Does it show ""Opening Balance"" and ""Closing Balance""? → Likely bank-statement </disambiguation-rules>
<output-format> ⚠️  CRITICAL: You MUST respond with ONLY valid JSON. No additional text before or after the JSON object. ⚠️  Your response must START with { and END with } - nothing else! ⚠️  Do NOT write explanations, comments, or markdown - ONLY the JSON object!
Expected JSON structure: {
  ""classification_reason"": ""Detailed reasoning with specific visual and textual evidence that led to this classification. List the KEY IDENTIFIERS found and explain why confidence is high/medium/low."",
  ""class"": ""exact_document_type_from_list"",
  ""confidence"": 0.95,
  ""document_boundary"": ""start""
}
Field requirements: - ""class"": MUST be exactly ""invoice"" or ""bank-statement"" (lowercase, hyphen for bank statement) - ""confidence"": Number between 0.0 and 1.0 - ""document_boundary"": MUST be exactly ""start"" or ""continue"" (lowercase) - ""classification_reason"": Brief explanation (1-2 sentences)
INCORRECT examples (DO NOT USE - these will cause parsing errors): ❌ ""Class"": ""Invoice"" (wrong case and capitalization) ❌ ""class"": ""bank statement"" (use hyphen: ""bank-statement"") ❌ ""document_boundary"": ""Start"" (must be lowercase: ""start"") ❌ Adding explanatory text outside the JSON object ❌ Here is my analysis: {...} (no text before the JSON!) ❌ ```json\
{...}\
``` (no markdown code blocks!) ❌ Let me classify this page. {...} (no explanatory text!)
CORRECT example (THIS IS EXACTLY WHAT YOU MUST RETURN): ✅ {""classification_reason"": ""Clear invoice with invoice number INV-123, itemized charges, and VAT breakdown"", ""class"": ""invoice"", ""confidence"": 0.95, ""document_boundary"": ""start""}
Remember: Your entire response must be parseable as JSON. Test mentally: can I call JSON.parse() on my response? </output-format>

<document-ocr-data> To: Newsteer Limited 12a Fleet Business Park Sandy Lane Church Crookham Fleet Hampshire GU52 8BF UNITED KINGDOM Invoice Date 2 Feb 2024 Reference Number Expense Claims Ross Bettridge (ross.bettridge@gmail.com) Description Quantity Unit Price VAT Amount GBP EE - Phone 1.00 30.00 No VAT 30.00 Subtotal 30.00 TOTAL GBP 30.00 Less Amount Paid 30.00 AMOUNT DUE 0.00 DUE DATE 23 Apr 2024 This is not a tax invoice </document-ocr-data>
<document-image> '}, {'image': '[image_data]'}, {'text': ' </document-image>
<final-instructions> Analyze the document above by: 1. Applying the <classification-instructions> to examine visual and textual features 2. Using <classification-examples> as reference patterns 3. Applying <disambiguation-rules> if choosing between invoice and bank-statement 4. Selecting ONLY from document types in <document-types> 5. Providing confidence score based on strength of evidence 6. Outputting in EXACT JSON format specified in <output-format>
CRITICAL FORMATTING RULES: - Output ONLY the JSON object, nothing else - Use exact lowercase values: ""invoice"" or ""bank-statement"" for class - Use exact lowercase values: ""start"" or ""continue"" for document_boundary - Ensure valid JSON syntax (proper quotes, commas, braces) - Do NOT add explanatory text before or after the JSON </final-instructions>'}]}]
"
1764447304746,"[INFO]	2025-11-29T20:15:04.746Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - additionalModelRequestFields: {'inferenceConfig': {'topK': 5}}
"
1764447304770,"[INFO]	2025-11-29T20:15:04.770Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 2.50s
"
1764447304770,"[INFO]	2025-11-29T20:15:04.770Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5015, 'outputTokens': 83, 'totalTokens': 5098}
"
1764447304799,"[WARNING]	2025-11-29T20:15:04.799Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447304800,"[INFO]	2025-11-29T20:15:04.799Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 2.43s
"
1764447304800,"[INFO]	2025-11-29T20:15:04.800Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5014, 'outputTokens': 88, 'totalTokens': 5102}
"
1764447304800,"[INFO]	2025-11-29T20:15:04.800Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	No resize requested (width or height is None/empty), returning original image
"
1764447304800,"[INFO]	2025-11-29T20:15:04.800Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Detected image format: jpeg
"
1764447304800,"[INFO]	2025-11-29T20:15:04.800Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Classifying page 28 with Bedrock
"
1764447304867,"[INFO]	2025-11-29T20:15:04.867Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 4: 2.73 seconds
"
1764447304868,"[WARNING]	2025-11-29T20:15:04.868Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447304868,"[WARNING]	2025-11-29T20:15:04.868Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447304868,"[INFO]	2025-11-29T20:15:04.868Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice structure with a recipient section, invoice date, reference number, itemized charges, and financial calculations. It also includes a note stating 'This is not a tax invoice', which confirms it is an expense claim rather than a VAT invoice."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447304868,"[INFO]	2025-11-29T20:15:04.868Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 4 classified as invoice
"
1764447304891,"[INFO]	2025-11-29T20:15:04.891Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 2: 2.75 seconds
"
1764447304892,"[WARNING]	2025-11-29T20:15:04.892Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447304892,"[WARNING]	2025-11-29T20:15:04.892Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447304892,"[INFO]	2025-11-29T20:15:04.892Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, recipient details, itemized charges, and financial calculations typical of an invoice. It includes an invoice date, reference number, and amount due section, confirming it as an invoice.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447304892,"[INFO]	2025-11-29T20:15:04.892Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 2 classified as invoice
"
1764447304910,"[WARNING]	2025-11-29T20:15:04.910Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447304911,"[INFO]	2025-11-29T20:15:04.911Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 2.69s
"
1764447304911,"[INFO]	2025-11-29T20:15:04.911Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5017, 'outputTokens': 125, 'totalTokens': 5142}
"
1764447304952,"[INFO]	2025-11-29T20:15:04.952Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 1: 2.81 seconds
"
1764447304953,"[WARNING]	2025-11-29T20:15:04.953Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447304953,"[WARNING]	2025-11-29T20:15:04.953Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447304953,"[INFO]	2025-11-29T20:15:04.953Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice structure with a recipient section, invoice date, reference number, itemized charges, and financial calculations. It also includes a note stating 'This is not a tax invoice', which aligns with the expense claim subtype of an invoice."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447304953,"[INFO]	2025-11-29T20:15:04.953Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 1 classified as invoice
"
1764447304967,"[INFO]	2025-11-29T20:15:04.967Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 15: 2.82 seconds
"
1764447304969,"[WARNING]	2025-11-29T20:15:04.968Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447304969,"[WARNING]	2025-11-29T20:15:04.969Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447304969,"[INFO]	2025-11-29T20:15:04.969Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, recipient details, itemized charges, and financial calculations typical of an invoice. It includes an invoice date, reference number, and amount due, confirming it as an invoice.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447304969,"[INFO]	2025-11-29T20:15:04.969Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 15 classified as invoice
"
1764447305031,"[WARNING]	2025-11-29T20:15:05.030Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Removed <<CACHEPOINT>> tags for unsupported model: arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.amazon.nova-pro-v1:0. CachePoint is only supported for: eu.anthropic.claude-3-7-sonnet-20250219-v1:0, eu.anthropic.claude-sonnet-4-20250514-v1:0, eu.anthropic.claude-sonnet-4-5-20250929-v1:0, eu.amazon.nova-lite-v1:0, eu.amazon.nova-pro-v1:0
"
1764447305032,"[INFO]	2025-11-29T20:15:05.032Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request attempt 1/7:
"
1764447305032,"[INFO]	2025-11-29T20:15:05.032Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - model: arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.amazon.nova-pro-v1:0
"
1764447305032,"[INFO]	2025-11-29T20:15:05.032Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - inferenceConfig: {'topP': 0.1, 'maxTokens': 8000}
"
1764447305032,"[INFO]	2025-11-29T20:15:05.032Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - system: [{'text': 'You are a multimodal document classification expert specializing in UK financial and commercial documents. Your task is to classify documents into predefined categories with HIGH CONFIDENCE based on visual layout, textual content, and distinctive features. You MUST provide a confidence score from 0.0 to 1.0 reflecting the strength of classification evidence. Your output must be valid JSON according to the requested format.
<variables> <document-ocr-data>: OCR-extracted text content providing textual information for classification <document-image>: Visual representation showing layout, formatting, logos, and structure <document-types>: Valid document types you must classify into - ONLY use types from this list </variables>'}]
"
1764447305032,"[INFO]	2025-11-29T20:15:05.032Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - messages: [{'role': 'user', 'content': [{'text': '<task-description> Analyze the provided document using both visual layout and textual content to determine its document type with high confidence. Decide if this page starts a new document (""start"") or continues the previous document (""continue""). </task-description>
<document-types> invoice  \t[ A commercial invoice or expense claim document issued by a supplier, vendor, or individual to request payment for goods or services purchased.
KEY IDENTIFIERS: - Header text: ""Invoice"", ""Tax Invoice"", ""VAT Invoice"", ""Proforma Invoice"", ""Credit Note"", ""Receipt"" - Supplier/vendor details at top (company name, address, VAT/tax registration number) - Line items table with columns: description, quantity, unit price, amount - Financial calculations: subtotal, VAT/GST breakdown (often 20%% in UK), total amount - Invoice metadata: invoice number, invoice date, due date - Payment terms and bank details for wire transfer - May include purchase order number, customer reference
DISTINGUISHING FEATURES: - Itemized charges showing WHAT was purchased (products/services) - Amounts OWED (not paid) - this is a request for payment - Business-to-business OR individual-to-business format - VAT invoice number format (e.g., ""INV-2024-001"", ""#12345"") - May show ""PAID"" stamp or payment status if settled
INCLUDES SUBTYPES: - Supplier invoices (formal business invoices with VAT registration) - Expense claims/receipts (individual purchases, simpler format, from shops/restaurants) - Credit notes (negative invoices for refunds/adjustments) ]
bank-statement  \t[ A financial statement issued by a bank or financial institution documenting account activity and transactions over a specific time period.
KEY IDENTIFIERS: - Bank logo and institution name (e.g., Barclays, HSBC, Lloyds, NatWest, Metro Bank) - Account holder name and address - Account number (often partially masked: ****1234) - Sort code (UK: XX-XX-XX format) - Statement period with clear start and end dates - Opening balance and closing balance - Chronological transaction list with dates
TRANSACTION TABLE COLUMNS: - Date (transaction date) - Description (merchant name, payment reference, transaction type) - Money OUT (debits, payments, withdrawals) - Money IN (credits, deposits, transfers received) - Running balance (account balance after each transaction)
DISTINGUISHING FEATURES: - Shows money flowing IN and OUT of an account (not requesting payment) - Transaction history format (NOT itemized sales) - Statement period dates (e.g., ""01 Oct 2024 - 31 Oct 2024"") - Transaction types: DD (Direct Debit), SO (Standing Order), POS (Point of Sale), BACS, CHAPS, ATM - Interest charges, bank fees, overdraft information may be included - NOT an invoice - this is account activity documentation
TRANSACTION TYPES COMMONLY SEEN: - Direct Debits (regular bills: utilities, subscriptions) - Standing Orders (regular transfers) - Card payments (POS, contactless, chip & PIN) - Bank transfers (BACS, CHAPS, Faster Payments) - ATM withdrawals - Salary deposits - Interest earned/charged ] </document-types>
<classification-examples> Example 1 - Invoice Classification: Visual evidence: Header text ""TAX INVOICE"", company logo at top, table with columns (Description, Qty, Unit Price, Amount) Textual evidence: ""Invoice Number: INV-2024-12345"", ""Invoice Date: 15/11/2024"", itemized list showing ""Office Chairs x 5 @ £120.00"", financial calculation showing ""Subtotal: £600.00"", ""VAT 20%: £120.00"", ""Total Due: £720.00"", ""Payment Terms: Net 30 days"" Classification: ""invoice"" Confidence: 0.98 Reasoning: Clear invoice structure with all distinctive features - invoice number, supplier details, itemized charges, VAT breakdown, payment terms. High confidence due to multiple matching identifiers. Document Boundary: start
Example 2 - Bank Statement Classification: Visual evidence: Bank logo (Barclays), professional letterhead, transaction table layout with date/description/amount columns Textual evidence: ""Barclays Bank PLC"", ""Statement Period: 01/10/2024 - 31/10/2024"", ""Account: ****1234"", ""Sort Code: 20-00-00"", ""Opening Balance: £5,420.50"", transaction list including ""15 Oct DD - Electric Company £85.00"", ""18 Oct POS - Tesco Superstore £42.15"", ""25 Oct BACS Credit - Salary £2,800.00"", ""Closing Balance: £8,093.35"" Classification: ""bank-statement"" Confidence: 0.99 Reasoning: Unmistakable bank statement format - bank header, statement period, account details, chronological transactions with debits/credits, running balance. All key identifiers present. Document Boundary: start
Example 3 - Expense Receipt (Invoice subtype): Visual evidence: Simple receipt format from retail store, POS terminal print style Textual evidence: ""Tesco Express"", ""Receipt #: 1234"", ""Date: 15/11/2024"", list of grocery items with prices, ""Total: £35.42"", ""Card Payment"" Classification: ""invoice"" Confidence: 0.85 Reasoning: Classifying as ""invoice"" because it shows itemized purchases with amounts. This is a receipt/expense claim document (invoice subtype). Confidence slightly lower than formal B2B invoices due to simpler format, but still clearly requesting/documenting payment for goods. Document Boundary: start </classification-examples>
<classification-instructions> Follow these steps to achieve HIGH CONFIDENCE classification:
1. VISUAL ANALYSIS:
   - Examine logos, headers, letterheads (bank logos vs company logos)
   - Analyze document structure (transaction table vs itemized invoice)
   - Check for distinctive formatting (statement period vs invoice number)

2. TEXTUAL ANALYSIS:
   - Identify key terminology (""Invoice"", ""Statement"", ""Account"", ""VAT"", ""Sort Code"")
   - Look for distinctive metadata (invoice number format vs account number format)
   - Analyze transaction/line item patterns (money IN/OUT vs items purchased)

3. FEATURE MATCHING:
   - Count how many KEY IDENTIFIERS match each document type
   - More matches = higher confidence
   - Look for DISTINGUISHING FEATURES that definitively rule in/out types

4. CONFIDENCE ASSESSMENT:
   HIGH (0.90-1.0): Multiple distinctive features clearly match ONE type, no ambiguity
   MEDIUM (0.70-0.89): Most features match, minor ambiguity or missing secondary features
   LOW (0.0-0.69): Limited features, conflicting signals, or poor image quality

5. DOCUMENT BOUNDARY (CRITICAL FOR ACCURATE BATCHING):
   This flag determines whether a page starts a NEW document or continues the previous one.
   Accurate boundary detection enables optimal parallel processing.
   
   ⚠️ CRITICAL RULE: When classifying EACH PAGE INDEPENDENTLY, you must determine if this page
   starts a NEW invoice or continues the PREVIOUS invoice. Look for continuation signals!
   
   For INVOICES - Set ""continue"" when you see ANY of these signals:
   ✓ **NO invoice header/title** at top of page (no ""INVOICE"", ""TAX INVOICE"", ""RECEIPT"")
   ✓ **NO ""Bill To:"" or ""To:"" section** (new invoices always have recipient details)
   ✓ **NO company logo/letterhead** at top (continuation pages are plain)
   ✓ **Mid-table content** - Description/Qty/Price columns continuing from previous page
   ✓ **Page number indicators**: ""Page 2 of 3"", ""Continued from page X"", ""Page 2""
   ✓ **Terms & conditions** at bottom (usually last page of invoice)
   ✓ **Footer text only** - payment instructions, disclaimers, thank you notes
   ✓ **Same invoice number visible** as previous page (if you can infer context)
   
   For INVOICES - Set ""start"" ONLY when you see CLEAR SIGNALS of a NEW invoice:
   ✓ NEW ""Invoice Number:"" or ""Invoice #XXX"" in header area
   ✓ NEW ""Bill To:"" or ""To:"" section (indicates new customer/recipient)
   ✓ Company logo/letterhead at TOP of page (fresh invoice header)
   ✓ Fresh invoice header text: ""INVOICE"", ""TAX INVOICE"", ""RECEIPT"" at top
   ✓ New invoice date in header area (not buried in footer)
   ✓ Line items table starting from beginning (not mid-table continuation)
   
   **DEFAULT BEHAVIOR - CRITICAL**:
   - If page has NO clear invoice header/logo/recipient → prefer ""continue""
   - If page looks like middle of a table → definitely ""continue""
   - If page has footer/terms only → definitely ""continue""
   - Only use ""start"" when you see CLEAR NEW INVOICE SIGNALS
   - **When uncertain, prefer ""continue"" to avoid splitting multi-page invoices**
   
   For BANK STATEMENTS - Set ""start"" when you see:
   ✓ Bank logo and statement header
   ✓ ""Statement Period: DD/MM/YYYY - DD/MM/YYYY""
   ✓ New account number or statement date range
   
   For BANK STATEMENTS - Set ""continue"" when you see:
   ✓ Transaction list continuation
   ✓ Same account number, continued transaction table
   
   **REMEMBER**: You see ONE page at a time. Look for absence of invoice header signals!

6. CRITICAL: Only use document types explicitly listed in <document-types> section above </classification-instructions>
<disambiguation-rules> Invoice vs Bank Statement confusion points: - Invoice: Shows WHAT was purchased (line items) and money OWED - Bank Statement: Shows WHERE money went/came from (transactions) and account ACTIVITY - Invoice: Has supplier details, invoice number, payment terms - Bank Statement: Has bank logo, account number, statement period - Invoice: Requests payment or documents a purchase - Bank Statement: Documents account history over time
If uncertain, check: - Does it have an invoice number? → Likely invoice - Does it have an account number and statement period? → Likely bank-statement - Does it show ""Total Due"" or ""Amount Owed""? → Likely invoice - Does it show ""Opening Balance"" and ""Closing Balance""? → Likely bank-statement </disambiguation-rules>
<output-format> ⚠️  CRITICAL: You MUST respond with ONLY valid JSON. No additional text before or after the JSON object. ⚠️  Your response must START with { and END with } - nothing else! ⚠️  Do NOT write explanations, comments, or markdown - ONLY the JSON object!
Expected JSON structure: {
  ""classification_reason"": ""Detailed reasoning with specific visual and textual evidence that led to this classification. List the KEY IDENTIFIERS found and explain why confidence is high/medium/low."",
  ""class"": ""exact_document_type_from_list"",
  ""confidence"": 0.95,
  ""document_boundary"": ""start""
}
Field requirements: - ""class"": MUST be exactly ""invoice"" or ""bank-statement"" (lowercase, hyphen for bank statement) - ""confidence"": Number between 0.0 and 1.0 - ""document_boundary"": MUST be exactly ""start"" or ""continue"" (lowercase) - ""classification_reason"": Brief explanation (1-2 sentences)
INCORRECT examples (DO NOT USE - these will cause parsing errors): ❌ ""Class"": ""Invoice"" (wrong case and capitalization) ❌ ""class"": ""bank statement"" (use hyphen: ""bank-statement"") ❌ ""document_boundary"": ""Start"" (must be lowercase: ""start"") ❌ Adding explanatory text outside the JSON object ❌ Here is my analysis: {...} (no text before the JSON!) ❌ ```json\
{...}\
``` (no markdown code blocks!) ❌ Let me classify this page. {...} (no explanatory text!)
CORRECT example (THIS IS EXACTLY WHAT YOU MUST RETURN): ✅ {""classification_reason"": ""Clear invoice with invoice number INV-123, itemized charges, and VAT breakdown"", ""class"": ""invoice"", ""confidence"": 0.95, ""document_boundary"": ""start""}
Remember: Your entire response must be parseable as JSON. Test mentally: can I call JSON.parse() on my response? </output-format>

<document-ocr-data> To: Newsteer Limited 12a Fleet Business Park Sandy Lane Church Crookham Fleet Hampshire GU52 8BF UNITED KINGDOM Invoice Date 9 Jan 2024 Industrial Agents Society Reference Number CE518F1F3525 Description Quantity Unit Price VAT Amount GBP IAS Subscription (Agent) 1.00 75.00 20% 75.00 Jan 9, 2024 - Jan 9, 2025 - Tracy Cooper Subtotal 75.00 TOTAL 20% 15.00 TOTAL GBP 90.00 Less Amount Paid 90.00 AMOUNT DUE 0.00 DUE DATE 9 Jan 2024 This is not a tax invoice </document-ocr-data>
<document-image> '}, {'image': '[image_data]'}, {'text': ' </document-image>
<final-instructions> Analyze the document above by: 1. Applying the <classification-instructions> to examine visual and textual features 2. Using <classification-examples> as reference patterns 3. Applying <disambiguation-rules> if choosing between invoice and bank-statement 4. Selecting ONLY from document types in <document-types> 5. Providing confidence score based on strength of evidence 6. Outputting in EXACT JSON format specified in <output-format>
CRITICAL FORMATTING RULES: - Output ONLY the JSON object, nothing else - Use exact lowercase values: ""invoice"" or ""bank-statement"" for class - Use exact lowercase values: ""start"" or ""continue"" for document_boundary - Ensure valid JSON syntax (proper quotes, commas, braces) - Do NOT add explanatory text before or after the JSON </final-instructions>'}]}]
"
1764447305033,"[INFO]	2025-11-29T20:15:05.033Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  - additionalModelRequestFields: {'inferenceConfig': {'topK': 5}}
"
1764447305164,"[INFO]	2025-11-29T20:15:05.164Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 14: 3.02 seconds
"
1764447305165,"[WARNING]	2025-11-29T20:15:05.165Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305165,"[WARNING]	2025-11-29T20:15:05.165Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305165,"[INFO]	2025-11-29T20:15:05.165Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice structure with a recipient section, invoice date, reference number, itemized charges, and financial calculations. It also includes an 'AMOUNT DUE' section showing zero due, indicating full payment."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447305165,"[INFO]	2025-11-29T20:15:05.165Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 14 classified as invoice
"
1764447305172,"[INFO]	2025-11-29T20:15:05.172Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 20: 3.03 seconds
"
1764447305172,"[WARNING]	2025-11-29T20:15:05.172Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305172,"[WARNING]	2025-11-29T20:15:05.172Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305172,"[INFO]	2025-11-29T20:15:05.172Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice structure with a recipient section, invoice date, reference number, itemized charges, and financial calculations. It also includes an invoice number and payment details, aligning with the key identifiers of an invoice.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447305172,"[INFO]	2025-11-29T20:15:05.172Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 20 classified as invoice
"
1764447305212,"[INFO]	2025-11-29T20:15:05.212Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.38s
"
1764447305212,"[INFO]	2025-11-29T20:15:05.212Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5014, 'outputTokens': 72, 'totalTokens': 5086}
"
1764447305301,"[INFO]	2025-11-29T20:15:05.300Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 6: 3.16 seconds
"
1764447305302,"[WARNING]	2025-11-29T20:15:05.302Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305302,"[WARNING]	2025-11-29T20:15:05.302Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305302,"[INFO]	2025-11-29T20:15:05.302Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, recipient details, itemized charges, and financial calculations typical of an invoice. It includes an invoice date, reference number, and amount due section, confirming it as an invoice.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447305302,"[INFO]	2025-11-29T20:15:05.302Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 6 classified as invoice
"
1764447305316,"[INFO]	2025-11-29T20:15:05.316Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 18: 3.15 seconds
"
1764447305317,"[WARNING]	2025-11-29T20:15:05.317Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305317,"[WARNING]	2025-11-29T20:15:05.317Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305317,"[INFO]	2025-11-29T20:15:05.317Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice structure with a recipient section, invoice date, reference number, itemized charges, and total amount due. It also includes a note stating 'This is not a tax invoice', which aligns with the expense claim subtype of an invoice."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447305317,"[INFO]	2025-11-29T20:15:05.317Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 18 classified as invoice
"
1764447305324,"[INFO]	2025-11-29T20:15:05.324Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 11: 3.18 seconds
"
1764447305325,"[WARNING]	2025-11-29T20:15:05.325Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305325,"[WARNING]	2025-11-29T20:15:05.325Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305326,"[INFO]	2025-11-29T20:15:05.326Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice header, reference number, itemized charges, and financial calculations typical of an invoice. It includes a recipient section, invoice date, and a table with description, quantity, unit price, VAT, and amount. The presence of 'AMOUNT DUE' and 'DUE DATE' further confirms it is an invoice."", 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447305326,"[INFO]	2025-11-29T20:15:05.326Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 11 classified as invoice
"
1764447305340,"[INFO]	2025-11-29T20:15:05.340Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 9: 3.20 seconds
"
1764447305341,"[WARNING]	2025-11-29T20:15:05.341Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305341,"[WARNING]	2025-11-29T20:15:05.341Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305341,"[INFO]	2025-11-29T20:15:05.341Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice structure with a recipient section, invoice date, reference number, itemized charges, and financial calculations. It also includes a note stating 'This is not a tax invoice', which aligns with the expense claim subtype of an invoice."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447305341,"[INFO]	2025-11-29T20:15:05.341Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 9 classified as invoice
"
1764447305346,"[INFO]	2025-11-29T20:15:05.346Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 16: 3.21 seconds
"
1764447305348,"[WARNING]	2025-11-29T20:15:05.348Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305348,"[WARNING]	2025-11-29T20:15:05.348Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305348,"[INFO]	2025-11-29T20:15:05.348Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice header, reference number, itemized charges, and financial calculations typical of an invoice. The presence of 'Invoice Date', 'Reference Number', and 'Amount Due' further confirms it as an invoice."", 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447305348,"[INFO]	2025-11-29T20:15:05.348Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 16 classified as invoice
"
1764447305421,"[INFO]	2025-11-29T20:15:05.421Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 8: 3.28 seconds
"
1764447305423,"[WARNING]	2025-11-29T20:15:05.423Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305423,"[WARNING]	2025-11-29T20:15:05.423Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305423,"[INFO]	2025-11-29T20:15:05.423Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear header 'Invoice Date', 'Reference Number', and itemized charges with a description, quantity, unit price, VAT, and amount. It also includes a 'TOTAL GBP', 'Less Amount Paid', and 'AMOUNT DUE' sections, which are typical of an invoice. The presence of 'This is not a tax invoice' further supports the classification as an expense claim (a subtype of invoice)."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447305423,"[INFO]	2025-11-29T20:15:05.423Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 8 classified as invoice
"
1764447305443,"[INFO]	2025-11-29T20:15:05.442Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 21: 1.63 seconds
"
1764447305443,"[WARNING]	2025-11-29T20:15:05.443Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305443,"[WARNING]	2025-11-29T20:15:05.443Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305443,"[INFO]	2025-11-29T20:15:05.443Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, recipient details, itemized charges, and financial calculations typical of an invoice. It also includes an invoice date, reference number, and payment details.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447305443,"[INFO]	2025-11-29T20:15:05.443Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 21 classified as invoice
"
1764447305553,"[WARNING]	2025-11-29T20:15:05.552Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447305553,"[INFO]	2025-11-29T20:15:05.553Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.47s
"
1764447305553,"[INFO]	2025-11-29T20:15:05.553Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5023, 'outputTokens': 80, 'totalTokens': 5103}
"
1764447305644,"[INFO]	2025-11-29T20:15:05.644Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 22: 1.58 seconds
"
1764447305644,"[WARNING]	2025-11-29T20:15:05.644Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305644,"[WARNING]	2025-11-29T20:15:05.644Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305644,"[INFO]	2025-11-29T20:15:05.644Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, recipient details, itemized charges, and financial calculations typical of an invoice. It includes an invoice date, reference number, and amount due section, confirming it is a request for payment.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447305644,"[INFO]	2025-11-29T20:15:05.644Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 22 classified as invoice
"
1764447305731,"[WARNING]	2025-11-29T20:15:05.731Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447305732,"[INFO]	2025-11-29T20:15:05.731Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.60s
"
1764447305732,"[INFO]	2025-11-29T20:15:05.732Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 4997, 'outputTokens': 83, 'totalTokens': 5080}
"
1764447305817,"[INFO]	2025-11-29T20:15:05.817Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 23: 1.70 seconds
"
1764447305817,"[WARNING]	2025-11-29T20:15:05.817Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447305817,"[WARNING]	2025-11-29T20:15:05.817Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447305817,"[INFO]	2025-11-29T20:15:05.817Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice header, reference number, itemized charges, and financial calculations typical of an invoice. It also includes a due date and states 'This is not a tax invoice', confirming it is an expense claim invoice."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447305817,"[INFO]	2025-11-29T20:15:05.817Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 23 classified as invoice
"
1764447305994,"[WARNING]	2025-11-29T20:15:05.994Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447305994,"[INFO]	2025-11-29T20:15:05.994Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.74s
"
1764447305994,"[INFO]	2025-11-29T20:15:05.994Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 8968, 'outputTokens': 72, 'totalTokens': 9040}
"
1764447305996,"[WARNING]	2025-11-29T20:15:05.996Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447305997,"[INFO]	2025-11-29T20:15:05.997Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.70s
"
1764447305997,"[INFO]	2025-11-29T20:15:05.997Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5003, 'outputTokens': 78, 'totalTokens': 5081}
"
1764447306009,"[WARNING]	2025-11-29T20:15:06.009Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447306010,"[INFO]	2025-11-29T20:15:06.010Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.51s
"
1764447306010,"[INFO]	2025-11-29T20:15:06.010Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5014, 'outputTokens': 84, 'totalTokens': 5098}
"
1764447306202,"[INFO]	2025-11-29T20:15:06.202Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 24: 2.02 seconds
"
1764447306204,"[WARNING]	2025-11-29T20:15:06.203Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447306204,"[WARNING]	2025-11-29T20:15:06.204Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447306204,"[INFO]	2025-11-29T20:15:06.204Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a header labeled 'Invoice', includes an invoice date, reference number, and itemized charges with VAT details, aligning with the structure and key identifiers of an invoice."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447306204,"[INFO]	2025-11-29T20:15:06.204Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 24 classified as invoice
"
1764447306217,"[INFO]	2025-11-29T20:15:06.216Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 25: 1.95 seconds
"
1764447306218,"[WARNING]	2025-11-29T20:15:06.218Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447306218,"[WARNING]	2025-11-29T20:15:06.218Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447306218,"[INFO]	2025-11-29T20:15:06.218Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, recipient details, itemized charges, and financial calculations typical of an invoice. It includes an invoice date, reference number, and amount due section, confirming it as an invoice.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447306218,"[INFO]	2025-11-29T20:15:06.218Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 25 classified as invoice
"
1764447306224,"[INFO]	2025-11-29T20:15:06.224Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 26: 1.78 seconds
"
1764447306224,"[WARNING]	2025-11-29T20:15:06.224Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447306224,"[WARNING]	2025-11-29T20:15:06.224Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447306224,"[INFO]	2025-11-29T20:15:06.224Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': ""The document contains a clear invoice structure with a recipient section, invoice date, reference number, itemized charges, and total amount due. It also includes a note stating 'This is not a tax invoice', confirming it as an expense claim."", 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447306224,"[INFO]	2025-11-29T20:15:06.224Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 26 classified as invoice
"
1764447306319,"[WARNING]	2025-11-29T20:15:06.319Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447306319,"[INFO]	2025-11-29T20:15:06.319Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.57s
"
1764447306320,"[INFO]	2025-11-29T20:15:06.320Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5009, 'outputTokens': 78, 'totalTokens': 5087}
"
1764447306392,"[WARNING]	2025-11-29T20:15:06.392Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Connection pool is full, discarding connection: bedrock-runtime.eu-central-1.amazonaws.com. Connection pool size: 10
"
1764447306392,"[INFO]	2025-11-29T20:15:06.392Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Bedrock request successful after 1 attempts. Duration: 1.36s
"
1764447306392,"[INFO]	2025-11-29T20:15:06.392Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Token Usage: {'inputTokens': 5043, 'outputTokens': 64, 'totalTokens': 5107}
"
1764447306412,"[INFO]	2025-11-29T20:15:06.412Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 27: 1.76 seconds
"
1764447306413,"[WARNING]	2025-11-29T20:15:06.413Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447306413,"[WARNING]	2025-11-29T20:15:06.413Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447306414,"[INFO]	2025-11-29T20:15:06.414Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, recipient details, itemized charges, and financial calculations typical of an invoice. It includes an invoice date, reference number, and amount due section, confirming it as an invoice.', 'class': 'invoice', 'confidence': 0.95, 'document_boundary': 'start'}
"
1764447306414,"[INFO]	2025-11-29T20:15:06.414Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 27 classified as invoice
"
1764447306487,"[INFO]	2025-11-29T20:15:06.487Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification of page 28: 1.69 seconds
"
1764447306487,"[WARNING]	2025-11-29T20:15:06.487Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Structured data extraction will only work for JSON.
"
1764447306487,"[WARNING]	2025-11-29T20:15:06.487Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	YAML library not available. Format detection will only work for JSON.
"
1764447306487,"[INFO]	2025-11-29T20:15:06.487Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Parsed classification response as json: {'classification_reason': 'The document contains a clear invoice header, reference number, itemized charges, VAT breakdown, and total amount due, indicating it is an invoice.', 'class': 'invoice', 'confidence': 0.98, 'document_boundary': 'start'}
"
1764447306487,"[INFO]	2025-11-29T20:15:06.487Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Page 28 classified as invoice
"
1764447306489,"[INFO]	2025-11-29T20:15:06.489Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	All pages succeeded for document users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf - skipping cache (no retry needed)
"
1764447306489,"[INFO]	2025-11-29T20:15:06.489Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Document classified with 28 sections in 4.77 seconds
"
1764447306489,"[INFO]	2025-11-29T20:15:06.489Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	🔧 Smart batching enabled - creating optimized sections
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Detected 28 invoices in 28 pages
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Created section 1: 15 invoices, 15 pages
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Created section 2 (final): 13 invoices, 13 pages
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Smart batching complete: 28 pages → 2 sections
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	✅ Smart batching complete: 28 original sections → 2 optimized sections
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	================================================================================
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	📊 Classification complete: 28 pages, ~28 invoices across 2 sections
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	   (Page count = VALIDATION, Invoice count = METRIC)
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  Section 1: invoice, 15 pages, ~15 invoices
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	  Section 2: invoice, 13 pages, ~13 invoices
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	================================================================================
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	🔄 Using user hint 'invoice' for routing (validation mode)
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	📝 Overrode classification: model='invoice' → user='invoice' (confidence=1.00) for routing
"
1764447306490,"[INFO]	2025-11-29T20:15:06.490Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	🔍 VALIDATION: user='invoice', model='invoice' (confidence=1.00), match=True
"
1764447306601,"[INFO]	2025-11-29T20:15:06.601Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	✅ User and model agree on 'invoice'. Validation ID: 5f17b93c-ce2a-48c2-93ec-244822ed89a3
"
1764447306601,"[INFO]	2025-11-29T20:15:06.601Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Time taken for classification: 4.94 seconds
"
1764447306601,"[INFO]	2025-11-29T20:15:06.601Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	🔍 LLM boundary detection enabled (model: arn:aws:bedrock:eu-central-1:864899848062:inference-profile/eu.anthropic.claude-3-5-sonnet-20240620-v1:0)
"
1764447306607,"[INFO]	2025-11-29T20:15:06.607Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	🔍 Detecting boundaries for invoice section 1
"
1764447307139,"[INFO]	2025-11-29T20:15:07.139Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	📄 Section text length: 89135 chars
"
1764447307139,"[ERROR]	2025-11-29T20:15:07.139Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	❌ Error in LLM boundary detection: '
    ""id""'
"
1764447307139,"[WARNING]	2025-11-29T20:15:07.139Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	⚠️ Boundary detection/validation failed for section 1
"
1764447307140,"[INFO]	2025-11-29T20:15:07.140Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	🔍 Detecting boundaries for invoice section 2
"
1764447307611,"[INFO]	2025-11-29T20:15:07.610Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	📄 Section text length: 38184 chars
"
1764447307611,"[ERROR]	2025-11-29T20:15:07.611Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	❌ Error in LLM boundary detection: '
    ""id""'
"
1764447307611,"[WARNING]	2025-11-29T20:15:07.611Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	⚠️ Boundary detection/validation failed for section 2
"
1764447307611,"[INFO]	2025-11-29T20:15:07.611Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Lambda metering for Classification: duration=6.754s, memory=4096.0MB, gb_seconds=27.0
"
1764447307611,"[INFO]	2025-11-29T20:15:07.611Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Document size after classification: 22694 bytes
"
1764447307611,"[INFO]	2025-11-29T20:15:07.611Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Document size (22694 bytes) exceeds 0KB threshold, compressing to S3
"
1764447307725,"[INFO]	2025-11-29T20:15:07.725Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Compressed document users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf to s3://fiscalshield-idp-dev-workingbucket-c1mept6rt9di/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764447307617_classification_state.json
"
1764447307727,"[INFO]	2025-11-29T20:15:07.726Z	b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Response: {""document"": {""id"": ""users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf"", ""document_id"": ""users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf"", ""s3_uri"": ""s3://fiscalshield-idp-dev-workingbucket-c1mept6rt9di/compressed_documents/users/23b4b872-20a1-709e-ffef-d20a604f60b5/test_invoice.pdf/1764447307617_classification_state.json"", ""timestamp"": ""1764447307617"", ""status"": ""CLASSIFYING"", ""num_pages"": 28, ""sections"": [{""section_id"": ""1"", ""classification"": ""invoice"", ""confidence"": 1.0}, {""section_id"": ""2"", ""classification"": ""invoice"", ""confidence"": 1.0}], ""compressed"": true, ""user_id"": ""23b4b872-20a1-709e-ffef-d20a604f60b5"", ""client_id"": ""15944206"", ""company_number"": ""15944206"", ""company_name"": ""TRESAI LIMITED""}}
"
1764447307734,"END RequestId: b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56
"
1764447307734,"REPORT RequestId: b7f8b2b0-7cdf-4fe5-8fa7-290f78c28f56	Duration: 6877.09 ms	Billed Duration: 8014 ms	Memory Size: 4096 MB	Max Memory Used: 152 MB	Init Duration: 1136.31 ms	
"