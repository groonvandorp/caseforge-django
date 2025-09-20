# Security Documentation

This document outlines the security measures implemented in the CaseForge application.

## 🔒 Frontend Security

### Vulnerability Management

**Fixed CVEs (2025-09-20):**
- **nth-check** `<2.0.1` → `>=2.0.1` (High severity)
- **axios** `<1.12.0` → `1.12.2` (High severity)
- **postcss** `<8.4.31` → `>=8.4.31` (Moderate severity)
- **webpack-dev-server** `<=5.2.0` → `>=5.2.1` (Moderate severity)
- **cross-spawn** `7.0.3` → `>=7.0.5` (High severity)

### Security Overrides

The following security overrides are configured in `frontend/package.json`:

```json
"overrides": {
  "nth-check": ">=2.0.1",
  "postcss": ">=8.4.31",
  "webpack-dev-server": ">=5.2.1",
  "cross-spawn": ">=7.0.5"
}
```

These overrides force secure versions of transitive dependencies even when parent packages haven't updated their requirements.

### Docker Security

**Multi-stage build process:**
- Build stage: Includes all dependencies and security audit
- Production stage: Only runtime dependencies, non-root user

**Security features:**
- Non-root user (`react:nodejs`) for runtime
- Minimal production image (no dev dependencies)
- Security audit during build process
- Latest Alpine base image

### Security Validation

**Automated security checking:**
```bash
# Run security validation
./deployment/scripts/security-check.sh
```

This script:
- ✅ Checks for high-severity vulnerabilities
- ✅ Validates security overrides are in place
- ✅ Tests build process
- ✅ Fails CI/CD on security issues

## 🛡️ Container Security

### Dockerfile Best Practices

1. **Multi-stage builds** - Separate build and runtime stages
2. **Non-root user** - Application runs as `react` user (UID 1001)
3. **Minimal attack surface** - Only production files in final image
4. **Security scanning** - `npm audit` during build
5. **Latest base images** - Regular updates to Node.js Alpine

### Build Process

```dockerfile
# Stage 1: Build with security audit
RUN npm audit --audit-level=high
RUN npm run build

# Stage 2: Production with non-root user
USER react
CMD ["serve", "-s", "build", "-l", "3000"]
```

## 🔍 Security Monitoring

### CI/CD Integration

Add to your pipeline:

```yaml
# Example GitHub Actions
- name: Security Check
  run: ./deployment/scripts/security-check.sh

# Example GitLab CI
security_check:
  script:
    - ./deployment/scripts/security-check.sh
```

### Regular Maintenance

**Weekly:**
- Run `npm audit` to check for new vulnerabilities
- Update dependencies with `npm update`

**Monthly:**
- Review and update security overrides
- Scan Docker images with security tools
- Update base images in Dockerfiles

**When new CVEs are reported:**
- Update affected packages immediately
- Add overrides if package maintainers are slow to update
- Re-run security validation

## 🚨 Incident Response

**If container scan finds vulnerabilities:**

1. **Identify the package:** Check which package has the CVE
2. **Check if already fixed:** Run `npm audit` locally
3. **Apply fix:**
   - Update package: `npm update package-name`
   - Add override: Update `package.json` overrides section
   - Force version: `npm install package-name@safe-version`
4. **Validate fix:** Run `./deployment/scripts/security-check.sh`
5. **Rebuild containers:** `docker build` with updated dependencies
6. **Re-scan:** Verify the CVE is resolved

## 📋 Security Checklist

**Before deployment:**
- [ ] Run `npm audit --audit-level=high`
- [ ] Execute `./deployment/scripts/security-check.sh`
- [ ] Build Docker image successfully
- [ ] Scan container image for vulnerabilities
- [ ] Verify non-root user in container
- [ ] Check all overrides are current

**Regular maintenance:**
- [ ] Weekly dependency updates
- [ ] Monthly security review
- [ ] Quarterly base image updates
- [ ] Annual security architecture review

## 🔗 References

- [npm audit documentation](https://docs.npmjs.com/cli/v8/commands/npm-audit)
- [Docker security best practices](https://docs.docker.com/develop/security-best-practices/)
- [Node.js security checklist](https://blog.risingstack.com/node-js-security-checklist/)
- [CVE Database](https://cve.mitre.org/)

---

**Last updated:** 2025-09-20
**Next review:** 2025-10-20