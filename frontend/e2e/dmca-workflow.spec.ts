/**
 * End-to-end tests for DMCA takedown workflow
 * Tests the complete process from content detection to takedown submission
 */

import { test, expect } from '@playwright/test'
import path from 'path'

test.describe('DMCA Takedown Workflow', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login')
    await page.getByLabel(/email/i).fill('test@example.com')
    await page.getByLabel(/password/i).fill('TestPassword123!')
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL('/dashboard')
  })

  test.describe('Profile Management', () => {
    test('should create a new creator profile', async ({ page }) => {
      await page.goto('/profiles')
      await page.getByRole('button', { name: /create.*profile/i }).click()
      
      // Fill profile form
      await page.getByLabel(/stage name/i).fill('TestCreator2024')
      await page.getByLabel(/real name/i).fill('Test Creator')
      await page.getByLabel(/bio/i).fill('Professional content creator specializing in digital art')
      
      // Add social media accounts
      await page.getByLabel(/instagram/i).fill('@testcreator2024')
      await page.getByLabel(/twitter/i).fill('@testcreator2024')
      await page.getByLabel(/onlyfans/i).fill('testcreator2024')
      
      // Enable monitoring
      await page.getByRole('checkbox', { name: /enable.*monitoring/i }).check()
      
      await page.getByRole('button', { name: /create profile/i }).click()
      
      // Verify profile creation
      await expect(page.getByText(/profile created successfully/i)).toBeVisible()
      await expect(page.getByText('TestCreator2024')).toBeVisible()
    })

    test('should upload reference content for AI matching', async ({ page }) => {
      await page.goto('/profiles')
      
      // Assume we have an existing profile
      await page.getByRole('button', { name: /view.*profile/i }).first().click()
      await page.getByRole('tab', { name: /reference content/i }).click()
      
      // Upload reference image
      const fileInput = page.locator('input[type="file"]')
      await fileInput.setInputFiles(path.join(__dirname, 'fixtures', 'reference-image.jpg'))
      
      await page.getByLabel(/content title/i).fill('Original Artwork #1')
      await page.getByLabel(/description/i).fill('My original digital artwork created in 2024')
      await page.getByRole('button', { name: /upload content/i }).click()
      
      await expect(page.getByText(/content uploaded successfully/i)).toBeVisible()
      await expect(page.getByText('Original Artwork #1')).toBeVisible()
    })

    test('should configure monitoring settings', async ({ page }) => {
      await page.goto('/profiles')
      
      await page.getByRole('button', { name: /edit.*profile/i }).first().click()
      await page.getByRole('tab', { name: /monitoring/i }).click()
      
      // Configure monitoring settings
      await page.getByRole('checkbox', { name: /instagram monitoring/i }).check()
      await page.getByRole('checkbox', { name: /twitter monitoring/i }).check()
      await page.getByRole('checkbox', { name: /reddit monitoring/i }).check()
      
      // Set monitoring keywords
      await page.getByLabel(/keywords/i).fill('testcreator, digital art, leaked, free')
      
      // Set monitoring frequency
      await page.getByRole('combobox', { name: /frequency/i }).selectOption('daily')
      
      await page.getByRole('button', { name: /save settings/i }).click()
      
      await expect(page.getByText(/settings saved successfully/i)).toBeVisible()
    })
  })

  test.describe('Infringement Detection', () => {
    test('should detect and display infringements', async ({ page }) => {
      await page.goto('/infringements')
      
      // Should show infringements list
      await expect(page.getByText(/infringements detected/i)).toBeVisible()
      
      // Check for infringement cards
      const infringementCards = page.locator('[data-testid="infringement-card"]')
      await expect(infringementCards).toHaveCount({ min: 1 })
      
      // Verify infringement details
      const firstCard = infringementCards.first()
      await expect(firstCard.getByText(/confidence.*score/i)).toBeVisible()
      await expect(firstCard.getByRole('button', { name: /view details/i })).toBeVisible()
      await expect(firstCard.getByRole('button', { name: /create takedown/i })).toBeVisible()
    })

    test('should filter infringements by platform', async ({ page }) => {
      await page.goto('/infringements')
      
      // Filter by Instagram
      await page.getByRole('combobox', { name: /platform/i }).selectOption('instagram')
      
      await expect(page.getByText('Instagram')).toBeVisible()
      
      // Should only show Instagram infringements
      const platformBadges = page.locator('[data-testid="platform-badge"]')
      const count = await platformBadges.count()
      
      for (let i = 0; i < count; i++) {
        await expect(platformBadges.nth(i)).toHaveText('Instagram')
      }
    })

    test('should sort infringements by confidence score', async ({ page }) => {
      await page.goto('/infringements')
      
      await page.getByRole('combobox', { name: /sort by/i }).selectOption('confidence_desc')
      
      // Verify sorting - confidence scores should be in descending order
      const confidenceElements = page.locator('[data-testid="confidence-score"]')
      const count = await confidenceElements.count()
      
      if (count > 1) {
        const firstScore = parseFloat(await confidenceElements.first().textContent() || '0')
        const lastScore = parseFloat(await confidenceElements.last().textContent() || '0')
        expect(firstScore).toBeGreaterThanOrEqual(lastScore)
      }
    })

    test('should view detailed infringement analysis', async ({ page }) => {
      await page.goto('/infringements')
      
      await page.getByRole('button', { name: /view details/i }).first().click()
      
      // Should show detailed analysis modal
      await expect(page.getByText(/infringement analysis/i)).toBeVisible()
      await expect(page.getByText(/ai analysis results/i)).toBeVisible()
      await expect(page.getByText(/similarity score/i)).toBeVisible()
      await expect(page.getByText(/detected features/i)).toBeVisible()
      
      // Should show action buttons
      await expect(page.getByRole('button', { name: /create takedown/i })).toBeVisible()
      await expect(page.getByRole('button', { name: /mark as false positive/i })).toBeVisible()
    })
  })

  test.describe('Takedown Request Creation', () => {
    test('should create takedown from infringement', async ({ page }) => {
      await page.goto('/infringements')
      
      // Create takedown from first infringement
      await page.getByRole('button', { name: /create takedown/i }).first().click()
      
      // Verify pre-filled information
      await expect(page.getByLabel(/infringing url/i)).toHaveValue(/https?:\/\//)
      await expect(page.getByLabel(/profile/i)).toHaveValue(/testcreator/i)
      
      // Fill additional details
      await page.getByLabel(/original work title/i).fill('My Original Digital Artwork')
      await page.getByLabel(/infringement description/i).fill('Unauthorized distribution of my copyrighted digital artwork without permission')
      
      // Contact information
      await page.getByLabel(/contact name/i).fill('Test Creator')
      await page.getByLabel(/contact email/i).fill('creator@example.com')
      await page.getByLabel(/contact address/i).fill('123 Creator St, Art City, AC 12345')
      
      // Legal declarations
      await page.getByRole('checkbox', { name: /good faith statement/i }).check()
      await page.getByRole('checkbox', { name: /accuracy statement/i }).check()
      
      // Digital signature
      await page.getByLabel(/signature/i).fill('Test Creator')
      
      await page.getByRole('button', { name: /submit takedown/i }).click()
      
      await expect(page.getByText(/takedown request created successfully/i)).toBeVisible()
    })

    test('should create bulk takedown requests', async ({ page }) => {
      await page.goto('/takedowns')
      
      await page.getByRole('button', { name: /bulk takedown/i }).click()
      
      // Select multiple infringements
      await page.getByRole('checkbox', { name: /select all visible/i }).check()
      
      // Fill common information
      await page.getByLabel(/copyright owner/i).fill('Test Creator')
      await page.getByLabel(/contact email/i).fill('creator@example.com')
      
      // Common description template
      await page.getByLabel(/common description/i).fill('Unauthorized distribution of my copyrighted content')
      
      await page.getByRole('button', { name: /create bulk takedowns/i }).click()
      
      await expect(page.getByText(/bulk takedown requests created/i)).toBeVisible()
      await expect(page.getByText(/requests created: \d+/)).toBeVisible()
    })

    test('should validate required fields in takedown form', async ({ page }) => {
      await page.goto('/takedowns/create')
      
      // Try to submit without required fields
      await page.getByRole('button', { name: /submit takedown/i }).click()
      
      // Should show validation errors
      await expect(page.getByText(/infringing url is required/i)).toBeVisible()
      await expect(page.getByText(/original work title is required/i)).toBeVisible()
      await expect(page.getByText(/copyright owner is required/i)).toBeVisible()
    })
  })

  test.describe('Takedown Management', () => {
    test('should view takedown requests list', async ({ page }) => {
      await page.goto('/takedowns')
      
      // Should show takedowns table
      await expect(page.getByText(/takedown requests/i)).toBeVisible()
      
      // Check table headers
      await expect(page.getByText(/url/i)).toBeVisible()
      await expect(page.getByText(/status/i)).toBeVisible()
      await expect(page.getByText(/created/i)).toBeVisible()
      await expect(page.getByText(/actions/i)).toBeVisible()
      
      // Should have action buttons
      await expect(page.getByRole('button', { name: /view/i }).first()).toBeVisible()
      await expect(page.getByRole('button', { name: /process/i }).first()).toBeVisible()
    })

    test('should process a takedown request', async ({ page }) => {
      await page.goto('/takedowns')
      
      // Process first pending takedown
      await page.getByRole('button', { name: /process/i }).first().click()
      
      // Confirm processing
      await expect(page.getByText(/process takedown request/i)).toBeVisible()
      await expect(page.getByText(/hosting provider.*identified/i)).toBeVisible()
      
      await page.getByRole('button', { name: /confirm processing/i }).click()
      
      await expect(page.getByText(/takedown request processed/i)).toBeVisible()
      await expect(page.getByText(/notices sent: \d+/)).toBeVisible()
    })

    test('should track takedown status changes', async ({ page }) => {
      await page.goto('/takedowns')
      
      // View takedown details
      await page.getByRole('button', { name: /view/i }).first().click()
      
      // Should show status timeline
      await expect(page.getByText(/status timeline/i)).toBeVisible()
      await expect(page.getByText(/created/i)).toBeVisible()
      
      // Update status
      await page.getByRole('button', { name: /update status/i }).click()
      await page.getByRole('combobox', { name: /new status/i }).selectOption('successful')
      await page.getByLabel(/notes/i).fill('Content successfully removed by platform')
      
      await page.getByRole('button', { name: /update/i }).click()
      
      await expect(page.getByText(/status updated successfully/i)).toBeVisible()
      await expect(page.getByText(/successful/i)).toBeVisible()
    })

    test('should export takedown data', async ({ page }) => {
      await page.goto('/takedowns')
      
      // Setup download promise before clicking
      const downloadPromise = page.waitForEvent('download')
      
      await page.getByRole('button', { name: /export/i }).click()
      await page.getByRole('menuitem', { name: /export to csv/i }).click()
      
      // Wait for download
      const download = await downloadPromise
      expect(download.suggestedFilename()).toMatch(/takedowns.*\.csv/)
    })
  })

  test.describe('Analytics and Reporting', () => {
    test('should display takedown statistics', async ({ page }) => {
      await page.goto('/dashboard')
      
      // Should show statistics cards
      await expect(page.getByText(/total takedowns/i)).toBeVisible()
      await expect(page.getByText(/success rate/i)).toBeVisible()
      await expect(page.getByText(/pending requests/i)).toBeVisible()
      await expect(page.getByText(/this month/i)).toBeVisible()
    })

    test('should show takedown analytics charts', async ({ page }) => {
      await page.goto('/reports')
      
      // Should show various charts
      await expect(page.getByText(/takedown trends/i)).toBeVisible()
      await expect(page.getByText(/platform breakdown/i)).toBeVisible()
      await expect(page.getByText(/success rate over time/i)).toBeVisible()
      
      // Charts should be rendered
      await expect(page.locator('[data-testid="takedown-trends-chart"]')).toBeVisible()
      await expect(page.locator('[data-testid="platform-breakdown-chart"]')).toBeVisible()
    })

    test('should filter analytics by date range', async ({ page }) => {
      await page.goto('/reports')
      
      // Change date range
      await page.getByRole('button', { name: /date range/i }).click()
      await page.getByRole('menuitem', { name: /last 3 months/i }).click()
      
      // Charts should update
      await expect(page.getByText(/last 3 months/i)).toBeVisible()
      
      // Wait for charts to reload
      await page.waitForTimeout(1000)
      await expect(page.locator('[data-testid="takedown-trends-chart"]')).toBeVisible()
    })
  })

  test.describe('Error Handling and Edge Cases', () => {
    test('should handle network errors gracefully', async ({ page }) => {
      // Simulate network error
      await page.route('**/api/v1/takedowns/**', route => route.abort())
      
      await page.goto('/takedowns')
      
      // Should show error message
      await expect(page.getByText(/unable to load takedowns/i)).toBeVisible()
      await expect(page.getByRole('button', { name: /retry/i })).toBeVisible()
    })

    test('should handle invalid URLs in takedown form', async ({ page }) => {
      await page.goto('/takedowns/create')
      
      await page.getByLabel(/infringing url/i).fill('not-a-valid-url')
      await page.getByRole('button', { name: /submit takedown/i }).click()
      
      await expect(page.getByText(/please enter a valid url/i)).toBeVisible()
    })

    test('should handle file upload errors', async ({ page }) => {
      await page.goto('/profiles')
      await page.getByRole('button', { name: /create.*profile/i }).click()
      
      // Try to upload invalid file type
      const fileInput = page.locator('input[type="file"]')
      await fileInput.setInputFiles(path.join(__dirname, 'fixtures', 'invalid-file.txt'))
      
      await expect(page.getByText(/only image files are allowed/i)).toBeVisible()
    })
  })
})