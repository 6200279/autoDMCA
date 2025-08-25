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
  http.get('http://localhost:8080/api/v1/profiles', () => {
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

  // Submission endpoints
  http.get('http://localhost:8080/api/v1/submissions', ({ request }) => {
    const url = new URL(request.url)
    const page = parseInt(url.searchParams.get('page') || '1')
    const limit = parseInt(url.searchParams.get('limit') || '10')
    const status = url.searchParams.get('status')
    const type = url.searchParams.get('type')
    const priority = url.searchParams.get('priority')

    const mockSubmissions = [
      {
        id: '1',
        user_id: 1,
        profile_id: 1,
        type: 'images',
        priority: 'normal',
        status: 'active',
        title: 'Test Image Submission',
        urls: ['https://example.com/image1.jpg', 'https://example.com/image2.jpg'],
        files: [],
        tags: ['photography', 'portrait'],
        category: 'photography',
        description: 'Test submission description',
        progress_percentage: 75,
        estimated_completion: '2024-01-01T15:00:00Z',
        auto_monitoring: true,
        notify_on_infringement: true,
        total_urls: 2,
        created_at: '2024-01-01T10:00:00Z',
        updated_at: '2024-01-01T14:00:00Z'
      },
      {
        id: '2',
        user_id: 1,
        profile_id: null,
        type: 'videos',
        priority: 'high',
        status: 'processing',
        title: 'Video Content Batch',
        urls: ['https://example.com/video1.mp4'],
        files: [],
        tags: ['content'],
        category: 'video_content',
        description: 'Important video submission',
        progress_percentage: 45,
        estimated_completion: '2024-01-01T16:00:00Z',
        auto_monitoring: false,
        notify_on_infringement: true,
        total_urls: 1,
        created_at: '2024-01-01T11:00:00Z',
        updated_at: '2024-01-01T14:30:00Z'
      },
      {
        id: '3',
        user_id: 1,
        profile_id: 1,
        type: 'documents',
        priority: 'urgent',
        status: 'failed',
        title: 'Document Submission',
        urls: ['https://example.com/doc1.pdf'],
        files: [],
        tags: ['legal'],
        category: 'written_content',
        description: 'Legal document',
        progress_percentage: 0,
        estimated_completion: null,
        auto_monitoring: true,
        notify_on_infringement: true,
        total_urls: 1,
        created_at: '2024-01-01T09:00:00Z',
        updated_at: '2024-01-01T13:00:00Z'
      }
    ]

    let filteredSubmissions = mockSubmissions

    if (status) {
      filteredSubmissions = filteredSubmissions.filter(s => s.status === status)
    }
    if (type) {
      filteredSubmissions = filteredSubmissions.filter(s => s.type === type)
    }
    if (priority) {
      filteredSubmissions = filteredSubmissions.filter(s => s.priority === priority)
    }

    const startIndex = (page - 1) * limit
    const endIndex = startIndex + limit
    const paginatedSubmissions = filteredSubmissions.slice(startIndex, endIndex)

    return HttpResponse.json({
      items: paginatedSubmissions,
      total: filteredSubmissions.length,
      page,
      size: limit,
      pages: Math.ceil(filteredSubmissions.length / limit)
    })
  }),

  http.get('http://localhost:8080/api/v1/submissions/:id', ({ params }) => {
    const submission = {
      id: params.id,
      user_id: 1,
      profile_id: 1,
      type: 'images',
      priority: 'normal',
      status: 'active',
      title: 'Test Submission',
      urls: ['https://example.com/image1.jpg'],
      files: [],
      tags: ['test'],
      category: 'photography',
      description: 'Test submission',
      progress_percentage: 50,
      estimated_completion: '2024-01-01T15:00:00Z',
      auto_monitoring: true,
      notify_on_infringement: true,
      total_urls: 1,
      created_at: '2024-01-01T10:00:00Z',
      updated_at: '2024-01-01T14:00:00Z'
    }

    return HttpResponse.json(submission)
  }),

  http.post('http://localhost:8080/api/v1/submissions', async ({ request }) => {
    const body = await request.json()
    
    const newSubmission = {
      id: Date.now().toString(),
      user_id: 1,
      profile_id: body.profile_id || null,
      type: body.type,
      priority: body.priority,
      status: 'pending',
      title: body.title,
      urls: body.urls || [],
      files: [],
      tags: body.tags || [],
      category: body.category || null,
      description: body.description || null,
      progress_percentage: 0,
      estimated_completion: null,
      auto_monitoring: body.auto_monitoring ?? true,
      notify_on_infringement: body.notify_on_infringement ?? true,
      total_urls: (body.urls || []).length,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }

    return HttpResponse.json(newSubmission, { status: 201 })
  }),

  http.put('http://localhost:8080/api/v1/submissions/:id', async ({ params, request }) => {
    const body = await request.json()
    
    const updatedSubmission = {
      id: params.id,
      user_id: 1,
      profile_id: body.profile_id || 1,
      type: body.type || 'images',
      priority: body.priority || 'normal',
      status: body.status || 'active',
      title: body.title || 'Updated Submission',
      urls: body.urls || ['https://example.com/image1.jpg'],
      files: body.files || [],
      tags: body.tags || ['updated'],
      category: body.category || 'photography',
      description: body.description || 'Updated submission',
      progress_percentage: body.progress_percentage ?? 75,
      estimated_completion: body.estimated_completion,
      auto_monitoring: body.auto_monitoring ?? true,
      notify_on_infringement: body.notify_on_infringement ?? true,
      total_urls: (body.urls || ['https://example.com/image1.jpg']).length,
      created_at: '2024-01-01T10:00:00Z',
      updated_at: new Date().toISOString()
    }

    return HttpResponse.json(updatedSubmission)
  }),

  http.delete('http://localhost:8080/api/v1/submissions/:id', ({ params }) => {
    return HttpResponse.json({ message: 'Submission deleted successfully' })
  }),

  http.post('http://localhost:8080/api/v1/submissions/:id/cancel', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'cancelled',
      message: 'Submission cancelled successfully'
    })
  }),

  http.post('http://localhost:8080/api/v1/submissions/:id/retry', ({ params }) => {
    return HttpResponse.json({
      id: params.id,
      status: 'pending',
      message: 'Submission retry initiated'
    })
  }),

  http.get('http://localhost:8080/api/v1/submissions/:id/progress', ({ params }) => {
    return HttpResponse.json({
      submission_id: params.id,
      progress_percentage: 65,
      current_stage: 'Processing URLs',
      total_stages: 5,
      current_stage_number: 3,
      estimated_completion: '2024-01-01T16:00:00Z',
      processed_urls: 8,
      total_urls: 12,
      errors: []
    })
  }),

  http.post('http://localhost:8080/api/v1/submissions/upload', async ({ request }) => {
    const formData = await request.formData()
    const files = formData.getAll('files') as File[]
    
    if (files.length === 0) {
      return HttpResponse.json(
        { detail: 'No files provided' },
        { status: 400 }
      )
    }

    // Simulate file size validation
    const maxSize = 100 * 1024 * 1024 // 100MB
    const oversizedFiles = files.filter(file => file.size > maxSize)
    if (oversizedFiles.length > 0) {
      return HttpResponse.json(
        { detail: `Files too large: ${oversizedFiles.map(f => f.name).join(', ')}` },
        { status: 400 }
      )
    }

    // Simulate file type validation
    const allowedTypes = [
      'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp',
      'video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/flv', 'video/mkv',
      'application/pdf', 'application/msword', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    const invalidFiles = files.filter(file => !allowedTypes.includes(file.type))
    if (invalidFiles.length > 0) {
      return HttpResponse.json(
        { detail: `Invalid file types: ${invalidFiles.map(f => f.name).join(', ')}` },
        { status: 400 }
      )
    }

    // Mock successful upload response
    const fileUrls = files.map((file, index) => 
      `https://cdn.example.com/uploads/${Date.now()}-${index}-${file.name}`
    )

    return HttpResponse.json({
      file_urls: fileUrls,
      upload_id: `upload_${Date.now()}`,
      total_files: files.length,
      total_size: files.reduce((sum, file) => sum + file.size, 0)
    })
  }),

  http.post('http://localhost:8080/api/v1/submissions/validate-urls', async ({ request }) => {
    const body = await request.json()
    const urls = body.urls as string[]
    
    if (!urls || urls.length === 0) {
      return HttpResponse.json(
        { detail: 'No URLs provided' },
        { status: 400 }
      )
    }

    const validationResults = urls.map(url => {
      try {
        const urlObj = new URL(url)
        const domain = urlObj.hostname
        
        // Simulate some invalid URLs for testing
        const isValid = !url.includes('invalid.com') && !url.includes('blocked.site')
        
        return {
          url,
          is_valid: isValid,
          domain,
          error_message: isValid ? null : 'URL is not accessible or blocked'
        }
      } catch {
        return {
          url,
          is_valid: false,
          domain: 'unknown',
          error_message: 'Invalid URL format'
        }
      }
    })

    return HttpResponse.json(validationResults)
  }),

  http.post('http://localhost:8080/api/v1/submissions/bulk', async ({ request }) => {
    const body = await request.json()
    const { submissions, apply_to_all } = body
    
    if (!submissions || submissions.length === 0) {
      return HttpResponse.json(
        { detail: 'No submissions provided' },
        { status: 400 }
      )
    }

    const createdSubmissions = submissions.map((submission: any, index: number) => ({
      id: (Date.now() + index).toString(),
      user_id: 1,
      profile_id: submission.profile_id || apply_to_all?.profile_id || null,
      type: submission.type,
      priority: submission.priority || apply_to_all?.priority || 'normal',
      status: 'pending',
      title: submission.title,
      urls: submission.urls || [],
      files: [],
      tags: submission.tags || apply_to_all?.tags || [],
      category: submission.category || apply_to_all?.category || null,
      description: submission.description || null,
      progress_percentage: 0,
      estimated_completion: null,
      auto_monitoring: submission.auto_monitoring ?? apply_to_all?.auto_monitoring ?? true,
      notify_on_infringement: submission.notify_on_infringement ?? apply_to_all?.notify_on_infringement ?? true,
      total_urls: (submission.urls || []).length,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }))

    return HttpResponse.json({
      submissions: createdSubmissions,
      total_created: createdSubmissions.length,
      batch_id: `batch_${Date.now()}`
    }, { status: 201 })
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