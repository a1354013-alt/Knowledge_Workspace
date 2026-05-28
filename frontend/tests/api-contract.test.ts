import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

import { apiPaths } from '../src/api/endpoints'

type ApiBranchValue = string | ((...args: string[]) => string) | ApiTree
interface ApiTree {
  [key: string]: ApiBranchValue
}

const testDir = path.dirname(fileURLToPath(import.meta.url))
const openapiPath = path.resolve(testDir, '../../docs/openapi.json')
const openapi = JSON.parse(fs.readFileSync(openapiPath, 'utf-8')) as { paths: Record<string, unknown> }
const openapiMatchers = Object.keys(openapi.paths).map((route) => ({
  route,
  pattern: new RegExp(`^${route.replace(/\{[^/]+\}/g, '[^/]+')}$`),
}))

function collectApiRoutes(tree: ApiTree): string[] {
  return Object.values(tree).flatMap((value) => {
    if (typeof value === 'string') {
      return [value]
    }
    if (typeof value === 'function') {
      const args = Array.from({ length: value.length }, (_, index) => `fixture-${index}`)
      return [value(...args)]
    }
    return collectApiRoutes(value)
  })
}

describe('frontend API contract', () => {
  it('maps every frontend API helper route to an OpenAPI path', () => {
    const routes = collectApiRoutes(apiPaths as ApiTree)
    for (const route of routes) {
      expect(openapiMatchers.some((entry) => entry.pattern.test(route)), `missing OpenAPI route for ${route}`).toBe(true)
    }
  })
})
