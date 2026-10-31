# Changelog

All notable changes to this community egg are documented here.

## 1.1.0 - 2026-11-01

### Fixed

- Added the required second UDP beacon allocation (`BEACON_PORT`, default `8888`) with explicit fail-closed shell behavior, canonical `1024`–`65535` validation, and a numeric same-port guard
- Switched startup from the shipping binary to the upstream `RSDragonwildsServer.sh` launcher with explicit `-Port` and `-BeaconPort`
- Enforced ASCII-only 32-character owner/administrator IDs and single-line INI-bound names and passwords
- Restricted additional arguments with pathname expansion disabled
- Hardened installation with HTTPS-only transfer controls, exact SteamCMD archive size/SHA-256 verification, permission-safe extraction, a clean idempotent SteamCMD bootstrap, strict single-root app-manifest parsing, and launcher/binary checks
- Replaced inherited personal author metadata with a neutral non-identifying contact value while preserving upstream attribution
- Corrected the current first-party minimum memory to 4 GiB
- Added a canonical LF-only installer source and automated PTDL/config/script consistency tests
- Pinned the runtime and installer container images to the exact Linux/amd64 manifests used for live acceptance

### Validation status

- Local static, fail-closed, privacy, and proprietary-payload checks are automated
- Clean anonymous Wings installation of App `4019830` build `26161880`, native process survival, distinct game/beacon UDP listeners, EOS session creation, `ReadyToJoin=1`, recurring heartbeats, saves/autosaves, controlled Pterodactyl restart, readiness recovery, save persistence, and a five-minute post-restart soak passed
- Exact public-browser matching and a real client join/reconnect remain unverified client-side checks; they were not inferred from the server-side EOS markers

## 1.0.0 - 2026-08-22

### Added

- Anonymous SteamCMD installation for dedicated-server App ID `4019830`
- Native Linux dedicated-server runtime
- Forced Linux depot selection with `@sSteamCmdForcePlatformType linux`
- Fail-fast installation with `set -euo pipefail`
- Server-binary existence and executable checks
- Automatic SteamCMD update option
- Configurable owner ID, world name, server name, passwords, and player limit
- Blank-by-default administrator and world passwords
- Effective 16-character world-name validation
- One-allocation UDP startup
- Direct `exec` signal forwarding
- EOS session-based `START SESSION - Success` readiness marker
- Public-browser, owner/admin, persistence, update, and troubleshooting documentation
- Known-safe SPUD autosave warning documentation

### Tested

- PTDL v2 JSON validation
- Disposable Pterodactyl import/export round trip
- Anonymous native Linux installation
- Startup update check
- EOS session creation and recurring heartbeats
- `ReadyToJoin=1`
- UDP game-port binding
- Clean Pterodactyl stop/start
- World save creation and periodic autosaves
- Persistent world reload across restart
- Secret and private-infrastructure scan

### Known limitations

- Public browser visibility and end-to-end joining should always be confirmed with a real Dragonwilds client.
- Dragonwilds emits noisy `Chunk ID Players` serializer warnings during otherwise successful saves.
- There are no dedicated-server console commands known at the time of publication.
