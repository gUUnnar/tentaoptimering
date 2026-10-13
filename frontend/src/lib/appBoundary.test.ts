import assert from "node:assert/strict"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join, relative, sep } from "node:path"
import { describe, it } from "node:test"
import { fileURLToPath } from "node:url"

const SRC = fileURLToPath(new URL("..", import.meta.url))

function sourceFiles(directory: string): string[] {
  return readdirSync(directory).flatMap(name => {
    const path = join(directory, name)
    return statSync(path).isDirectory() ? sourceFiles(path) : /\.(ts|tsx)$/.test(name) ? [path] : []
  })
}

const appFiles = sourceFiles(SRC).filter(path => !relative(SRC, path).split(sep).includes("testing") && !/\.test\.ts$/.test(path))

describe("testdata hör inte hemma i appen", () => {
  it("appkod importerar aldrig något under lib/testing", () => {
    assert.ok(appFiles.length > 10)
    const offenders = appFiles.filter(path => /from\s+["'][^"']*\/testing\//.test(readFileSync(path, "utf8")))
    assert.deepEqual(offenders.map(path => relative(SRC, path)), [])
  })
  it("det finns ingen mockväxel eller något mockläge kvar i appkoden", () => {
    const offenders = appFiles.filter(path => /isMockRequested|loadJointApi|jointMock|mock=1|mockläge/i.test(readFileSync(path, "utf8")))
    assert.deepEqual(offenders.map(path => relative(SRC, path)), [])
  })
})

describe("inga rester av den borttagna motorn", () => {
  const removedRoutes = /\/api\/(parameters|scenarios|simulations|runs\/compare)|["'`]\/api\/runs["'`]|\/api\/runs\/\$\{[^}]*\}(?!\/(events|warm-start)\b)/
  it("appkoden anropar inga borttagna API-rutter", () => {
    const offenders = appFiles.filter(path => removedRoutes.test(readFileSync(path, "utf8")))
    assert.deepEqual(offenders.map(path => relative(SRC, path)), [])
  })
  it("gränssnittet nämner ingen äldre motor", () => {
    const offenders = appFiles.filter(path => /äldre motor|legacy-nav/i.test(readFileSync(path, "utf8")))
    assert.deepEqual(offenders.map(path => relative(SRC, path)), [])
  })
})
