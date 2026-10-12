# Sanad (سَنَد)


**Check your file before you share it.**
A local-first compliance assistant for Saudi Arabia's Personal Data Protection Law (PDPL). Sanad finds personal data in an organization's files, classifies it by the law's definitions, and tells you what the law requires — all running on the organization's own machine.



---

## The problem

An employee is about to send a payroll sheet, a contract, or a complaint to another organization — and the file contains national ID numbers, IBANs, and phone numbers that have no reason to be there. Meanwhile, shared drives hold forgotten exports and old backups with data on thousands of people that nobody knows about.

The PDPL and its Implementing Regulation require organizations to collect only the minimum necessary data, to protect it, and to destroy it once its purpose ends. But you can't protect data you don't know you have.

## What Sanad does

| | |
|---|---|
| **Detects** | National/Iqama IDs, passports, IBANs, phone numbers, emails, addresses, names, dates of birth, health data, religious belief, and credit data — even when column names are meaningless |
| **Classifies** | Each finding by the PDPL's Article 1 definitions (personal / sensitive / credit data), with a risk level and a confidence level |
| **Advises** | Required actions, each linked to the relevant article of the law or its regulations |
| **Answers** | Questions about the scanned files, grounded in the current text of the law (including the 2023 amendments) |
| **Monitors** | A shared folder every night, scanning only new or changed files and keeping a history of every run |
| **Suggests** | A practical action for each finding before the file is shared |
| **Reports** | A printable PDF report for management |


## Target user

**The Data Protection Officer (DPO).** Article 32 of the Implementing Regulation requires appointing one in several cases — including public entities providing services that involve large-scale processing of personal data. The DPO's duties include overseeing impact assessments and notifying the authority of data breaches. Sanad gives them the picture they need: where the personal data is, how risky it is, and what to do about it.

```

## Data engineering

- **Legal text preparation:** The law and its two regulations were collected from the official gazette (Umm Al-Qura). PDF extraction breaks Arabic ligatures, so the published text was used instead, with a cleaning script.
- **Merging amendments:** The original law (Royal Decree M/19) was merged with the amendments of Royal Decree M/148 into a single current text: 19 unchanged articles, 23 amended, and 1 repealed (Article 32), which is excluded from search. Every article is tagged with its status.
- **Retrieval (RAG):** One chunk per article, bge-m3 embeddings, ChromaDB, and a similarity threshold so the model doesn't answer when no relevant article exists. Sources are shown only if the answer actually cites them.
- **Incremental scanning:** Each file gets a content fingerprint (SHA-256). If size and modification time are unchanged, the file isn't even read; if the fingerprint is unchanged, it's skipped. Only new and changed files are scanned.
- **Star-schema warehouse (DuckDB):** Findings are linked to file *content*, not to a scan run, so every run stores a full snapshot without redoing work. Metrics, the timeline, and what-changed-since-last-scan are computed from it.
- **Scheduling (Prefect):** A daily run at 2 AM Riyadh time with retries. If the local model is down, the run stops instead of saving incomplete results.
- **Multiple formats:** All sheets in Excel files, plus tables and text in Word and PDF files — including a fix for reversed Arabic letters in PDF tables.

## Results

On a synthetic test set for a fictional government service entity ("Taysir Platform"), with known ground truth:

| Metric | Precision | Recall |
|---|---|---|
| Column detection (14 columns + 3 negative examples that look like IDs) | 100% | 100% |
| Fixed-format values in free text (123 values) | 100% | 100% |

**To be clear:** the test set is small and synthetic, and the types added later (passport, health, religion, credit) don't have published accuracy figures yet. Details in the [test data datasheet](docs/test_data_datasheet.md) (Arabic).

## Tech stack

Python · FastAPI · Ollama (Qwen2.5-3B, bge-m3) · ChromaDB · DuckDB · Prefect · PyMuPDF · python-docx · HTML/CSS/JavaScript

Runs on an ordinary laptop with 8 GB of RAM and no GPU.

## Privacy

- Files are scanned on the organization's own machine and never sent to a third party. Uploaded files are deleted after scanning.
- The language model runs locally through Ollama.
- All data in this repository and in the screenshots is synthetic.

## Current limitations

- Scanned (image-only) PDFs are not supported.
- The model is small (3B) and can make mistakes in its answers, so a person stays in the loop.
- Risk levels are Sanad's internal prioritization; the PDPL does not define risk levels.
- Sanad is an assistive tool, not legal advice.

## Roadmap

- An evaluation set for the new data types and for the assistant's answers.
- OCR for images and scanned documents.
- Direct connections to databases and cloud drives.
- Comparing ALLaM with Qwen on legal questions.

## About the code

This repository shows the web app, the data pipeline (incremental scanning, warehouse, and scheduling), and the retrieval layer over the law. **The personal data detector, the mapping from findings to legal articles, and the assistant's file-specific instructions are not published.** They are available for review on request. 


## Legal sources

- [Personal Data Protection Law (M/19)](https://www.uqn.gov.sa/details?p=18347) and [its amendments (M/148)](https://www.uqn.gov.sa/details?p=21670)
- [Implementing Regulation of the PDPL](https://www.uqn.gov.sa/details?p=23595)
- [Regulation on Personal Data Transfer outside the Kingdom](https://www.uqn.gov.sa/details?p=25412)
