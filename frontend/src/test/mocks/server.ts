/**
 * Mock Service Worker server setup for testing
 * Provides API mocking for all backend endpoints
 */

import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

// Mock data
const mockUser = {
  id: 1,
  email: 'test@example.com',
  username: 'testuser',
  full_name: 'Test User',
  is_active: true,
  is_superuser: false,
  created_at: '2024-01-01T00:00:00Z',
}

const mockProfile = {
  id: 1,
  user_id: 1,
  stage_name: 'TestCreator',
  real_name: 'Test Creator',
  bio: 'Test creator bio',
  monitoring_enabled: true,
  social_media_accounts: {
    instagram: '@testcreator',
    twitter: '@testcreator',
  },
  protection_level: 'premium',
}

const mockTakedown = {
  id: 1,
  profile_id: 1,
  infringing_url: 'https://example.com/stolen-content',
  original_work_title: 'My Original Content',
  copyright_owner: 'Test Creator',
  status: 'pending',
  created_at: '2024-01-01T00:00:00Z',
}

const mockInfringement = {
  id: 1,
  profile_id: 1,
  url: 'https://example.com/infringement',
  title: 'Stolen Content',
  description: 'My content was stolen',
  confidence_score: 0.95,
  status: 'detected',
  platform: 'instagram',
  created_at: '2024-01-01T00:00:00Z',
}

