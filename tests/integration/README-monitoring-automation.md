# Monitoring E2E rollout safeguards

Before enabling unattended runs:

- Acquire an exclusive lock and refuse to overwrite an existing synthetic fixture.
- Verify Prometheus FIRING and clearing for all four alerts.
- Validate Alertmanager routing and Discord delivery independently; Prometheus alone is insufficient.
- Ensure cleanup on errors and interruptions, and report incomplete runs.
- Keep the runner development-only until an isolated production test design is reviewed.
- Run under a restricted systemd service and timer, with deployment managed by Ansible.
- Account for the one-hour `RestoreTestTooOld` pending period.
