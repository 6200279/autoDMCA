import { test, expect, Page } from '@playwright/test'

// Test data
const testUser = {
  email: 'e2e-test@example.com',
  username: 'e2e_test_user',
  fullName: 'E2E Test User',
  password: 'TestPassword123!',
}

const testProfile = {
  stageName: 'E2E Test Creator',
  realName: 'Real Test Creator',
  bio: 'Professional content creator for E2E testing',
  socialAccounts: {
    instagram: '@e2e_test_creator',
    twitter: '@e2e_test_creator',
    onlyfans: 'e2e_test_creator',
  },
  keywords: ['e2e test', 'automation', 'content creator'],
}

test.describe('User Onboarding Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Start from home page
    await page.goto('/')
  })

  test('complete user registration and profile setup', async ({ page }) => {
    // Navigate to registration
    await page.getByRole('link', { name: /sign up/i }).click()
    await expect(page).toHaveURL('/register')

    // Fill registration form
    await page.getByLabel(/email/i).fill(testUser.email)
    await page.getByLabel(/username/i).fill(testUser.username)
    await page.getByLabel(/full name/i).fill(testUser.fullName)
    await page.getByLabel(/password/i).first().fill(testUser.password)
    await page.getByLabel(/confirm password/i).fill(testUser.password)

    // Accept terms and conditions
    await page.getByRole('checkbox', { name: /terms/i }).check()

    // Submit registration
    await page.getByRole('button', { name: /create account/i }).click()

    // Should redirect to dashboard after successful registration
    await expect(page).toHaveURL('/dashboard')
    await expect(page.getByText(/welcome/i)).toBeVisible()

    // Check for onboarding prompt
    await expect(page.getByText(/complete your profile/i)).toBeVisible()
  })

  test('complete profile creation wizard', async ({ page }) => {
    // Login first
    await loginUser(page, testUser.email, testUser.password)

    // Navigate to profile creation
    await page.getByRole('button', { name: /create profile/i }).click()
    await expect(page).toHaveURL('/profiles/create')

    // Step 1: Basic Information
    await page.getByLabel(/stage name/i).fill(testProfile.stageName)
    await page.getByLabel(/real name/i).fill(testProfile.realName)
    await page.getByLabel(/bio/i).fill(testProfile.bio)

    await page.getByRole('button', { name: /next/i }).click()

    // Step 2: Social Media Accounts
    await page.getByLabel(/instagram/i).fill(testProfile.socialAccounts.instagram)
    await page.getByLabel(/twitter/i).fill(testProfile.socialAccounts.twitter)
    await page.getByLabel(/onlyfans/i).fill(testProfile.socialAccounts.onlyfans)

    await page.getByRole('button', { name: /next/i }).click()

    // Step 3: Monitoring Keywords
    for (const keyword of testProfile.keywords) {
      await page.getByLabel(/add keyword/i).fill(keyword)
      await page.getByRole('button', { name: /add/i }).click()
    }

    // Verify keywords were added
    for (const keyword of testProfile.keywords) {
      await expect(page.getByText(keyword)).toBeVisible()
    }

    await page.getByRole('button', { name: /next/i }).click()

    // Step 4: Content Upload (optional)
    // Upload a test image
    const fileInput = page.getByLabel(/upload reference image/i)
    await fileInput.setInputFiles('e2e/fixtures/test-image.jpg')

    // Wait for upload to complete
    await expect(page.getByText(/upload successful/i)).toBeVisible()

    // Complete profile creation
    await page.getByRole('button', { name: /create profile/i }).click()

    // Should redirect to profiles page
    await expect(page).toHaveURL('/profiles')
    await expect(page.getByText(testProfile.stageName)).toBeVisible()

    // Verify profile appears in list
    await expect(page.getByRole('cell', { name: testProfile.stageName })).toBeVisible()
    await expect(page.getByRole('cell', { name: /active/i })).toBeVisible()
  })

  test('complete subscription setup', async ({ page }) => {
    // Login and ensure profile exists
    await loginUser(page, testUser.email, testUser.password)
    await createTestProfile(page, testProfile)

    // Navigate to billing
    await page.getByRole('link', { name: /billing/i }).click()
    await expect(page).toHaveURL('/billing')

    // Should show free plan initially
    await expect(page.getByText(/free plan/i)).toBeVisible()

    // Upgrade to premium
    await page.getByRole('button', { name: /upgrade/i }).click()

    // Select premium plan
    await page.getByRole('radio', { name: /premium/i }).check()
    await page.getByRole('button', { name: /select plan/i }).click()

    // Fill payment information (using Stripe test data)
    await page.getByLabel(/card number/i).fill('4242424242424242')
    await page.getByLabel(/expiry/i).fill('12/25')
    await page.getByLabel(/cvc/i).fill('123')
    await page.getByLabel(/postal code/i).fill('12345')

    // Complete subscription
    await page.getByRole('button', { name: /subscribe/i }).click()

    // Wait for payment processing
    await expect(page.getByText(/processing payment/i)).toBeVisible()
    await expect(page.getByText(/subscription activated/i)).toBeVisible({ timeout: 10000 })

    // Verify subscription status
    await expect(page.getByText(/premium plan/i)).toBeVisible()
    await expect(page.getByText(/active/i)).toBeVisible()
  })

  test('start first monitoring scan', async ({ page }) => {
    // Login and setup
    await loginUser(page, testUser.email, testUser.password)
    await createTestProfile(page, testProfile)

    // Navigate to scanning
    await page.getByRole('link', { name: /scanning/i }).click()
    await expect(page).toHaveURL('/scanning')

    // Start comprehensive scan
    await page.getByRole('button', { name: /start scan/i }).click()

    // Configure scan options
    await page.getByRole('checkbox', { name: /web search/i }).check()
    await page.getByRole('checkbox', { name: /social media/i }).check()
    await page.getByRole('checkbox', { name: /image search/i }).check()

    // Select scan depth
    await page.getByRole('radio', { name: /comprehensive/i }).check()

    // Start the scan
    await page.getByRole('button', { name: /begin scan/i }).click()

    // Should show scan in progress
    await expect(page.getByText(/scan started/i)).toBeVisible()
    await expect(page.getByRole('progressbar')).toBeVisible()

    // Navigate to scan results (scan should complete quickly in test environment)
    await page.waitForTimeout(5000) // Wait for scan to progress

    // Check scan status
    await page.getByRole('link', { name: /view results/i }).click()
    await expect(page.getByText(/scan results/i)).toBeVisible()

    // Should show some results or "no infringements found"
    await expect(
      page.getByText(/infringements found/i).or(page.getByText(/no infringements found/i))
    ).toBeVisible()
  })

  test('complete onboarding checklist', async ({ page }) => {
    // Login
    await loginUser(page, testUser.email, testUser.password)

    // Should see onboarding checklist
    await expect(page.getByText(/onboarding checklist/i)).toBeVisible()

    const checklist = page.locator('[data-testid="onboarding-checklist"]')

    // Initially should have incomplete items
    await expect(checklist.getByText(/create profile/i)).toBeVisible()
    await expect(checklist.getByText(/verify email/i)).toBeVisible()
    await expect(checklist.getByText(/setup monitoring/i)).toBeVisible()

    // Complete profile creation
    await createTestProfile(page, testProfile)

    // Return to dashboard
    await page.getByRole('link', { name: /dashboard/i }).click()

    // Profile creation should be checked off
    await expect(checklist.getByText(/create profile/i)).toHaveClass(/completed/i)

    // Email verification (simulate)
    await page.getByRole('button', { name: /verify email/i }).click()
    await expect(page.getByText(/verification email sent/i)).toBeVisible()

    // Setup monitoring
    await page.getByRole('button', { name: /setup monitoring/i }).click()
    await page.getByRole('checkbox', { name: /enable monitoring/i }).check()
    await page.getByRole('button', { name: /save settings/i }).click()

    // Should show completion
    await expect(page.getByText(/onboarding complete/i)).toBeVisible()
    await expect(page.getByText(/🎉/)).toBeVisible() // Celebration emoji
  })

  test('onboarding tour walkthrough', async ({ page }) => {
    // Login
    await loginUser(page, testUser.email, testUser.password)

    // Start tour
    await page.getByRole('button', { name: /take tour/i }).click()

    // Tour step 1: Dashboard overview
    await expect(page.getByText(/welcome to your dashboard/i)).toBeVisible()
    await page.getByRole('button', { name: /next/i }).click()

    // Tour step 2: Profile management
    await expect(page.getByText(/manage your creator profiles/i)).toBeVisible()
    await page.getByRole('button', { name: /next/i }).click()

    // Tour step 3: Monitoring features
    await expect(page.getByText(/automated monitoring/i)).toBeVisible()
    await page.getByRole('button', { name: /next/i }).click()

    // Tour step 4: DMCA tools
    await expect(page.getByText(/dmca takedown tools/i)).toBeVisible()
    await page.getByRole('button', { name: /next/i }).click()

    // Tour step 5: Settings
    await expect(page.getByText(/customize your experience/i)).toBeVisible()
    await page.getByRole('button', { name: /finish tour/i }).click()

    // Tour should be complete
    await expect(page.getByText(/tour complete/i)).toBeVisible()
  })

  test('handles onboarding errors gracefully', async ({ page }) => {
    // Test with invalid data
    await page.goto('/register')

    // Try to register with invalid email
    await page.getByLabel(/email/i).fill('invalid-email')
    await page.getByLabel(/username/i).fill('test')
    await page.getByLabel(/password/i).first().fill('weak')
    await page.getByRole('button', { name: /create account/i }).click()

    // Should show validation errors
    await expect(page.getByText(/invalid email/i)).toBeVisible()
    await expect(page.getByText(/username too short/i)).toBeVisible()
    await expect(page.getByText(/password too weak/i)).toBeVisible()

    // Form should not submit
    await expect(page).toHaveURL('/register')
  })

  test('allows skipping optional onboarding steps', async ({ page }) => {
    // Login
    await loginUser(page, testUser.email, testUser.password)

    // Go to profile creation
    await page.getByRole('button', { name: /create profile/i }).click()

    // Fill only required fields
    await page.getByLabel(/stage name/i).fill(testProfile.stageName)
    await page.getByRole('button', { name: /next/i }).click()

    // Skip social media accounts
    await page.getByRole('button', { name: /skip/i }).click()

    // Skip keywords
    await page.getByRole('button', { name: /skip/i }).click()

    // Skip content upload
    await page.getByRole('button', { name: /skip/i }).click()

    // Should still create profile successfully
    await expect(page.getByText(/profile created/i)).toBeVisible()
    await expect(page.getByText(testProfile.stageName)).toBeVisible()
  })

  test('saves onboarding progress', async ({ page }) => {
    // Start onboarding
    await page.goto('/register')
    await page.getByLabel(/email/i).fill(testUser.email)
    await page.getByLabel(/username/i).fill(testUser.username)
    await page.getByLabel(/full name/i).fill(testUser.fullName)
    await page.getByLabel(/password/i).first().fill(testUser.password)
    await page.getByLabel(/confirm password/i).fill(testUser.password)
    await page.getByRole('checkbox', { name: /terms/i }).check()
    await page.getByRole('button', { name: /create account/i }).click()

    // Start profile creation but don't complete
    await page.getByRole('button', { name: /create profile/i }).click()
    await page.getByLabel(/stage name/i).fill(testProfile.stageName)

    // Refresh page to simulate navigation away
    await page.reload()

    // Should preserve form data
    await expect(page.getByLabel(/stage name/i)).toHaveValue(testProfile.stageName)
  })

  // Helper functions
  async function loginUser(page: Page, email: string, password: string) {
    await page.goto('/login')
    await page.getByLabel(/email/i).fill(email)
    await page.getByLabel(/password/i).fill(password)
    await page.getByRole('button', { name: /sign in/i }).click()
    await expect(page).toHaveURL('/dashboard')
  }

  async function createTestProfile(page: Page, profile: typeof testProfile) {
    await page.getByRole('button', { name: /create profile/i }).click()
    await page.getByLabel(/stage name/i).fill(profile.stageName)
    await page.getByLabel(/real name/i).fill(profile.realName)
    await page.getByLabel(/bio/i).fill(profile.bio)
    await page.getByRole('button', { name: /next/i }).click()

    // Fill social accounts
    await page.getByLabel(/instagram/i).fill(profile.socialAccounts.instagram)
    await page.getByRole('button', { name: /next/i }).click()

    // Add keywords
    for (const keyword of profile.keywords) {
      await page.getByLabel(/add keyword/i).fill(keyword)
      await page.getByRole('button', { name: /add/i }).click()
    }
    await page.getByRole('button', { name: /next/i }).click()

    // Skip content upload
    await page.getByRole('button', { name: /skip/i }).click()

    // Create profile
    await page.getByRole('button', { name: /create profile/i }).click()
    await expect(page.getByText(/profile created/i)).toBeVisible()
  }
})