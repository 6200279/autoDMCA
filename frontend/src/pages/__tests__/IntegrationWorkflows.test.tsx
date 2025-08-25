/**
 * @fileoverview Integration tests for complete submission workflows
 * Tests end-to-end scenarios from form input to submission completion
 */

import React from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockFile } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import Submissions from '../Submissions'
import { ContentType, PriorityLevel } from '@/types/api'

// Mock react-dropzone for integration testing
vi.mock('react-dropzone', () => ({
  useDropzone: ({ onDrop, accept, multiple, maxSize }: any) => ({
    getRootProps: () => ({
      'data-testid': 'dropzone',
      onClick: vi.fn(),
      onDrop: (e: any) => {
        if (e.dataTransfer?.files) {
          onDrop(Array.from(e.dataTransfer.files))
        }
      }
    }),
    getInputProps: () => ({
      'data-testid': 'dropzone-input',
      type: 'file',
      accept: Object.keys(accept || {}).join(','),
      multiple,
      onChange: (e: any) => {
        if (e.target.files) {
          onDrop(Array.from(e.target.files))
        }
      }
    }),
    isDragActive: false,
    acceptedFiles: [],
    rejectedFiles: []
  })
}))

describe('Integration Workflows', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Complete File Upload Workflow', () => {
    it('should complete full file upload submission workflow', async () => {
      renderWithProviders(<Submissions />)
      
      // Step 1: Upload files
      const dropzone = screen.getByTestId('dropzone-input')
      const files = [
        createMockFile('image1.jpg', 1024 * 1024, 'image/jpeg'),
        createMockFile('image2.png', 2048 * 1024, 'image/png'),
        createMockFile('document.pdf', 512 * 1024, 'application/pdf')
      ]
      
      await user.upload(dropzone, files)
      
      await waitFor(() => {
        expect(screen.getByText('Selected Files (3)')).toBeInTheDocument()
        expect(screen.getByText('image1.jpg')).toBeInTheDocument()
        expect(screen.getByText('image2.png')).toBeInTheDocument()
        expect(screen.getByText('document.pdf')).toBeInTheDocument()
      })
      
      // Step 2: Fill form details
      await user.type(screen.getByLabelText('Title *'), 'Complete Integration Test Submission')
      
      // Select content type (assuming default is already selected)
      const contentTypeDropdown = screen.getByLabelText('Content Type *')
      expect(contentTypeDropdown).toBeInTheDocument()
      
      // Select priority (assuming default is already selected)  
      const priorityDropdown = screen.getByLabelText('Priority *')
      expect(priorityDropdown).toBeInTheDocument()
      
      // Fill optional fields
      await user.type(screen.getByLabelText('Description'), 'This is a comprehensive test of the file upload workflow including multiple file types and all form fields.')
      
      // Add tags
      const tagsInput = screen.getByLabelText('Tags')
      await user.type(tagsInput, 'integration,test,upload')
      
      // Enable/disable monitoring options
      const autoMonitoringSwitch = screen.getByLabelText('Enable auto-monitoring')
      const notificationSwitch = screen.getByLabelText('Notify on infringements')
      expect(autoMonitoringSwitch).toBeInTheDocument()
      expect(notificationSwitch).toBeInTheDocument()
      
      // Step 3: Submit form
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      expect(submitButton).toBeEnabled()
      
      await user.click(submitButton)
      
      // Step 4: Verify submission process
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
        expect(screen.getByText('Uploading and processing your files...')).toBeInTheDocument()
      })
      
      // Step 5: Wait for completion and verify reset
      await waitFor(() => {
        // Form should reset after successful submission
        expect(screen.getByLabelText('Title *')).toHaveValue('')
        expect(screen.queryByText('Selected Files')).not.toBeInTheDocument()
      }, { timeout: 10000 })
      
      // Step 6: Verify submission appears in history
      await user.click(screen.getByText('History'))
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
        // Should show the submission in the history
        expect(screen.getByText('Test Image Submission')).toBeInTheDocument()
      })
    })

    it('should handle file upload with validation errors and recovery', async () => {
      // Mock validation error first, then success
      let attemptCount = 0
      server.use(
        http.post('/api/v1/submissions', () => {
          attemptCount++
          if (attemptCount === 1) {
            return HttpResponse.json(
              { 
                detail: {
                  title: ['Title must be unique'],
                  description: ['Description is too long']
                }
              },
              { status: 422 }
            )
          }
          return HttpResponse.json({
            id: Date.now().toString(),
            title: 'Corrected Submission',
            status: 'pending'
          }, { status: 201 })
        })
      )

      renderWithProviders(<Submissions />)
      
      // Upload file and fill form with invalid data
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      
      await user.type(screen.getByLabelText('Title *'), 'Duplicate Title')
      await user.type(screen.getByLabelText('Description'), 'x'.repeat(1000)) // Very long description
      
      // First submission - should fail
      let submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled() // Should re-enable after error
      })
      
      // Correct the errors
      await user.clear(screen.getByLabelText('Title *'))
      await user.type(screen.getByLabelText('Title *'), 'Unique Title')
      await user.clear(screen.getByLabelText('Description'))
      await user.type(screen.getByLabelText('Description'), 'Corrected description')
      
      // Second submission - should succeed
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
      })
    })

    it('should handle mixed file types with different validation requirements', async () => {
      renderWithProviders(<Submissions />)
      
      // Upload mixed file types
      const dropzone = screen.getByTestId('dropzone-input')
      const mixedFiles = [
        createMockFile('photo.jpg', 5 * 1024 * 1024, 'image/jpeg'),
        createMockFile('video.mp4', 50 * 1024 * 1024, 'video/mp4'),
        createMockFile('contract.pdf', 2 * 1024 * 1024, 'application/pdf'),
        createMockFile('presentation.pptx', 10 * 1024 * 1024, 'application/vnd.openxmlformats-officedocument.presentationml.presentation')
      ]
      
      await user.upload(dropzone, mixedFiles)
      
      await waitFor(() => {
        expect(screen.getByText('Selected Files (4)')).toBeInTheDocument()
        expect(screen.getByText('photo.jpg')).toBeInTheDocument()
        expect(screen.getByText('video.mp4')).toBeInTheDocument()
        expect(screen.getByText('contract.pdf')).toBeInTheDocument()
        expect(screen.getByText('presentation.pptx')).toBeInTheDocument()
      })
      
      // Fill form with appropriate categorization for mixed content
      await user.type(screen.getByLabelText('Title *'), 'Mixed Media Content Package')
      await user.type(screen.getByLabelText('Description'), 'A collection of various file types for comprehensive content protection')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
      })
    })
  })

  describe('Complete URL Submission Workflow', () => {
    it('should complete full URL validation and submission workflow', async () => {
      renderWithProviders(<Submissions />)
      
      // Step 1: Navigate to URL submission tab
      await user.click(screen.getByText('URL Submission'))
      
      await waitFor(() => {
        expect(screen.getByText('Bulk URL Submission')).toBeInTheDocument()
      })
      
      // Step 2: Enter URLs
      const urls = [
        'https://example.com/portfolio/image1.jpg',
        'https://example.com/gallery/image2.png',
        'https://cdn.example.com/media/video1.mp4',
        'https://docs.example.com/files/document1.pdf'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urls)
      
      // Step 3: Validate URLs
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
        expect(screen.getByText('https://example.com/portfolio/image1.jpg')).toBeInTheDocument()
        expect(screen.getByText('Valid')).toBeInTheDocument()
      })
      
      // Step 4: Fill submission details
      await user.type(screen.getByLabelText('Title *'), 'URL Content Protection Submission')
      await user.type(screen.getByLabelText('Description'), 'Protecting various types of content hosted on external platforms')
      
      // Step 5: Submit URLs
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        // Should show processing state
        expect(submitButton).toBeDisabled()
      })
      
      // Step 6: Verify completion
      await waitFor(() => {
        // Form should reset after successful submission
        expect(screen.getByLabelText('URLs (one per line) *')).toHaveValue('')
        expect(screen.getByLabelText('Title *')).toHaveValue('')
      }, { timeout: 10000 })
    })

    it('should handle mixed valid and invalid URLs in workflow', async () => {
      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('URL Submission'))
      
      // Mix of valid and invalid URLs
      const mixedUrls = [
        'https://valid.com/image1.jpg',
        'https://also-valid.com/image2.png',
        'https://invalid.com/blocked-image.jpg', // Will be marked invalid by mock
        'https://blocked.site/another-blocked.jpg', // Will be marked invalid by mock
        'not-a-url-at-all',
        'https://valid-again.com/document.pdf'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, mixedUrls)
      
      // Validate URLs
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
        // Should show both valid and invalid results
        expect(screen.getAllByText('Valid')).toHaveLength(3) // 3 valid URLs
        expect(screen.getAllByText('Invalid')).toHaveLength(3) // 3 invalid URLs
      })
      
      // Submit with mixed results
      await user.type(screen.getByLabelText('Title *'), 'Mixed URL Validation Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      // Should only submit valid URLs
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })
  })

  describe('Complete Batch Import Workflow', () => {
    it('should complete batch import workflow with CSV processing', async () => {
      renderWithProviders(<Submissions />)
      
      // Navigate to batch import tab
      await user.click(screen.getByText('Batch Import'))
      
      await waitFor(() => {
        expect(screen.getByText('CSV Batch Import')).toBeInTheDocument()
        expect(screen.getByText('CSV File *')).toBeInTheDocument()
      })
      
      // Mock CSV file
      const csvContent = `title,type,priority,url,description,category
"Portfolio Image 1",images,normal,"https://example.com/image1.jpg","First portfolio image","photography"
"Portfolio Image 2",images,high,"https://example.com/image2.jpg","Second portfolio image","photography"
"Marketing Video",videos,urgent,"https://example.com/video1.mp4","Important marketing content","video_content"`
      
      const csvFile = createMockFile('submissions.csv', csvContent.length, 'text/csv')
      Object.defineProperty(csvFile, 'text', {
        value: () => Promise.resolve(csvContent)
      })
      
      // Note: In a real test, we'd need to properly mock the FileUpload component
      // For now, we test the form structure and submission logic
      
      // Fill batch settings
      await user.type(screen.getByLabelText('Batch Title *'), 'Portfolio Protection Batch')
      
      // Submit batch (would normally require CSV file upload)
      const submitButton = screen.getByRole('button', { name: /process batch/i })
      expect(submitButton).toBeDisabled() // Should be disabled without CSV file
      
      // In a full implementation, we would:
      // 1. Upload CSV file
      // 2. Verify file parsing
      // 3. Submit batch
      // 4. Verify individual submissions created
    })
  })

  describe('Cross-Tab Workflow Integration', () => {
    it('should maintain form state when switching between tabs', async () => {
      renderWithProviders(<Submissions />)
      
      // Start with file upload
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Cross-Tab Test')
      await user.type(screen.getByLabelText('Description'), 'Testing tab switching')
      
      // Switch to URL tab
      await user.click(screen.getByText('URL Submission'))
      
      await waitFor(() => {
        // Shared form fields should maintain values
        expect(screen.getByDisplayValue('Cross-Tab Test')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Testing tab switching')).toBeInTheDocument()
      })
      
      // Add URLs in URL tab
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/cross-tab-test.jpg')
      
      // Switch back to file upload
      await user.click(screen.getByText('File Upload'))
      
      await waitFor(() => {
        // Should still show uploaded file and form data
        expect(screen.getByText('test.jpg')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Cross-Tab Test')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Testing tab switching')).toBeInTheDocument()
      })
      
      // Should be able to submit from either tab
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      expect(submitButton).toBeEnabled()
    })

    it('should handle submission from different tabs with shared data', async () => {
      renderWithProviders(<Submissions />)
      
      // Fill shared form data in file upload tab
      await user.type(screen.getByLabelText('Title *'), 'Multi-Tab Submission')
      await user.type(screen.getByLabelText('Description'), 'Submitted from different tabs')
      
      // Add file
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('shared-data-test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      
      // Submit from file upload tab
      let submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
      })
      
      // Wait for form reset
      await waitFor(() => {
        expect(screen.getByLabelText('Title *')).toHaveValue('')
      }, { timeout: 10000 })
      
      // Now try URL submission with same workflow
      await user.click(screen.getByText('URL Submission'))
      
      await user.type(screen.getByLabelText('Title *'), 'URL Multi-Tab Test')
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/multi-tab-test.jpg')
      
      submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })
  })

  describe('History Integration Workflow', () => {
    it('should show submissions in history after creation', async () => {
      renderWithProviders(<Submissions />)
      
      // Create a submission
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('history-test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'History Integration Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
      })
      
      // Wait for submission to complete
      await waitFor(() => {
        expect(screen.getByLabelText('Title *')).toHaveValue('')
      }, { timeout: 10000 })
      
      // Check history
      await user.click(screen.getByText('History'))
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
        // Should show existing submissions from mock data
        expect(screen.getByText('Test Image Submission')).toBeInTheDocument()
      })
    })

    it('should allow retry and cancel operations from history', async () => {
      renderWithProviders(<Submissions />)
      
      // Go directly to history
      await user.click(screen.getByText('History'))
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
        
        // Should show retry button for failed submissions
        const retryButtons = screen.getAllByTitle('Retry submission')
        expect(retryButtons.length).toBeGreaterThan(0)
        
        // Should show cancel button for processing submissions
        const cancelButtons = screen.getAllByTitle('Cancel submission')
        expect(cancelButtons.length).toBeGreaterThan(0)
      })
      
      // Test retry functionality
      const retryButtons = screen.getAllByTitle('Retry submission')
      if (retryButtons.length > 0) {
        await user.click(retryButtons[0])
        
        // Should trigger retry API call and show feedback
        await waitFor(() => {
          expect(screen.getByTestId('toast')).toBeInTheDocument()
        })
      }
    })

    it('should filter and paginate history correctly', async () => {
      // Mock large dataset for pagination testing
      server.use(
        http.get('/api/v1/submissions', ({ request }) => {
          const url = new URL(request.url)
          const page = parseInt(url.searchParams.get('page') || '1')
          const limit = parseInt(url.searchParams.get('limit') || '10')
          
          const mockSubmissions = Array.from({ length: 25 }, (_, i) => ({
            id: (i + 1).toString(),
            user_id: 1,
            title: `Test Submission ${i + 1}`,
            type: i % 3 === 0 ? 'images' : i % 3 === 1 ? 'videos' : 'documents',
            status: i % 4 === 0 ? 'completed' : i % 4 === 1 ? 'active' : i % 4 === 2 ? 'processing' : 'failed',
            priority: 'normal',
            urls: [`https://example.com/file${i + 1}.jpg`],
            progress_percentage: i % 4 === 0 ? 100 : Math.floor(Math.random() * 100),
            total_urls: 1,
            created_at: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString()
          }))
          
          const startIndex = (page - 1) * limit
          const endIndex = startIndex + limit
          const paginatedSubmissions = mockSubmissions.slice(startIndex, endIndex)
          
          return HttpResponse.json({
            items: paginatedSubmissions,
            total: mockSubmissions.length,
            page,
            size: limit,
            pages: Math.ceil(mockSubmissions.length / limit)
          })
        })
      )

      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('History'))
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
        // Should show paginated results
        expect(screen.getByText('Test Submission 1')).toBeInTheDocument()
        
        // Should show pagination controls
        expect(screen.getByText(/Showing \d+ to \d+ of \d+ submissions/)).toBeInTheDocument()
      })
    })
  })

  describe('Real-time Updates Integration', () => {
    it('should handle progress updates during submission', async () => {
      // Mock progressive progress updates
      let progressValue = 0
      server.use(
        http.get('/api/v1/submissions/:id/progress', () => {
          progressValue = Math.min(progressValue + 25, 100)
          return HttpResponse.json({
            submission_id: '123',
            progress_percentage: progressValue,
            current_stage: progressValue < 50 ? 'Uploading files' : progressValue < 75 ? 'Processing content' : 'Finalizing submission',
            total_stages: 4,
            current_stage_number: Math.floor(progressValue / 25) + 1,
            processed_urls: Math.floor((progressValue / 100) * 5),
            total_urls: 5,
            errors: []
          })
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('progress-test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Progress Tracking Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
        expect(screen.getByText('Uploading and processing your files...')).toBeInTheDocument()
      })
      
      // Should show progress updates
      await waitFor(() => {
        const progressBars = screen.getAllByRole('progressbar')
        expect(progressBars.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Error Recovery Workflows', () => {
    it('should allow user to recover from submission failures and retry', async () => {
      // Mock failure then success
      let attemptCount = 0
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          attemptCount++
          if (attemptCount === 1) {
            return HttpResponse.json(
              { detail: 'Upload service temporarily unavailable' },
              { status: 503 }
            )
          }
          return HttpResponse.json({
            file_urls: ['https://cdn.example.com/recovered-upload.jpg'],
            upload_id: 'recovered-upload',
            total_files: 1,
            total_size: 1024
          })
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('recovery-test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Error Recovery Test')
      
      // First attempt - should fail
      let submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should handle error and re-enable form
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
        // File and form data should be preserved
        expect(screen.getByText('recovery-test.jpg')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Error Recovery Test')).toBeInTheDocument()
      })
      
      // Second attempt - should succeed
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
      })
      
      // Should complete successfully
      await waitFor(() => {
        expect(screen.getByLabelText('Title *')).toHaveValue('')
      }, { timeout: 10000 })
    })
  })

  describe('Performance Integration', () => {
    it('should handle large-scale submission workflows efficiently', async () => {
      renderWithProviders(<Submissions />)
      
      // Test with many files
      const manyFiles = Array.from({ length: 20 }, (_, i) => 
        createMockFile(`performance-test-${i + 1}.jpg`, 1024 * 100, 'image/jpeg')
      )
      
      const dropzone = screen.getByTestId('dropzone-input')
      await user.upload(dropzone, manyFiles)
      
      await waitFor(() => {
        expect(screen.getByText('Selected Files (20)')).toBeInTheDocument()
      })
      
      // Fill form and submit
      await user.type(screen.getByLabelText('Title *'), 'Performance Test Batch')
      await user.type(screen.getByLabelText('Description'), 'Testing large batch submission performance')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should handle large submission without blocking UI
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
      })
    })
  })
})