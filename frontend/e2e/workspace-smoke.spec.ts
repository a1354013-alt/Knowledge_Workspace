import { expect, test, type Page } from '@playwright/test'

const emptyListPaths = new Set([
  '/api/autotest/runs',
  '/api/docs',
  '/api/knowledge/entries',
  '/api/logbook/entries',
  '/api/photos',
  '/api/prompts',
])

function makeRows(count: number) {
  return Array.from({ length: count }, (_, index) => {
    const suffix = String(index + 1).padStart(3, '0')
    const timestamp = `2026-06-04T10:${String(index % 60).padStart(2, '0')}:00Z`
    return {
      id: suffix,
      title: `Large dataset item ${suffix}`,
      problem: `Problem ${suffix}`,
      root_cause: `Root cause ${suffix}`,
      solution: `Solution ${suffix}`,
      tags: `bulk, item-${suffix}`,
      status: index % 3 === 0 ? 'verified' : 'reviewed',
      source_type: 'manual',
      source_ref: '',
      related_item_ids: [],
      created_at: timestamp,
      updated_at: timestamp,
      filename: `document-${suffix}.txt`,
      category: 'bulk',
      description: `Photo description ${suffix}`,
      ocr_text: '',
      ocr_status: 'completed',
      uploaded_at: timestamp,
      project_name: `Project ${suffix}`,
      prompt_output: '',
      content: `Prompt body ${suffix}`,
    }
  })
}

async function mockApi(page: Page, options: { large?: boolean } = {}) {
  const rows = options.large ? makeRows(120) : []
  await page.route(/^https?:\/\/[^/]+\/api\//, async (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname

    if (path === '/api/login') {
      await route.fulfill({ json: { access_token: 'smoke-token', token_type: 'bearer' } })
      return
    }
    if (path === '/api/me') {
      await route.fulfill({ json: { user_id: 'owner', role: 'owner', display_name: 'Owner' } })
      return
    }
    if (options.large && path === '/api/docs') {
      await route.fulfill({ json: rows.map((row) => ({ ...row, id: `doc-${row.id}`, index_status: 'indexed' })) })
      return
    }
    if (options.large && path === '/api/photos') {
      await route.fulfill({ json: rows.map((row) => ({ ...row, id: `photo-${row.id}`, filename: `photo-${row.id}.png`, index_status: 'indexed' })) })
      return
    }
    if (options.large && path === '/api/knowledge/entries') {
      await route.fulfill({ json: rows.map((row) => ({ ...row, id: `knowledge-${row.id}` })) })
      return
    }
    if (options.large && path === '/api/logbook/entries') {
      await route.fulfill({ json: rows.map((row) => ({ ...row, id: `logbook-${row.id}` })) })
      return
    }
    if (options.large && path === '/api/prompts') {
      await route.fulfill({ json: rows.map((row) => ({ ...row, id: `prompt-${row.id}` })) })
      return
    }
    if (options.large && path === '/api/autotest/runs') {
      await route.fulfill({
        json: rows.map((row, index) => ({
          id: `run-${row.id}`,
          project_name: row.project_name,
          status: index % 2 === 0 ? 'passed' : 'failed',
          created_at: row.created_at,
        })),
      })
      return
    }
    if (emptyListPaths.has(path)) {
      await route.fulfill({ json: [] })
      return
    }
    if (path === '/api/dashboard/health') {
      await route.fulfill({
        json: {
          knowledge: { total: rows.length, by_status: { draft: 0, reviewed: rows.length, verified: 0, archived: 0 } },
          logbook: { total: rows.length, with_solution: rows.length, promoted_to_knowledge: 0, resolution_rate: rows.length ? 100 : 0 },
          autotest: {
            total_runs: rows.length,
            passed: Math.ceil(rows.length / 2),
            failed: Math.floor(rows.length / 2),
            pass_rate: rows.length ? 50 : 0,
            recent_runs: rows.slice(0, 20).map((row) => ({ id: `run-${row.id}`, project_name: row.project_name, status: 'passed', created_at: row.created_at })),
          },
          documents: { total: rows.length, indexed: rows.length, pending: 0, failed_documents: 0, archived_documents: 0 },
          recent_activity: {
            days: 7,
            documents_added: rows.length,
            knowledge_added: rows.length,
            logbook_added: rows.length,
            autotest_runs: rows.length,
            autotest_passed: Math.ceil(rows.length / 2),
            autotest_failed: Math.floor(rows.length / 2),
          },
        },
      })
      return
    }
    if (path === '/api/autotest/capabilities') {
      await route.fulfill({
        json: {
          mode: 'simulated',
          runner_mode: 'simulated',
          docker_available: false,
          docker_sandbox_available: false,
          docker_sandbox_unavailable_reason: 'not configured',
        },
      })
      return
    }
    if (path === '/api/index/status') {
      await route.fulfill({
        json: {
          provider: {
            configured_provider: 'demo_hash',
            active_provider: 'demo-fallback',
            status: 'degraded',
            index_mode: 'demo_hash_embedding',
            demo_mode: true,
            semantic_search_ready: false,
            message: 'Demo fallback active',
            details: [],
          },
          summary: {
            document: { total: rows.length, pending: 0, indexed: rows.length, failed: 0, unavailable: 0, excluded: 0 },
            knowledge: { total: rows.length, pending: rows.length, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
            logbook: { total: rows.length, pending: rows.length, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
            photo: { total: rows.length, pending: rows.length, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
            prompt: { total: rows.length, pending: rows.length, indexed: 0, failed: 0, unavailable: 0, excluded: 0 },
          },
          failed_items: [],
        },
      })
      return
    }
    if (path === '/api/settings/llm') {
      await route.fulfill({
        json: {
          primary_provider: 'ollama',
          active_provider: 'none',
          model: 'llama3.1',
          base_url: 'http://localhost:11434',
          primary_healthy: false,
          fallback_enabled: true,
          llm_ready_for_generation: false,
          error_message: '',
        },
      })
      return
    }
    if (path === '/api/settings/ocr') {
      await route.fulfill({ json: { enabled: false, available: false, tesseract_cmd: '', tesseract_version: '', details: '' } })
      return
    }
    if (path === '/api/meta/templates') {
      await route.fulfill({ json: { templates: [] } })
      return
    }

    await route.fulfill({ status: 404, json: { detail: `Unhandled smoke route: ${path}` } })
  })
}

async function expectBodyDoesNotScroll(page: Page) {
  const bodyScrolls = await page.evaluate(() => {
    const root = document.scrollingElement
    return root ? root.scrollHeight > root.clientHeight : false
  })
  expect(bodyScrolls).toBe(false)
}

async function login(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.clear()
    window.localStorage.setItem('knowledge-workspace-locale', 'en')
  })
  await page.goto('/')
  await page.locator('#userId').fill('owner')
  await page.locator('#password input').fill('OwnerPass123!')
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page.getByRole('heading', { name: 'Personal AI Knowledge Workspace' })).toBeVisible()
}

