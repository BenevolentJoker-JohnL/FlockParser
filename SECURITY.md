# Security Policy

## Supported Versions

We currently support the following versions with security updates:

| Version | Supported          | Notes |
| ------- | ------------------ | ----- |
| 1.0.x   | :white_check_mark: | Current release |
| < 1.0   | :x:                | Pre-release versions (not supported) |

---

## Known Security Considerations

FlockParser is designed for **privacy-first, local processing**. However, there are important security considerations depending on which interface you use.

### Privacy Levels by Interface

| Interface | Data Location | Security Level |
|-----------|---------------|----------------|
| **CLI** | 100% Local | 🟢 **Highest** - No external network calls |
| **Web UI** | 100% Local | 🟢 **High** - Localhost only by default |
| **REST API** | Local Network | 🟡 **Medium** - Requires API key authentication |
| **MCP Server** | Cloud (Anthropic) | 🔴 **Lower** - Document snippets sent to Claude API |

### Current Security Limitations

**See [KNOWN_ISSUES.md](KNOWN_ISSUES.md#security-concerns) for detailed security limitations, including:**

1. **REST API:**
   - No rate limiting (DoS risk)
   - No user management or RBAC
   - Default API key must be changed

2. **Data at Rest:**
   - No encryption of ChromaDB databases
   - No encryption of processed files
   - Relies on filesystem permissions

3. **Network Security:**
   - Ollama nodes communicate over plain HTTP
   - No TLS by default
   - No mutual authentication between nodes

4. **Input Validation:**
   - Limited validation of uploaded PDFs
   - No file size limits enforced by default
   - No malware scanning

---

## Reporting a Vulnerability

**We take security seriously.** If you discover a security vulnerability, please follow responsible disclosure:

### 🔒 For Security Issues (Private Reporting)

**DO NOT open a public GitHub issue for security vulnerabilities.**

Instead:

1. **Email:** benevolentjoker@gmail.com
2. **Subject:** `[SECURITY] FlockParser Vulnerability`
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

### Response Timeline

- **Initial response:** Within 48 hours
- **Severity assessment:** Within 1 week
- **Fix timeline:** Depends on severity
  - **Critical:** Hotfix within 1 week
  - **High:** Patch in next minor release (~2-4 weeks)
  - **Medium/Low:** Addressed in next planned release

### Disclosure Policy

- We will work with you to understand and validate the issue
- We will develop a fix and test it thoroughly
- We will credit you in the security advisory (unless you prefer to remain anonymous)
- We will publish a security advisory on GitHub after the fix is released

---

## Security Best Practices

### For Users

#### REST API Deployment

**Always change the default API key:**

```bash
# Generate a strong random key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set it in environment
export FLOCKPARSE_API_KEY="your-strong-random-key-here"
```

**Use HTTPS in production:**

```nginx
# nginx reverse proxy example
server {
    listen 443 ssl;
    server_name flockparse.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Rate limiting
    limit_req zone=api_limit burst=20 nodelay;
}

limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
```

**Restrict network access:**

```bash
# Firewall - only allow specific IPs
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Or bind to specific interface
uvicorn flock_ai_api:app --host 192.168.1.10 --port 8000
```

---

#### MCP Server Usage

**⚠️ Privacy Warning:** The MCP server sends document snippets to Anthropic's cloud API.

**Recommendations:**
- Only use with non-sensitive documents
- Review Anthropic's privacy policy: https://www.anthropic.com/privacy
- Use CLI/Web UI for confidential documents
- Consider using local-only interfaces for:
  - Healthcare records (HIPAA)
  - Legal documents (attorney-client privilege)
  - Financial data
  - Personal information

---

#### Data Protection

**Encrypt at rest:**

```bash
# Use encrypted filesystem
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup luksOpen /dev/sdX flockparse_data
sudo mkfs.ext4 /dev/mapper/flockparse_data
sudo mount /dev/mapper/flockparse_data /mnt/flockparse

# Or use encrypted home directory (Ubuntu)
ecryptfs-setup-private
```

**Set restrictive permissions:**

```bash
# Protect databases
chmod 700 chroma_db_cli/
chmod 700 uploads/
chmod 700 converted_files/

# Protect configuration
chmod 600 .env
chmod 600 ~/.pypirc  # If you have one
```

**Regular backups:**

```bash
# Backup with encryption
tar -czf - chroma_db_cli/ | gpg -c > backup_$(date +%Y%m%d).tar.gz.gpg
```

---

#### Node Communication Security

**Use VPN for distributed nodes:**

```bash
# Option 1: WireGuard
# Install: sudo apt install wireguard
# Configure VPN between nodes

# Option 2: Tailscale (easier)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# Then use Tailscale IPs in node configuration
NODES = [
    {"url": "http://100.64.1.2:11434"},  # Tailscale IP
]
```

**Or use SSH tunnels:**

```bash
# Forward remote Ollama to local port
ssh -L 11435:localhost:11434 user@remote-node -N -f

# Then configure FlockParser to use localhost:11435
```

---

### For Developers

**Input validation:**

```python
# Validate file uploads
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB

if len(file_content) > MAX_FILE_SIZE:
    raise ValueError("File too large")

# Validate file type
import magic
mime = magic.from_buffer(file_content, mime=True)
if mime != 'application/pdf':
    raise ValueError("Not a valid PDF")
```

**Sanitize user inputs:**

```python
# Never trust user input
import bleach

query = bleach.clean(user_query)
```

**Use secrets management:**

```python
# Don't hardcode secrets
import os
from pathlib import Path

# Read from environment or file
API_KEY = os.getenv("FLOCKPARSE_API_KEY")
if not API_KEY:
    key_file = Path.home() / ".flockparse" / "api_key"
    if key_file.exists():
        API_KEY = key_file.read_text().strip()
```

**Audit logging:**

```python
import logging

# Log all API access
logger.info(f"API access: {request.client.host} - {request.url.path}")
```

---

## Security Roadmap

### v1.1.0 (Planned)

- [ ] Add rate limiting to REST API
- [ ] Add audit logging
- [ ] File size validation
- [ ] Better input sanitization

### v1.2.0 (Planned)

- [ ] TLS documentation for Ollama nodes
- [ ] MCP authentication
- [ ] Security scanning in CI (Bandit, safety)

### v1.3.0 (Planned)

- [ ] Application-level encryption for ChromaDB
- [ ] User management and RBAC for REST API
- [ ] Secrets management integration (Vault, AWS Secrets Manager)

### v2.0.0 (Planned)

- [ ] Full compliance framework (GDPR, HIPAA, SOC 2)
- [ ] Penetration testing results
- [ ] Security certifications

---

## Compliance Considerations

### GDPR (EU Data Protection)

**Current status:** Not certified

**Considerations:**
- FlockParser processes documents locally (good for GDPR)
- But: MCP server sends data to US-based Anthropic (may violate GDPR)
- No built-in data deletion mechanisms yet
- No consent management

**Recommendation:**
- Use CLI/Web UI only for GDPR-regulated data
- Avoid MCP server for EU citizen data
- Implement data retention policies manually

---

### HIPAA (Healthcare Data)

**Current status:** Not certified

**Considerations:**
- No Business Associate Agreement (BAA) available
- No encryption at rest by default
- No audit logging
- No access controls beyond API keys

**Recommendation:**
- Do not use for Protected Health Information (PHI)
- Or use only with filesystem encryption + strong access controls
- Wait for v2.0.0 with full compliance features

---

### SOC 2 (Security & Availability)

**Current status:** Not audited

**Recommendation:** Not suitable for SOC 2 compliance yet.

---

## License

Security issues are covered under the same [MIT License](LICENSE) as the main project.

---

## Credits

Security researchers who responsibly disclose vulnerabilities will be credited here:

- *No vulnerabilities reported yet*

---

## Questions?

For non-security questions, use:
- GitHub Discussions: https://github.com/B-A-M-N/FlockParser/discussions
- GitHub Issues: https://github.com/B-A-M-N/FlockParser/issues

For security-sensitive questions, email: benevolentjoker@gmail.com
