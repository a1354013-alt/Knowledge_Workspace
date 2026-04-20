import { beforeEach, describe, expect, it, vi } from 'vitest'

function installLocalStorageStub() {
  const storage = {
    data: new Map(),
    getItem(key) {
      return this.data.has(key) ? this.data.get(key) : null
    },
    setItem(key, value) {
      this.data.set(key, value)
    },
    removeItem(key) {
      this.data.delete(key)
    },
  }
  globalThis.localStorage = storage
  return storage
}

beforeEach(() => {
  vi.resetModules()
  installLocalStorageStub()
  if (!globalThis.CustomEvent) {
    class SimpleCustomEvent extends Event {
      constructor(type, options = {}) {
        super(type)
        this.detail = options.detail
      }
    }
    globalThis.CustomEvent = SimpleCustomEvent
  }
})

describe('auth token storage', () => {
  it('uses one persistent source', async () => {
    const storage = installLocalStorageStub()
    const auth = await import('../src/auth.js')
    auth.clearToken()
    auth.setToken('abc123')
    expect(auth.getToken()).toBe('abc123')
    expect(storage.getItem(auth.AUTH_STORAGE_KEY)).toBe('abc123')
    auth.clearToken()
    expect(auth.restoreToken()).toBe(null)
  })

  it('unauthorized event notifies listeners once and can be removed', async () => {
    const auth = await import('../src/auth.js')
    let detail = ''
    const cleanup = auth.onUnauthorized((event) => {
      detail = event.detail
    })
    auth.notifyUnauthorized('expired')
    expect(detail).toBe('expired')
    cleanup()
    detail = ''
    auth.notifyUnauthorized('ignored')
    expect(detail).toBe('')
  })
})
