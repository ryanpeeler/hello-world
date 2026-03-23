I need your approval to create the commit. Here's what I plan to do:

**Commit message:**
```
Add researchclaw pipeline and test suite

Introduces the full researchclaw package (CLI, pipeline stages, LLM adapters,
literature collection, experiment sandbox, LaTeX export, quality checks) along
with a corresponding test suite covering config, evolution, hardware, prompts,
quality, stages, and LaTeX export.
```

**Staged files:** 57 new files under `researchclaw/` and `tests/`  
**Not included:** `artifacts/`, `config.carbon-nanotubes.yaml`, and `__pycache__` dirs (untracked, likely runtime outputs)

Should I proceed with this commit and then push to the remote branch?