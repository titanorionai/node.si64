# Changelog

## v1.0.1-rc1 (2026-01-21)

- Bake `python-dotenv` into the image and add `titan_config.py` to the container so the image runs standalone (no bind mounts required).
- Add `DEPLOY_RC1.md` with build/push/validation commands for ARM64 Release Candidate.
- Added RC1 quick-run instructions to `README.md` and `VANGUARD_QUICK_START.md`.
- Updated `Dockerfile` to include config and dotenv files during build.
- Verified no-volume smoke test: container stays Up and reports `TITAN LIMB ONLINE`.

Released by: CI operator
