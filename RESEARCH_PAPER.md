# ACADEMIC RESEARCH PROPOSAL & PAPER MATERIALS

**Title:** Privacy-Aware Agentic AI for Retrieval-Augmented Question Answering and Verified Modification of Multi-Format Documents  
**Domain:** Artificial Intelligence, Software Engineering, Applied Cryptography, Multi-Agent Systems  

---

## 1. Research Problem Statement
Commercial LLMs and Retrieval-Augmented Generation (RAG) applications typically require uploading sensitive business and personal documents to third-party cloud vectors and databases. Furthermore, while LLMs excel at conversational question answering, they frequently hallucinate or generate unsafe, destructive code when tasked with editing structured documents like spreadsheets, contracts, and legal PDFs. 

There is an acute research gap for a **privacy-first, unified agentic architecture** that can:
1. Guarantee zero plaintext persistence on cloud storage.
2. Maintain provenance across heterogeneous document formats (TXT, XLSX, PDF).
3. Safely execute natural-language document modifications using deterministic, validated tools rather than arbitrary code execution.
4. Provide transactional rollback and an encrypted audit trail.

---

## 2. Research Objectives
1. **Design a Local Privacy Architecture**: Construct an envelope encryption framework combining Argon2id key derivation and AES-256-GCM authenticated encryption, paired with an ephemeral in-memory vector database.
2. **Develop a Multi-Format Unified RAG Pipeline**: Build a context-preserving ingestion engine for unstructured text, tabular Excel data (sheets, rows, cells, formulas), and structured PDFs.
3. **Implement an Agentic Workflow via LangGraph**: Design a multi-node state graph with high-precision intent classification (`QUESTION`, `MODIFICATION`, `CLARIFICATION`, `UNSUPPORTED_OPERATION`).
4. **Formulate a Transactional Document Versioning Protocol**: Ensure modifications follow an ACID-like transactional model (temporary working copy $\to$ execution $\to$ integrity validation $\to$ commit $\to$ rollback capability).

---

## 3. Methodology & System Architecture

```
User Natural Language Request
             │
             ▼
┌───────────────────────────┐
│ Intent Classifier Router  │ (LangGraph Node)
└────────────┬──────────────┘
             │
   ┌─────────┴─────────┐
   ▼                   ▼
[QUESTION]       [MODIFICATION]
   │                   │
   │                   ▼
   │     ┌───────────────────────────┐
   │     │ Structured Plan Generator │
   │     └─────────────┬─────────────┘
   │                   │
   │                   ▼
   │     ┌───────────────────────────┐
   │     │ Approval Check (Dual Mode)│
   │     └─────────────┬─────────────┘
   │                   │
   │                   ▼
   │     ┌───────────────────────────┐
   │     │ Deterministic Tool Exec   │
   │     └─────────────┬─────────────┘
   │                   │
   │                   ▼
   │     ┌───────────────────────────┐
   │     │ Post-Validation & Checksum│
   │     └─────────────┬─────────────┘
   │                   │
   │                   ▼
   │     ┌───────────────────────────┐
   │     │ Commit Version & Re-Index │
   │     └───────────────────────────┘
   │
   ▼
┌───────────────────────────┐
│ Ephemeral ChromaDB Search │ (In-Memory Only)
└────────────┬──────────────┘
             │
             ▼
┌───────────────────────────┐
│ Grounded LLM Synthesis    │ (With Source Citations)
└───────────────────────────┘
```

---

## 4. Key Novelties & Contributions
- **Zero-Cloud Plaintext Persistence**: Data is either encrypted with AES-256-GCM locally or stored ephemerally in RAM.
- **Audited Tool Dispatcher**: Natural language edits are translated into structured parameters passed to verified Python processors (`openpyxl`, `fitz`) rather than executing raw LLM code.
- **Unified Citation System**: Citations identify worksheet names, rows, and cell coordinates for Excel, page numbers for PDF, and line ranges for TXT.
- **Rollback Guarantee**: Previous document states are preserved as immutable encrypted snapshots.

---

## 5. Experimental Evaluation Plan
1. **Retrieval Precision & Recall**: Evaluate top-4 retrieval accuracy on heterogeneous multi-format queries using synthetic ground truth documents.
2. **Intent Classification F1-Score**: Benchmark the router across 100 test queries spanning questions, modifications, ambiguous instructions, and malicious system commands.
3. **Modification Integrity Rate**: Measure the success rate of Excel formula updates, duplicate removals, and PDF page extractions against file corruption metrics.
4. **Encryption Overhead**: Measure throughput (MB/sec) for Argon2id key derivation and AES-256-GCM encryption across varying file sizes (10KB to 25MB).

