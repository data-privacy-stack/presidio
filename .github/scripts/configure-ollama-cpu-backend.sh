#!/usr/bin/env sh

set -eu

case "$(uname -m)" in
  x86_64|amd64) ;;
  *)
    echo "Ollama CPU backend workaround is not needed on $(uname -m)."
    exit 0
    ;;
esac

container_id="$(docker compose ps -q ollama)"
if [ -z "$container_id" ]; then
  echo "Unable to find the running Ollama container." >&2
  exit 1
fi

docker exec "$container_id" sh -eu -c '
  echo "Ollama container CPU model:"
  grep -m1 -E "^model name" /proc/cpuinfo || true
  echo "Ollama container ISA flags:"
  grep -m1 -E "^flags" /proc/cpuinfo | tr " " "\n" | grep -E "^(avx2|avx512f|avx512_bf16|amx_tile)$" || true

  for variant in skylakex cannonlake cascadelake icelake cooperlake zen4 sapphirerapids; do
    for library in /usr/lib/ollama/libggml-cpu-"$variant".*; do
      [ -e "$library" ] || continue
      echo "Disabling unsupported Ollama backend: $library"
      mv "$library" "$library.disabled"
    done
  done

  echo "Remaining Ollama CPU backend libraries:"
  find /usr/lib/ollama -maxdepth 1 -type f -name "libggml-cpu-*" -print | sort
'

echo "Restarting Ollama after disabling AVX-512/AMX backends."
docker restart "$container_id" >/dev/null

for _ in $(seq 1 60); do
  if docker exec "$container_id" ollama list >/dev/null 2>&1; then
    echo "Ollama is ready."
    exit 0
  fi
  sleep 1
done

echo "Ollama did not become ready after its CPU backend restart." >&2
exit 1
