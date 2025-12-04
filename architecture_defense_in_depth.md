# De-identification Pipeline: "Defense-in-Depth" Architecture

## Executive Summary
This document outlines the proposed multi-layered privacy architecture for the automated de-identification of medical media. By moving beyond simple biometric redaction to a comprehensive, AI-driven content analysis model, this pipeline ensures robust compliance with HIPAA Safe Harbor standards and minimizes the risk of inadvertent PHI (Protected Health Information) leakage.

## The "Defense-in-Depth" Strategy

We propose a three-layer protection model. Each layer acts as a safety net for the others, ensuring that if one detection method fails, another catches the sensitive data.

### Layer 1: Biometric & Audio Redaction (The "Blunt Force" Layer)
*Objective:* Remove obvious biological identifiers and direct identifiers from the media.
*   **Visual:** Automated Face Blurring (OpenCV/Azure Face API).
    *   *Action:* Detects and blurs all human faces frame-by-frame.
*   **Audio:** Speech-to-Text Transcription (Azure Speech Services).
    *   *Action:* Converts all spoken audio to text for downstream analysis.
*   **Text:** Entity Extraction (Azure AI Language: Health).
    *   *Action:* Detects and redacts names, dates, and locations from the transcript.

### Layer 2: Visual Data Leakage Protection (The "Context" Layer)
*Objective:* Catch non-biological PHI that appears visually on screen (e.g., slides, X-rays, whiteboards).
*   **Technology:** Azure AI Video Indexer (OCR & Object Detection).
*   **Mechanism:**
    *   **Optical Character Recognition (OCR):** Scans every frame for embedded text.
    *   **Risk Detection:** Flags patterns matching MRNs (Medical Record Numbers), DOBs (Date of Birth), or patient names appearing on presentation slides or medical imaging.
    *   *Action:* If a slide contains "Patient: John Doe" or "MRN: 12345", that specific time range is flagged for aggressive blurring or removal.

### Layer 3: Semantic & Speaker Verification (The "Logic" Layer)
*Objective:* Identify subtle, context-dependent privacy risks.
*   **Technology:** Large Language Models (LLMs) & Speaker Diarization.
*   **Mechanism:**
    *   **Speaker Identification:** Verifies that only authorized presenters are speaking. Segments with unauthorized voices (e.g., a patient's voice in a clip) can be automatically muted.
    *   **Quasi-Identifier Detection (LLM):** Analyzes the transcript for combinations of data that are not PHI individually but are identifying together (e.g., "A 45-year-old plumber from [Small Town] with [Rare Disease]").
    *   *Action:* The LLM suggests "generalization" (e.g., changing "Small Town" to "the region") to preserve anonymity.

---

## Technical Workflow (Proposed)

1.  **Ingest:** Video is uploaded to Azure Blob Storage.
2.  **Parallel Processing:**
    *   *Track A (Visual):* Azure Video Indexer performs OCR and Face Detection.
    *   *Track B (Audio):* Azure Speech Services generates a verbatim transcript.
3.  **De-identification Engine:**
    *   Azure Health De-identification Service scans Track B (Transcript) for textual PHI.
    *   Custom Regex Logic scans Track A (OCR) for visual PHI patterns.
4.  **Redaction Application:**
    *   FFmpeg applies Gaussian blur to faces (Track A) and sensitive slide regions (Track A).
    *   Audio is muted or "beeped" at timestamps corresponding to redacted transcript text.
5.  **Output:** A fully sanitized media file + A "Compliance Report" JSON detailing what was removed and why.

## Value Proposition for Compliance
*   ** redundancy:** We do not rely on a single model. Text-on-screen is caught even if not spoken; spoken names are caught even if not shown.
*   **Auditability:** The pipeline generates a machine-readable audit trail of every redaction event.
*   **Scalability:** Leveraging Azure AI Services (Batch) allows processing hundreds of hours of content weekly without manual intervention.

