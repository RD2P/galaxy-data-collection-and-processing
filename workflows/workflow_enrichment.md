# Workflow enrichment notes

Short version
-------------
Make `workflows_structured.jsonl` more useful for embeddings and search by adding LLM-generated semantic fields and cleaned metadata. Do this streaming and resumable so it is safe to run on large files.

Files
-----
- Input: `workflows_structured.jsonl` (one JSON object per line with `id` and `text`)
- Output: `workflows_enriched.jsonl` (one JSON object per line with original fields plus enrichment)

What to add
-----------
- `enriched_summary`: 1–3 sentence plain-language summary
- `normalized_inputs`: list of {name, type, description}
- `normalized_outputs`: list of {name, type, description}
- `key_steps`: list of {id, short_description}
- `tags`: up to 5 inferred topics
- `confidence`: simple score or label
- `metadata`: timestamp, model, prompt_version

How to run it
--------------
- Stream the input file line-by-line to keep memory usage low
- Skip IDs already present in `workflows_enriched.jsonl` so the job is resumable
- Batch API calls where possible to improve throughput and reduce cost
- Retry transient errors with exponential backoff

Pilot and checks
----------------
- Run a small pilot of ~100 items
- Quick checks
	- JSON parses
	- Required fields present
	- `enriched_summary` is present and within expected length
	- `tags` are reasonable
- Human-review a 1% sample and adjust prompts

Embedding step
--------------
- Generate embeddings in a separate pass using `enriched_summary` or concatenated canonical fields

Resume behavior
---------------
- Write enriched lines as they complete and skip existing IDs on restart

Tiny sketch
----------
```python
for rec in read_jsonl('workflows_structured.jsonl'):
    if id_in_output(rec['id']):
        continue
    enriched = call_llm(rec['text'])
    write_jsonl('workflows_enriched.jsonl', {**rec, **enriched})
```