// API handlers
export const handlers = [
  // Authentication endpoints
  http.post('/api/v1/auth/login', async ({ request }) => {
    const body = await request.formData()
    const username = body.get('username')
    const password = body.get('password')

    if (username === 'test@example.com' && password === 'testpassword') {
      return HttpResponse.json({
        access_token: 'mock-access-token',
        refresh_token: 'mock-refresh-token',
        token_type: 'bearer',
        user: mockUser,
      })
    }

    return HttpResponse.json(
      { detail: 'Incorrect email or password' },
      { status: 401 }
    )
  }),

  http.post('/api/v1/auth/register', async ({ request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      access_token: 'mock-access-token',
      user: {
        ...mockUser,
        email: body.email,
        username: body.username,
        full_name: body.full_name,
      },
    }, { status: 201 })
  }),

  http.get('/api/v1/auth/me', ({ request }) => {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader || !authHeader.includes('mock-access-token')) {
      return HttpResponse.json(
        { detail: 'Not authenticated' },
        { status: 401 }
      )
    }

    return HttpResponse.json(mockUser)
  }),

  http.post('/api/v1/auth/logout', () => {
    return HttpResponse.json({ message: 'Successfully logged out' })
  }),

  http.post('/api/v1/auth/refresh', async ({ request }) => {
    const body = await request.json()
    
    if (body.refresh_token === 'mock-refresh-token') {
      return HttpResponse.json({
        access_token: 'new-mock-access-token',
        refresh_token: 'new-mock-refresh-token',
      })
    }

    return HttpResponse.json(
      { detail: 'Invalid refresh token' },
      { status: 401 }
    )
  }),

  // Profile endpoints
  http.get('/api/v1/profiles', () => {
    return HttpResponse.json({
      items: [mockProfile],
      total: 1,
      page: 1,
      size: 10,
    })
  }),

  http.post('/api/v1/profiles', async ({ request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      ...mockProfile,
      ...body,
      id: Date.now(),
    }, { status: 201 })
  }),

  http.get('/api/v1/profiles/:id', ({ params }) => {
    return HttpResponse.json({
      ...mockProfile,
      id: parseInt(params.id as string),
    })
  }),

  http.patch('/api/v1/profiles/:id', async ({ params, request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      ...mockProfile,
      ...body,
      id: parseInt(params.id as string),
    })
  }),

  // Takedown endpoints
  http.get('/api/v1/takedowns', ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const size = parseInt(url.searchParams.get('size') || '10')
    
    return HttpResponse.json({
      items: [mockTakedown],
      total: 1,
      page,
      size,
    })
  }),

  http.post('/api/v1/takedowns', async ({ request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      ...mockTakedown,
      ...body,
      id: Date.now(),
    }, { status: 201 })
  }),

  http.get('/api/v1/takedowns/:id', ({ params }) => {
    return HttpResponse.json({
      ...mockTakedown,
      id: parseInt(params.id as string),
    })
  }),

  http.post('/api/v1/takedowns/:id/process', ({ params }) => {
    return HttpResponse.json({
      message: 'Takedown request processed successfully',
      takedown_id: parseInt(params.id as string),
    })
  }),

  http.get('/api/v1/takedowns/statistics', () => {
    return HttpResponse.json({
      total_requests: 10,
      pending: 2,
      sent: 5,
      successful: 3,
      failed: 0,
      success_rate: 100,
    })
  }),

  // Infringement endpoints
  http.get('/api/v1/infringements', () => {
    return HttpResponse.json({
      items: [mockInfringement],
      total: 1,
      page: 1,
      size: 10,
    })
  }),

  http.post('/api/v1/infringements', async ({ request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      ...mockInfringement,
      ...body,
      id: Date.now(),
    }, { status: 201 })
  }),

  // Dashboard endpoints
  http.get('/api/v1/dashboard/stats', () => {
    return HttpResponse.json({
      total_profiles: 5,
      active_monitoring: 3,
      total_infringements: 15,
      resolved_cases: 12,
      success_rate: 80,
      recent_activity: [
        {
          id: 1,
          type: 'infringement_detected',
          description: 'New infringement detected on Instagram',
          timestamp: '2024-01-01T12:00:00Z',
        },
        {
          id: 2,
          type: 'takedown_successful',
          description: 'Takedown request successful',
          timestamp: '2024-01-01T11:00:00Z',
        },
      ],
    })
  }),

  // Billing endpoints
  http.get('/api/v1/billing/subscription', () => {
    return HttpResponse.json({
      id: 'sub_123',
      status: 'active',
      plan: 'premium',
      current_period_start: '2024-01-01T00:00:00Z',
      current_period_end: '2024-02-01T00:00:00Z',
      cancel_at_period_end: false,
    })
  }),

  http.get('/api/v1/billing/usage', () => {
    return HttpResponse.json({
      current_period: {
        scans: 150,
        takedowns: 5,
        monitoring_profiles: 3,
      },
      limits: {
        scans: 1000,
        takedowns: 50,
        monitoring_profiles: 10,
      },
    })
  }),

  // AI/ML endpoints
  http.post('/api/v1/ai/analyze-content', async ({ request }) => {
    const formData = await request.formData()
    
    return HttpResponse.json({
      similarity_score: 0.85,
      is_match: true,
      confidence: 'high',
      features_matched: ['face_recognition', 'image_hash'],
      analysis_id: 'analysis_123',
    })
  }),

  http.post('/api/v1/ai/add-reference', async ({ request }) => {
    const formData = await request.formData()
    
    return HttpResponse.json({
      reference_id: 'ref_123',
      status: 'added',
      features_extracted: ['face_encoding', 'image_hash', 'metadata'],
    })
  }),

  // Social media monitoring endpoints
  http.post('/api/v1/social-media/start-monitoring', async ({ request }) => {
    const body = await request.json()
    
    return HttpResponse.json({
      job_id: 'job_123',
      status: 'started',
      estimated_duration: '30 minutes',
    })
  }),

  http.get('/api/v1/social-media/monitoring-results/:jobId', ({ params }) => {
    return HttpResponse.json({
      job_id: params.jobId,
      status: 'completed',
      results: {
        profiles_found: 3,
        suspicious_accounts: 2,
        confidence_scores: [0.85, 0.92, 0.67],
        recommendations: [
          'Report fake_account_1 for impersonation',
          'Monitor suspicious_account_2 for further activity',
        ],
      },
    })
  }),

  // Error simulation endpoints for testing error handling
  http.get('/api/v1/test/500', () => {
    return HttpResponse.json(
      { detail: 'Internal server error' },
      { status: 500 }
    )
  }),

  http.get('/api/v1/test/timeout', () => {
    return new Promise(() => {}) // Never resolves, simulates timeout
  }),

  http.get('/api/v1/test/network-error', () => {
    return HttpResponse.error()
  }),
]

// Create and export the server
export const server = setupServer(...handlers)