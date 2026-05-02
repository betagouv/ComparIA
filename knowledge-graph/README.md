# Knowledge Graph

Structured postmortems and debugging memory for the CompaRAG project.

Each file is a self-contained "graph" of entities (project, bugs, root causes,
fixes, learnings) and the relations between them. The format is designed to be:

- **Human-readable**: YAML, with descriptive comments.
- **Machine-ingestible**: convertible to mem0 graph memory with a few lines of
  Python (see ingestion stub below).
- **Versioned**: each file is dated and pinned to the commits/PRs that fixed
  things — so the graph stays a reliable source of truth even years later.

## File naming

`YYYY-MM-DD-short-topic-slug.yaml`

Examples:
- `2026-05-02-clarifeye-debug.yaml`
- `2026-05-15-rag-quality-experiment.yaml`

## Schema

```yaml
session:
  date: YYYY-MM-DD
  topic: short title
  branch: git branch where work happened
  prs: [list of PR numbers on the repo]

entities:
  - id: unique_snake_case_id
    type: Project | MCPServer | Bug | RootCause | Fix | Learning
    name: human-readable name
    metadata: free-form dict

relations:
  - {from: entity_id, rel: VERB_PHRASE, to: entity_id}

learnings:
  - short imperative sentence (propagable to future sessions)
```

## Ingesting into mem0 (sketch)

```python
import yaml
from mem0 import Memory

m = Memory()
graph = yaml.safe_load(open("knowledge-graph/2026-05-02-clarifeye-debug.yaml"))

for ent in graph["entities"]:
    m.add(
        messages=[{"role": "system", "content": f"{ent['type']}: {ent['name']}"}],
        user_id="comparag",
        metadata={**ent.get("metadata", {}), "entity_id": ent["id"]},
    )

for rel in graph["relations"]:
    m.add(
        messages=[{"role": "system", "content": f"{rel['from']} {rel['rel']} {rel['to']}"}],
        user_id="comparag",
    )
```
