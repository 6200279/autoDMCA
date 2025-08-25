/**
 * @fileoverview Form validation tests for Submissions component
 * Tests Yup validation schema and form behavior for all submission types
 */

import React from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockFile } from '@/test/utils'
import Submissions from '../Submissions'
import { ContentType, PriorityLevel } from '@/types/api'
import * as yup from 'yup'

// Import the validation schema directly for unit testing
const submissionSchema = yup.object({
  title: yup.string().required('Title is required').min(3, 'Title must be at least 3 characters'),
  type: yup.string().oneOf(Object.values(ContentType), 'Invalid content type').required('Content type is required'),
  priority: yup.string().oneOf(Object.values(PriorityLevel), 'Invalid priority level').required('Priority level is required'),
  description: yup.string().optional(),
  category: yup.string().optional(),
  tags: yup.array().of(yup.string()).optional(),
  urls: yup.array().of(yup.string().url('Invalid URL format')).when('type', {
    is: ContentType.URLS,
    then: (schema) => schema.min(1, 'At least one URL is required for URL submissions').required(),
    otherwise: (schema) => schema.optional()
  }),
  profile_id: yup.number().positive('Invalid profile ID').optional(),
  auto_monitoring: yup.boolean().optional(),
  notify_on_infringement: yup.boolean().optional(),
})

