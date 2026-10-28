# Security Policy (`SyrisBruhh42` Public Portfolio)

---

## 1. Public-Repository Safety & Zero-Trust Hygiene

All public repositories under `SyrisBruhh42` enforce strict Zero-Trust public release guardrails:

1. **Zero Secrets & Credentials**: No API keys, tokens, private keys, `.env` files, or authentication material are permitted in working trees or commit history.
2. **Zero Local Workstation / Network Metadata**: No local host paths, private RFC1918/mesh IP addresses, or internal infrastructure identifiers are published to public repositories.
3. **Zero Binary State Bloat**: Runtime databases (`.db`, `.sqlite3`, `-wal`, `-shm`) and local session artifacts are excluded from version control.

---

## 2. Reporting a Vulnerability

If you discover a security issue or unintended sensitive data exposure in any public `SyrisBruhh42` repository, please report it via GitHub's **Private Vulnerability Reporting** feature on the affected repository rather than opening a public issue containing exploit details.
