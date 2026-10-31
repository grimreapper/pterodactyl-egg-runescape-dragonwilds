import json
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EGG_PATH = ROOT / "egg-runescape-dragonwilds.json"
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9][A-Za-z0-9.+_-]*@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+\b"
)


def load_egg():
    return json.loads(EGG_PATH.read_text(encoding="utf-8"))


def variables_by_name(egg):
    return {item["env_variable"]: item for item in egg["variables"]}


def extract_shell_function(source, name):
    marker = f"{name}() {{"
    start = source.index(marker)
    depth = 0
    in_single = False
    in_double = False
    escaped = False
    for index in range(start, len(source)):
        character = source[index]
        if escaped:
            escaped = False
            continue
        if character == "\\" and not in_single:
            escaped = True
            continue
        if character == "'" and not in_double:
            in_single = not in_single
            continue
        if character == '"' and not in_single:
            in_double = not in_double
            continue
        if in_single or in_double:
            continue
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                end = source.find("\n", index)
                return source[start:] if end == -1 else source[start : end + 1]
    raise AssertionError(f"unterminated shell function: {name}")


def validate_manifest(tmp_path, contents):
    manifest = tmp_path / "appmanifest_4019830.acf"
    manifest.write_text(contents, encoding="utf-8", newline="\n")
    source = (ROOT / "scripts" / "install.sh").read_text(encoding="utf-8")
    validator = extract_shell_function(source, "manifest_field_is_unique_top_level")
    script = (
        "set -euo pipefail\n"
        f"{validator}\n"
        'manifest_field_is_unique_top_level "$1" appid 4019830\n'
        'manifest_field_is_unique_top_level "$1" StateFlags 4\n'
    )
    return subprocess.run(
        ["bash", "-c", script, "manifest-validator", str(manifest)],
        text=True,
        capture_output=True,
        check=False,
    )


def render_startup(game_port, beacon_port, additional_args="", max_players="6"):
    return (
        load_egg()["startup"]
        .replace("{{SERVER_PORT}}", str(game_port))
        .replace("{{BEACON_PORT}}", str(beacon_port))
        .replace("{{MAX_PLAYERS}}", str(max_players))
        .replace("{{ADDITIONAL_ARGS}}", additional_args)
    )


def test_public_metadata_is_neutral_and_keeps_upstream_attribution():
    egg = load_egg()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert egg["author"] == "community@example.invalid"
    assert egg["author"].endswith("@example.invalid")
    assert "David Wolfe (Red-Thirten)" in readme
    assert "https://github.com/redthirten" in readme


def test_startup_uses_upstream_launcher_and_distinct_beacon_allocation():
    egg = load_egg()
    variables = variables_by_name(egg)

    assert egg["meta"]["version"] == "PTDL_v2"
    for field in ("files", "startup", "logs"):
        assert isinstance(json.loads(egg["config"][field]), dict)

    beacon = variables["BEACON_PORT"]
    assert beacon["default_value"] == "8888"
    assert beacon["rules"] == r"required|integer|between:1024,65535|regex:/\A[1-9][0-9]{3,4}\z/"

    startup = egg["startup"]
    assert "10#${game_port} == 10#${beacon_port}" in startup
    assert "exec ./RSDragonwildsServer.sh" in startup
    assert '-Port="${game_port}"' in startup
    assert '-BeaconPort="${beacon_port}"' in startup


def test_installer_is_canonical_syntax_checked_and_fail_closed():
    egg = load_egg()
    embedded = egg["scripts"]["installation"]["script"]
    canonical_path = ROOT / "scripts" / "install.sh"
    canonical = canonical_path.read_text(encoding="utf-8")

    assert embedded == canonical
    assert "\r" not in canonical
    subprocess.run(["bash", "-n", str(canonical_path)], check=True)

    required_controls = (
        "set -euo pipefail",
        "--proto '=https'",
        "--tlsv1.2",
        "--max-filesize",
        "--no-same-owner --no-same-permissions",
        "STEAMCMD_SHA256=",
        "STEAMCMD_SIZE=",
        "sha256sum --check",
        '[[ "${SRCDS_APPID}" == "4019830" ]]',
        "appmanifest_${SRCDS_APPID}.acf",
        'manifest_field_is_unique_top_level "${manifest}" StateFlags 4',
        "RSDragonwildsServer.sh",
        "RSDragonwildsServer-Linux-Shipping",
        '[[ -s "${launcher}" ]]',
        '[[ -s "${binary}" ]]',
    )
    for control in required_controls:
        assert control in canonical


