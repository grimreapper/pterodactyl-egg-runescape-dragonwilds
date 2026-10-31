#!/bin/bash
set -euo pipefail
umask 022

export HOME=/mnt/server
readonly STEAMCMD_URL="https://media.steampowered.com/client/steamcmd_linux.tar.gz"
readonly STEAMCMD_SHA256="cebf0046bfd08cf45da6bc094ae47aa39ebf4155e5ede41373b579b8f1071e7c"
readonly STEAMCMD_SIZE="2428561"
readonly STEAMCMD_MAX_SIZE="8388608"
readonly STEAMCMD_DIR="${HOME}/steamcmd"
archive=""

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    if [[ -n "${archive}" ]]; then
        rm -f -- "${archive}"
    fi
}
trap cleanup EXIT

SRCDS_APPID="${SRCDS_APPID:-}"
[[ "${SRCDS_APPID}" == "4019830" ]] || fail "SRCDS_APPID must be exactly 4019830."

rm -rf -- "${STEAMCMD_DIR:?}"
mkdir -p "${STEAMCMD_DIR}" "${HOME}/steamapps"
archive="$(mktemp "${TMPDIR:-/tmp}/steamcmd_linux.XXXXXX.tar.gz")"

curl \
    --fail \
    --show-error \
    --location \
    --proto '=https' \
    --tlsv1.2 \
    --retry 3 \
    --retry-all-errors \
    --connect-timeout 20 \
    --max-time 300 \
    --max-filesize "${STEAMCMD_MAX_SIZE}" \
    --output "${archive}" \
    "${STEAMCMD_URL}"

actual_size="$(stat -c '%s' "${archive}")"
[[ "${actual_size}" == "${STEAMCMD_SIZE}" ]] || fail "SteamCMD archive size mismatch: expected ${STEAMCMD_SIZE}, got ${actual_size}."
printf '%s  %s\n' "${STEAMCMD_SHA256}" "${archive}" | sha256sum --check --status || fail "SteamCMD archive checksum mismatch."

tar --extract --gzip --file "${archive}" --directory "${STEAMCMD_DIR}" --no-same-owner --no-same-permissions
chmod +x "${STEAMCMD_DIR}/steamcmd.sh"

"${STEAMCMD_DIR}/steamcmd.sh" \
    +@sSteamCmdForcePlatformType linux \
    +force_install_dir "${HOME}" \
    +login anonymous \
    +app_update "${SRCDS_APPID}" validate \
    +quit

manifest_field_is_unique_top_level() {
    local path="$1"
    local key="$2"
    local expected="$3"
    LC_ALL=C awk -v wanted_key="${key}" -v expected="${expected}" '
        function record_key(key, value) {
            if (tolower(key) == wanted_key) {
                total++
                if (depth == 1) {
                    top++
                    top_value = value
                }
            }
        }
        function string_token(value, key) {
            if (finished || invalid) {
                invalid = 1
                return
            }
            if (!pending) {
                pending_key = value
                pending = 1
                return
            }
            key = pending_key
            pending_key = ""
            pending = 0
            if (depth == 0) {
                invalid = 1
                return
            }
            record_key(key, value)
        }
        function open_object(key) {
            if (finished || invalid || !pending) {
                invalid = 1
                return
            }
            key = pending_key
            pending_key = ""
            pending = 0
            record_key(key, "")
            if (depth == 0) {
                if (root_seen || tolower(key) != "appstate") {
                    invalid = 1
                    return
                }
                root_seen = 1
            }
            depth++
        }
        function close_object() {
            if (invalid || pending || depth <= 0) {
                invalid = 1
                return
            }
            depth--
            if (depth == 0) finished = 1
        }
        BEGIN {
            depth = 0
            total = 0
            top = 0
            top_value = ""
            pending_key = ""
            pending = 0
            root_seen = 0
            finished = 0
            invalid = 0
            wanted_key = tolower(wanted_key)
        }
        {
            line = $0
            length_line = length(line)
            index_line = 1
            while (index_line <= length_line && !invalid) {
                character = substr(line, index_line, 1)
                next_character = substr(line, index_line + 1, 1)
                if (character ~ /[[:space:]]/) {
                    index_line++
                } else if (character == "/" && next_character == "/") {
                    break
                } else if (character == "{") {
                    open_object()
                    index_line++
                } else if (character == "}") {
                    close_object()
                    index_line++
                } else if (character == "\"") {
                    value = ""
                    closed_quote = 0
                    index_line++
                    while (index_line <= length_line) {
                        character = substr(line, index_line, 1)
                        if (character == "\\") {
                            index_line++
                            if (index_line > length_line) {
                                invalid = 1
                                break
                            }
                            escaped = substr(line, index_line, 1)
                            if (escaped == "\"" || escaped == "\\") {
                                value = value escaped
                            } else if (escaped == "n") {
                                value = value "\n"
                            } else if (escaped == "t") {
                                value = value "\t"
                            } else {
                                invalid = 1
                                break
                            }
                            index_line++
                        } else if (character == "\"") {
                            closed_quote = 1
                            index_line++
                            break
                        } else {
                            value = value character
                            index_line++
                        }
                    }
                    if (!closed_quote) invalid = 1
                    if (!invalid) string_token(value)
                } else {
                    invalid = 1
                }
            }
        }
        END {
            exit !(invalid == 0 && root_seen == 1 && finished == 1 && depth == 0 && pending == 0 && total == 1 && top == 1 && top_value == expected)
        }
    ' "${path}"
}

readonly manifest="${HOME}/steamapps/appmanifest_${SRCDS_APPID}.acf"
readonly launcher="${HOME}/RSDragonwildsServer.sh"
readonly binary="${HOME}/RSDragonwilds/Binaries/Linux/RSDragonwildsServer-Linux-Shipping"

[[ -s "${manifest}" ]] || fail "Steam app manifest is missing: ${manifest}"
manifest_field_is_unique_top_level "${manifest}" appid 4019830 || fail "Steam app manifest must identify App ID 4019830 exactly once at the AppState top level."
manifest_field_is_unique_top_level "${manifest}" StateFlags 4 || fail "Steam app manifest must report StateFlags 4 exactly once at the AppState top level."
[[ -s "${launcher}" ]] || fail "Upstream Linux launcher is missing or empty: ${launcher}"
[[ -s "${binary}" ]] || fail "Linux server binary is missing or empty: ${binary}"
chmod +x "${launcher}" "${binary}"

mkdir -p "${HOME}/.steam/sdk32" "${HOME}/.steam/sdk64"
install -m 0644 "${STEAMCMD_DIR}/linux32/steamclient.so" "${HOME}/.steam/sdk32/steamclient.so"
install -m 0644 "${STEAMCMD_DIR}/linux64/steamclient.so" "${HOME}/.steam/sdk64/steamclient.so"

printf '\nRuneScape: Dragonwilds dedicated server installed and verified.\n'
