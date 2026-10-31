# Troubleshooting

## Installation reports `Missing configuration`

Dedicated-server App ID `4019830` has native Linux content, but SteamCMD may fail unless the platform is forced explicitly.

The current egg installer includes:

```text
+@sSteamCmdForcePlatformType linux
```

If an older imported egg omits that argument, import the current JSON and reinstall after backing up world saves.

## Installation completes but the executable is missing

Expected executable:

```text
RSDragonwilds/Binaries/Linux/RSDragonwildsServer-Linux-Shipping
```

The current installer uses `set -euo pipefail`, strictly validates one `AppState` manifest root with unique top-level `appid` and `StateFlags` values, and checks `RSDragonwildsServer.sh` plus that binary before returning success. If any check fails:

- inspect the installation log for SteamCMD errors;
- confirm outbound access to the Steam CDN;
- confirm at least 20 GB disk is available;
- verify `SRCDS_APPID` is `4019830`;
- reinstall after correcting the underlying cause.

No Steam account should be required because App ID `4019830` supports anonymous download.

## Panel remains yellow or starting

The egg expects this exact readiness marker:

```text
START SESSION - Success
```

Check:

1. The imported startup configuration contains:

```json
{"done":"START SESSION - Success"}
```

2. The startup command validates both ports, rejects duplicate or non-canonical values, rejects additional arguments that override either port, and ends by executing:

```text
exec ./RSDragonwildsServer.sh -Port="${game_port}" -BeaconPort="${beacon_port}" -log -ini:Game:[/Script/Engine.GameSession]:MaxPlayers={{MAX_PLAYERS}} "${extra_args[@]}"
```

3. Recent logs show successful EOS session creation.
4. An existing server created from an older egg may retain its old per-server startup command. Update that server's Startup command or recreate it from the current egg.

Do not use a merely running container as the readiness test.

## Server is running but absent from the Public browser

Check all of the following:

- `START SESSION - Success` appears;
- `ReadyToJoin=1` appears;
- an EOS session ID is created;
- recurring `HeartbeatSession` messages appear;
- the primary game allocation and `BEACON_PORT` are distinct;
- both UDP allocations are mapped, forwarded, and allowed end to end;
- the server has a valid 32-character `OWNER_ID`;
- players search the exact, case-sensitive world name;
- browser filters do not hide passworded or full worlds.

Search uses the world name, not the Pterodactyl name or `SERVER_NAME`.

LAN clients should use the **Direct** tab because EOS advertises the public endpoint.

The upstream defaults are game UDP `7777` and beacon UDP `8888`. A server may appear in the Worlds list but fail to join if either allocation is unavailable.

## Players can join but the owner has no owner controls

`OWNER_ID` must be the owner's real 32-character Dragonwilds Player ID from the bottom of the in-game **Settings** menu.

A format-valid placeholder can allow the process to boot but does not grant ownership. Ordinary players do not need the owner's Player ID to join.

Owner identity and administrator-password access are separate mechanisms.

## Administrator access does not work

- Set a unique `ADMIN_PASSWORD` in Pterodactyl.
- Restart the server so the generated Linux server config is refreshed.
- In game, open **Pause Menu → Settings → Server Management** and enter that password.
- Confirm the server is reading:

```text
RSDragonwilds/Saved/Config/LinuxServer/DedicatedServer.ini
```

Do not publish the generated config or password.

## World name is truncated

Dragonwilds effectively limits the world/slot name to 16 characters. The egg validates `DEFAULT_WORLD_NAME` with `max:16`.

Uploaded worlds use their embedded world name and ignore the default name variable.

## Red `Chunk ID Players` errors appear during saving

These warnings are known:

```text
LogSpudData: Error: Chunk ID Players is more than 4 characters long, will be truncated
LogSpudData: Error: Chunk ID Players is more than 4 characters long, truncating
```

They were non-fatal in testing when followed by:

```text
LogSpudSubsystem: Save to slot <world>: Success
```

Verify:

- `RSDragonwilds/Saved/SaveGames/<world>.sav` advances;
- `<world>.sav.backup` advances;
- there are no save failure, load failure, or corruption messages;
- the container remains stable.

Do not delete a healthy world to silence these lines.

## World does not survive a restart

Before changing files, verify:

1. A `.sav` file exists under `RSDragonwilds/Saved/SaveGames/`.
2. A controlled Pterodactyl stop completes cleanly.
3. The next start uses the same Wings volume.
4. Logs identify the same world/slot and world GUID.
5. No reinstall, volume replacement, or intentional world reset occurred.

Always back up `SaveGames/` before reinstalling or moving the server.

## Automatic update does not run

The runtime image handles `AUTO_UPDATE=1` before the startup command executes.

Expected behavior:

```text
Success! App '4019830' already up to date.
```

or SteamCMD download/update output when a new build exists.

Do not add a second SteamCMD command to the game startup. Duplicate update wrappers complicate readiness and signal handling.

If updating an older server:

- confirm `AUTO_UPDATE=1`;
- confirm the selected Docker image is the digest-pinned `ghcr.io/pelican-eggs/steamcmd:debian` image from the release egg;
- stop cleanly and back up `SaveGames/`;
- restart and inspect the pre-launch SteamCMD output.

## First start takes a long time

Initial SteamCMD installation and validation can take several minutes. Wait for the EOS readiness marker rather than judging only by container uptime.
