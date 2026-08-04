import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "node_modules", "dist", "backups", "artifacts"}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".json", ".yml", ".yaml", ".md", ".sql", ".ps1", ".ttl", ".rq"}
PATTERNS = {
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "OpenAI key": re.compile(r"sk-[A-Za-z0-9]{20,}"),
}


def scan(root: Path = ROOT) -> list[str]:
    findings = []
    for directory, directories, files in root.walk():
        directories[:] = [name for name in directories if name not in EXCLUDED]
        for name in files:
            path = directory / name
            if name == ".env" or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for label, pattern in PATTERNS.items():
                if pattern.search(text):
                    findings.append(f"{label}: {path.relative_to(root)}")
    return findings


if __name__ == "__main__":
    results = scan()
    if results:
        raise SystemExit("Critical secret patterns found:\n" + "\n".join(results))
    print("Security scan passed: no critical secret patterns found.")
