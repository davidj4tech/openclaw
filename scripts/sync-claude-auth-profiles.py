#!/usr/bin/env python3
"""Sync Claude Code OAuth tokens into OpenClaw service auth-profiles.json"""
import json, sys

claude_creds_path = '/home/ryer/.claude/.credentials.json'
auth_profiles_path = '/var/lib/openclaw/.openclaw/agents/main/agent/auth-profiles.json'

with open(claude_creds_path) as f:
    creds = json.load(f)

oauth = creds.get('claudeAiOauth', {})
access = oauth.get('accessToken')
refresh = oauth.get('refreshToken')
expires = oauth.get('expiresAt', 0)

if not access or not refresh or expires <= 0:
    print('sync-claude-auth-profiles: no valid OAuth tokens in Claude Code credentials', file=sys.stderr)
    sys.exit(1)

with open(auth_profiles_path) as f:
    profiles = json.load(f)

anthropic_profiles = [k for k, v in profiles.get('profiles', {}).items()
                      if v.get('provider') == 'anthropic' and v.get('type') == 'oauth']

if not anthropic_profiles:
    print('sync-claude-auth-profiles: no anthropic oauth profile found in auth-profiles.json', file=sys.stderr)
    sys.exit(1)

for key in anthropic_profiles:
    profiles['profiles'][key].update({'access': access, 'refresh': refresh, 'expires': expires})
    print(f'sync-claude-auth-profiles: updated {key} (expires: {expires})')

with open(auth_profiles_path, 'w') as f:
    json.dump(profiles, f, indent=2)
    f.write('\n')
