### Institutional Memory (MVP)
Build an MVP Python project named Institutional Memory: a lightweight web-chatbot that answers operational / developer questions (natural or structured) using a knowledge base (KB) of technical documentation (for MVP, ingest any open-source docs such as JBoss guides / Markdown). Use Gemini API for generation and optionally support local Ollama models if present. Use only open-source or free components for everything else.

### Goals (what success looks like)
1. Ingest a set of technical docs (Markdown/HTML/text) into a searchable KB.
2. Provide a web chat UI where users type questions and get step-by-step answers grounded in KB content.
3. Use RAG (vector retrieval + Gemini generation) to ensure answers are sourced, not hallucinated.
4. Keep the system modular so model/db/ingest logic can be swapped later.
5. All code in Python. No paid services except Gemini.

### High-level approach (let the agent choose specifics)
 - Ingestion: Crawl / load local files (Markdown/HTML) → parse → chunk into passages → attach metadata (title, path, tags). Also we can go with a github repo (where we will give wikis like docs or files) to simulate something like of wikis where we can update and now the model will be having context about the updated changes and now will take that into memory. so for that we can do something like whenever we are running it will trigger the model to ingest the updates in the repo like any new pushes or commits and take that into context. Check that how we can do that thing since it would be very awesome 
 - Embeddings: Generate semantic vectors for chunks. Use an open/free approach (Chroma or FAISS for vector store). You may use Gemini embeddings if supported; otherwise use a local open-source embedder.
 - Vector DB: Chroma or FAISS recommended — simple, embeddable, free. Keep an abstraction so you can swap later.
 - Retrieval: At query time, embed query → similarity search → return top-K chunks with metadata.
 - Generation: Provide retrieved context to Gemini (prompt template: system instruction + context chunks + user query) to generate a concise, stepwise answer. Include the sources / snippet references in the final response.
 - Web UI: Minimal, fast to implement. Options: Streamlit (fast), Flask/FastAPI + simple HTML (flexible). Let the agent choose; emphasize a simple single-page chat view with answers and source listing.
 - Versioning & updates: Keep docs in a Git repo (or local folder). Provide an ingest command that re-indexes changed files. Optionally support webhooks later.
 - Logging & feedback: Log queries, chosen chunks, and final responses. Add a simple thumbs-up/down feedback UI to capture user rating and optional comment.

 
 ### Tradeoffs / choices to let the agent decide
 - Streamlit vs FastAPI+React: Streamlit is fastest for MVP; FastAPI gives API-first structure for later integrations.
 - Chroma vs FAISS: Chroma has built-in persistence and a nicer Python API; FAISS is lightweight and super fast. Let the agent pick.
 - Embeddings via Gemini vs local embedder: If Gemini supports embeddings in your account, use it for simplicity. Otherwise use sentence-transformers locally.
 - Prompting strategy: Keep prompt templates safe and concise. Agent should include an instruction to the LLM to cite the chunks used and avoid hallucination.

### Sample doc (put this in data/jboss_restart.md)
Use this sample so the agent has test data:
    ```markdown
    # Restarting JBoss - Example Runbook (v1)
    Steps V1:
    1. SSH to gateway01 VM
    2. Change user to test2
    3. As test2 run /etc/standalone.sh

    # Restarting JBoss - Updated (v2)
    Steps V2:
    1. SSH to gateway02 VM
    2. Change user to test3
    3. Clear /home/test3/*.log files
    4. Run /etc/jbossas/standalone.sh
    ```

Acceptance criteria (MVP)
1. python ingest.py reads data/ and builds a vector index (exit 0 on success).
2. python app.py launches a web UI where a user asks: “How do I restart JBoss?” → bot replies with step-by-step instructions and shows source: jboss_restart.md and which version chunk was used.
3. When the document is updated and ingest.py is run again, the bot returns the updated steps.
4. Basic logging of queries + chosen chunks to a local logfile.
5. A simple feedback control (thumbs up/down) that records user feedback.

### Testing & examples (what to test)
 - Query: “How do I restart JBoss?” → Expect v1 or v2 steps, with source.
 - Update jboss_restart.md (change VM name) → Run ingest.py → Query again → Expect updated VM name.
 - Structured query: Provide dropdown for service=JBoss + action=restart and see same answer.
 - also make a reset function or file kind of thing which can be used to reset the vector db and ingestions and start again


### Extra suggestions for the agent (future roadmap, Not much necessary for the current MVP Buildup so chill it, just gave context)
 - Add role-based access and per-doc permissions.
 - CI hook: re-index on doc changes (e.g., Git push or Confluence webhook).
 - Add analytics dashboard for popular queries and low-rated answers.
 - Integrate with JIRA, Slack, MS Teams (ChatOps) later.


### Deliverables (ask the agent to produce)
 - Full Python project with the files above.
 - README with setup & run steps (how to set GEMINI_API_KEY, how to run ingest.py, and app.py).
 - Minimal but with all essential and requirements, documented prompt template used when calling Gemini (so we can tune later).
 - Sample data/jboss_restart.md included.

### Tone for the agent
 - Be pragmatic: prioritize working end-to-end over bells & whistles.
 - Keep code readable and modular.
 - Prefer open-source libs, no paid services other than Gemini.