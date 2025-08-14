/**
 * End-to-end tests for authentication flows
 * Tests login, registration, logout, and protected routes
 */

import { test, expect } from '@playwright/test'

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    // Clear any existing authentication
    await page.context().clearCookies()
    await page.goto('/')
  })

  test.describe('Login', () => {
    test('should display login form', async ({ page }) => {
      await page.goto('/login')
      
      await expect(page).toHaveTitle(/Content Protection Platform/)
      await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible()
      await expect(page.getByLabel(/email/i)).toBeVisible()
      await expect(page.getByLabel(/password/i)).toBeVisible()
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
    })

    test('should login with valid credentials', async ({ page }) => {
      await page.goto('/login')
      
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      // Should redirect to dashboard
      await expect(page).toHaveURL('/dashboard')
      await expect(page.getByText(/dashboard/i)).toBeVisible()
    })

    test('should show error for invalid credentials', async ({ page }) => {
      await page.goto('/login')
      
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('wrongpassword')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page.getByText(/incorrect.*password/i)).toBeVisible()
    })

    test('should validate required fields', async ({ page }) => {
      await page.goto('/login')
      
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page.getByText(/email is required/i)).toBeVisible()
      await expect(page.getByText(/password is required/i)).toBeVisible()
    })

    test('should validate email format', async ({ page }) => {
      await page.goto('/login')
      
      await page.getByLabel(/email/i).fill('invalid-email')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page.getByText(/please enter a valid email/i)).toBeVisible()
    })

    test('should remember me option work', async ({ page }) => {
      await page.goto('/login')
      
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('checkbox', { name: /remember me/i }).check()
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page).toHaveURL('/dashboard')
      
      // Close and reopen browser to test persistence
      await page.context().close()
      // In a real test, you'd create a new context here and verify the user is still logged in
    })
  })

  test.describe('Registration', () => {
    test('should display registration form', async ({ page }) => {
      await page.goto('/register')
      
      await expect(page).toHaveTitle(/Content Protection Platform/)
      await expect(page.getByRole('heading', { name: /create.*account/i })).toBeVisible()
      await expect(page.getByLabel(/email/i)).toBeVisible()
      await expect(page.getByLabel(/username/i)).toBeVisible()
      await expect(page.getByLabel(/full name/i)).toBeVisible()
      await expect(page.getByLabel(/password/i)).toBeVisible()
    })

    test('should register new user successfully', async ({ page }) => {
      await page.goto('/register')
      
      const uniqueEmail = `newuser${Date.now()}@example.com`
      const uniqueUsername = `newuser${Date.now()}`
      
      await page.getByLabel(/email/i).fill(uniqueEmail)
      await page.getByLabel(/username/i).fill(uniqueUsername)
      await page.getByLabel(/full name/i).fill('New Test User')
      await page.getByLabel(/password/i).fill('NewPassword123!')
      await page.getByRole('button', { name: /create account/i }).click()
      
      // Should redirect to dashboard after successful registration
      await expect(page).toHaveURL('/dashboard')
      await expect(page.getByText(/welcome.*new test user/i)).toBeVisible()
    })

    test('should show error for duplicate email', async ({ page }) => {
      await page.goto('/register')
      
      await page.getByLabel(/email/i).fill('test@example.com') // Existing user
      await page.getByLabel(/username/i).fill('uniqueusername')
      await page.getByLabel(/full name/i).fill('Test User')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('button', { name: /create account/i }).click()
      
      await expect(page.getByText(/email.*already.*registered/i)).toBeVisible()
    })

    test('should validate password strength', async ({ page }) => {
      await page.goto('/register')
      
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/username/i).fill('testuser')
      await page.getByLabel(/full name/i).fill('Test User')
      await page.getByLabel(/password/i).fill('weak')
      await page.getByRole('button', { name: /create account/i }).click()
      
      await expect(page.getByText(/password.*must.*8.*characters/i)).toBeVisible()
    })
  })

  test.describe('Logout', () => {
    test('should logout successfully', async ({ page }) => {
      // First login
      await page.goto('/login')
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page).toHaveURL('/dashboard')
      
      // Then logout
      await page.getByRole('button', { name: /logout/i }).click()
      
      // Should redirect to login page
      await expect(page).toHaveURL('/login')
      await expect(page.getByText(/welcome back/i)).toBeVisible()
    })

    test('should clear user session on logout', async ({ page }) => {
      // Login first
      await page.goto('/login')
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page).toHaveURL('/dashboard')
      
      // Logout
      await page.getByRole('button', { name: /logout/i }).click()
      
      // Try to access protected route
      await page.goto('/dashboard')
      
      // Should be redirected back to login
      await expect(page).toHaveURL('/login')
    })
  })

  test.describe('Protected Routes', () => {
    test('should redirect unauthenticated users to login', async ({ page }) => {
      const protectedRoutes = [
        '/dashboard',
        '/profiles',
        '/takedowns',
        '/infringements',
        '/settings'
      ]

      for (const route of protectedRoutes) {
        await page.goto(route)
        await expect(page).toHaveURL('/login')
      }
    })

    test('should allow authenticated users to access protected routes', async ({ page }) => {
      // Login first
      await page.goto('/login')
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      const protectedRoutes = [
        { path: '/dashboard', title: /dashboard/i },
        { path: '/profiles', title: /profiles/i },
        { path: '/takedowns', title: /takedowns/i },
        { path: '/infringements', title: /infringements/i },
      ]

      for (const route of protectedRoutes) {
        await page.goto(route.path)
        await expect(page).toHaveURL(route.path)
        await expect(page.getByText(route.title)).toBeVisible()
      }
    })

    test('should maintain authentication across page refreshes', async ({ page }) => {
      // Login
      await page.goto('/login')
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page).toHaveURL('/dashboard')
      
      // Refresh the page
      await page.reload()
      
      // Should still be on dashboard (not redirected to login)
      await expect(page).toHaveURL('/dashboard')
      await expect(page.getByText(/dashboard/i)).toBeVisible()
    })
  })

  test.describe('Password Reset', () => {
    test('should display forgot password form', async ({ page }) => {
      await page.goto('/login')
      await page.getByRole('link', { name: /forgot.*password/i }).click()
      
      await expect(page).toHaveURL('/forgot-password')
      await expect(page.getByText(/reset.*password/i)).toBeVisible()
      await expect(page.getByLabel(/email/i)).toBeVisible()
    })

    test('should send password reset email', async ({ page }) => {
      await page.goto('/forgot-password')
      
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByRole('button', { name: /send.*reset/i }).click()
      
      await expect(page.getByText(/email.*sent/i)).toBeVisible()
    })

    test('should handle non-existent email gracefully', async ({ page }) => {
      await page.goto('/forgot-password')
      
      await page.getByLabel(/email/i).fill('nonexistent@example.com')
      await page.getByRole('button', { name: /send.*reset/i }).click()
      
      // Should not reveal whether email exists (security best practice)
      await expect(page.getByText(/email.*sent/i)).toBeVisible()
    })
  })

  test.describe('Session Management', () => {
    test('should handle expired tokens gracefully', async ({ page }) => {
      // Login normally
      await page.goto('/login')
      await page.getByLabel(/email/i).fill('test@example.com')
      await page.getByLabel(/password/i).fill('TestPassword123!')
      await page.getByRole('button', { name: /sign in/i }).click()
      
      await expect(page).toHaveURL('/dashboard')
      
      // Simulate token expiration by clearing storage
      await page.evaluate(() => {
        localStorage.removeItem('auth_token')
        localStorage.removeItem('refresh_token')
      })
      
      // Try to access protected route
      await page.goto('/profiles')
      
      // Should be redirected to login
      await expect(page).toHaveURL('/login')
    })

    test('should refresh token automatically', async ({ page }) => {
      // This test would require setting up a scenario where the access token
      // is expired but the refresh token is still valid
      // Implementation depends on your token refresh logic
    })
  })
})