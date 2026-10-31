# Pterodactyl Egg: RuneScape: Dragonwilds

A community-maintained PTDL v2 egg for the native Linux **RuneScape: Dragonwilds** dedicated server.

The egg installs the official dedicated-server package anonymously through SteamCMD, launches the native Linux server, exposes the supported world and access settings as Pterodactyl variables, preserves dedicated-world saves, advertises through Epic Online Services (EOS), and reports a real session-ready marker to Wings.

> This project is not affiliated with Jagex, RuneScape, RuneScape: Dragonwilds, Valve, Steam, Epic Online Services, Pterodactyl, or Pelican. It does not distribute game files.

## What this egg handles

- Anonymous SteamCMD installation and validation
- Native Linux dedicated-server runtime
- Forced Linux depot selection to avoid SteamCMD `Missing configuration`
- Automatic SteamCMD update checks on startup
- Two UDP allocations: game port `7777` and beacon port `8888` by default
- The upstream `RSDragonwildsServer.sh` Linux launcher with explicit game and beacon ports
- Public EOS session advertisement
- Configurable owner ID, world name, server name, passwords, and player limit
- No embedded passwords: `ADMIN_PASSWORD` must be set and `WORLD_PASSWORD` may remain empty
- Dedicated-world persistence under `RSDragonwilds/Saved/SaveGames/`
- Genuine session readiness detection instead of process-only detection
- Direct signal delivery with `exec` to the upstream launcher; clean stop/save behavior remains a live acceptance gate
- Strict installer failure handling and binary verification

## Requirements

- Pterodactyl Panel and Wings
- An x86-64 Linux Wings node capable of running:
  - `ghcr.io/pelican-eggs/steamcmd:debian@sha256:ad309cbab24e211d2a973d0be8a92c957642a6d5b0b1d31f0cc561ff26f3048e`
  - `ghcr.io/pelican-eggs/installers:debian@sha256:3f0d9f085986cfe422c25428a044529f512de7aa8f0c9998cbdccdaf01647b27`
- Two distinct UDP server allocations (game and beacon)
- A valid 32-character Dragonwilds Player ID for the world owner
- A unique administrator password

No Steam account, game ownership, Steam password, or Steam Guard code is required. Dedicated-server App ID `4019830` supports anonymous SteamCMD access.

## Current 1.1.0 acceptance

- Pterodactyl Panel `1.11.11`
- Pterodactyl Wings `1.11.13`
- PTDL v2 import/export round trip
- `ghcr.io/pelican-eggs/steamcmd:debian` resolved to the pinned Linux/amd64 manifest digest `sha256:ad309cbab24e211d2a973d0be8a92c957642a6d5b0b1d31f0cc561ff26f3048e`
- `ghcr.io/pelican-eggs/installers:debian` resolved to the pinned Linux/amd64 manifest digest `sha256:3f0d9f085986cfe422c25428a044529f512de7aa8f0c9998cbdccdaf01647b27`
- Native Linux x86-64 Wings node
- Dedicated-server App ID `4019830`, Steam build `26161880`
- Clean anonymous installation and executable/manifest validation
- Native process survival, distinct game/beacon UDP listeners, EOS session creation, `ReadyToJoin=1`, and recurring heartbeats
- Save creation, autosave, controlled Pterodactyl restart, listener/readiness recovery, and save persistence
- Five-minute post-restart soak with no OOM or restart loop

Exact public-browser matching and a real Client App ID `1374490` join/reconnect were not automated for this release and remain unverified client-side checks. Server-side acceptance did not substitute a panel-installed flag for process, socket, EOS, heartbeat, save, and restart evidence.

Newer panel, Wings, and container-image versions should work with the PTDL v2 export, but have not necessarily been tested by this repository.

The release pins both executable container images by Linux/amd64 manifest digest. Updating either digest is a reviewed release change: resolve the tag again, inspect the new manifest, rerun the full test suite and live acceptance, then update the egg and documentation together.

