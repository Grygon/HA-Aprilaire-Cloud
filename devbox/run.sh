#!/usr/bin/env bash
# Local Home Assistant dev box (rootless podman) for the aprilaire_cloud integration.
#
# Usage:
#   ./run.sh up        # (re)sync integration, seed entry from ../../.env, start HA
#   ./run.sh logs      # follow HA logs
#   ./run.sh down      # stop & remove the container
#   ./run.sh restart   # restart (picks up code changes after a `sync`)
#   ./run.sh sync      # copy the integration into the config dir (no restart)
#   ./run.sh shell     # shell inside the running container
#   ./run.sh test      # run the pytest suite in a throwaway container
#   ./run.sh reset     # stop and wipe the config dir (fresh HA + re-onboard)
#
# The UI is at http://localhost:8123 . On first visit you'll onboard (create a
# local account) -- the aprilaire_cloud integration is already set up headlessly
# from the seeded config entry, so the thermostat appears regardless.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTEGRATION_SRC="$HERE/../custom_components/aprilaire_cloud"
ENV_FILE="${APRILAIRE_ENV_FILE:-$HERE/../../.env}"
CONFIG="$HERE/config"
IMAGE="ghcr.io/home-assistant/home-assistant:stable"
NAME="ha-aprilaire-dev"

sync_integration() {
  mkdir -p "$CONFIG/custom_components"
  rm -rf "$CONFIG/custom_components/aprilaire_cloud"
  cp -r "$INTEGRATION_SRC" "$CONFIG/custom_components/aprilaire_cloud"
  find "$CONFIG/custom_components/aprilaire_cloud" -name __pycache__ -type d -prune -exec rm -rf {} +
  echo "synced integration -> $CONFIG/custom_components/aprilaire_cloud"
}

write_config_yaml() {
  if [ ! -f "$CONFIG/configuration.yaml" ]; then
    cat > "$CONFIG/configuration.yaml" <<'YAML'
default_config:

logger:
  default: warning
  logs:
    custom_components.aprilaire_cloud: debug
YAML
    echo "wrote configuration.yaml"
  fi
}

case "${1:-up}" in
  up)
    sync_integration
    write_config_yaml
    python3 "$HERE/seed_entry.py" "$CONFIG" "$ENV_FILE"
    podman rm -f "$NAME" >/dev/null 2>&1 || true
    podman run -d --name "$NAME" \
      -p 8123:8123 \
      -v "$CONFIG:/config:Z" \
      -e TZ="$(cat /etc/timezone 2>/dev/null || echo America/Chicago)" \
      "$IMAGE" >/dev/null
    echo "started $NAME -> http://localhost:8123"
    echo "follow logs with: $0 logs"
    ;;
  logs)    exec podman logs -f "$NAME" ;;
  down)    podman rm -f "$NAME" >/dev/null 2>&1 || true; echo "stopped $NAME" ;;
  restart) sync_integration; podman restart "$NAME"; echo "restarted $NAME" ;;
  sync)    sync_integration ;;
  test)
    # Run the pytest suite in a *throwaway* container (leaves the live dev box
    # untouched). Mounts the repo read-write for pytest's cache and a pip cache
    # so repeat runs are fast.
    REPO="$(cd "$HERE/.." && pwd)"
    mkdir -p "$HERE/.pipcache"
    exec podman run --rm \
      -v "$REPO:/src:Z" \
      -v "$HERE/.pipcache:/root/.cache/pip:Z" \
      -w /src \
      --entrypoint sh \
      "$IMAGE" -c '
        set -e
        python -m pip install --quiet --root-user-action=ignore -r requirements-test.txt
        exec python -m pytest "$@"
      ' sh "${@:2}"
    ;;
  shell)   exec podman exec -it "$NAME" bash ;;
  reset)
    podman rm -f "$NAME" >/dev/null 2>&1 || true
    rm -rf "$CONFIG"
    echo "wiped $CONFIG"
    ;;
  *) echo "usage: $0 {up|logs|down|restart|sync|shell|reset}" >&2; exit 1 ;;
esac
