# OpenClaw Installation Guide

This guide documents the installation process for OpenClaw on a system with a dedicated system user.

## Prerequisites

- Node.js >= 22.12.0
- pnpm 10.23.0 or later
- System user (e.g., `openclaw`) with nologin shell
- Sufficient memory (8GB+ RAM recommended) or swap space configured

## 1. Configure Swap Space (if needed)

If your system has limited RAM (< 8GB free), configure swap to handle native module compilation:

```bash
# Check if swap exists
free -h

# If swap is 0, create a 4GB swapfile
sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make it permanent across reboots (Optional)
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Configure pnpm for Self-Contained Installation

Create or update `.npmrc` in the project directory to keep all pnpm files local:

```bash
cd /opt/openclaw

# Add to existing .npmrc or create new one
cat >> .npmrc << 'EOF'
store-dir=/opt/openclaw/.pnpm-store
cache-dir=/opt/openclaw/.pnpm-cache
EOF
```

This ensures:

- Package store stays in `/opt/openclaw/.pnpm-store`
- HTTP cache stays in `/opt/openclaw/.pnpm-cache`
- No dependencies on user home directories

## 3. Install Dependencies

Run the installation with limited concurrency to prevent memory issues:

```bash
cd /opt/openclaw
pnpm install --reporter=append-only --network-concurrency=1 --child-concurrency=1
```

**Note**: You may see an ACL permission error at the end (`EPERM: operation not permitted, chmod`). This is expected and doesn't affect functionality.

## 4. Build the Project

```bash
cd /opt/openclaw
sudo -u openclaw pnpm build
pnpm ui:build
```

**Important**: Run `pnpm build` as the `openclaw` service user, not as your admin
user. The bundler (rolldown) generates Node-version-specific output — building as a
user with a newer Node (e.g. Node 24 via nvm) produces output incompatible with the
Node 22 runtime. See `LOCAL-CHANGES.md` for details.

The `ui:build` step builds the Control UI - a web interface for managing the gateway. This is optional for CLI-only usage but recommended for service deployments.

## 5. Fix Ownership

If you installed as a different user than the service account, change ownership:

```bash
sudo chown -R openclaw:openclaw \
  /opt/openclaw/node_modules \
  /opt/openclaw/dist \
  /opt/openclaw/.pnpm-store \
  /opt/openclaw/.npmrc \
  /opt/openclaw/ui/node_modules
```

Add `.pnpm-cache` to the list if it exists.

**Note**: The `ui/node_modules` directory is created when building the Control UI.

## 6. Configure Permissions for Future Edits

To ensure that newly created or edited files maintain `openclaw:openclaw` ownership, configure the directory with appropriate ACLs and setgid bit:

```bash
# Set the setgid bit so new files inherit the group
sudo chmod g+s /opt/openclaw

# Configure default ACLs so new files are owned by openclaw user
sudo setfacl -d -m u::rwx /opt/openclaw
sudo setfacl -d -m g::rwx /opt/openclaw
sudo setfacl -d -m o::r-x /opt/openclaw

# If you have specific users who need access (e.g., 'ryer'), add them:
sudo setfacl -d -m u:ryer:rwx /opt/openclaw
sudo setfacl -m u:ryer:rwx /opt/openclaw
```

This configuration ensures:

- New files inherit the `openclaw` group (via setgid bit)
- Default ACLs control ownership and permissions for new files
- Authorized users can edit files while maintaining proper ownership

To verify the configuration:

```bash
getfacl /opt/openclaw
```

You should see `default:` entries showing the ACL rules for new files.

## 7. Configure System Service Paths (Recommended for Production)

For a proper FHS-compliant system service, configure openclaw to use standard Linux directories:

```bash
# Create FHS directories
sudo mkdir -p /etc/openclaw
sudo mkdir -p /var/lib/openclaw
sudo mkdir -p /var/log/openclaw

# Set ownership
sudo chown openclaw:openclaw /etc/openclaw
sudo chown openclaw:openclaw /var/lib/openclaw
sudo chown openclaw:openclaw /var/log/openclaw