Verified release downloads, including the importable egg and `SHA256SUMS`, are available from [`v1.1.0`](https://github.com/grimreapper/pterodactyl-egg-runescape-dragonwilds/releases/tag/v1.1.0).

## Installation

1. Download [`egg-runescape-dragonwilds.json`](egg-runescape-dragonwilds.json).
2. In the Pterodactyl admin area, open a SteamCMD-compatible nest and import the egg.
3. Create a server from the imported **RuneScape: Dragonwilds** egg.
4. Assign two distinct UDP allocations: game port `7777` and beacon port `8888` are the upstream defaults. If different allocations are used, set `BEACON_PORT` to the additional allocation; the primary allocation is supplied as `SERVER_PORT`.
5. Forward and allow both UDP allocations end to end. A world can be listed by EOS but still reject joins when the beacon port is unavailable.
6. Set `OWNER_ID` to the 32-character Player ID shown at the bottom of the in-game **Settings** menu.
7. Set a unique `ADMIN_PASSWORD`.
8. Set `DEFAULT_WORLD_NAME` to the public world name players should search for. It is case-sensitive and limited to 16 characters.
9. Leave `WORLD_PASSWORD` blank for an open server, or set one for private access.
10. Keep `AUTO_UPDATE=1` unless startup update checks are intentionally disabled.
11. Start the server and wait for:

```text
START SESSION - Success
```

The first installation can take several minutes while SteamCMD downloads and validates the native Linux server package.

## Suggested resources

The current first-party minimum is 4 GiB RAM. A conservative six-player starting allocation is:

| Resource | Suggested value |
|---|---:|
| Memory | 8 GB |
| CPU | 2–3 logical cores |
| Disk | 20 GB |
| Swap | 0–2 GB |

An earlier 1.0.0 empty-server observation used approximately 775 MB RAM, about 2.5% of one CPU snapshot, and 5.4 GB disk after installation. It is historical sizing guidance, not a 1.1.0 load test. Real requirements depend on world size, player activity, game updates, and container behavior.

## Important variables

| Variable | Purpose |
|---|---|
| `OWNER_ID` | Required 32-character Player ID for the world owner |
| `DEFAULT_WORLD_NAME` | New-world name and exact case-sensitive Public-browser search term; maximum 16 characters |
| `SERVER_NAME` | Displayed as the server creator/name in the browser; maximum 16 characters |
| `ADMIN_PASSWORD` | Required 8–128 character password granting access to in-game Server Management; no password is embedded in the egg |
| `WORLD_PASSWORD` | Optional join password; blank means open |
| `ADMIN_LIST` | Optional Unreal-style list of Player IDs with persistent administrator access |
| `BEACON_PORT` | Required second UDP allocation; default `8888`, distinct from `SERVER_PORT` |
| `MAX_PLAYERS` | Player capacity from 1 to 6 |
| `ADDITIONAL_ARGS` | Optional advanced launcher arguments restricted to non-shell metacharacters; cannot override game or beacon ports |
| `AUTO_UPDATE` | Enables the container image's SteamCMD update check before startup |
| `SRCDS_APPID` | Fixed dedicated-server App ID `4019830` |

All exposed variables include Pterodactyl descriptions and validation rules.

## Player ID and access semantics

`OWNER_ID` assigns ownership and owner-only controls. It is not a whitelist.

Ordinary players do **not** need the owner's Player ID. They can join and play when the world is public and they satisfy any configured world-password requirement. Each server should still be configured with the real owner's Player ID so ownership and administrative behavior work correctly.

The administrator password is separate. A player who knows it can open **Pause Menu → Settings → Server Management** and receives administrator access until that password changes.

## Public discovery and joining

Dragonwilds uses EOS-backed public discovery.

1. Start the server and wait for the readiness marker.
2. In Dragonwilds, open **Worlds**.
3. Select the **Public** tab.
4. Search for the exact, case-sensitive world name.
5. Select the matching result and join.

Search uses the **world name**, not the Pterodactyl server name, IP address, or `SERVER_NAME` value. LAN players can use the **Direct** tab instead.

Healthy advertisement logs include:

```text
START SESSION - Success
ReadyToJoin=1
HeartbeatSession
```

An EOS session and recurring heartbeats prove backend advertisement. A real game client is still the authoritative test of browser visibility and external joining.

## Installation and update behavior

The installer forces native Linux content:

```text
+@sSteamCmdForcePlatformType linux
+login anonymous
+app_update 4019830 validate
```

It uses `set -euo pipefail`, recreates only the SteamCMD bootstrap directory for safe repeat installations, pins the bootstrap archive by exact size and SHA-256, extracts without archive-supplied ownership or permission modes, requires one well-formed `AppState` root with unique top-level `appid` and `StateFlags` values, and verifies that both the upstream launcher and shipping executable exist before installation can succeed:

```text
RSDragonwildsServer.sh
RSDragonwilds/Binaries/Linux/RSDragonwildsServer-Linux-Shipping
```

The current bootstrap pin is 2,428,561 bytes with SHA-256 `cebf0046bfd08cf45da6bc094ae47aa39ebf4155e5ede41373b579b8f1071e7c`. A legitimate Valve archive rotation intentionally fails closed until the repository pin is reviewed and updated.

With `AUTO_UPDATE=1`, the SteamCMD runtime image checks the dedicated-server App ID before launching. The startup command does not run a second duplicate update.

Expected current-build output resembles:

```text
Success! App '4019830' already up to date.
```

## Readiness and shutdown

The egg does not treat a running Docker container as proof that Dragonwilds is joinable. Pterodactyl reaches ready only after:

```text
START SESSION - Success
```

For a complete operational check, also confirm:

- `ReadyToJoin` becomes `1`;
- EOS creates a session and emits recurring heartbeats;
- the game binds both UDP sockets;
- the expected `.sav` file is created;
- a controlled Pterodactyl stop exits cleanly;
- restarting loads the same persistent world.

The startup command uses `exec` with `RSDragonwildsServer.sh`, so Wings signals reach the upstream launcher directly. Release 1.1.0 also passed a controlled Pterodactyl restart: the process and both listeners recovered, EOS readiness and heartbeats resumed, and the same save persisted.

## Acceptance status

Release 1.1.0 recorded the following on a disposable Wings server:

- anonymous SteamCMD installation of App ID `4019830`, including build `26161880` and its app manifest;
- existence of `RSDragonwildsServer.sh` and the Linux shipping binary;
- a start with non-default, distinct allocations and confirmation that both UDP sockets are bound;
- `START SESSION - Success`, `ReadyToJoin=1`, EOS session creation, and recurring heartbeats;
- save creation and autosave;
- controlled Pterodactyl restart, recovery, reload of the same persistent save, and a five-minute post-restart soak without OOM or a restart loop.

Exact public-browser matching and a real remote client join/reconnect through the public path were not automated and remain unverified client-side checks. A successful EOS session marker is not presented as proof of those client checks.

## World data and backups

Persistent data is stored under:

```text
RSDragonwilds/Saved/
```

Important paths:

```text
RSDragonwilds/Saved/SaveGames/
RSDragonwilds/Saved/Config/LinuxServer/DedicatedServer.ini
RSDragonwilds/Saved/Logs/
```

Back up `SaveGames/` before reinstalling, moving, replacing, or resetting a world. Steam can restore game binaries, but it cannot restore player-created world data.

A minimal backup exclusion pattern is documented in the [upstream reference](UPSTREAM-README.md#sample-ignore-file-for-backups).

## Known quirks

### SPUD `Players` chunk warning

Dragonwilds may print these lines during autosaves:

```text
LogSpudData: Error: Chunk ID Players is more than 4 characters long, will be truncated
LogSpudData: Error: Chunk ID Players is more than 4 characters long, truncating
```

They are a noisy game-side serializer warning. In testing they were harmless when immediately followed by:

```text
LogSpudSubsystem: Save to slot <world>: Success
```

Confirm the primary `.sav` and `.sav.backup` timestamps continue advancing and that no save/load/corruption failure appears. Do not delete world saves merely to suppress the red console text.

### Public search is case-sensitive

Players must search for the exact world name. `SERVER_NAME` is displayed metadata and is not the primary search term.

### No known server console commands

There are no dedicated-server console commands known at the time of publication.

See [Troubleshooting](docs/TROUBLESHOOTING.md) for installation, readiness, discovery, owner, and persistence checks.

## Security

- The egg contains no Steam credentials, panel credentials, IP addresses, private hostnames, owner IDs, administrator passwords, or world passwords.
- INI-bound names and passwords reject CR, LF, tabs, NUL, DEL, and other control characters before Pterodactyl renders the configuration.
- Always set a unique `ADMIN_PASSWORD`.
- Use a world password when the server should not be public.
- Treat Player IDs as account identifiers and avoid publishing live values unnecessarily.
- Do not commit panel exports or generated config files containing live values.

## Attribution

This Pterodactyl adaptation is based on the maintained Pelican Games SteamCMD Dragonwilds egg originally authored by [David Wolfe (Red-Thirten)](https://github.com/redthirten), with contributions documented by the [Pelican project](https://github.com/pelican-eggs/games-steamcmd/tree/main/runescape_dragonwilds).

The hardened PTDL v2 adaptation adds forced Linux depot selection, fail-closed installation, pinned SteamCMD bootstrap verification, upstream-launcher use, dual-port configuration, corrected Pterodactyl variable documentation, and direct signal forwarding.

## License

The egg wrapper and repository documentation are available under the [MIT License](LICENSE). RuneScape, RuneScape: Dragonwilds, Jagex, Steam, Epic Online Services, Pterodactyl, and Pelican remain subject to their respective owners and licenses.