def test_manifest_validator_accepts_canonical_case_variants_and_documented_escapes(
    tmp_path,
):
    manifests = (
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n}\n',
        '"APPSTATE"\n{\n    "APPID" "4019830"\n    "stateflags" "4"\n}\n',
        '"AppState"\n{\n'
        '    // Steam metadata may contain documented escapes.\n'
        '    "appid" "4019830"\n'
        '    "StateFlags" "4"\n'
        '    "Note" "quote: \\" slash: \\\\ line\\n tab\\t"\n'
        '}\n',
        '"AppState" // token boundaries may cross comments and lines\n{\n'
        '    "appid" // value follows on the next line\n'
        '    "4019830"\n'
        '    "StateFlags"\n'
        '    // value follows after a comment-only line\n'
        '    "4"\n}\n',
    )
    for index, contents in enumerate(manifests):
        case_dir = tmp_path / str(index)
        case_dir.mkdir()
        result = validate_manifest(case_dir, contents)
        assert result.returncode == 0, (contents, result.stderr)


def test_manifest_validator_rejects_nested_duplicate_and_malformed_bypasses(tmp_path):
    attacks = (
        '"AppState"\n{\n'
        '    "Nested"\n    {\n'
        '        "appid" "4019830"\n'
        '        "StateFlags" "4"\n'
        '    }\n}\n',
        '"WrongRoot"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n}\n',
        '"AppState"\n{\n    "appid" "4019830"\n    "appid" "4019830"\n'
        '    "StateFlags" "4"\n}\n',
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n'
        '    "APPID" // duplicate value split around a comment\n'
        '    "999999"\n}\n',
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n'
        '    "Nested" { "APPID" "4019830" }\n}\n',
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n'
        '    "Nested" { "stateflags" "4" }\n}\n',
        '"AppState"\n{\n    "appid" "999999"\n    "StateFlags" "4"\n'
        '    "Nested" { "appid" "4019830" }\n}\n',
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "2"\n'
        '    "Nested" { "StateFlags" "4" }\n}\n',
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n',
        '"AppState"\n{\n    appid "4019830"\n    "StateFlags" "4"\n}\n',
        '"AppState"\n{\n    "app" // key-splitting must not form appid\n'
        '    "id" "4019830"\n    "StateFlags" "4"\n}\n',
        '"AppState"\n{\n    "app\\id" "4019830"\n    "StateFlags" "4"\n}\n',
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n'
        '    "UnknownEscape" "reject\\qthis"\n}\n',
        '"junk" "value"\n'
        '"AppState"\n{\n    "appid" "4019830"\n    "StateFlags" "4"\n}\n',
        '"AppState"\n{\n'
        '    "" "appid" "4019830" "StateFlags" "4" ""\n'
        '}\n',
        '"AppState"\n{\n    "Nested" { "brace" "}"\n'
        '        "appid" "4019830"\n        "StateFlags" "4"\n'
        '        "restore" "{" }\n}\n',
        '"AppState" { "appid" "4019830" "StateFlags" "4" }\n'
        '"AppState" { "other" "root" }\n',
    )
    for index, contents in enumerate(attacks):
        case_dir = tmp_path / str(index)
        case_dir.mkdir()
        result = validate_manifest(case_dir, contents)
        assert result.returncode != 0, contents


