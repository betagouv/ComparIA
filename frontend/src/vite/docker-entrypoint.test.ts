import { spawnSync } from 'node:child_process'
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { brotliCompressSync, brotliDecompressSync, gunzipSync, gzipSync } from 'node:zlib'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

// The image is built once with a placeholder as base path; the entrypoint sets
// the Instance path when the container starts. Run on a small build tree that
// has the shapes of the real one: the assets directory named after the base,
// the base with and without its leading slash, precompressed copies.
const ENTRYPOINT = join(import.meta.dirname, '../../docker-entrypoint.sh')
const PLACEHOLDER = '/__INSTANCE_PATH__'

let build: string

function write(path: string, content: string, precompress = false) {
  const file = join(build, path)
  mkdirSync(join(file, '..'), { recursive: true })
  writeFileSync(file, content)
  if (precompress) {
    writeFileSync(`${file}.gz`, gzipSync(content))
    writeFileSync(`${file}.br`, brotliCompressSync(content))
  }
}

function start(instancePath: string | undefined, command = 'true') {
  return spawnSync(ENTRYPOINT, ['sh', '-c', command], {
    env: {
      PATH: process.env.PATH,
      BUILD_DIR: build,
      INSTANCE_PATH_PLACEHOLDER: PLACEHOLDER,
      ...(instancePath === undefined ? {} : { INSTANCE_PATH: instancePath })
    },
    encoding: 'utf8'
  })
}

function allFiles(dir: string): string[] {
  const out = spawnSync('find', [dir, '-type', 'f'], { encoding: 'utf8' }).stdout
  return out.split('\n').filter(Boolean)
}

beforeEach(() => {
  build = mkdtempSync(join(tmpdir(), 'entrypoint-'))
  write('client/__INSTANCE_PATH__/_app/immutable/app.abc123.js', `fetch("${PLACEHOLDER}/x")`, true)
  write('client/__INSTANCE_PATH__/_app/immutable/plain.def456.css', 'a{color:red}', true)
  write('client/__INSTANCE_PATH__/favicon/favicon.svg', '<svg/>')
  write('client/.well-known/security.txt', 'Contact: nobody')
  write('server/chunks/manifest.js', `base: "${PLACEHOLDER}", appPath: "__INSTANCE_PATH__/_app"`)
})
afterEach(() => rmSync(build, { recursive: true, force: true }))

describe('docker entrypoint', () => {
  it('serves the app under the Instance path chosen at start', () => {
    const result = start('/fr')

    expect(result.status).toBe(0)
    expect(readFileSync(join(build, 'client/fr/_app/immutable/app.abc123.js'), 'utf8')).toBe(
      'fetch("/fr/x")'
    )
    expect(existsSync(join(build, 'client/fr/favicon/favicon.svg'))).toBe(true)
    expect(existsSync(join(build, 'client/__INSTANCE_PATH__'))).toBe(false)
    expect(readFileSync(join(build, 'server/chunks/manifest.js'), 'utf8')).toBe(
      'base: "/fr", appPath: "fr/_app"'
    )
  })

  it('leaves no reference to the placeholder, in content or in names', () => {
    start('/fr')

    for (const file of allFiles(build)) {
      expect(file).not.toContain('__INSTANCE_PATH__')
      if (!file.endsWith('.gz') && !file.endsWith('.br'))
        expect(readFileSync(file, 'utf8')).not.toContain('__INSTANCE_PATH__')
    }
  })

  it('does not leave a precompressed copy stale', () => {
    start('/fr')

    const file = join(build, 'client/fr/_app/immutable/app.abc123.js')
    expect(gunzipSync(readFileSync(`${file}.gz`)).toString()).toBe('fetch("/fr/x")')
    expect(brotliDecompressSync(readFileSync(`${file}.br`)).toString()).toBe('fetch("/fr/x")')
  })

  it('does not compress a file that had no precompressed copy', () => {
    start('/fr')

    expect(existsSync(join(build, 'client/fr/favicon/favicon.svg.gz'))).toBe(false)
  })

  it('serves from the root with an empty path, as before', () => {
    const result = start('')

    expect(result.status).toBe(0)
    expect(readFileSync(join(build, 'client/_app/immutable/app.abc123.js'), 'utf8')).toBe(
      'fetch("/x")'
    )
    expect(existsSync(join(build, 'client/favicon/favicon.svg'))).toBe(true)
    expect(existsSync(join(build, 'client/.well-known/security.txt'))).toBe(true)
    expect(readFileSync(join(build, 'server/chunks/manifest.js'), 'utf8')).toBe(
      'base: "", appPath: "_app"'
    )
    const file = join(build, 'client/_app/immutable/app.abc123.js')
    expect(gunzipSync(readFileSync(`${file}.gz`)).toString()).toBe('fetch("/x")')
  })

  it('treats a missing path as an empty one', () => {
    expect(start(undefined).status).toBe(0)
    expect(existsSync(join(build, 'client/_app/immutable/app.abc123.js'))).toBe(true)
  })

  it('accepts a path without leading slash or with a trailing one', () => {
    start('fr/')

    expect(existsSync(join(build, 'client/fr/_app/immutable/app.abc123.js'))).toBe(true)
  })

  it('refuses a path with characters that do not belong in one', () => {
    const result = start('/fr; rm -rf /')

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('not a valid path')
    expect(existsSync(join(build, 'client/__INSTANCE_PATH__'))).toBe(true)
  })

  it('refuses to start a restarted container with another path, instead of serving the old one', () => {
    start('/fr')

    const result = start('/da')

    expect(result.status).not.toBe(0)
    expect(result.stderr).toContain('start a new container')
  })

  it('starts again with the same path', () => {
    start('/fr')

    expect(start('/fr').status).toBe(0)
  })

  it('runs the command it is given', () => {
    expect(start('/fr', 'echo started').stdout).toBe('started\n')
  })
})
