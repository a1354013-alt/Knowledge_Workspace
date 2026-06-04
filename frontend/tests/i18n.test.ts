import { describe, expect, it } from 'vitest'

import { locales, messages, setLocale, t, type Locale } from '../src/i18n'

function flattenKeys(value: unknown, prefix = ''): string[] {
  if (!value || typeof value !== 'object') {
    return []
  }
  return Object.entries(value as Record<string, unknown>).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key
    return typeof child === 'string' ? [path] : flattenKeys(child, path)
  })
}

describe('i18n message catalog', () => {
  it('keeps zh-TW and en key paths in sync', () => {
    const zhKeys = flattenKeys(messages['zh-TW']).sort()
    const enKeys = flattenKeys(messages.en).sort()

    expect(zhKeys).toEqual(enKeys)
  })

  it('contains the common user-visible toast and error keys', () => {
    const requiredKeys = [
      'common.requestFailed',
      'common.previewFailed',
      'common.downloadFailed',
      'common.saveFailed',
      'common.uploadFailed',
      'common.deleteFailed',
      'docsPhotos.noFileSelected',
      'docsPhotos.chooseDocumentToUpload',
      'docsPhotos.chooseImageToUpload',
      'docsPhotos.rebuildNeedsAttention',
      'search.searchFailed',
      'knowledge.questionRequired',
      'knowledge.qaFailed',
      'settings.llmStatusFailed',
      'settings.templateLoadFailed',
      'settings.ocrStatusFailed',
      'settings.indexStatusFailed',
      'settings.indexRebuildFailed',
    ]

    for (const locale of locales) {
      setLocale(locale as Locale)
      for (const key of requiredKeys) {
        expect(t(key), `${locale}:${key}`).not.toBe(key)
      }
    }
  })
})
