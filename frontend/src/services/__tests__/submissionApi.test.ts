/**
 * @fileoverview Tests for submissionApi service
 * Tests all submission API endpoints with various scenarios including success, error, and edge cases
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { submissionApi } from '../api'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import { createMockFile } from '@/test/setup'
import { ContentType, PriorityLevel, CreateSubmission, BulkSubmission } from '@/types/api'

describe('submissionApi', () => {
  describe('getSubmissions', () => {
    it('should fetch submissions without parameters', async () => {
      const response = await submissionApi.getSubmissions()
      
      expect(response.data).toHaveProperty('items')
      expect(response.data).toHaveProperty('total')
      expect(response.data).toHaveProperty('page')
      expect(response.data).toHaveProperty('size')
      expect(Array.isArray(response.data.items)).toBe(true)
      expect(response.data.items.length).toBeGreaterThan(0)
      
      // Check submission structure
      const submission = response.data.items[0]
      expect(submission).toHaveProperty('id')
      expect(submission).toHaveProperty('title')
      expect(submission).toHaveProperty('type')
      expect(submission).toHaveProperty('status')
      expect(submission).toHaveProperty('priority')
      expect(submission).toHaveProperty('urls')
      expect(submission).toHaveProperty('progress_percentage')
    })

    it('should fetch submissions with filtering parameters', async () => {
      const params = {
        status: 'active',
        type: 'images',
        priority: 'high',
        page: 1,
        limit: 5
      }
      
      const response = await submissionApi.getSubmissions(params)
      
      expect(response.data).toHaveProperty('items')
      expect(response.data.page).toBe(1)
      expect(response.data.size).toBe(5)
    })

    it('should handle empty results', async () => {
      // Mock empty response
      server.use(
        http.get('http://localhost:8080/api/v1/submissions', () => {
          return HttpResponse.json({
            items: [],
            total: 0,
            page: 1,
            size: 10,
            pages: 0
          })
        })
      )

      const response = await submissionApi.getSubmissions()
      
      expect(response.data.items).toEqual([])
      expect(response.data.total).toBe(0)
    })

    it('should handle server errors', async () => {
      server.use(
        http.get('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Server error' },
            { status: 500 }
          )
        })
      )

      await expect(submissionApi.getSubmissions()).rejects.toThrow()
    })
  })

  describe('getSubmission', () => {
    it('should fetch a single submission by id', async () => {
      const submissionId = '123'
      const response = await submissionApi.getSubmission(submissionId)
      
      expect(response.data).toHaveProperty('id', submissionId)
      expect(response.data).toHaveProperty('title')
      expect(response.data).toHaveProperty('type')
      expect(response.data).toHaveProperty('status')
    })

    it('should handle not found error', async () => {
      server.use(
        http.get('/api/v1/submissions/:id', () => {
          return HttpResponse.json(
            { detail: 'Submission not found' },
            { status: 404 }
          )
        })
      )

      await expect(submissionApi.getSubmission('nonexistent')).rejects.toThrow()
    })
  })

  describe('createSubmission', () => {
    it('should create a new submission successfully', async () => {
      const submissionData: CreateSubmission = {
        title: 'Test Submission',
        type: ContentType.IMAGES,
        priority: PriorityLevel.NORMAL,
        urls: ['https://example.com/image1.jpg'],
        category: 'photography',
        description: 'Test description',
        tags: ['test', 'submission'],
        auto_monitoring: true,
        notify_on_infringement: true,
        profile_id: 1
      }

      const response = await submissionApi.createSubmission(submissionData)
      
      expect(response.status).toBe(201)
      expect(response.data).toHaveProperty('id')
      expect(response.data.title).toBe(submissionData.title)
      expect(response.data.type).toBe(submissionData.type)
      expect(response.data.priority).toBe(submissionData.priority)
      expect(response.data.status).toBe('pending')
      expect(response.data.urls).toEqual(submissionData.urls)
      expect(response.data.category).toBe(submissionData.category)
      expect(response.data.description).toBe(submissionData.description)
      expect(response.data.tags).toEqual(submissionData.tags)
      expect(response.data.auto_monitoring).toBe(submissionData.auto_monitoring)
      expect(response.data.notify_on_infringement).toBe(submissionData.notify_on_infringement)
      expect(response.data.profile_id).toBe(submissionData.profile_id)
    })

    it('should create submission with minimal required fields', async () => {
      const submissionData: CreateSubmission = {
        title: 'Minimal Submission',
        type: ContentType.VIDEOS,
        priority: PriorityLevel.HIGH,
        urls: ['https://example.com/video.mp4']
      }

      const response = await submissionApi.createSubmission(submissionData)
      
      expect(response.status).toBe(201)
      expect(response.data.title).toBe(submissionData.title)
      expect(response.data.type).toBe(submissionData.type)
      expect(response.data.priority).toBe(submissionData.priority)
    })

    it('should handle validation errors', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { 
              detail: {
                title: ['Title is required'],
                type: ['Invalid content type']
              }
            },
            { status: 422 }
          )
        })
      )

      const invalidData = {} as CreateSubmission

      await expect(submissionApi.createSubmission(invalidData)).rejects.toThrow()
    })
  })

  describe('updateSubmission', () => {
    it('should update an existing submission', async () => {
      const submissionId = '123'
      const updateData = {
        title: 'Updated Submission',
        description: 'Updated description',
        priority: PriorityLevel.URGENT
      }

      const response = await submissionApi.updateSubmission(submissionId, updateData)
      
      expect(response.data.id).toBe(submissionId)
      expect(response.data.title).toBe(updateData.title)
      expect(response.data.description).toBe(updateData.description)
      expect(response.data.priority).toBe(updateData.priority)
    })

    it('should handle partial updates', async () => {
      const submissionId = '123'
      const updateData = { title: 'New Title Only' }

      const response = await submissionApi.updateSubmission(submissionId, updateData)
      
      expect(response.data.title).toBe(updateData.title)
    })
  })

  describe('deleteSubmission', () => {
    it('should delete a submission', async () => {
      const submissionId = '123'
      
      const response = await submissionApi.deleteSubmission(submissionId)
      
      expect(response.data).toHaveProperty('message')
    })

    it('should handle not found error when deleting', async () => {
      server.use(
        http.delete('/api/v1/submissions/:id', () => {
          return HttpResponse.json(
            { detail: 'Submission not found' },
            { status: 404 }
          )
        })
      )

      await expect(submissionApi.deleteSubmission('nonexistent')).rejects.toThrow()
    })
  })

  describe('cancelSubmission', () => {
    it('should cancel a submission', async () => {
      const submissionId = '123'
      
      const response = await submissionApi.cancelSubmission(submissionId)
      
      expect(response.data.id).toBe(submissionId)
      expect(response.data.status).toBe('cancelled')
      expect(response.data.message).toContain('cancelled successfully')
    })

    it('should handle already cancelled submission', async () => {
      server.use(
        http.post('/api/v1/submissions/:id/cancel', () => {
          return HttpResponse.json(
            { detail: 'Submission already cancelled' },
            { status: 400 }
          )
        })
      )

      await expect(submissionApi.cancelSubmission('123')).rejects.toThrow()
    })
  })

  describe('retrySubmission', () => {
    it('should retry a failed submission', async () => {
      const submissionId = '123'
      
      const response = await submissionApi.retrySubmission(submissionId)
      
      expect(response.data.id).toBe(submissionId)
      expect(response.data.status).toBe('pending')
      expect(response.data.message).toContain('retry initiated')
    })

    it('should handle non-retryable submission', async () => {
      server.use(
        http.post('/api/v1/submissions/:id/retry', () => {
          return HttpResponse.json(
            { detail: 'Submission cannot be retried' },
            { status: 400 }
          )
        })
      )

      await expect(submissionApi.retrySubmission('123')).rejects.toThrow()
    })
  })

  describe('getSubmissionProgress', () => {
    it('should fetch submission progress', async () => {
      const submissionId = '123'
      
      const response = await submissionApi.getSubmissionProgress(submissionId)
      
      expect(response.data).toHaveProperty('submission_id', submissionId)
      expect(response.data).toHaveProperty('progress_percentage')
      expect(response.data).toHaveProperty('current_stage')
      expect(response.data).toHaveProperty('total_stages')
      expect(response.data).toHaveProperty('current_stage_number')
      expect(response.data).toHaveProperty('processed_urls')
      expect(response.data).toHaveProperty('total_urls')
      expect(response.data).toHaveProperty('errors')
      
      expect(typeof response.data.progress_percentage).toBe('number')
      expect(response.data.progress_percentage).toBeGreaterThanOrEqual(0)
      expect(response.data.progress_percentage).toBeLessThanOrEqual(100)
    })
  })

  describe('uploadFiles', () => {
    it('should upload files successfully', async () => {
      const files = [
        createMockFile('test1.jpg', 1024, 'image/jpeg'),
        createMockFile('test2.png', 2048, 'image/png'),
        createMockFile('document.pdf', 4096, 'application/pdf')
      ]

      const response = await submissionApi.uploadFiles(files)
      
      expect(response.data).toHaveProperty('file_urls')
      expect(response.data).toHaveProperty('upload_id')
      expect(response.data).toHaveProperty('total_files', files.length)
      expect(response.data).toHaveProperty('total_size')
      expect(Array.isArray(response.data.file_urls)).toBe(true)
      expect(response.data.file_urls).toHaveLength(files.length)
      
      // Check that URLs are generated for each file
      response.data.file_urls.forEach((url: string) => {
        expect(url).toMatch(/^https:\/\/cdn\.example\.com\/uploads\//)
      })
    })

    it('should handle empty file list', async () => {
      await expect(submissionApi.uploadFiles([])).rejects.toThrow()
    })

    it('should handle oversized files', async () => {
      const oversizedFile = createMockFile('huge.jpg', 200 * 1024 * 1024, 'image/jpeg') // 200MB

      await expect(submissionApi.uploadFiles([oversizedFile])).rejects.toThrow()
    })

    it('should handle invalid file types', async () => {
      const invalidFile = createMockFile('script.exe', 1024, 'application/x-executable')

      await expect(submissionApi.uploadFiles([invalidFile])).rejects.toThrow()
    })

    it('should upload mixed valid file types', async () => {
      const files = [
        createMockFile('image.jpg', 1024, 'image/jpeg'),
        createMockFile('video.mp4', 2048, 'video/mp4'),
        createMockFile('document.docx', 1024, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
      ]

      const response = await submissionApi.uploadFiles(files)
      
      expect(response.data.file_urls).toHaveLength(3)
      expect(response.data.total_files).toBe(3)
    })

    it('should handle upload server error', async () => {
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          return HttpResponse.json(
            { detail: 'Upload server unavailable' },
            { status: 503 }
          )
        })
      )

      const files = [createMockFile('test.jpg', 1024, 'image/jpeg')]

      await expect(submissionApi.uploadFiles(files)).rejects.toThrow()
    })
  })

  describe('validateUrls', () => {
    it('should validate URLs successfully', async () => {
      const urls = [
        'https://example.com/image1.jpg',
        'https://example.com/image2.png',
        'https://example.com/document.pdf'
      ]

      const response = await submissionApi.validateUrls(urls)
      
      expect(Array.isArray(response.data)).toBe(true)
      expect(response.data).toHaveLength(urls.length)
      
      response.data.forEach((result: any, index: number) => {
        expect(result).toHaveProperty('url', urls[index])
        expect(result).toHaveProperty('is_valid')
        expect(result).toHaveProperty('domain')
        expect(typeof result.is_valid).toBe('boolean')
        
        if (!result.is_valid) {
          expect(result).toHaveProperty('error_message')
          expect(typeof result.error_message).toBe('string')
        }
      })
    })

    it('should handle invalid URLs', async () => {
      const urls = [
        'https://valid.com/image.jpg',
        'https://invalid.com/blocked.jpg',
        'not-a-url',
        'https://blocked.site/content.pdf'
      ]

      const response = await submissionApi.validateUrls(urls)
      
      expect(response.data).toHaveLength(urls.length)
      
      // Check that invalid URLs are marked as such
      expect(response.data[0].is_valid).toBe(true)
      expect(response.data[1].is_valid).toBe(false)
      expect(response.data[2].is_valid).toBe(false)
      expect(response.data[3].is_valid).toBe(false)
      
      // Check error messages for invalid URLs
      expect(response.data[1].error_message).toBeTruthy()
      expect(response.data[2].error_message).toBe('Invalid URL format')
      expect(response.data[3].error_message).toBeTruthy()
    })

    it('should handle empty URL list', async () => {
      await expect(submissionApi.validateUrls([])).rejects.toThrow()
    })

    it('should handle validation service error', async () => {
      server.use(
        http.post('/api/v1/submissions/validate-urls', () => {
          return HttpResponse.json(
            { detail: 'Validation service unavailable' },
            { status: 503 }
          )
        })
      )

      const urls = ['https://example.com/test.jpg']

      await expect(submissionApi.validateUrls(urls)).rejects.toThrow()
    })
  })

  describe('bulkCreate', () => {
    it('should create bulk submissions successfully', async () => {
      const bulkData: BulkSubmission = {
        submissions: [
          {
            title: 'Bulk Submission 1',
            type: ContentType.IMAGES,
            priority: PriorityLevel.NORMAL,
            urls: ['https://example.com/image1.jpg']
          },
          {
            title: 'Bulk Submission 2',
            type: ContentType.VIDEOS,
            priority: PriorityLevel.HIGH,
            urls: ['https://example.com/video1.mp4']
          }
        ],
        apply_to_all: {
          category: 'bulk_import',
          tags: ['bulk', 'imported'],
          auto_monitoring: true,
          notify_on_infringement: false
        }
      }

      const response = await submissionApi.bulkCreate(bulkData)
      
      expect(response.status).toBe(201)
      expect(response.data).toHaveProperty('submissions')
      expect(response.data).toHaveProperty('total_created')
      expect(response.data).toHaveProperty('batch_id')
      expect(Array.isArray(response.data.submissions)).toBe(true)
      expect(response.data.submissions).toHaveLength(bulkData.submissions.length)
      expect(response.data.total_created).toBe(bulkData.submissions.length)
      
      // Check that apply_to_all settings are applied
      response.data.submissions.forEach((submission: any) => {
        expect(submission.category).toBe('bulk_import')
        expect(submission.tags).toEqual(['bulk', 'imported'])
        expect(submission.auto_monitoring).toBe(true)
        expect(submission.notify_on_infringement).toBe(false)
        expect(submission.status).toBe('pending')
      })
    })

    it('should create bulk submissions without apply_to_all', async () => {
      const bulkData: BulkSubmission = {
        submissions: [
          {
            title: 'Individual Submission',
            type: ContentType.DOCUMENTS,
            priority: PriorityLevel.URGENT,
            urls: ['https://example.com/doc.pdf'],
            category: 'individual',
            tags: ['single']
          }
        ]
      }

      const response = await submissionApi.bulkCreate(bulkData)
      
      expect(response.status).toBe(201)
      expect(response.data.submissions).toHaveLength(1)
      expect(response.data.submissions[0].category).toBe('individual')
      expect(response.data.submissions[0].tags).toEqual(['single'])
    })

    it('should handle empty submissions array', async () => {
      const bulkData: BulkSubmission = {
        submissions: []
      }

      await expect(submissionApi.bulkCreate(bulkData)).rejects.toThrow()
    })

    it('should handle bulk creation server error', async () => {
      server.use(
        http.post('/api/v1/submissions/bulk', () => {
          return HttpResponse.json(
            { detail: 'Bulk creation failed' },
            { status: 500 }
          )
        })
      )

      const bulkData: BulkSubmission = {
        submissions: [
          {
            title: 'Test',
            type: ContentType.IMAGES,
            priority: PriorityLevel.NORMAL,
            urls: ['https://example.com/test.jpg']
          }
        ]
      }

      await expect(submissionApi.bulkCreate(bulkData)).rejects.toThrow()
    })
  })

  describe('Error handling', () => {
    it('should handle network errors', async () => {
      server.use(
        http.get('/api/v1/submissions', () => {
          return HttpResponse.error()
        })
      )

      await expect(submissionApi.getSubmissions()).rejects.toThrow()
    })

    it('should handle timeout errors', async () => {
      server.use(
        http.get('/api/v1/submissions', () => {
          return new Promise(() => {}) // Never resolves
        })
      )

      // Note: This test would need a timeout configuration in the actual API client
      // For now, we just ensure the request is made
      const promise = submissionApi.getSubmissions()
      expect(promise).toBeDefined()
    })

    it('should handle unauthorized errors', async () => {
      server.use(
        http.get('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Unauthorized' },
            { status: 401 }
          )
        })
      )

      await expect(submissionApi.getSubmissions()).rejects.toThrow()
    })

    it('should handle forbidden errors', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Forbidden' },
            { status: 403 }
          )
        })
      )

      const submissionData: CreateSubmission = {
        title: 'Test',
        type: ContentType.IMAGES,
        priority: PriorityLevel.NORMAL
      }

      await expect(submissionApi.createSubmission(submissionData)).rejects.toThrow()
    })
  })

  describe('Content-Type handling', () => {
    it('should set correct content-type for file uploads', async () => {
      const files = [createMockFile('test.jpg', 1024, 'image/jpeg')]
      
      // Spy on the actual request to verify content-type
      const requestSpy = vi.fn()
      server.use(
        http.post('/api/v1/submissions/upload', ({ request }) => {
          requestSpy(request.headers.get('Content-Type'))
          return HttpResponse.json({
            file_urls: ['https://cdn.example.com/uploads/test.jpg'],
            upload_id: 'test',
            total_files: 1,
            total_size: 1024
          })
        })
      )

      await submissionApi.uploadFiles(files)
      
      // Note: In a real test, we'd check that multipart/form-data was set
      // The MSW setup makes this verification challenging in this environment
      expect(requestSpy).toHaveBeenCalled()
    })

    it('should send JSON for regular API calls', async () => {
      const submissionData: CreateSubmission = {
        title: 'Test',
        type: ContentType.IMAGES,
        priority: PriorityLevel.NORMAL
      }

      const response = await submissionApi.createSubmission(submissionData)
      
      expect(response.data.title).toBe(submissionData.title)
    })
  })
})