def test_release_boundary_and_installer_controls_are_explicit():
    egg = load_egg()
    canonical_path = ROOT / "scripts" / "install.sh"
    canonical = canonical_path.read_text(encoding="utf-8")

    assert egg["docker_images"] == {
        "ghcr.io/pelican-eggs/steamcmd:debian (pinned amd64)": (
            "ghcr.io/pelican-eggs/steamcmd:debian@sha256:"
            "ad309cbab24e211d2a973d0be8a92c957642a6d5b0b1d31f0cc561ff26f3048e"
        )
    }
    installation = egg["scripts"]["installation"]
    assert installation["container"] == (
        "ghcr.io/pelican-eggs/installers:debian@sha256:"
        "3f0d9f085986cfe422c25428a044529f512de7aa8f0c9998cbdccdaf01647b27"
    )
    assert installation["entrypoint"] == "/bin/bash"

    assert canonical.count("https://") == 1
    assert "http://" not in canonical
    assert "https://media.steampowered.com/client/steamcmd_linux.tar.gz" in canonical
    assert 'rm -rf -- "${STEAMCMD_DIR:?}"' in canonical
    assert canonical.index('rm -rf -- "${STEAMCMD_DIR:?}"') < canonical.index(
        'mkdir -p "${STEAMCMD_DIR}"'
    )

    wrong_app = subprocess.run(
        ["/bin/bash", str(canonical_path)],
        env={**os.environ, "PATH": "", "SRCDS_APPID": "1374490"},
        text=True,
        capture_output=True,
        check=False,
    )
    assert wrong_app.returncode == 1
    assert "must be exactly 4019830" in wrong_app.stderr

    current_paths = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    ).stdout.decode().split("\0")
    history_objects = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    history_entries = [line.split(" ", 1) for line in history_objects]
    history_paths = [entry[1] for entry in history_entries if len(entry) == 2]
    forbidden_suffixes = (".dll", ".exe", ".pak", ".sav", ".so")
    for path in [*current_paths, *history_paths]:
        assert not path.lower().endswith(forbidden_suffixes), path
        assert "RSDragonwilds/Binaries" not in path

    public_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    )
    personal_email_fixture = "operator" + "@" + "example.com"
    assert EMAIL_PATTERN.findall(personal_email_fixture) == [personal_email_fixture]
    assert EMAIL_PATTERN.findall("ghcr.io/example/debian@sha256:deadbeef") == []
    emails = set(EMAIL_PATTERN.findall(public_text))
    assert emails <= {"community@example.invalid"}
    assert not re.search(r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", public_text)
    assert not re.search(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", public_text)
    assert not re.search(r"\b192\.168\.\d{1,3}\.\d{1,3}\b", public_text)

    history_text = []
    for entry in history_entries:
        object_id = entry[0]
        object_type = subprocess.run(
            ["git", "cat-file", "-t", object_id],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.strip()
        if object_type != "blob":
            continue
        blob = subprocess.run(
            ["git", "cat-file", "blob", object_id],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        assert b"\x00" not in blob, entry
        history_text.append(blob.decode("utf-8"))

    reachable_text = "\n".join(history_text)
    history_emails = set(EMAIL_PATTERN.findall(reachable_text))
    assert history_emails <= {"community@example.invalid"}
    private_home_fixture = "/home/" + "hermes/"
    private_domain_fixture = "quiet" + "node.io"
    assert private_home_fixture not in reachable_text
    assert private_domain_fixture not in reachable_text.lower()
    assert not re.search(r"\b(?:10|127)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", reachable_text)
    assert not re.search(r"\b172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b", reachable_text)
    assert not re.search(r"\b192\.168\.\d{1,3}\.\d{1,3}\b", reachable_text)

    commit_metadata = subprocess.run(
        ["git", "log", "--all", "--format=%an%x00%ae%x00%cn%x00%ce"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout
    for line in commit_metadata.splitlines():
        author_name, author_email, committer_name, committer_email = line.split("\x00")
        assert author_name == "grimreapper"
        assert committer_name == "grimreapper"
        assert author_email.endswith("@users.noreply.github.com")
        assert committer_email.endswith("@users.noreply.github.com")

    assert variables_by_name(egg)["ADMIN_PASSWORD"]["default_value"] == ""
    assert variables_by_name(egg)["WORLD_PASSWORD"]["default_value"] == ""


def test_supported_variables_have_safe_rules_and_current_config_mappings():
    egg = load_egg()
    variables = variables_by_name(egg)
    assert set(variables) == {
        "AUTO_UPDATE",
        "OWNER_ID",
        "DEFAULT_WORLD_NAME",
        "SERVER_NAME",
        "ADMIN_PASSWORD",
        "WORLD_PASSWORD",
        "ADMIN_LIST",
        "BEACON_PORT",
        "MAX_PLAYERS",
        "ADDITIONAL_ARGS",
        "SRCDS_APPID",
    }

    assert variables["OWNER_ID"]["rules"] == (
        r"required|string|regex:/\A[A-Za-z0-9]{32}\z/"
    )
    single_line = r"regex:/\A[^\x00-\x1F\x7F]*\z/"
    assert variables["ADMIN_PASSWORD"]["rules"] == (
        f"required|string|min:8|max:128|{single_line}"
    )
    assert variables["WORLD_PASSWORD"]["rules"] == (
        f"nullable|string|max:128|{single_line}"
    )
    assert variables["BEACON_PORT"]["rules"] == (
        r"required|integer|between:1024,65535|regex:/\A[1-9][0-9]{3,4}\z/"
    )
    assert variables["MAX_PLAYERS"]["rules"] == "required|integer|between:1,6"
    assert variables["SRCDS_APPID"]["user_editable"] is False
    assert variables["SRCDS_APPID"]["rules"] == "required|integer|in:4019830"
    assert variables["ADMIN_LIST"]["rules"] == (
        r"required|string|regex:/\A\((?:[A-Za-z0-9]{32}(?:,[A-Za-z0-9]{32})*)?\)\z/|max:1057"
    )
    additional_rules = variables["ADDITIONAL_ARGS"]["rules"]
    assert "regex:" in additional_rules
    assert "\\A" in additional_rules
    assert "\\z" in additional_rules

    files = json.loads(egg["config"]["files"])
    mappings = files["RSDragonwilds/Saved/Config/LinuxServer/DedicatedServer.ini"]["find"]
    assert mappings["[/Script/Dominion.DedicatedServerSettings].AdministratorList"] == "{{server.build.env.ADMIN_LIST}}"
    startup = egg["startup"]
    assert 'additional_args="{{ADDITIONAL_ARGS}}"' in startup
    assert "read -r -a extra_args" in startup
    assert startup.endswith('"${extra_args[@]}"')


def test_identity_and_ini_values_are_ascii_or_single_line_before_rendering():
    egg = load_egg()
    variables = variables_by_name(egg)

    def validation_pattern(name):
        rules = variables[name]["rules"]
        pattern = rules.split("regex:/", 1)[1].rsplit("/", 1)[0]
        return re.compile(pattern.replace(r"\z", r"\Z"))

    owner_pattern = validation_pattern("OWNER_ID")
    assert owner_pattern.fullmatch("A0" * 16)
    assert owner_pattern.fullmatch("é" + "A" * 31) is None
    assert owner_pattern.fullmatch("_" + "A" * 31) is None

    safe_values = {
        "DEFAULT_WORLD_NAME": "Ashen Realm",
        "SERVER_NAME": "Dragon Keep",
        "ADMIN_PASSWORD": "Strong pass = []",
        "WORLD_PASSWORD": "Optional pass",
    }
    control_characters = ("\x00", "\t", "\n", "\r", "\x1f", "\x7f")
    for name, safe_value in safe_values.items():
        pattern = validation_pattern(name)
        assert pattern.fullmatch(safe_value)
        for control in control_characters:
            assert pattern.fullmatch(safe_value + control) is None, (name, repr(control))

    files = json.loads(egg["config"]["files"])
    mappings = files["RSDragonwilds/Saved/Config/LinuxServer/DedicatedServer.ini"]["find"]
    template_to_name = {
        f"{{{{server.build.env.{name}}}}}": name for name in safe_values
    }
    rendered_lines = [
        f"{key}={safe_values[template_to_name[value]]}"
        for key, value in mappings.items()
        if value in template_to_name
    ]
    rendered = "\n".join(rendered_lines)
    assert len(rendered_lines) == 4
    assert rendered.count("\n") == 3
    assert all(
        not any(character in line for character in control_characters)
        for line in rendered_lines
    )


def test_documentation_requires_dual_udp_and_records_live_acceptance_status():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    upstream_readme = (ROOT / "UPSTREAM-README.md").read_text(encoding="utf-8")
    troubleshooting = (ROOT / "docs" / "TROUBLESHOOTING.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    assert "Two UDP allocations" in readme
    assert "game port `7777`" in readme
    assert "beacon port `8888`" in readme
    assert "RSDragonwildsServer.sh" in readme
    assert "## Acceptance status" in readme
    assert "build `26161880`" in readme
    assert "controlled Pterodactyl restart" in readme
    assert "remain unverified client-side checks" in readme
    assert "for clean Pterodactyl shutdowns" not in readme
    for gate in ("both UDP sockets", "remote client", "join", "reconnect"):
        assert gate in readme
    assert "One UDP server allocation" not in readme
    assert "One configurable UDP game allocation" not in readme
    assert "8888" in upstream_readme
    assert "Beacon" in upstream_readme

    assert "BEACON_PORT" in troubleshooting
    assert "both UDP allocations" in troubleshooting
    assert "## 1.1.0 - 2026-11-01" in changelog
    assert "real client join/reconnect remain unverified" in changelog


def test_metadata_and_docs_use_current_four_gib_first_party_minimum():
    egg = load_egg()
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    upstream_readme = (ROOT / "UPSTREAM-README.md").read_text(encoding="utf-8")

    assert "minimum is 4 GiB" in egg["description"]
    assert "current first-party minimum is 4 GiB" in readme
    assert "| RAM | 4096 MiB" in upstream_readme
    assert "2 GB base" not in egg["description"]
    assert "3072 MiB" not in upstream_readme


def test_startup_rejects_noncanonical_ports_before_launcher_execution(tmp_path):
    startup = load_egg()["startup"]
    assert startup.startswith("set -euo pipefail;")

    invalid_pairs = (
        ("", "8888"),
        ("7777", ""),
        ("77:77", "8888"),
        ("07777", "8888"),
        ("7777", "08888"),
        ("not-a-port", "8888"),
        ("1023", "8888"),
        ("7777", "65536"),
    )
    for index, (game_port, beacon_port) in enumerate(invalid_pairs):
        case_dir = tmp_path / str(index)
        case_dir.mkdir()
        marker = case_dir / "launcher-ran"
        launcher = case_dir / "RSDragonwildsServer.sh"
        launcher.write_text(
            "#!/bin/bash\ntouch \"$LAUNCH_MARKER\"\n",
            encoding="utf-8",
        )
        launcher.chmod(0o755)
        result = subprocess.run(
            ["bash", "-c", render_startup(game_port, beacon_port)],
            cwd=case_dir,
            env={**os.environ, "LAUNCH_MARKER": str(marker)},
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 1, (game_port, beacon_port, result.stderr)
        assert "invalid" in result.stderr.lower()
        assert not marker.exists()

    for index, (game_port, beacon_port) in enumerate(((1024, 65535), (65535, 1024))):
        case_dir = tmp_path / f"valid-{index}"
        case_dir.mkdir()
        launcher = case_dir / "RSDragonwildsServer.sh"
        launcher.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        launcher.chmod(0o755)
        subprocess.run(
            ["bash", "-c", render_startup(game_port, beacon_port)],
            cwd=case_dir,
            check=True,
        )


def test_startup_fail_closed_and_disables_argument_globbing(tmp_path):
    def render(game_port, beacon_port, additional_args=""):
        return render_startup(game_port, beacon_port, additional_args)

    same_port = subprocess.run(
        ["bash", "-c", render(7777, 7777)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert same_port.returncode == 1
    assert "must be different" in same_port.stderr

    signed_same_port = subprocess.run(
        ["bash", "-c", render(7777, "+7777")],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert signed_same_port.returncode == 1
    assert "invalid" in signed_same_port.stderr

    args_path = tmp_path / "args.txt"
    launcher = tmp_path / "RSDragonwildsServer.sh"
    launcher.write_text(
        "#!/bin/bash\nprintf '%s\\n' \"$@\" > \"$ARGS_OUT\"\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)
    (tmp_path / "-Example=a").touch()
    env = {**os.environ, "ARGS_OUT": str(args_path)}

    reserved_port = subprocess.run(
        ["bash", "-c", render(17777, 18888, "-Port=9999")],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert reserved_port.returncode == 1
    assert "must not override" in reserved_port.stderr

    subprocess.run(
        ["bash", "-c", render(17777, 18888, "-Example=[a]")],
        cwd=tmp_path,
        env=env,
        check=True,
    )
    assert args_path.read_text(encoding="utf-8").splitlines() == [
        "-Port=17777",
        "-BeaconPort=18888",
        "-log",
        "-ini:Game:[/Script/Engine.GameSession]:MaxPlayers=6",
        "-Example=[a]",
    ]
