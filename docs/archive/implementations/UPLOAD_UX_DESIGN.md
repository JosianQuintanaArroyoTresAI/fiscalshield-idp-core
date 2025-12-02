# Upload Interface - Visual Design

## 📱 Complete Layout

```
┌────────────────────────────────────────────────────────────────┐
│                      Upload Documents                          │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│ Select Document Type                                           │
│ Choose the type of documents you want to upload               │
│                                                                │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ 📄 Invoices │  │ 🏦 Bank          │  │ Other Document   │ │
│  │   (ACTIVE)  │  │    Statements    │  │     Types ▼      │ │
│  └─────────────┘  └──────────────────┘  └──────────────────┘ │
│   [Primary Blue]   [Normal Grey]         [Dropdown]          │
└────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────┐
│                                                                │
│                          📁                                    │
│                                                                │
│              Drag and drop files here                          │
│                                                                │
│                          or                                    │
│                                                                │
│                  ┌──────────────────┐                         │
│                  │  Browse Files    │                         │
│                  └──────────────────┘                         │
│                                                                │
│          Supports: PDF, PNG, JPG (Max 100MB per file)         │
│                                                                │
└────────────────────────────────────────────────────────────────┘
                    [Large clickable area]


┌────────────────────────────────────────────────────────────────┐
│ Selected Files (3)                                             │
│                                                                │
│ 📎 invoice-jan-2025.pdf (2.34 MB)                             │
│ 📎 invoice-feb-2025.pdf (1.89 MB)                             │
│ 📎 invoice-mar-2025.pdf (3.12 MB)                             │
└────────────────────────────────────────────────────────────────┘


        ┌───────────────────────────────────────┐
        │  ⬆️  Upload 3 invoice(s)              │
        └───────────────────────────────────────┘
                [Primary Button - Large]
```

## 🎨 State Changes

### **State 1: Initial (No Type Selected)**

```
Document Type Buttons:  [Normal Grey] [Normal Grey] [Dropdown]
Upload Area:            Greyed out, "Select a document type to enable upload"
Browse Button:          Hidden
Upload Button:          Disabled
```

### **State 2: Invoice Selected**

```
Document Type Buttons:  [✓ Primary Blue] [Normal Grey] [Dropdown]
Upload Area:            Active (light background, dashed border)
                       "Drag and drop files here"
Browse Button:          Visible and enabled
Upload Button:          Disabled (no files yet)
```

### **State 3: Files Selected**

```
Document Type Buttons:  [✓ Primary Blue] [Normal Grey] [Dropdown]
Upload Area:            Active
Selected Files Box:     Shows 3 files with names and sizes
Upload Button:          Enabled "Upload 3 invoice(s)"
```

### **State 4: Dragging Over**

```
Upload Area:            Blue dashed border (3px)
                       Blue background tint
                       "Drop files here"
```

### **State 5: Uploading**

```
Document Type Buttons:  Disabled
Upload Area:            Disabled
Upload Button:          Loading spinner "Uploading... (2/3)"
Upload Results:         Shows progress as each file completes
```

### **State 6: Upload Complete**

```
Upload Results Box:     ✅ invoice-jan-2025.pdf: Uploaded successfully
                       ✅ invoice-feb-2025.pdf: Uploaded successfully
                       ✅ invoice-mar-2025.pdf: Uploaded successfully
```

## 🎭 Interactive Behaviors

### **Clicking "Invoices" Button:**
```
Before:  [Normal]  →  After: [✓ Primary Blue]
Effect:  - Upload area becomes active
         - Previous file selection cleared
         - documentType = 'invoice'
```

### **Clicking "Bank Statements" Button:**
```
Before:  [✓ Invoice (Blue)]  →  After: [Normal] [✓ Bank Statements (Blue)]
Effect:  - Switches selection
         - Upload area stays active
         - Previous files cleared
         - documentType = 'bank-statement'
```

### **Opening "Other Document Types" Dropdown:**
```
Shows:  💰 Payslip
        🪪 Driver's License
        📋 W2 Tax Form
        ✅ Check
        🏠 Homeowners Insurance

On Select:
        Dropdown button text changes to "✓ Payslip"
        Dropdown button turns Primary Blue
        documentType = selected value
```

### **Dragging Files Over Upload Area:**
```
Mouse enters with files:
    Border: 2px dashed #aab7b8  →  3px dashed #0972d3
    Background: #fafafa  →  #f0f8ff (light blue)
    Text: "Drag and drop"  →  "Drop files here"

Mouse leaves:
    Returns to normal active state
```

### **Clicking Upload Area:**
```
If document type selected:
    → Opens file browser (same as "Browse Files" button)

If no document type:
    → Shows error: "Please select a document type first"
```

### **Clicking "Browse Files":**
```
Opens native file picker:
    Filter: .pdf, .png, .jpg, .jpeg
    Multiple selection: Enabled
    Max size: 100MB per file
```

## 🌈 Color Scheme

| Element | Normal | Active/Selected | Hover |
|---------|--------|-----------------|-------|
| Document Type Button | Grey (#545b64) | Primary Blue (#0972d3) | Light Blue |
| Upload Area Border | Light Grey (#d5dbdb) | Grey (#aab7b8) | Blue (#0972d3) on drag |
| Upload Area Background | Disabled (#f5f5f5) | Active (#fafafa) | Drag (#f0f8ff) |
| Text | Grey (#545b64) | Dark (#16191f) | - |
| Upload Button | Primary Blue | - | Darker Blue |

## 📐 Dimensions

| Element | Size |
|---------|------|
| Document Type Buttons | Standard height, auto width |
| Upload Area | Full width, 200px height |
| Browse Files Button | Standard button size |
| Upload Button | Full width, large variant |
| File List Items | Full width, compact spacing |

## 🔤 Typography

| Element | Font Style |
|---------|-----------|
| "Upload Documents" | Heading H2 |
| "Select Document Type" | Form Label |
| Button Text | Button Default |
| Drag Area Main Text | Heading M |
| "or" divider | Body S, secondary color |
| File format text | Body S, secondary color |
| File names in list | Body S |

## ✨ Animations

- **Button Selection**: Instant color change with checkmark fade-in
- **Upload Area Activation**: Smooth opacity and border color transition (0.3s)
- **Drag Over**: Border and background color transition (0.2s)
- **File List Appearance**: Fade in (0.3s)
- **Upload Progress**: Smooth progress indicator

## 🎯 User Flow Example

1. **User opens page** → Sees "Select Document Type" with buttons
2. **Clicks "📄 Invoices"** → Button turns blue with ✓, upload area activates
3. **Drags 3 PDF files** → Border turns blue, "Drop files here" message
4. **Drops files** → File list appears showing 3 files with sizes
5. **Clicks "Upload 3 invoice(s)"** → Button shows "Uploading... (1/3)"
6. **Each file uploads** → Results appear with ✅ success indicators
7. **All complete** → Can select new type and upload more files

## 🎪 Edge Cases Handled

✅ **No document type selected** → Upload area disabled with clear message  
✅ **Switch document type** → Previous selection cleared, no confusion  
✅ **Drag without type** → Error message shown  
✅ **Multiple file selection** → All files listed with sizes  
✅ **Upload failure** → Individual file status (success/error)  
✅ **Large files** → Size displayed, 100MB limit enforced by backend  
✅ **Wrong file type** → File picker filters to accepted types  

---

This design creates a clear, intuitive user journey: **Select Type → Upload Files**
