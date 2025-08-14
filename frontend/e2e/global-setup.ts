/**
 * Global setup for Playwright E2E tests
 * Prepares test environment, database, and authentication
 */

import { chromium, FullConfig } from '@playwright/test'

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting E2E test setup...')

  const browser = await chromium.launch()
  const page = await browser.newPage()

  try {
    // Wait for backend to be ready
    console.log('⏳ Waiting for backend to be ready...')
    let backendReady = false
    let attempts = 0
    const maxAttempts = 30

    while (!backendReady && attempts < maxAttempts) {
      try {
        const response = await page.request.get('http://localhost:8000/api/v1/health')
        if (response.status() === 200) {
          backendReady = true
          console.log('✅ Backend is ready')
        }
      } catch (error) {
        attempts++
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }

    if (!backendReady) {
      throw new Error('Backend failed to start within timeout')
    }

    // Wait for frontend to be ready
    console.log('⏳ Waiting for frontend to be ready...')
    let frontendReady = false
    attempts = 0

    while (!frontendReady && attempts < maxAttempts) {
      try {
        await page.goto('http://localhost:5173')
        frontendReady = true
        console.log('✅ Frontend is ready')
      } catch (error) {
        attempts++
        await new Promise(resolve => setTimeout(resolve, 1000))
      }
    }

    if (!frontendReady) {
      throw new Error('Frontend failed to start within timeout')
    }

    // Initialize test database
    console.log('🗄️ Initializing test database...')
    try {
      await page.request.post('http://localhost:8000/api/v1/test/reset-database')
      console.log('✅ Test database initialized')
    } catch (error) {
      console.warn('⚠️ Could not reset test database:', error)
    }

    // Create test users
    console.log('👤 Creating test users...')
    try {
      // Create regular test user
      await page.request.post('http://localhost:8000/api/v1/test/create-user', {
        data: {
          email: 'test@example.com',
          username: 'testuser',
          password: 'TestPassword123!',
          full_name: 'Test User',
          is_active: true,
        }
      })

      // Create admin test user
      await page.request.post('http://localhost:8000/api/v1/test/create-user', {
        data: {
          email: 'admin@example.com',
          username: 'admin',
          password: 'AdminPassword123!',
          full_name: 'Admin User',
          is_active: true,
          is_superuser: true,
        }
      })

      // Create test creator profile
      await page.request.post('http://localhost:8000/api/v1/test/create-profile', {
        data: {
          user_email: 'test@example.com',
          stage_name: 'TestCreator',
          real_name: 'Test Creator',
          bio: 'Test creator for E2E testing',
          monitoring_enabled: true,
        }
      })

      console.log('✅ Test users created')
    } catch (error) {
      console.warn('⚠️ Could not create test users:', error)
    }

    // Pre-authenticate test user and store credentials
    console.log('🔐 Pre-authenticating test user...')
    try {
      const loginResponse = await page.request.post('http://localhost:8000/api/v1/auth/login', {
        form: {
          username: 'test@example.com',
          password: 'TestPassword123!'
        }
      })

      if (loginResponse.ok()) {
        const loginData = await loginResponse.json()
        
        // Store authentication state
        const storageState = {
          cookies: [],
          origins: [
            {
              origin: 'http://localhost:5173',
              localStorage: [
                {
                  name: 'auth_token',
                  value: loginData.access_token
                },
                {
                  name: 'refresh_token',
                  value: loginData.refresh_token
                },
                {
                  name: 'user_data',
                  value: JSON.stringify(loginData.user)
                }
              ]
            }
          ]
        }

        // Save authenticated state for tests
        await page.context().storageState({ path: 'e2e/auth-state.json' })
        console.log('✅ Authentication state saved')
      }
    } catch (error) {
      console.warn('⚠️ Could not pre-authenticate:', error)
    }

    console.log('🎉 E2E test setup completed successfully!')

  } catch (error) {
    console.error('❌ E2E test setup failed:', error)
    throw error
  } finally {
    await browser.close()
  }
}

export default globalSetup