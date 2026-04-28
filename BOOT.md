# BOOT.md — First-Run Setup

This file runs once when the gateway starts, in an isolated boot session.
Use it to verify environment state and surface any setup issues.

## Checklist

- Verify workspace/ exists and is readable
- Verify identity files (SOUL.md, IDENTITY.md) are present
- Log boot timestamp to state/boot_status.log
- Return `BOOT_OK` if all checks pass; otherwise surface the specific failure
