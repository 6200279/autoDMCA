/**
 * Global teardown for Playwright E2E tests
 * Cleans up test environment and resources
 */

import { FullConfig } from '@playwright/test'
import { chromium } from '@playwright/test'
import fs from 'fs'
import path from 'path'

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting E2E test teardown...')

  const browser = await chromium.launch()
  const page = await browser.newPage()

  try {
    // Clean up test database
    console.log('🗄️ Cleaning up test database...')
    try {
      await page.request.post('http://localhost:8000/api/v1/test/cleanup-database')
      console.log('✅ Test database cleaned up')
    } catch (error) {
      console.warn('⚠️ Could not clean up test database:', error)
    }

    // Clean up temporary files
    console.log('🗂️ Cleaning up temporary files...')
    try {
      const tempFiles = [
        'e2e/auth-state.json',
        'test-results/storage-state.json'
      ]

      for (const file of tempFiles) {
        if (fs.existsSync(file)) {
          fs.unlinkSync(file)
        }
      }

      console.log('✅ Temporary files cleaned up')
    } catch (error) {
      console.warn('⚠️ Could not clean up temporary files:', error)
    }

    // Clean up uploaded test files
    console.log('📁 Cleaning up uploaded test files...')
    try {
      await page.request.post('http://localhost:8000/api/v1/test/cleanup-uploads')
      console.log('✅ Test uploads cleaned up')
    } catch (error) {
      console.warn('⚠️ Could not clean up test uploads:', error)
    }

    console.log('🎉 E2E test teardown completed successfully!')

  } catch (error) {
    console.error('❌ E2E test teardown failed:', error)
  } finally {
    await browser.close()
  }
}

export default globalTeardown