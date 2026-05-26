import { vi } from 'vitest'
import { setConfirmHandler } from '../src/services/confirm'

setConfirmHandler(async () => true)

if (!globalThis.navigator) {
  ;(globalThis as unknown as { navigator: unknown }).navigator = {}
}

if (!globalThis.navigator.clipboard) {
  ;(globalThis.navigator as unknown as { clipboard: unknown }).clipboard = {
    writeText: vi.fn(async (_text: string) => {}),
  } as unknown as Clipboard
}