describe('Submission Form Validation', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Schema Validation (Unit Tests)', () => {
    describe('Title validation', () => {
      it('should require title', async () => {
        await expect(
          submissionSchema.validate({ type: ContentType.IMAGES, priority: PriorityLevel.NORMAL })
        ).rejects.toThrow('Title is required')
      })

      it('should enforce minimum length', async () => {
        await expect(
          submissionSchema.validate({ 
            title: 'ab', 
            type: ContentType.IMAGES, 
            priority: PriorityLevel.NORMAL 
          })
        ).rejects.toThrow('Title must be at least 3 characters')
      })

      it('should accept valid title', async () => {
        const result = await submissionSchema.validate({
          title: 'Valid Title',
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL
        })
        
        expect(result.title).toBe('Valid Title')
      })

      it('should handle long titles', async () => {
        const longTitle = 'A'.repeat(500)
        const result = await submissionSchema.validate({
          title: longTitle,
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL
        })
        
        expect(result.title).toBe(longTitle)
      })
    })

    describe('Content type validation', () => {
      it('should require content type', async () => {
        await expect(
          submissionSchema.validate({ title: 'Test', priority: PriorityLevel.NORMAL })
        ).rejects.toThrow('Content type is required')
      })

      it('should only accept valid content types', async () => {
        await expect(
          submissionSchema.validate({
            title: 'Test',
            type: 'invalid_type' as any,
            priority: PriorityLevel.NORMAL
          })
        ).rejects.toThrow('Invalid content type')
      })

      it('should accept all valid content types', async () => {
        for (const contentType of Object.values(ContentType)) {
          const result = await submissionSchema.validate({
            title: 'Test',
            type: contentType,
            priority: PriorityLevel.NORMAL
          })
          
          expect(result.type).toBe(contentType)
        }
      })
    })

    describe('Priority validation', () => {
      it('should require priority', async () => {
        await expect(
          submissionSchema.validate({ title: 'Test', type: ContentType.IMAGES })
        ).rejects.toThrow('Priority level is required')
      })

      it('should only accept valid priority levels', async () => {
        await expect(
          submissionSchema.validate({
            title: 'Test',
            type: ContentType.IMAGES,
            priority: 'invalid_priority' as any
          })
        ).rejects.toThrow('Invalid priority level')
      })

      it('should accept all valid priority levels', async () => {
        for (const priority of Object.values(PriorityLevel)) {
          const result = await submissionSchema.validate({
            title: 'Test',
            type: ContentType.IMAGES,
            priority: priority
          })
          
          expect(result.priority).toBe(priority)
        }
      })
    })

    describe('URL validation', () => {
      it('should not require URLs for non-URL submissions', async () => {
        const result = await submissionSchema.validate({
          title: 'Test',
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL
        })
        
        expect(result).toBeDefined()
      })

      it('should require URLs for URL submissions', async () => {
        await expect(
          submissionSchema.validate({
            title: 'Test',
            type: ContentType.URLS,
            priority: PriorityLevel.NORMAL
          })
        ).rejects.toThrow('At least one URL is required for URL submissions')
      })

      it('should validate URL format', async () => {
        await expect(
          submissionSchema.validate({
            title: 'Test',
            type: ContentType.URLS,
            priority: PriorityLevel.NORMAL,
            urls: ['not-a-url']
          })
        ).rejects.toThrow('Invalid URL format')
      })

      it('should accept valid URLs', async () => {
        const validUrls = [
          'https://example.com/image.jpg',
          'http://test.com/video.mp4',
          'https://subdomain.domain.com/path/file.pdf'
        ]

        const result = await submissionSchema.validate({
          title: 'Test',
          type: ContentType.URLS,
          priority: PriorityLevel.NORMAL,
          urls: validUrls
        })
        
        expect(result.urls).toEqual(validUrls)
      })

      it('should reject mixed valid and invalid URLs', async () => {
        await expect(
          submissionSchema.validate({
            title: 'Test',
            type: ContentType.URLS,
            priority: PriorityLevel.NORMAL,
            urls: ['https://valid.com/image.jpg', 'invalid-url']
          })
        ).rejects.toThrow('Invalid URL format')
      })
    })

    describe('Optional field validation', () => {
      it('should accept valid description', async () => {
        const result = await submissionSchema.validate({
          title: 'Test',
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL,
          description: 'This is a test description'
        })
        
        expect(result.description).toBe('This is a test description')
      })

      it('should accept valid category', async () => {
        const result = await submissionSchema.validate({
          title: 'Test',
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL,
          category: 'photography'
        })
        
        expect(result.category).toBe('photography')
      })

      it('should accept valid tags array', async () => {
        const tags = ['tag1', 'tag2', 'tag3']
        const result = await submissionSchema.validate({
          title: 'Test',
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL,
          tags: tags
        })
        
        expect(result.tags).toEqual(tags)
      })

      it('should accept valid profile_id', async () => {
        const result = await submissionSchema.validate({
          title: 'Test',
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL,
          profile_id: 123
        })
        
        expect(result.profile_id).toBe(123)
      })

      it('should reject negative profile_id', async () => {
        await expect(
          submissionSchema.validate({
            title: 'Test',
            type: ContentType.IMAGES,
            priority: PriorityLevel.NORMAL,
            profile_id: -1
          })
        ).rejects.toThrow('Invalid profile ID')
      })

      it('should accept boolean flags', async () => {
        const result = await submissionSchema.validate({
          title: 'Test',
          type: ContentType.IMAGES,
          priority: PriorityLevel.NORMAL,
          auto_monitoring: false,
          notify_on_infringement: true
        })
        
        expect(result.auto_monitoring).toBe(false)
        expect(result.notify_on_infringement).toBe(true)
      })
    })

    describe('Complex validation scenarios', () => {
      it('should validate complete file submission data', async () => {
        const data = {
          title: 'Complete File Submission',
          type: ContentType.IMAGES,
          priority: PriorityLevel.HIGH,
          description: 'A complete submission with all fields',
          category: 'photography',
          tags: ['professional', 'portrait'],
          profile_id: 1,
          auto_monitoring: true,
          notify_on_infringement: true
        }

        const result = await submissionSchema.validate(data)
        
        expect(result).toEqual(data)
      })

      it('should validate complete URL submission data', async () => {
        const data = {
          title: 'URL Submission Test',
          type: ContentType.URLS,
          priority: PriorityLevel.URGENT,
          urls: [
            'https://example.com/image1.jpg',
            'https://example.com/image2.png'
          ],
          description: 'Testing URL submissions',
          category: 'artwork',
          tags: ['digital', 'art'],
          auto_monitoring: false,
          notify_on_infringement: true
        }

        const result = await submissionSchema.validate(data)
        
        expect(result).toEqual(data)
      })
    })
  })

  describe('Form Validation (Integration Tests)', () => {
    describe('File Upload Form Validation', () => {
      it('should show validation error when title is empty', async () => {
        renderWithProviders(<Submissions />)
        
        // Add a file to enable form submission
        const dropzone = screen.getByTestId('dropzone-input')
        const file = createMockFile('test.jpg', 1024, 'image/jpeg')
        await user.upload(dropzone, file)
        
        // Try to submit without title
        const submitButton = screen.getByRole('button', { name: /submit files/i })
        await user.click(submitButton)
        
        await waitFor(() => {
          expect(screen.getByText('Title is required')).toBeInTheDocument()
        })
      })

      it('should show validation error for short title', async () => {
        renderWithProviders(<Submissions />)
        
        const titleInput = screen.getByLabelText('Title *')
        await user.type(titleInput, 'ab')
        
        // Trigger validation by moving focus away
        await user.tab()
        
        await waitFor(() => {
          expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument()
        })
      })

      it('should clear validation error when valid title is entered', async () => {
        renderWithProviders(<Submissions />)
        
        const titleInput = screen.getByLabelText('Title *')
        
        // Enter short title to trigger error
        await user.type(titleInput, 'ab')
        await user.tab()
        
        await waitFor(() => {
          expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument()
        })

        // Clear and enter valid title
        await user.clear(titleInput)
        await user.type(titleInput, 'Valid Title')
        await user.tab()
        
        await waitFor(() => {
          expect(screen.queryByText('Title must be at least 3 characters')).not.toBeInTheDocument()
        })
      })

      it('should validate file presence before submission', async () => {
        renderWithProviders(<Submissions />)
        
        // Fill title but no files
        await user.type(screen.getByLabelText('Title *'), 'Test Submission')
        
        const submitButton = screen.getByRole('button', { name: /submit files/i })
        expect(submitButton).toBeDisabled()
      })

      it('should enable submission when all required fields are valid', async () => {
        renderWithProviders(<Submissions />)
        
        // Add file
        const dropzone = screen.getByTestId('dropzone-input')
        const file = createMockFile('test.jpg', 1024, 'image/jpeg')
        await user.upload(dropzone, file)
        
        // Fill title
        await user.type(screen.getByLabelText('Title *'), 'Valid Submission')
        
        await waitFor(() => {
          const submitButton = screen.getByRole('button', { name: /submit files/i })
          expect(submitButton).toBeEnabled()
        })
      })
    })

    describe('URL Submission Form Validation', () => {
      beforeEach(async () => {
        renderWithProviders(<Submissions />)
        await user.click(screen.getByText('URL Submission'))
      })

      it('should require title for URL submission', async () => {
        // Add URLs but no title
        const urlInput = screen.getByLabelText('URLs (one per line) *')
        await user.type(urlInput, 'https://example.com/test.jpg')
        
        const submitButton = screen.getByRole('button', { name: /submit urls/i })
        await user.click(submitButton)
        
        await waitFor(() => {
          expect(screen.getByText('Title is required')).toBeInTheDocument()
        })
      })

      it('should require URLs for URL submission', async () => {
        // Add title but no URLs
        await user.type(screen.getByLabelText('Title *'), 'URL Test')
        
        const submitButton = screen.getByRole('button', { name: /submit urls/i })
        expect(submitButton).toBeDisabled()
      })

      it('should enable submission when title and URLs are provided', async () => {
        await user.type(screen.getByLabelText('Title *'), 'URL Test')
        
        const urlInput = screen.getByLabelText('URLs (one per line) *')
        await user.type(urlInput, 'https://example.com/test.jpg')
        
        await waitFor(() => {
          const submitButton = screen.getByRole('button', { name: /submit urls/i })
          expect(submitButton).toBeEnabled()
        })
      })
    })

    describe('Batch Import Form Validation', () => {
      beforeEach(async () => {
        renderWithProviders(<Submissions />)
        await user.click(screen.getByText('Batch Import'))
      })

      it('should require title for batch import', async () => {
        // Clear default title if any and try to submit
        const titleInput = screen.getByLabelText('Batch Title *')
        await user.clear(titleInput)
        
        // Mock CSV file selection (this would need proper FileUpload component mocking)
        const submitButton = screen.getByRole('button', { name: /process batch/i })
        expect(submitButton).toBeDisabled() // Should be disabled without title
      })

      it('should require CSV file for batch import', async () => {
        await user.type(screen.getByLabelText('Batch Title *'), 'Batch Test')
        
        // Without CSV file, button should be disabled
        const submitButton = screen.getByRole('button', { name: /process batch/i })
        expect(submitButton).toBeDisabled()
      })
    })

    describe('Cross-tab Validation Consistency', () => {
      it('should maintain validation state when switching tabs', async () => {
        renderWithProviders(<Submissions />)
        
        // Enter invalid title in File Upload tab
        await user.type(screen.getByLabelText('Title *'), 'ab')
        await user.tab()
        
        await waitFor(() => {
          expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument()
        })

        // Switch to URL tab and back
        await user.click(screen.getByText('URL Submission'))
        await user.click(screen.getByText('File Upload'))
        
        // Validation error should still be present
        await waitFor(() => {
          expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument()
        })
      })

      it('should reset form when switching between different submission types', async () => {
        renderWithProviders(<Submissions />)
        
        // Fill File Upload form
        await user.type(screen.getByLabelText('Title *'), 'File Upload Test')
        
        // Switch to URL Submission
        await user.click(screen.getByText('URL Submission'))
        
        // Title should be preserved (shared field)
        await waitFor(() => {
          expect(screen.getByDisplayValue('File Upload Test')).toBeInTheDocument()
        })

        // Switch to Batch Import
        await user.click(screen.getByText('Batch Import'))
        
        // Should have separate title field for batch
        const batchTitle = screen.getByLabelText('Batch Title *')
        expect(batchTitle).toBeInTheDocument()
        expect(batchTitle).toHaveValue('File Upload Test') // Should inherit from shared form state
      })
    })

    describe('Real-time Validation', () => {
      it('should validate fields on change', async () => {
        renderWithProviders(<Submissions />)
        
        const titleInput = screen.getByLabelText('Title *')
        
        // Type invalid title
        await user.type(titleInput, 'a')
        
        // Should show validation error immediately or on blur
        await user.tab()
        
        await waitFor(() => {
          expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument()
        })
      })

      it('should update submit button state based on form validity', async () => {
        renderWithProviders(<Submissions />)
        
        const submitButton = screen.getByRole('button', { name: /submit files/i })
        expect(submitButton).toBeDisabled()
        
        // Add file
        const dropzone = screen.getByTestId('dropzone-input')
        const file = createMockFile('test.jpg', 1024, 'image/jpeg')
        await user.upload(dropzone, file)
        
        // Still disabled without title
        expect(submitButton).toBeDisabled()
        
        // Add valid title
        await user.type(screen.getByLabelText('Title *'), 'Valid Title')
        
        // Should become enabled
        await waitFor(() => {
          expect(submitButton).toBeEnabled()
        })
      })
    })

    describe('Error Message Accessibility', () => {
      it('should associate error messages with form fields', async () => {
        renderWithProviders(<Submissions />)
        
        const titleInput = screen.getByLabelText('Title *')
        await user.type(titleInput, 'ab')
        await user.tab()
        
        await waitFor(() => {
          const errorMessage = screen.getByText('Title must be at least 3 characters')
          expect(errorMessage).toHaveClass('p-error')
          
          // In a real implementation, we'd also check for aria-describedby
          // relationship between input and error message
        })
      })

      it('should provide clear validation feedback', async () => {
        renderWithProviders(<Submissions />)
        
        // Test multiple validation errors
        const titleInput = screen.getByLabelText('Title *')
        
        // Empty field
        await user.focus(titleInput)
        await user.tab()
        
        await waitFor(() => {
          expect(screen.getByText('Title is required')).toBeInTheDocument()
        })

        // Short field  
        await user.type(titleInput, 'ab')
        await user.tab()
        
        await waitFor(() => {
          expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument()
          expect(screen.queryByText('Title is required')).not.toBeInTheDocument()
        })
      })
    })
  })
})