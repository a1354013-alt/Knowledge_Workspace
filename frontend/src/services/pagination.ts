import { get } from '../api'
import { t } from '../i18n'

export type PaginatedResponse<T> = {
  items: T[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export function ensurePaginatedResponse<T>(value: unknown, label: string): PaginatedResponse<T> {
  const payload = value as Partial<PaginatedResponse<T>>
  if (
    !payload ||
    typeof payload !== 'object' ||
    !Array.isArray(payload.items) ||
    typeof payload.total !== 'number' ||
    typeof payload.limit !== 'number' ||
    typeof payload.offset !== 'number' ||
    typeof payload.has_more !== 'boolean'
  ) {
    throw new Error(t('common.invalidPayload', { label }))
  }
  return payload as PaginatedResponse<T>
}

export async function fetchAllPages<T>(url: string, label: string, pageSize = 200): Promise<T[]> {
  const items: T[] = []
  let offset = 0
  for (;;) {
    const page = ensurePaginatedResponse<T>(
      await get<PaginatedResponse<T>>(url, { params: { limit: pageSize, offset } }),
      label
    )
    items.push(...page.items)
    if (!page.has_more) {
      return items
    }
    offset += page.items.length
    if (page.items.length === 0 || offset > page.total + page.limit) {
      throw new Error(t('common.invalidPayload', { label }))
    }
  }
}