# Create environment file for the service
sudo tee /etc/openclaw/openclaw.env << 'EOF'
# OpenClaw FHS paths
OPENCLAW_CONFIG_PATH=/etc/openclaw/openclaw.json
OPENCLAW_STATE_DIR=/var/lib/openclaw
HOME=/var/lib/openclaw
EOF
```

When running openclaw as a service, source this environment file:

```bash
# Example systemd service snippet
[Service]
EnvironmentFile=/etc/openclaw/openclaw.env
```

This ensures:

- **Config**: `/etc/openclaw/openclaw.json` (system configuration)
- **State/Data**: `/var/lib/openclaw/` (sessions, databases, state files)
- **Logs**: `/var/log/openclaw/` (application logs)
- **Application**: `/opt/openclaw/` (binaries and code, read-only)

## 8. Verify Installation

Test that the service user can run OpenClaw:

```bash
sudo -u openclaw bash -c 'cd /opt/openclaw && node openclaw.mjs --version'
```

You should see the version number (e.g., `2026.2.6-3`).

## 9. Troubleshooting

### Installation Hangs

**Symptom**: `pnpm install` freezes the system

**Causes**:

- Insufficient memory during native module compilation
- No swap space configured

**Solution**: Add swap space (see step 1) and use limited concurrency flags

### pnpm hangs when it Tries to Self-Update When Running as System User

**Symptom**: Endless loop of `pnpm add pnpm@...` when running as service user

**Cause**: pnpm tries to install itself for new users

**Solution**: Either:

- Install as a regular user and fix ownership (recommended)
- Or set `PNPM_HOME=/usr` environment variable when running as system user

### Permission Errors

**Symptom**: `EPERM: operation not permitted, chmod`

**Cause**: ACL restrictions on files

**Impact**: Only prevents binary symlink creation; doesn't affect functionality

**Solution**: Can be ignored, or fix ACLs:

```bash
setfacl -m mask::rwx /opt/openclaw/openclaw.mjs
```

## 10. Future Updates

When updating dependencies, always run as the `openclaw` service user:

```bash
sudo -u openclaw bash -c "cd /opt/openclaw && pnpm install"
sudo -u openclaw pnpm build
```

See `LOCAL-CHANGES.md` for the full git-install update procedure including how to
rebase local patches onto upstream and resolve common conflicts.

The `.npmrc` configuration ensures all pnpm operations remain self-contained within `/opt/openclaw/`.

## 11. Plugin Dependencies (Optional)

OpenClaw plugins may require additional system tools. On macOS, these are typically installed via Homebrew. **On Linux, use your native package manager instead** - Homebrew is not recommended.

### Arch Linux

Common dependencies for OpenClaw plugins:

```bash
# Core utilities
sudo pacman -S postgresql tailscale

# Optional: Database for prose extension
sudo systemctl enable postgresql
sudo systemctl start postgresql

# Optional: Tailscale for wide-area gateway discovery
sudo systemctl enable --now tailscaled

# Optional: Additional tools as needed
sudo pacman -S jq curl wget git
```

### Other Linux Distributions

**Debian/Ubuntu:**

```bash
sudo apt install postgresql tailscale jq curl wget git
```

**Fedora/RHEL:**

```bash
sudo dnf install postgresql tailscale jq curl wget git
```

### macOS-Only Plugins

The following plugins are macOS-specific and won't work on Linux:

- `apple-notes` - requires macOS Notes app
- `apple-reminders` - requires macOS Reminders app
- `goplaces` - macOS location tracking
- `imessage` - requires macOS Messages app

### Tool Detection

OpenClaw automatically detects tools in your `PATH` regardless of installation method. Tools installed via native package managers (pacman, apt, dnf) work seamlessly - **no Homebrew required on Linux**.

## 12. System Requirements

- **Disk Space**: ~2-3GB for node_modules, pnpm store, and build output
- **Memory**: 8GB RAM recommended, or 4GB RAM + 4GB swap minimum
- **Network**: Required for downloading packages during installation
