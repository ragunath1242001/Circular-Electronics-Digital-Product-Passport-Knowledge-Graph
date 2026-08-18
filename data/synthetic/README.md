# Synthetic DPP ecosystem

`scenario.json` defines the reproducible 10,000-document MVP scenario. Generate it
from the repository root:

```powershell
backend/.venv/Scripts/python scripts/generate_synthetic.py
```

The ignored `generated/` directory contains:

- `documents.jsonl`: metadata envelopes with embedded JSON-LD DPP documents;
- `ground-truth.jsonl`: injected faults and their expected detectors;
- `organisations.json`: fictional organisation identities and archetypes;
- `summary.json`: counts and SHA-256 hashes for reproducibility.

Ground truth is deliberately separate from detector input. All organisations and
products are fictional.