async function expectShellFitsViewport(page: Page) {
  await expectBodyDoesNotScroll(page)
  for (const selector of ['.topbar', '.tab-strip', '.tab-panel-shell']) {
    const box = await page.locator(selector).boundingBox()
    expect(box, selector).not.toBeNull()
    expect(box!.y).toBeGreaterThanOrEqual(0)
    expect(box!.y + box!.height).toBeLessThanOrEqual(page.viewportSize()!.height + 1)
  }
}

async function expectMainContentCanScroll(page: Page) {
  const canScroll = await page.evaluate(() =>
    ['.main-grid', '.tab-panel-shell', '.page-content', '.p-datatable-wrapper'].some((selector) => {
      const element = document.querySelector(selector)
      return element ? element.scrollHeight > element.clientHeight : false
    })
  )
  expect(canScroll).toBe(true)
}

test('login, navigate, refresh, switch locale, reload, and logout', async ({ page }) => {
  await mockApi(page)
  await login(page)

  await expect(page.getByText('Owner: Owner')).toBeVisible()
  await expectBodyDoesNotScroll(page)

  await page.getByRole('button', { name: 'Documents & Photos' }).click()
  await expect(page.getByText('Documents', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Refresh' }).first().click()
  await expectBodyDoesNotScroll(page)

  await page.getByLabel('Language').selectOption('zh-TW')
  await page.getByLabel('語言').selectOption('en')
  await expect(page.getByRole('button', { name: 'Documents & Photos' })).toBeVisible()

  for (const tab of ['Health', 'Activity', 'Search', 'Knowledge Base', 'Problem Logbook', 'Documents & Photos', 'Auto Test', 'Prompts', 'Settings']) {
    await page.getByRole('button', { name: tab }).click()
    if (tab === 'Auto Test') {
      await expect(page.getByText('Safe simulation mode is active').first()).toBeVisible()
    }
    await expectBodyDoesNotScroll(page)
  }

  await page.reload()
  await expect(page.getByText('Personal AI Knowledge Workspace').first()).toBeVisible()

  await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
})

for (const viewport of [
  { width: 1366, height: 768 },
  { width: 1920, height: 1080 },
  { width: 1280, height: 720 },
]) {
  test(`large datasets stay inside the app shell at ${viewport.width}x${viewport.height}`, async ({ page }) => {
    await page.setViewportSize(viewport)
    await mockApi(page, { large: true })
    await login(page)
    await expectShellFitsViewport(page)

    for (const tab of ['Activity', 'Knowledge Base', 'Problem Logbook', 'Documents & Photos', 'Auto Test']) {
      await page.getByRole('button', { name: tab }).click()
      await expectShellFitsViewport(page)
      await expectMainContentCanScroll(page)
      await expect(page.locator('.p-datatable').first()).toBeVisible()
    }
  })
}
