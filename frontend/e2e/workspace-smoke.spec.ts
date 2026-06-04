import { expect, test, type Page } from '@playwright/test'

const emptyListPaths = new Set([
  '/api/autotest/runs',
  '/api/docs',
  '/api/knowledge/entries',
  '/api/logbook/entries',
  '/api/photos',
  '/api/prompts',
])

async function mockApi(page: Page) {
  await page.route('http://localhost:8000/api/**', async (route) => {
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
    if (emptyListPaths.has(path)) {
      await route.fulfill({ json: [] })
      return
    }
    if (path === '/api/dashboard/health') {
      await route.fulfill({
        json: {
          knowledge: { total: 0, by_status: { draft: 0, reviewed: 0, verified: 0, archived: 0 } },
          logbook: { total: 0, with_solution: 0, promoted_to_knowledge: 0, resolution_rate: 0 },
          autotest: { total_runs: 0, passed: 0, failed: 0, pass_rate: 0, recent_runs: [] },
          documents: { total: 0, indexed: 0, pending: 0, failed_documents: 0, archived_documents: 0 },
          recent_activity: {
            days: 7,
            documents_added: 0,
            knowledge_added: 0,
            logbook_added: 0,
            autotest_runs: 0,
            autotest_passed: 0,
            autotest_failed: 0,
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

    await route.fulfill({ status: 404, json: { detail: `Unhandled smoke route: ${path}` } })
  })
}

test('login, navigate, refresh, switch locale, reload, and logout', async ({ page }) => {
  await mockApi(page)
  await page.goto('/')

  await expect(page.getByText('工程師的個人 AI 知識工作區')).toBeVisible()
  await page.locator('#userId').fill('owner')
  await page.locator('#password input').fill('OwnerPass123!')
  await page.getByRole('button', { name: '登入' }).click()

  await expect(page.getByRole('heading', { name: '個人 AI 知識工作區' })).toBeVisible()
  await expect(page.getByText('擁有者: Owner')).toBeVisible()

  await page.getByRole('button', { name: '文件與照片' }).click()
  await expect(page.getByText('Documents')).toBeVisible()
  await page.getByRole('button', { name: /Refresh|重新整理/ }).first().click()

  await page.getByLabel('語言').selectOption('en')
  await expect(page.getByRole('button', { name: 'Documents & Photos' })).toBeVisible()
  await page.getByRole('button', { name: 'Auto Test' }).click()
  await expect(page.getByText('Safe simulation mode is active').first()).toBeVisible()

  const bodyScrolls = await page.evaluate(() => {
    const root = document.scrollingElement
    return root ? root.scrollHeight > root.clientHeight : false
  })
  expect(bodyScrolls).toBe(false)

  await page.reload()
  await expect(page.getByRole('heading', { name: 'Personal AI Knowledge Workspace' })).toBeVisible()

  await page.getByRole('button', { name: 'Logout' }).click()
  await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible()
})
