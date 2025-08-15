import { test, expect, Page } from '@playwright/test'

// Test data
const testUser = {
  email: 'monitoring-test@example.com',
  password: 'TestPassword123!',
}

const testProfile = {
  stageName: 'Monitoring Test Creator',
  keywords: ['test creator', 'content monitoring', 'automation'],
}

test.describe('Content Monitoring Workflows', () => {
  test.beforeEach(async ({ page }) => {
    // Login and setup test profile
    await loginUser(page, testUser.email, testUser.password)
    await ensureTestProfile(page, testProfile)
  })

  test('start comprehensive content monitoring scan', async ({ page }) => {
    await page.goto('/scanning')

    // Verify scan configuration page
    await expect(page.getByRole('heading', { name: /start new scan/i })).toBeVisible()

    // Select profile to monitor
    await page.getByRole('combobox', { name: /select profile/i }).click()
    await page.getByRole('option', { name: testProfile.stageName }).click()

    // Configure scan types
    await page.getByRole('checkbox', { name: /web search/i }).check()
    await page.getByRole('checkbox', { name: /image search/i }).check()
    await page.getByRole('checkbox', { name: /social media/i }).check()
    await page.getByRole('checkbox', { name: /deep web/i }).check()

    // Set scan parameters
    await page.getByRole('combobox', { name: /scan depth/i }).click()
    await page.getByRole('option', { name: /comprehensive/i }).click()

    await page.getByRole('combobox', { name: /priority/i }).click()
    await page.getByRole('option', { name: /high/i }).click()

    // Add custom search terms
    await page.getByLabel(/additional keywords/i).fill('stolen content, unauthorized use')

    // Start scan
    await page.getByRole('button', { name: /start scan/i }).click()

    // Verify scan started
    await expect(page.getByText(/scan initiated successfully/i)).toBeVisible()
    await expect(page).toHaveURL(/\/scanning\/jobs\/.*/)

    // Check scan progress
    await expect(page.getByRole('progressbar')).toBeVisible()
    await expect(page.getByText(/estimated time remaining/i)).toBeVisible()

    // Should show scan phases
    await expect(page.getByText(/web search/i)).toBeVisible()
    await expect(page.getByText(/image analysis/i)).toBeVisible()
    await expect(page.getByText(/social media scan/i)).toBeVisible()

    // Wait for some progress (in real tests, this would be mocked)
    await page.waitForTimeout(3000)

    // Check for live updates
    const progressBar = page.getByRole('progressbar')
    const initialProgress = await progressBar.getAttribute('aria-valuenow')
    
    await page.waitForTimeout(2000)
    
    const updatedProgress = await progressBar.getAttribute('aria-valuenow')
    expect(parseInt(updatedProgress || '0')).toBeGreaterThan(parseInt(initialProgress || '0'))
  })

  test('view and analyze scan results', async ({ page }) => {
    // Start from completed scan (simulate)
    await page.goto('/scanning/results/mock-completed-scan')

    // Verify results page structure
    await expect(page.getByRole('heading', { name: /scan results/i })).toBeVisible()
    await expect(page.getByText(/scan completed/i)).toBeVisible()

    // Check summary statistics
    await expect(page.getByText(/total urls scanned/i)).toBeVisible()
    await expect(page.getByText(/potential infringements/i)).toBeVisible()
    await expect(page.getByText(/high confidence matches/i)).toBeVisible()

    // Filter results by confidence
    await page.getByRole('combobox', { name: /filter by confidence/i }).click()
    await page.getByRole('option', { name: /high confidence/i }).click()

    // Should update results list
    await expect(page.getByTestId('results-list')).toBeVisible()

    // Check individual result details
    const firstResult = page.getByTestId('result-item').first()
    await expect(firstResult.getByText(/confidence:/i)).toBeVisible()
    await expect(firstResult.getByText(/platform:/i)).toBeVisible()
    await expect(firstResult.getByText(/match type:/i)).toBeVisible()

    // Expand result for details
    await firstResult.getByRole('button', { name: /view details/i }).click()

    // Should show detailed analysis
    await expect(page.getByText(/similarity analysis/i)).toBeVisible()
    await expect(page.getByText(/facial recognition/i)).toBeVisible()
    await expect(page.getByText(/image hash comparison/i)).toBeVisible()

    // Check evidence display
    await expect(page.getByText(/original content/i)).toBeVisible()
    await expect(page.getByText(/detected content/i)).toBeVisible()

    // Verify action buttons
    await expect(page.getByRole('button', { name: /send takedown/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /mark as false positive/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /add to monitoring/i })).toBeVisible()
  })

  test('configure automated monitoring schedule', async ({ page }) => {
    await page.goto('/profiles')

    // Select profile to configure
    const profileRow = page.getByRole('row').filter({ hasText: testProfile.stageName })
    await profileRow.getByRole('button', { name: /settings/i }).click()

    // Navigate to monitoring settings
    await page.getByRole('tab', { name: /monitoring/i }).click()

    // Enable automated monitoring
    await page.getByRole('checkbox', { name: /enable automated monitoring/i }).check()

    // Configure scan frequency
    await page.getByRole('combobox', { name: /scan frequency/i }).click()
    await page.getByRole('option', { name: /daily/i }).click()

    // Set scan time
    await page.getByLabel(/scan time/i).fill('02:00')

    // Configure scan types for automation
    await page.getByRole('checkbox', { name: /web search/i }).check()
    await page.getByRole('checkbox', { name: /social media/i }).check()
    await page.getByRole('checkbox', { name: /image search/i }).check()

    // Set thresholds
    await page.getByLabel(/confidence threshold/i).fill('0.8')
    await page.getByLabel(/max results per scan/i).fill('100')

    // Configure notifications
    await page.getByRole('checkbox', { name: /email notifications/i }).check()
    await page.getByRole('checkbox', { name: /high priority alerts/i }).check()

    // Save configuration
    await page.getByRole('button', { name: /save monitoring settings/i }).click()

    // Verify settings saved
    await expect(page.getByText(/monitoring settings updated/i)).toBeVisible()

    // Check schedule display
    await expect(page.getByText(/next scan: tomorrow at 2:00 am/i)).toBeVisible()
  })

  test('handle infringement detection workflow', async ({ page }) => {
    // Start from a detected infringement
    await page.goto('/infringements')

    // Should show infringements list
    await expect(page.getByRole('heading', { name: /detected infringements/i })).toBeVisible()

    // Filter to show new detections
    await page.getByRole('combobox', { name: /status filter/i }).click()
    await page.getByRole('option', { name: /new/i }).click()

    // Select first infringement
    const firstInfringement = page.getByTestId('infringement-item').first()
    await firstInfringement.click()

    // Should show detailed view
    await expect(page.getByText(/infringement details/i)).toBeVisible()
    await expect(page.getByText(/confidence score/i)).toBeVisible()
    await expect(page.getByText(/detection method/i)).toBeVisible()

    // Review evidence
    await expect(page.getByText(/original content/i)).toBeVisible()
    await expect(page.getByText(/infringing content/i)).toBeVisible()

    // Decision options
    await expect(page.getByRole('button', { name: /confirm infringement/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /false positive/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /needs review/i })).toBeVisible()

    // Confirm as legitimate infringement
    await page.getByRole('button', { name: /confirm infringement/i }).click()

    // Should prompt for next action
    await expect(page.getByText(/infringement confirmed/i)).toBeVisible()
    await expect(page.getByRole('button', { name: /send takedown notice/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /add to report/i })).toBeVisible()

    // Proceed with takedown
    await page.getByRole('button', { name: /send takedown notice/i }).click()

    // Should navigate to takedown form
    await expect(page).toHaveURL(/\/takedowns\/create/)
    await expect(page.getByText(/dmca takedown notice/i)).toBeVisible()

    // Form should be pre-populated with infringement data
    await expect(page.getByLabel(/infringing url/i)).not.toHaveValue('')
    await expect(page.getByLabel(/description/i)).not.toHaveValue('')
  })

  test('manage monitoring alerts and notifications', async ({ page }) => {
    await page.goto('/dashboard')

    // Check for monitoring alerts
    const alertsSection = page.getByTestId('monitoring-alerts')
    await expect(alertsSection).toBeVisible()

    // Should show recent alerts
    await expect(alertsSection.getByText(/new infringement detected/i)).toBeVisible()
    await expect(alertsSection.getByText(/scan completed/i)).toBeVisible()

    // Click on alert to view details
    await alertsSection.getByText(/new infringement detected/i).click()

    // Should navigate to infringement details
    await expect(page).toHaveURL(/\/infringements\/.*/)

    // Go to notifications settings
    await page.goto('/settings/notifications')

    // Configure alert preferences
    await page.getByRole('checkbox', { name: /email alerts/i }).check()
    await page.getByRole('checkbox', { name: /browser notifications/i }).check()
    await page.getByRole('checkbox', { name: /sms alerts/i }).check()

    // Set alert thresholds
    await page.getByLabel(/minimum confidence for alerts/i).fill('0.9')
    await page.getByRole('checkbox', { name: /only high priority/i }).check()

    // Configure alert frequency
    await page.getByRole('combobox', { name: /alert frequency/i }).click()
    await page.getByRole('option', { name: /immediate/i }).click()

    // Save settings
    await page.getByRole('button', { name: /save notification settings/i }).click()

    // Verify settings saved
    await expect(page.getByText(/notification settings updated/i)).toBeVisible()
  })

  test('analyze monitoring performance and statistics', async ({ page }) => {
    await page.goto('/analytics/monitoring')

    // Verify analytics dashboard
    await expect(page.getByRole('heading', { name: /monitoring analytics/i })).toBeVisible()

    // Check key metrics
    await expect(page.getByText(/total scans completed/i)).toBeVisible()
    await expect(page.getByText(/infringements detected/i)).toBeVisible()
    await expect(page.getByText(/false positive rate/i)).toBeVisible()
    await expect(page.getByText(/average detection time/i)).toBeVisible()

    // Time period selector
    await page.getByRole('combobox', { name: /time period/i }).click()
    await page.getByRole('option', { name: /last 30 days/i }).click()

    // Should update charts
    await expect(page.getByTestId('detection-timeline-chart')).toBeVisible()
    await expect(page.getByTestId('platform-distribution-chart')).toBeVisible()
    await expect(page.getByTestId('confidence-score-chart')).toBeVisible()

    // Export analytics data
    await page.getByRole('button', { name: /export data/i }).click()

    // Should trigger download
    const downloadPromise = page.waitForEvent('download')
    await page.getByRole('button', { name: /download csv/i }).click()
    const download = await downloadPromise
    expect(download.suggestedFilename()).toMatch(/monitoring-analytics.*\.csv/)
  })

  test('handle monitoring errors and recovery', async ({ page }) => {
    // Simulate monitoring error scenario
    await page.goto('/scanning')

    // Start scan that will fail
    await page.getByRole('combobox', { name: /select profile/i }).click()
    await page.getByRole('option', { name: testProfile.stageName }).click()
    await page.getByRole('checkbox', { name: /web search/i }).check()
    await page.getByRole('button', { name: /start scan/i }).click()

    // Mock scan failure
    await page.route('**/api/v1/scanning/**', route => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Scanning service temporarily unavailable' })
      })
    })

    // Should show error state
    await expect(page.getByText(/scan failed/i)).toBeVisible()
    await expect(page.getByText(/scanning service temporarily unavailable/i)).toBeVisible()

    // Error recovery options
    await expect(page.getByRole('button', { name: /retry scan/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /contact support/i })).toBeVisible()

    // Retry the scan
    await page.getByRole('button', { name: /retry scan/i }).click()

    // Should attempt to restart
    await expect(page.getByText(/retrying scan/i)).toBeVisible()
  })

  test('bulk actions on monitoring results', async ({ page }) => {
    await page.goto('/infringements')

    // Select multiple infringements
    await page.getByRole('checkbox', { name: /select all/i }).check()

    // Should show bulk action bar
    await expect(page.getByTestId('bulk-actions-bar')).toBeVisible()
    await expect(page.getByText(/5 items selected/i)).toBeVisible()

    // Bulk action options
    await expect(page.getByRole('button', { name: /bulk takedown/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /mark as false positive/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /export selected/i })).toBeVisible()

    // Perform bulk takedown
    await page.getByRole('button', { name: /bulk takedown/i }).click()

    // Should show confirmation dialog
    await expect(page.getByText(/send takedown notices for 5 infringements/i)).toBeVisible()
    
    await page.getByRole('button', { name: /confirm/i }).click()

    // Should show progress
    await expect(page.getByText(/processing takedown notices/i)).toBeVisible()
    await expect(page.getByRole('progressbar')).toBeVisible()

    // Success confirmation
    await expect(page.getByText(/5 takedown notices sent successfully/i)).toBeVisible()
  })

  // Helper functions
  async function loginUser(page: Page, email: string, password: string) {
    await page.goto('/login')
    await page.getByLabel(/email/i).fill(email)
    await page.getByLabel(/password/i).fill(password)
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL('/dashboard')
  }

  async function ensureTestProfile(page: Page, profile: typeof testProfile) {
    await page.goto('/profiles')
    
    // Check if profile exists
    const profileExists = await page.getByText(profile.stageName).isVisible()
    
    if (!profileExists) {
      // Create the test profile
      await page.getByRole('button', { name: /create profile/i }).click()
      await page.getByLabel(/stage name/i).fill(profile.stageName)
      await page.getByRole('button', { name: /next/i }).click()
      await page.getByRole('button', { name: /skip/i }).click() // Skip social accounts
      
      // Add keywords
      for (const keyword of profile.keywords) {
        await page.getByLabel(/add keyword/i).fill(keyword)
        await page.getByRole('button', { name: /add/i }).click()
      }
      await page.getByRole('button', { name: /next/i }).click()
      await page.getByRole('button', { name: /skip/i }).click() // Skip content upload
      await page.getByRole('button', { name: /create profile/i }).click()
      
      await expect(page.getByText(/profile created/i)).toBeVisible()
    }
  }
})