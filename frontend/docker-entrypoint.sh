#!/bin/sh
# Fixes the Instance path of the app, then runs the command.
#
# The image is built with a placeholder as the SvelteKit base path
# (INSTANCE_PATH_PLACEHOLDER, see svelte.config.js and Dockerfile.front). The
# path the app is mounted under comes from INSTANCE_PATH, for example "/fr", or
# nothing to serve from the root. The placeholder is replaced by it in the built
# files, and the directory of the static assets, which adapter-node names after
# the base path, is moved there, so the same image serves every Instance.
#
# Files are rewritten in place. File names are left alone: hashed asset names
# stay valid, they are only looked up under the new path. A file that has
# precompressed copies (.gz, .br) gets them made again, never left stale.
set -eu

build_dir=${BUILD_DIR:-/app/build}
placeholder=${INSTANCE_PATH_PLACEHOLDER:-/__INSTANCE_PATH__}

# "/fr/", "fr" and "/fr" are the same path, "/" and "" are none.
path=$(printf '%s' "${INSTANCE_PATH:-}" | sed 's|/*$||')
if [ -n "$path" ]; then
	case "$path" in
	/*) ;;
	*) path="/$path" ;;
	esac
fi
# Segments of the usual URL characters only: the path goes into sed and into
# JavaScript strings of the built files.
case "$path" in
*[!A-Za-z0-9._~/-]* | *//*)
	echo "docker-entrypoint: INSTANCE_PATH '$path' is not a valid path" >&2
	exit 1
	;;
esac

# A restarted container keeps its rewritten files: a different path would find
# no placeholder left, so refuse it instead of serving the old one.
applied="$build_dir/.instance-path"
if [ -f "$applied" ]; then
	if [ "$(cat "$applied")" != "$path" ]; then
		echo "docker-entrypoint: build already set for '$(cat "$applied")', start a new container for '$path'" >&2
		exit 1
	fi
else
	changed=$(mktemp)
	# SvelteKit also keeps the base without its leading slash (appPath), which
	# becomes nothing, not a lone slash, when the path is empty.
	bare=${placeholder#/}
	grep -rlF -- "$bare" "$build_dir" >"$changed" || true
	while IFS= read -r file; do
		sed -i -e "s|$placeholder|$path|g" -e "s|$bare/|${path#/}${path:+/}|g" "$file"
	done <"$changed"

	# adapter-node serves build/client/<base>/..., named after the base path.
	assets="$build_dir/client/${placeholder#/}"
	if [ -d "$assets" ]; then
		if [ -z "$path" ]; then
			cp -a "$assets/." "$build_dir/client/"
			rm -rf "$assets"
		else
			mkdir -p "$(dirname "$build_dir/client$path")"
			mv "$assets" "$build_dir/client$path"
		fi
	fi

	# Same settings as adapter-node's own precompression.
	sed "s|^$build_dir/client/${placeholder#/}|$build_dir/client$path|" "$changed" |
		node --input-type=module -e '
import { readFileSync, writeFileSync, existsSync } from "node:fs"
import { constants, brotliCompressSync, gzipSync } from "node:zlib"
const files = readFileSync(0, "utf8").split("\n").filter(Boolean)
for (const file of files) {
  if (!existsSync(file + ".gz") && !existsSync(file + ".br")) continue
  const data = readFileSync(file)
  writeFileSync(file + ".gz", gzipSync(data, { level: 9 }))
  writeFileSync(
    file + ".br",
    brotliCompressSync(data, { params: { [constants.BROTLI_PARAM_QUALITY]: 11 } })
  )
}
'
	rm -f "$changed"
	printf '%s' "$path" >"$applied"
fi

exec "$@"
