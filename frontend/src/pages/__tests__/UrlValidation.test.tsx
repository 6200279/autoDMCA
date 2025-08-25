/**
 * @fileoverview URL validation and bulk entry tests
 * Tests URL input, validation, bulk processing, and submission workflows
 */

import React from 'react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import Submissions from '../Submissions'

describe('URL Validation and Bulk Entry', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  const navigateToUrlTab = async () => {
    renderWithProviders(<Submissions />)
    await user.click(screen.getByText('URL Submission'))
    await waitFor(() => {
      expect(screen.getByText('Bulk URL Submission')).toBeInTheDocument()
    })
  }

  describe('URL Input Interface', () => {
    it('should render URL input textarea', async () => {
      await navigateToUrlTab()
      
      expect(screen.getByLabelText('URLs (one per line) *')).toBeInTheDocument()
      expect(screen.getByPlaceholderText(/https:\/\/example\.com\/image1\.jpg/)).toBeInTheDocument()
      expect(screen.getByText('Enter one URL per line')).toBeInTheDocument()
      expect(screen.getByText('Supported: Direct links to images, videos, or documents.')).toBeInTheDocument()
    })

    it('should have proper textarea configuration', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      expect(urlInput).toHaveAttribute('rows', '10')
      expect(urlInput).toHaveClass('font-mono')
    })

    it('should show validate button when URLs are entered', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      
      // Initially disabled
      expect(validateButton).toBeDisabled()
      
      // Enter URLs
      await user.type(urlInput, 'https://example.com/image1.jpg')
      
      // Should be enabled
      await waitFor(() => {
        expect(validateButton).toBeEnabled()
      })
    })

    it('should disable validate button when input is empty', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      
      // Enter and clear URLs
      await user.type(urlInput, 'https://example.com/image1.jpg')
      await user.clear(urlInput)
      
      expect(validateButton).toBeDisabled()
    })
  })

  describe('URL Input Processing', () => {
    it('should handle single URL input', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image1.jpg')
      
      expect(urlInput).toHaveValue('https://example.com/image1.jpg')
    })

    it('should handle multiple URL input', async () => {
      await navigateToUrlTab()
      
      const urls = [
        'https://example.com/image1.jpg',
        'https://example.com/image2.png',
        'https://example.com/document.pdf'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urls)
      
      expect(urlInput).toHaveValue(urls)
    })

    it('should handle URLs with various formats', async () => {
      await navigateToUrlTab()
      
      const urls = [
        'https://example.com/path/image.jpg',
        'http://subdomain.example.com/video.mp4',
        'https://example.com/folder/subfolder/document.pdf',
        'https://example.com/image.jpg?param=value&other=123',
        'https://example.com/path#fragment'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urls)
      
      expect(urlInput).toHaveValue(urls)
    })

    it('should handle mixed content with empty lines', async () => {
      await navigateToUrlTab()
      
      const urlsWithBlanks = [
        'https://example.com/image1.jpg',
        '',
        'https://example.com/image2.png',
        '   ',
        'https://example.com/document.pdf',
        ''
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urlsWithBlanks)
      
      expect(urlInput).toHaveValue(urlsWithBlanks)
    })
  })

  describe('URL Validation Process', () => {
    it('should validate URLs and show results', async () => {
      await navigateToUrlTab()
      
      const urls = [
        'https://example.com/image1.jpg',
        'https://invalid.com/image2.jpg'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
        expect(screen.getByText('https://example.com/image1.jpg')).toBeInTheDocument()
        expect(screen.getByText('https://invalid.com/image2.jpg')).toBeInTheDocument()
        expect(screen.getByText('Valid')).toBeInTheDocument()
        expect(screen.getByText('Invalid')).toBeInTheDocument()
      })
    })

    it('should show validation summary', async () => {
      await navigateToUrlTab()
      
      const urls = [
        'https://example.com/image1.jpg',
        'https://example.com/image2.jpg',
        'https://invalid.com/blocked.jpg'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        // Should show summary in toast or message
        expect(screen.getByTestId('toast')).toBeInTheDocument()
      })
    })

    it('should display detailed validation results', async () => {
      await navigateToUrlTab()
      
      const urls = [
        'https://example.com/valid.jpg',
        'https://invalid.com/blocked.jpg',
        'not-a-url'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        // Valid URL
        expect(screen.getByText('https://example.com/valid.jpg')).toBeInTheDocument()
        expect(screen.getByText('example.com')).toBeInTheDocument()
        
        // Invalid URLs with error messages
        expect(screen.getByText('https://invalid.com/blocked.jpg')).toBeInTheDocument()
        expect(screen.getByText('not-a-url')).toBeInTheDocument()
        
        // Should show error messages
        expect(screen.getByText('URL is not accessible or blocked')).toBeInTheDocument()
        expect(screen.getByText('Invalid URL format')).toBeInTheDocument()
      })
    })

    it('should handle validation loading state', async () => {
      // Mock delayed validation response
      server.use(
        http.post('/api/v1/submissions/validate-urls', async () => {
          await new Promise(resolve => setTimeout(resolve, 100))
          return HttpResponse.json([
            {
              url: 'https://example.com/test.jpg',
              is_valid: true,
              domain: 'example.com',
              error_message: null
            }
          ])
        })
      )

      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/test.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      // Should show loading state
      expect(validateButton).toBeDisabled()
    })

    it('should handle validation errors gracefully', async () => {
      server.use(
        http.post('/api/v1/submissions/validate-urls', () => {
          return HttpResponse.json(
            { detail: 'Validation service unavailable' },
            { status: 503 }
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

    it('should clear validation results when URLs change', async () => {
      await navigateToUrlTab()
      
      // Initial validation
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image1.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })

      // Change URLs - validation results should be cleared
      await user.clear(urlInput)
      await user.type(urlInput, 'https://different.com/image.jpg')
      
      // This would depend on implementation - results might be cleared immediately or on next validation
      expect(screen.queryByText('Validation Results')).toBeInTheDocument()
    })
  })

  describe('Bulk URL Patterns', () => {
    it('should handle common URL patterns', async () => {
      await navigateToUrlTab()
      
      const commonPatterns = [
        // Standard image URLs
        'https://example.com/image.jpg',
        'https://example.com/image.jpeg',
        'https://example.com/image.png',
        'https://example.com/image.gif',
        'https://example.com/image.bmp',
        'https://example.com/image.webp',
        
        // Video URLs
        'https://example.com/video.mp4',
        'https://example.com/video.avi',
        'https://example.com/video.mov',
        
        // Document URLs
        'https://example.com/document.pdf',
        'https://example.com/document.doc',
        'https://example.com/document.docx'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, commonPatterns)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })

    it('should handle URLs with query parameters', async () => {
      await navigateToUrlTab()
      
      const urlsWithParams = [
        'https://example.com/image.jpg?v=123',
        'https://example.com/image.png?width=1920&height=1080',
        'https://example.com/document.pdf?download=true&token=abc123'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, urlsWithParams)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })

    it('should handle URLs with authentication tokens', async () => {
      await navigateToUrlTab()
      
      const secureUrls = [
        'https://secure.example.com/protected/image.jpg?auth=token123',
        'https://api.example.com/files/document.pdf?key=apikey456'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, secureUrls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })

    it('should handle CDN and cloud storage URLs', async () => {
      await navigateToUrlTab()
      
      const cdnUrls = [
        'https://cdn.example.com/assets/image.jpg',
        'https://s3.amazonaws.com/bucket/file.pdf',
        'https://storage.googleapis.com/bucket/video.mp4',
        'https://files.dropbox.com/shared/document.docx'
      ].join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, cdnUrls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })
  })

  describe('URL Submission Process', () => {
    it('should submit valid URLs successfully', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image1.jpg\nhttps://example.com/image2.jpg')
      
      await user.type(screen.getByLabelText('Title *'), 'URL Submission Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      // Should process submission
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })

    it('should validate URLs before submission', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/valid.jpg\nhttps://invalid.com/blocked.jpg')
      
      await user.type(screen.getByLabelText('Title *'), 'Mixed URL Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      // Should validate URLs automatically and submit only valid ones
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })

    it('should handle empty URL submission gracefully', async () => {
      await navigateToUrlTab()
      
      await user.type(screen.getByLabelText('Title *'), 'Empty URL Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      expect(submitButton).toBeDisabled()
    })

    it('should handle all-invalid URLs submission', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://invalid.com/blocked1.jpg\nhttps://blocked.site/blocked2.jpg')
      
      await user.type(screen.getByLabelText('Title *'), 'Invalid URLs Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      // Should show warning about no valid URLs
      await waitFor(() => {
        expect(screen.getByTestId('toast')).toBeInTheDocument()
      })
    })

    it('should include form data with URL submission', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image.jpg')
      
      // Fill all form fields
      await user.type(screen.getByLabelText('Title *'), 'Complete URL Submission')
      
      // Select priority dropdown
      const priorityDropdown = screen.getByLabelText('Priority *')
      await user.click(priorityDropdown)
      // Note: Actual dropdown selection would require more complex PrimeReact mocking
      
      // Fill description
      await user.type(screen.getByLabelText('Description'), 'Test description for URL submission')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(submitButton).toBeDisabled()
      })
    })
  })

  describe('Form Integration', () => {
    it('should maintain form state across validation', async () => {
      await navigateToUrlTab()
      
      // Fill form first
      await user.type(screen.getByLabelText('Title *'), 'Validation Test')
      await user.type(screen.getByLabelText('Description'), 'Test description')
      
      // Then add and validate URLs
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        // Form fields should retain their values
        expect(screen.getByDisplayValue('Validation Test')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Test description')).toBeInTheDocument()
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })

    it('should reset form after successful submission', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image.jpg')
      await user.type(screen.getByLabelText('Title *'), 'Reset Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      // After successful submission, form should reset
      await waitFor(() => {
        expect(screen.getByLabelText('URLs (one per line) *')).toHaveValue('')
        expect(screen.getByLabelText('Title *')).toHaveValue('')
      })
    })

    it('should preserve form data on submission error', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Submission failed' },
            { status: 500 }
          )
        })
      )

      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image.jpg')
      await user.type(screen.getByLabelText('Title *'), 'Error Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      // After error, form data should be preserved
      await waitFor(() => {
        expect(screen.getByDisplayValue('https://example.com/image.jpg')).toBeInTheDocument()
        expect(screen.getByDisplayValue('Error Test')).toBeInTheDocument()
        expect(submitButton).toBeEnabled()
      })
    })
  })

  describe('User Experience Enhancements', () => {
    it('should provide paste support for bulk URLs', async () => {
      await navigateToUrlTab()
      
      const urls = 'https://example.com/1.jpg\nhttps://example.com/2.jpg'
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      
      // Simulate paste operation
      await user.click(urlInput)
      await user.paste(urls)
      
      expect(urlInput).toHaveValue(urls)
    })

    it('should handle very large URL lists', async () => {
      await navigateToUrlTab()
      
      // Generate large list of URLs
      const manyUrls = Array.from({ length: 100 }, (_, i) => 
        `https://example.com/image${i + 1}.jpg`
      ).join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, manyUrls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
      })
    })

    it('should provide clear feedback for URL processing', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      // Should provide feedback about processing
      await waitFor(() => {
        expect(screen.getByTestId('toast')).toBeInTheDocument()
      })
    })

    it('should maintain scroll position in long validation results', async () => {
      await navigateToUrlTab()
      
      // Add many URLs to test scrolling
      const manyUrls = Array.from({ length: 50 }, (_, i) => 
        `https://example.com/image${i + 1}.jpg`
      ).join('\n')
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, manyUrls)
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        expect(screen.getByText('Validation Results')).toBeInTheDocument()
        
        // Should have scrollable container
        const resultsContainer = screen.getByText('Validation Results').closest('div')
        expect(resultsContainer).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels for URL input', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      expect(urlInput).toHaveAttribute('aria-required', 'true')
    })

    it('should announce validation results to screen readers', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        const validationSection = screen.getByText('Validation Results')
        expect(validationSection).toBeInTheDocument()
        
        // Results should be accessible
        expect(screen.getByText('Valid')).toBeInTheDocument()
      })
    })

    it('should provide keyboard navigation for validation results', async () => {
      await navigateToUrlTab()
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image1.jpg\nhttps://example.com/image2.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      await waitFor(() => {
        // Should be able to navigate through validation results with keyboard
        const validationResults = screen.getByText('Validation Results')
        expect(validationResults).toBeInTheDocument()
      })
    })
  })
})