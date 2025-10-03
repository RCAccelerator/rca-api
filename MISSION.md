# RCAv2: Scope and Mission Statement

## RCAv2 Mission Statement
RCAv2 empowers engineers to quickly debug and diagnose CI failures. By leveraging a third-party LLM (e.g., Gemini) and building an interface into **EoDWeb**, **Zuul**, and a **Slack bot (eodbot)**, we'll deliver actionable insights and intelligent automation—reducing friction and boosting developer productivity.

---

## Executive Summary

**The Problem:**  
Our engineers currently spend significant time manually diagnosing CI failures, leading to hundreds of lost engineering hours each month. This inefficiency slows down development cycles and delays delivery.

**The Vision:**  
RCAv2 is designed to deliver fast and accurate root cause analysis of build failures, minimizing developer toil and accelerating software delivery.

---

## Impact (Success Metrics)

- **Faster diagnosis** – Reduce the average time required to identify a root cause by *10%*.  
  - Method: Questionnaire for CI ops engineers  

- **Improved accuracy** – Automatically diagnose build failures with high reliability.  
  - Method: Questionnaire comparing usage between v1 and v2, showing at least a *10% increase in usage*

---

## Project Scope: RCAv2 for RHOSO 18

The RCAv2 project aims to deliver a streamlined way for developers and CI stakeholders to identify and understand the root cause of build failures in **RHOSO 18 tox, component, and integration jobs**.  
The solution will be integrated into existing workflows via **EoDWeb**, **Zuul**, and **Slack (through eodbot)**, all backed by a **Large Language Model (LLM).**

### Inputs & Processing
- **Input:** A Zuul build URL (downstream only)  
- **Processing:** Logs are ingested by **Log Juicer** and passed to the LLM  
- **Output:** A concise, actionable Root Cause Analysis (RCA) build report  

---

## RCA Build Report Features

- Clearly identifies the root cause of the failure (e.g., pinpointing the culprit in build artifacts).  
- Includes links to relevant context from integrated data sources (e.g., Jira issues, Slack discussions).  
- **Optional:** A chat interface (e.g., via Streamlit) to allow further queries, with potential for session persistence.  
- User feedback mechanism (thumbs-up/down) to help evaluate report usefulness—focused on manual assessment, not model training.  
- **Optional:** Suggests which team the issue should be assigned to.  

---

## Integration Points

- **EoDWeb UI:** A link in job status pages to request an RCA for failed jobs.  
- **Zuul Web UI:** Direct links to perform RCA on build artifacts.  
- **Slack (eodbot):** Slash commands to trigger RCA requests and share results within channels, increasing visibility and adoption.  

---

## Scope Limitations

- **Out of scope:** Training LLM (e.g., Gemini) models; only pre-trained models will be considered.  
- The team will evaluate which services and data sources the LLM can leverage (e.g., Jira, Slack, CI framework, Confluence, public documentation), but not all may be included (due to licensing or security limitations).  
- Access to end users will be **gated**—features will only be broadly exposed when stable, with **SSO-enabled selective rollout** to trusted testers first (to avoid poor first impressions).  

---

## Deliverables

By the conclusion of RCAv2, the project will produce:  

- A working RCA system integrated into **EoDWeb**, **Zuul**, and **Slack**  
- Documentation of models tested and their relative performance  
- An evaluation of supporting tools and frameworks used for context collection  
