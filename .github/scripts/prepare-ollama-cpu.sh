#!/usr/bin/env bash

set -euo pipefail

compose_file="${1:-docker-compose.yml}"
compose=(docker compose -f "$compose_file")

ollama_container="$("${compose[@]}" ps -q ollama)"
if [[ -z "$ollama_container" ]]; then
  echo "ollama-cpu: unable to find the running Ollama container" >&2
  exit 1
fi

host_architecture="$(uname -m)"
container_architecture="$(docker exec "$ollama_container" uname -m)"
cpu_model="$(awk -F ': *' '/^(model name|Model|Hardware)/ { print $2; exit }' /proc/cpuinfo)"
cpu_flags="$(awk -F ': *' '/^flags/ { print $2; exit }' /proc/cpuinfo)"
isa_flags=()

for flag in avx2 avx512f avx512_bf16 amx_tile; do
  if [[ " $cpu_flags " == *" $flag "* ]]; then
    isa_flags+=("$flag")
  fi
done

printf -v isa_summary '%s,' "${isa_flags[@]:-}"
isa_summary="${isa_summary%,}"
echo "ollama-cpu: host_architecture='$host_architecture' container_architecture='$container_architecture'"
echo "ollama-cpu: model='${cpu_model:-unknown}' isa='${isa_summary:-none}'"

log_backends() {
  docker exec "$ollama_container" sh -eu -c '
    found=0
    for lib_dir in /usr/local/lib/ollama /usr/lib/ollama /opt/ollama/lib; do
      [ -d "$lib_dir" ] || continue
      for library in "$lib_dir"/libggml-cpu-*; do
        [ -e "$library" ] || continue
        case "$library" in
          *.disabled) continue ;;
        esac
        found=1
        echo "ollama-cpu:   $library"
      done
    done
    if [ "$found" -eq 0 ]; then
      echo "ollama-cpu:   no libggml-cpu-* backends found"
    fi
  '
}

echo "ollama-cpu: available backends:"
log_backends

case "$container_architecture" in
  x86_64|amd64)
    docker exec --user 0 "$ollama_container" sh -eu -c '
      found=0
      remaining=0
      for lib_dir in /usr/local/lib/ollama /usr/lib/ollama /opt/ollama/lib; do
        [ -d "$lib_dir" ] || continue
        for library in "$lib_dir"/libggml-cpu-*; do
          [ -e "$library" ] || continue
          case "$library" in
            *.disabled) continue ;;
          esac
          found=1
          case "$(basename "$library")" in
            libggml-cpu-skylakex.*|\
            libggml-cpu-cannonlake.*|\
            libggml-cpu-cascadelake.*|\
            libggml-cpu-icelake.*|\
            libggml-cpu-cooperlake.*|\
            libggml-cpu-zen4.*|\
            libggml-cpu-sapphirerapids.*)
              mv "$library" "$library.disabled"
              echo "ollama-cpu: disabled $library"
              ;;
          esac
        done
      done

      if [ "$found" -eq 0 ]; then
        echo "ollama-cpu: no libggml-cpu-* backends found on amd64" >&2
        exit 1
      fi

      for lib_dir in /usr/local/lib/ollama /usr/lib/ollama /opt/ollama/lib; do
        [ -d "$lib_dir" ] || continue
        for library in "$lib_dir"/libggml-cpu-*; do
          [ -e "$library" ] || continue
          case "$library" in
            *.disabled) continue ;;
          esac
          remaining=1
        done
      done

      if [ "$remaining" -eq 0 ]; then
        echo "ollama-cpu: disabling AVX-512/AMX backends left no CPU backend" >&2
        exit 1
      fi
    '
    ;;
  aarch64|arm64)
    echo "ollama-cpu: AVX-512/AMX backend disabling is not needed on $container_architecture"
    ;;
  *)
    echo "ollama-cpu: unsupported container architecture '$container_architecture'" >&2
    exit 1
    ;;
esac

echo "ollama-cpu: remaining backends:"
log_backends

echo "ollama-cpu: restarting Ollama"
"${compose[@]}" restart ollama >/dev/null
ollama_container="$("${compose[@]}" ps -q ollama)"

for _ in $(seq 1 60); do
  container_state="$(docker inspect --format '{{.State.Status}}' "$ollama_container")"
  health_state="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$ollama_container")"

  if [[ "$health_state" == "healthy" || ("$health_state" == "none" && "$container_state" == "running") ]]; then
    echo "ollama-cpu: Ollama is ready"
    exit 0
  fi

  if [[ "$container_state" == "exited" || "$container_state" == "dead" ]]; then
    echo "ollama-cpu: Ollama stopped while waiting for readiness" >&2
    docker logs "$ollama_container" >&2
    exit 1
  fi

  sleep 5
done

echo "ollama-cpu: Ollama did not become healthy after restart" >&2
docker logs "$ollama_container" >&2
exit 1
