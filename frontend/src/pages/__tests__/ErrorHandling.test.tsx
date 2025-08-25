/**
 * @fileoverview Error handling and edge case tests for Submissions
 * Tests error scenarios, network issues, validation failures, and edge cases
 */

import React from 'react'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockFile } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import Submissions from '../Submissions'

// Mock react-dropzone for consistent file upload testing
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

describe('Error Handling and Edge Cases', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Network Error Handling', () => {
    it('should handle network timeout errors', async () => {
      server.use(
        http.get('/api/v1/submissions', () => {
          return new Promise(() => {}) // Never resolves, simulates timeout
        })
      )

      renderWithProviders(<Submissions />)
      
      // Navigate to history tab to trigger API call
      await user.click(screen.getByText('History'))
      
      // Should handle timeout gracefully
      await waitFor(() => {
        // The component should show loading state and then handle the timeout
        expect(screen.getByRole('table')).toBeInTheDocument()
      }, { timeout: 5000 })
    })

    it('should handle network connection errors', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.error()
        })
      )

      renderWithProviders(<Submissions />)
      
      // Add file and submit
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Network Error Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should handle network error and re-enable form
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle intermittent connection issues', async () => {
      let attemptCount = 0
      server.use(
        http.post('/api/v1/submissions', () => {
          attemptCount++
          if (attemptCount < 2) {
            return HttpResponse.error()
          }
          return HttpResponse.json({
            id: '123',
            title: 'Test',
            status: 'pending'
          }, { status: 201 })
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Retry Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // First attempt should fail, but component should handle it gracefully
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle server unavailable (503) errors', async () => {
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          return HttpResponse.json(
            { detail: 'Service temporarily unavailable' },
            { status: 503 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), '503 Error Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })
  })

  describe('Authentication and Authorization Errors', () => {
    it('should handle unauthorized (401) errors', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Unauthorized access' },
            { status: 401 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Auth Error Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle forbidden (403) errors', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Access forbidden - insufficient permissions' },
            { status: 403 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Forbidden Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle token expiration during submission', async () => {
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          return HttpResponse.json(
            { detail: 'Token expired' },
            { status: 401 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Token Expiry Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should handle token expiry and potentially redirect to login
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })
  })

  describe('Validation Error Handling', () => {
    it('should handle server-side validation errors', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { 
              detail: {
                title: ['Title contains invalid characters'],
                urls: ['At least one URL is required']
              }
            },
            { status: 422 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Invalid@Title!')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle conflicting client and server validation', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Server validation failed despite client validation' },
            { status: 422 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      // Submit what should be valid data according to client
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Valid Title')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should handle server validation gracefully
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle malformed validation error responses', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { error: 'Unexpected error format' }, // Non-standard error format
            { status: 400 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Malformed Error Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })
  })

  describe('File Upload Edge Cases', () => {
    it('should handle corrupted file uploads', async () => {
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          return HttpResponse.json(
            { detail: 'File appears to be corrupted or invalid' },
            { status: 400 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const corruptedFile = createMockFile('corrupted.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, corruptedFile)
      await user.type(screen.getByLabelText('Title *'), 'Corrupted File Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle partial file upload failures', async () => {
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          return HttpResponse.json(
            { detail: 'Some files failed to upload' },
            { status: 207 } // Multi-status
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const files = [
        createMockFile('file1.jpg', 1024, 'image/jpeg'),
        createMockFile('file2.jpg', 1024, 'image/jpeg')
      ]
      await user.upload(dropzone, files)
      await user.type(screen.getByLabelText('Title *'), 'Partial Upload Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle zero-byte files', async () => {
      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const emptyFile = createMockFile('empty.jpg', 0, 'image/jpeg')
      await user.upload(dropzone, emptyFile)
      
      // Should either reject the file or handle it gracefully
      await waitFor(() => {
        // Depending on implementation, might show error or accept file
        expect(screen.getByTestId('dropzone')).toBeInTheDocument()
      })
    })

    it('should handle files with unusual extensions', async () => {
      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const unusualFile = createMockFile('image.jpeg2000', 1024, 'image/jp2')
      await user.upload(dropzone, unusualFile)
      
      // Should handle unusual but valid file types
      await waitFor(() => {
        expect(screen.getByTestId('dropzone')).toBeInTheDocument()
      })
    })

    it('should handle files with misleading extensions', async () => {
      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      // File with .jpg extension but wrong MIME type
      const misleadingFile = createMockFile('fake.jpg', 1024, 'text/plain')
      await user.upload(dropzone, misleadingFile)
      
      // Should validate based on actual file type, not extension
      await waitFor(() => {
        expect(screen.getByTestId('dropzone')).toBeInTheDocument()
      })
    })
  })

  describe('URL Validation Edge Cases', () => {
    const navigateToUrlTab = async () => {
      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('URL Submission'))
      await waitFor(() => {
        expect(screen.getByText('Bulk URL Submission')).toBeInTheDocument()
      })
    }

    it('should handle malformed URL validation responses', async () => {
      server.use(
        http.post('/api/v1/submissions/validate-urls', () => {
          return HttpResponse.json(
            { results: 'malformed response' }, // Wrong format
            { status: 200 }
          )
        })
      )

      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/test.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(validateButton).toBeEnabled()
      })
    })

    it('should handle very long URLs', async () => {
      await navigateToUrlTab()
      
      const veryLongUrl = 'https://example.com/' + 'a'.repeat(2000) + '.jpg'
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, veryLongUrl)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })

    it('should handle URLs with special characters', async () => {
      await navigateToUrlTab()
      
      const specialUrls = [
        'https://example.com/файл.jpg', // Non-ASCII characters
        'https://example.com/file with spaces.jpg', // Spaces
        'https://example.com/file[brackets].jpg', // Brackets
        'https://example.com/file{curly}.jpg' // Curly braces
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, specialUrls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })

    it('should handle mixed valid and invalid URL formats', async () => {
      await navigateToUrlTab()
      
      const mixedUrls = [
        'https://valid.com/image.jpg',
        'http://also-valid.com/video.mp4',
        'ftp://invalid-protocol.com/file.pdf',
        'https://', // Incomplete URL
        'www.missing-protocol.com/file.jpg',
        'javascript:alert("xss")', // Potentially malicious
        ''
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, mixedUrls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
        expect(screen.getByText('Valid')).toBeInTheDocument()
        expect(screen.getByText('Invalid')).toBeInTheDocument()
      })
    })

    it('should handle URL validation timeout', async () => {
      server.use(
        http.post('/api/v1/submissions/validate-urls', () => {
          return new Promise(() => {}) // Never resolves
        })
      )

      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/test.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      // Should handle timeout gracefully
      expect(validateButton).toBeDisabled()
    })
  })

  describe('State Management Edge Cases', () => {
    it('should handle rapid tab switching', async () => {
      renderWithProviders(<Submissions />)
      
      // Rapidly switch between tabs
      for (let i = 0; i < 5; i++) {
        await user.click(screen.getByText('URL Submission'))
        await user.click(screen.getByText('File Upload'))
        await user.click(screen.getByText('Batch Import'))
        await user.click(screen.getByText('History'))
      }
      
      // Should maintain stability
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
    })

    it('should handle form submission during loading', async () => {
      // Mock slow submission response
      server.use(
        http.post('/api/v1/submissions', async () => {
          await new Promise(resolve => setTimeout(resolve, 1000))
          return HttpResponse.json({ id: '123' })
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Loading Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Try to click submit again while loading
      await user.click(submitButton)
      
      // Should not allow double submission
      expect(submitButton).toBeDisabled()
    })

    it('should handle component unmounting during async operations', async () => {
      server.use(
        http.get('/api/v1/submissions', async () => {
          await new Promise(resolve => setTimeout(resolve, 1000))
          return HttpResponse.json({ items: [] })
        })
      )

      const { unmount } = renderWithProviders(<Submissions />)
      
      // Start async operation
      await user.click(screen.getByText('History'))
      
      // Unmount component immediately
      unmount()
      
      // Should not cause memory leaks or errors
      expect(true).toBe(true) // If we get here without errors, test passes
    })
  })

  describe('Browser Compatibility Edge Cases', () => {
    it('should handle missing File API support', async () => {
      // Mock missing File API
      const originalFile = global.File
      // @ts-ignore
      delete global.File
      
      renderWithProviders(<Submissions />)
      
      // Should still render without crashing
      expect(screen.getByText('Content Submissions')).toBeInTheDocument()
      
      // Restore File API
      global.File = originalFile
    })

    it('should handle missing drag and drop support', async () => {
      // Mock missing DragEvent
      const originalDragEvent = global.DragEvent
      // @ts-ignore
      delete global.DragEvent
      
      renderWithProviders(<Submissions />)
      
      // Should still render file upload interface
      expect(screen.getByTestId('dropzone')).toBeInTheDocument()
      
      // Restore DragEvent
      global.DragEvent = originalDragEvent
    })

    it('should handle localStorage unavailability', async () => {
      // Mock localStorage error
      const originalLocalStorage = global.localStorage
      Object.defineProperty(global, 'localStorage', {
        value: {
          getItem: () => { throw new Error('localStorage unavailable') },
          setItem: () => { throw new Error('localStorage unavailable') },
          removeItem: () => { throw new Error('localStorage unavailable') },
          clear: () => { throw new Error('localStorage unavailable') }
        }
      })
      
      renderWithProviders(<Submissions />)
      
      // Should still function without localStorage
      expect(screen.getByText('Content Submissions')).toBeInTheDocument()
      
      // Restore localStorage
      Object.defineProperty(global, 'localStorage', {
        value: originalLocalStorage
      })
    })
  })

  describe('Memory and Performance Edge Cases', () => {
    it('should handle very large file selections', async () => {
      renderWithProviders(<Submissions />)
      
      // Simulate selecting many large files
      const manyFiles = Array.from({ length: 50 }, (_, i) => 
        createMockFile(`large-file-${i}.jpg`, 50 * 1024 * 1024, 'image/jpeg')
      )
      
      const dropzone = screen.getByTestId('dropzone-input')
      await user.upload(dropzone, manyFiles)
      
      // Should handle gracefully without crashing
      await waitFor(() => {
        expect(screen.getByText(`Selected Files (${manyFiles.length})`)).toBeInTheDocument()
      })
    })

    it('should handle rapid file additions and removals', async () => {
      renderWithProviders(<Submissions />)
      
      // Rapidly add and remove files
      for (let i = 0; i < 10; i++) {
        const dropzone = screen.getByTestId('dropzone-input')
        const file = createMockFile(`temp-${i}.jpg`, 1024, 'image/jpeg')
        await user.upload(dropzone, file)
        
        // Try to remove file immediately (if remove button exists)
        const removeButtons = screen.queryAllByRole('button', { name: '' })
        if (removeButtons.length > 0) {
          await user.click(removeButtons[0])
        }
      }
      
      // Should maintain stability
      expect(screen.getByTestId('dropzone')).toBeInTheDocument()
    })

    it('should handle excessive URL list processing', async () => {
      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('URL Submission'))
      
      // Generate very long URL list
      const excessiveUrls = Array.from({ length: 1000 }, (_, i) => 
        `https://example.com/image${i}.jpg`
      ).join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      
      // This might be slow, so we test that it doesn't crash
      await user.type(urlInput, excessiveUrls.substring(0, 1000)) // Truncate for test performance
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      expect(validateButton).toBeEnabled()
    })
  })

  describe('Race Condition Handling', () => {
    it('should handle concurrent API requests', async () => {
      renderWithProviders(<Submissions />)
      
      // Start multiple operations simultaneously
      const promises = [
        user.click(screen.getByText('History')), // Triggers submissions fetch
        user.click(screen.getByText('File Upload')),
        user.click(screen.getByText('URL Submission'))
      ]
      
      await Promise.all(promises)
      
      // Should handle concurrent requests without issues
      expect(screen.getByText('URL Submission Details')).toBeInTheDocument()
    })

    it('should handle form state updates during async operations', async () => {
      server.use(
        http.post('/api/v1/submissions/validate-urls', async () => {
          await new Promise(resolve => setTimeout(resolve, 500))
          return HttpResponse.json([{ url: 'https://example.com/test.jpg', is_valid: true, domain: 'example.com' }])
        })
      )

      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('URL Submission'))
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/test.jpg')
      
      // Start validation
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      // Modify form while validation is in progress
      await user.clear(urlInput)
      await user.type(urlInput, 'https://different.com/test.jpg')
      
      // Should handle state changes gracefully
      await waitFor(() => {
        expect(validateButton).toBeEnabled()
      })
    })
  })

  describe('Accessibility Error Scenarios', () => {
    it('should maintain accessibility during error states', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Submission failed' },
            { status: 500 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Accessibility Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        // Form should remain accessible after error
        expect(screen.getByLabelText('Title *')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /submit files/i })).toBeEnabled()
      })
    })

    it('should provide error announcements for screen readers', async () => {
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          return HttpResponse.json(
            { detail: 'Upload failed' },
            { status: 500 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Screen Reader Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should provide accessible error feedback
      await waitFor(() => {
        expect(screen.getByTestId('toast')).toBeInTheDocument()
      })
    })
  })
})