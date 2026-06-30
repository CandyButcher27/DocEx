# Intelligent Document Processing (IDP) Engine --- Architecture Summary (v1)

## Objective

Build a **privacy-first, offline Intelligent Document Processing (IDP)
framework** capable of extracting structured information from
semi-structured documents (insurance forms, KYC forms, invoices, etc.).

The goal is **not** 100% automation.

The goal is:

> Automatically extract all high-confidence fields and ask the user to
> verify or fill only the uncertain ones.

This aligns with real enterprise workflows and significantly reduces
manual effort.

------------------------------------------------------------------------

# High-Level Pipeline

``` text
PDF
│
├── Template Classification
│
├── Known Template?
│       │
│       ├── YES
│       │      ↓
│       │  Load Template
│       │
│       └── NO
│              ↓
│        Local VLM
│              ↓
│      Generate Template
│              ↓
│ Optional Human Verification GUI
│              ↓
│       Save Template
│
▼
ROI Extraction
│
▼
OCR Ensemble
│
▼
Decision Engine
│
▼
Human Review (only uncertain fields)
│
▼
Structured JSON Output
```

------------------------------------------------------------------------

# Module 1 --- Template Classification

## Purpose

Determine whether the uploaded document belongs to a previously known
template.

### Proposed Strategy

Primary: - Template Fingerprinting - Image Hashing

Fallback: - Embedding Similarity - Feature Matching

Reasoning: - Hash lookup is extremely fast. - Embeddings handle slightly
modified templates.

------------------------------------------------------------------------

# Module 2 --- Template Learning

If the template is unknown:

The **local VLM** performs:

-   Layout understanding
-   Field detection
-   Bounding box generation
-   Key-value association

Then:

Optional Human-in-the-Loop GUI

The user verifies:

-   Bounding boxes
-   Labels
-   Key-value mappings

The template is cached for future use.

Future uploads of the same template never invoke the VLM again.

------------------------------------------------------------------------

# Module 3 --- Template Storage

Each template stores:

-   Template ID
-   Bounding Boxes
-   Field Labels
-   Data Types
-   Validation Rules
-   Business Rules
-   OCR Metadata

Example:

``` yaml
Policy Number:
    bbox:
    datatype:
    regex:
    required:

PAN:
    bbox:
    datatype:
    regex:
```

------------------------------------------------------------------------

# Module 4 --- ROI Extraction

For known templates:

-   Load bounding boxes
-   Crop every ROI
-   Pass ROIs individually to OCR

No layout detection required.

------------------------------------------------------------------------

# Module 5 --- OCR Ensemble

Each ROI is processed independently by multiple OCR engines.

Example:

``` text
ROI

↓

Tesseract

↓

TrOCR

↓

PaddleOCR
```

Outputs are collected for later reasoning.

------------------------------------------------------------------------

# Module 6 --- Decision Engine (Core Innovation)

The Decision Engine becomes the heart of the system.

### Inputs

-   OCR outputs
-   OCR confidences
-   Validation rules
-   Business rules

### Responsibilities

-   Trust OCR
-   Use local VLM for arbitration
-   Ask the human

------------------------------------------------------------------------

## Decision Flow

### Step 1 --- OCR Consensus

Compare outputs from multiple OCR engines.

    OCR A
    AISPK6125E

    OCR B
    AISPK6125E

    OCR C
    AISPK6125E

Consensus achieved.

------------------------------------------------------------------------

### Step 2 --- Validation

Perform:

-   Regex validation
-   Datatype validation
-   Length validation
-   Required field validation
-   Business logic validation

Examples:

-   PAN format
-   Date validity
-   Numeric ranges
-   Policy number format

------------------------------------------------------------------------

### Step 3 --- Local VLM Arbitration

If OCR engines disagree or confidence is moderate:

Pass only the cropped ROI to the locally hosted VLM.

The VLM acts as an **arbitration engine**, not as the primary OCR
engine.

------------------------------------------------------------------------

### Step 4 --- Human Review

Only unresolved fields are shown to the user.

Example:

    Policy Number

    [ Cropped Image ]

    Prediction:
    35006917

    Confidence:
    63%

    Please verify.

------------------------------------------------------------------------

# Output

Final output:

``` json
{
  "Policy Number": "...",
  "PAN": "...",
  "Loan Amount": "...",
  "Date": "..."
}
```

Metadata example:

``` json
{
  "confidence": 0.97,
  "source": "OCR",
  "validated": true
}
```

or

``` json
{
  "confidence": 0.61,
  "source": "Human"
}
```

------------------------------------------------------------------------

# Privacy Constraints (Locked)

## Allowed

-   Local OCR models
-   Local VLM
-   Local processing
-   Human verification

## Not Allowed

-   Azure Document Intelligence
-   Google Document AI
-   AWS Textract
-   Any cloud OCR service

Reason:

Customer documents are confidential and must never leave the local
environment.

------------------------------------------------------------------------

# Human-in-the-Loop Philosophy

The objective is **not** perfect OCR.

The objective is:

-   Automatically extract high-confidence fields.
-   Ask the user only for uncertain fields.

Example:

    10 fields

    ↓

    7 extracted automatically

    ↓

    3 verified manually

This is considered a successful outcome.

------------------------------------------------------------------------

# Future Roadmap (Not Part of v1)

## v2

Integrate DocStruct.

Use layout-aware understanding to improve:

-   Template creation
-   ROI generation
-   Semantic structure

------------------------------------------------------------------------

## v3

Structure-aware RAG

    Document

    ↓

    DocStruct

    ↓

    Extraction

    ↓

    Knowledge Graph

    ↓

    Retriever

    ↓

    LLM

This becomes the long-term **Document Intelligence Platform**.

------------------------------------------------------------------------

# Locked Design Decisions

-   Privacy-first architecture (fully offline)
-   Human-in-the-loop workflow
-   Local VLM instead of cloud services
-   Template caching for known documents
-   OCR ensemble instead of a single OCR engine
-   Decision Engine as the central orchestration layer
-   Unknown templates are learned once and cached
-   Only uncertain fields require human intervention
-   JSON is the canonical output format

------------------------------------------------------------------------

# Immediate Development Plan

## Phase 1 --- Build the Extraction Engine

1.  Design the architecture (one module at a time).
2.  Build the template system.
3.  Implement template classification.
4.  Implement template creation.
5.  Implement ROI extraction.
6.  Integrate multiple OCR engines.
7.  Build the Decision Engine.
8.  Implement the Human Review UI.
9.  Produce structured JSON output.

Everything else (DocStruct integration, RAG, and the larger document
intelligence platform) is intentionally deferred until this foundation
is complete.
