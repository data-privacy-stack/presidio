#!/usr/bin/env bash
set -euo pipefail

compose_file="${COMPOSE_FILE:-docker-compose.yml}"
model="${OLLAMA_MODEL:-qwen2.5:1.5b}"
container_id="$(docker compose -f "$compose_file" ps -q ollama)"

if [[ -z "$container_id" ]]; then
  echo "ollama-ci: Ollama container is not running" >&2
  exit 1
fi

architecture="$(docker exec "$container_id" uname -m)"
cpu_model="$(
  docker exec "$container_id" sh -c \
    "sed -n 's/^model name[[:space:]]*: *//p' /proc/cpuinfo | head -n 1"
)"
cpu_flags="$(
  docker exec "$container_id" sh -c \
    "sed -n 's/^flags[[:space:]]*: *//p' /proc/cpuinfo | head -n 1"
)"
cpu_isa=""
for flag in avx2 avx512f avx512_bf16 amx_tile; do
  if [[ " $cpu_flags " == *" $flag "* ]]; then
    cpu_isa="${cpu_isa}${cpu_isa:+,}${flag}"
  fi
done
echo "ollama-ci: architecture='$architecture' model='${cpu_model:-unknown}' isa='${cpu_isa:-none}'"

lib_dir="$(
  docker exec "$container_id" sh -eu -c '
    for dir in /usr/lib/ollama /usr/local/lib/ollama /opt/ollama/lib; do
      set -- "$dir"/libggml-cpu-*
      if [ -e "$1" ]; then
        printf "%s\n" "$dir"
        exit 0
      fi
    done
  '
)"

case "$architecture" in
  x86_64 | amd64)
    if [[ -z "$lib_dir" ]]; then
      echo "ollama-ci: no libggml CPU backends found" >&2
      exit 1
    fi

    docker exec -i "$container_id" sh -eu -s -- "$lib_dir" <<'EOF'
lib_dir="$1"
variants="skylakex cannonlake cascadelake icelake cooperlake zen4 sapphirerapids"

for variant in $variants; do
  for build in "$lib_dir"/libggml-cpu-"$variant".*; do
    [ -e "$build" ] || continue
    case "$build" in
      *.disabled) continue ;;
    esac
    mv "$build" "${build}.disabled"
    echo "ollama-ci: disabled $(basename "$build")"
  done
done
EOF

    docker restart "$container_id" >/dev/null
    ;;
  aarch64 | arm64)
    echo "ollama-ci: AVX backend hardening is not applicable on arm64"
    ;;
  *)
    echo "ollama-ci: unsupported architecture '$architecture'" >&2
    exit 1
    ;;
esac

if [[ -n "$lib_dir" ]]; then
  docker exec "$container_id" sh -eu -c '
    lib_dir="$1"
    echo "ollama-ci: remaining CPU backends:"
    for build in "$lib_dir"/libggml-cpu-*; do
      [ -e "$build" ] || continue
      case "$build" in
        *.disabled) continue ;;
      esac
      echo "ollama-ci:   $(basename "$build")"
    done
  ' sh "$lib_dir"
fi

for _ in $(seq 1 30); do
  if docker exec "$container_id" ollama list >/dev/null 2>&1; then
    docker exec "$container_id" ollama pull "$model"
    docker exec "$container_id" ollama run "$model"
    exit 0
  fi
  sleep 2
done

echo "ollama-ci: Ollama did not become ready after 60 seconds" >&2
docker logs "$container_id" >&2
exit 1
