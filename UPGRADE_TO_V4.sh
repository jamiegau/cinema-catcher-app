#!/usr/bin/env bash
# Download this file into the EXISTING v3 installation, then run with sudo bash.
set -Eeuo pipefail
INSTALL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [[ "${1:-}" == --help || "${1:-}" == -h ]]; then
    printf '%s\n' 'Usage: sudo bash UPGRADE_TO_V4.sh [--check | --status | --rollback]' \
        'Run from the existing v3 installation. Default: guided full v3-to-v4 upgrade.' \
        '--check validates the installation without stopping services.' \
        '--status shows the saved upgrade state; --rollback restores the pre-upgrade snapshot.'
    exit 0
fi
[[ $EUID -eq 0 ]] || { printf 'Run with sudo bash %s/UPGRADE_TO_V4.sh\n' "$INSTALL_DIR" >&2; exit 1; }
command -v python3 >/dev/null || { echo 'Install python3 first.' >&2; exit 1; }

# Recovery must use the exact runner saved with this site's upgrade, even if
# GitHub is unavailable or a newer release has since been published.
if [[ "${1:-}" == --status || "${1:-}" == --rollback ]]; then
    [[ -f "$INSTALL_DIR/.catcher-upgrade/runner/upgrade_v4.py" ]] || {
        echo 'No upgrade started by this script was found. Do not guess a database copy.' >&2; exit 1;
    }
    exec python3 "$INSTALL_DIR/.catcher-upgrade/runner/upgrade_v4.py" --install-dir "$INSTALL_DIR" "$@"
fi
command -v git >/dev/null || { echo 'Install git first.' >&2; exit 1; }
umask 077
upgrade_tmp="$(mktemp -d /tmp/catcher-v4-release.XXXXXXXX)"
cleanup() {
    case "$upgrade_tmp" in /tmp/catcher-v4-release.*) rm -rf -- "$upgrade_tmp" ;; esac
}
trap cleanup EXIT
git clone --quiet --depth 1 --single-branch --branch main \
    https://github.com/jamiegau/cinema-catcher-app.git "$upgrade_tmp/release"
# All helpers/templates now come from one fetched commit, not separate moving URLs.
python3 "$upgrade_tmp/release/upgrade/upgrade_v4.py" \
    --install-dir "$INSTALL_DIR" --release-dir "$upgrade_tmp/release" "$@"
