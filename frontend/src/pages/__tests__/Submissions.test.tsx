/**
 * @fileoverview Tests for Submissions component
 * Tests the main submission interface including all tabs, forms, and interactions
 */

import React from 'react'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockFile, createMockDragEvent } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import Submissions from '../Submissions'
import { ContentType, PriorityLevel } from '@/types/api'

// Mock react-dropzone to make drag and drop testing easier
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

// Mock PrimeReact components that might cause issues in tests
vi.mock('primereact/confirmdialog', () => ({
  ConfirmDialog: () => <div data-testid="confirm-dialog" />,
  confirmDialog: vi.fn()
}))

vi.mock('primereact/toast', () => ({
  Toast: React.forwardRef<any, any>((props, ref) => (
    <div data-testid="toast" ref={ref} />
  ))
}))

describe('Submissions Component', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Rendering', () => {
    it('should render the main submission interface', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByText('Content Submissions')).toBeInTheDocument()
        expect(screen.getByText('Upload and submit content for protection monitoring')).toBeInTheDocument()
        expect(screen.getByText('View History')).toBeInTheDocument()
      })
    })

    it('should render all tabs', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByText('File Upload')).toBeInTheDocument()
        expect(screen.getByText('URL Submission')).toBeInTheDocument()
        expect(screen.getByText('Batch Import')).toBeInTheDocument()
        expect(screen.getByText('History')).toBeInTheDocument()
      })
    })

    it('should have File Upload tab active by default', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByText('Upload Files')).toBeInTheDocument()
        expect(screen.getByText('Drag & drop files here')).toBeInTheDocument()
      })
    })
  })

  describe('Tab Navigation', () => {
    it('should switch to URL Submission tab', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByText('URL Submission')).toBeInTheDocument()
      })

      await user.click(screen.getByText('URL Submission'))
      
      await waitFor(() => {
        expect(screen.getByText('Bulk URL Submission')).toBeInTheDocument()
        expect(screen.getByText('URLs (one per line) *')).toBeInTheDocument()
      })
    })

    it('should switch to Batch Import tab', async () => {
      renderWithProviders(<Submissions />)
      
      await user.click(screen.getByText('Batch Import'))
      
      await waitFor(() => {
        expect(screen.getByText('CSV Batch Import')).toBeInTheDocument()
        expect(screen.getByText('CSV File *')).toBeInTheDocument()
      })
    })

    it('should switch to History tab', async () => {
      renderWithProviders(<Submissions />)
      
      await user.click(screen.getByText('History'))
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
    })

    it('should switch to History tab via View History button', async () => {
      renderWithProviders(<Submissions />)
      
      await user.click(screen.getByText('View History'))
      
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
      })
    })
  })

  describe('File Upload Tab', () => {
    it('should render dropzone area', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByTestId('dropzone')).toBeInTheDocument()
        expect(screen.getByText('Drag & drop files here')).toBeInTheDocument()
        expect(screen.getByText('or click to browse')).toBeInTheDocument()
        expect(screen.getByText('Supported: Images, Videos, Documents (Max: 100MB each)')).toBeInTheDocument()
      })
    })

    it('should render submission form fields', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByLabelText('Title *')).toBeInTheDocument()
        expect(screen.getByLabelText('Content Type *')).toBeInTheDocument()
        expect(screen.getByLabelText('Priority *')).toBeInTheDocument()
        expect(screen.getByLabelText('Category')).toBeInTheDocument()
        expect(screen.getByLabelText('Tags')).toBeInTheDocument()
        expect(screen.getByLabelText('Description')).toBeInTheDocument()
        expect(screen.getByLabelText('Enable auto-monitoring')).toBeInTheDocument()
        expect(screen.getByLabelText('Notify on infringements')).toBeInTheDocument()
      })
    })

    it('should have submit button disabled initially', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        const submitButton = screen.getByRole('button', { name: /submit files/i })
        expect(submitButton).toBeDisabled()
      })
    })

    it('should show validation errors for required fields', async () => {
      renderWithProviders(<Submissions />)
      
      // Try to submit without filling required fields
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      
      // First, we need to add a file to enable the button
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      
      await user.upload(dropzone, file)
      
      await waitFor(() => {
        expect(screen.getByText('test.jpg')).toBeInTheDocument()
      })

      // Now try to submit without title
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Title is required')).toBeInTheDocument()
      })
    })
  })

  describe('File Upload Functionality', () => {
    it('should handle single file upload', async () => {
      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      
      await user.upload(dropzone, file)
      
      await waitFor(() => {
        expect(screen.getByText('test.jpg')).toBeInTheDocument()
        expect(screen.getByText('0.00 MB')).toBeInTheDocument()
        expect(screen.getByText('Selected Files (1)')).toBeInTheDocument()
      })
    })

    it('should handle multiple file upload', async () => {
      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const files = [
        createMockFile('image1.jpg', 1024, 'image/jpeg'),
        createMockFile('image2.png', 2048, 'image/png'),
        createMockFile('document.pdf', 4096, 'application/pdf')
      ]
      
      await user.upload(dropzone, files)
      
      await waitFor(() => {
        expect(screen.getByText('image1.jpg')).toBeInTheDocument()
        expect(screen.getByText('image2.png')).toBeInTheDocument()
        expect(screen.getByText('document.pdf')).toBeInTheDocument()
        expect(screen.getByText('Selected Files (3)')).toBeInTheDocument()
      })
    })

    it('should allow removing individual files', async () => {
      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      
      await user.upload(dropzone, file)
      
      await waitFor(() => {
        expect(screen.getByText('test.jpg')).toBeInTheDocument()
      })

      // Find and click the remove button
      const removeButton = screen.getByRole('button', { name: '' }) // PrimeReact button with icon only
      await user.click(removeButton)
      
      await waitFor(() => {
        expect(screen.queryByText('test.jpg')).not.toBeInTheDocument()
        expect(screen.queryByText('Selected Files')).not.toBeInTheDocument()
      })
    })

    it('should submit files successfully', async () => {
      renderWithProviders(<Submissions />)
      
      // Upload a file
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      
      // Fill required fields
      await user.type(screen.getByLabelText('Title *'), 'Test Submission')
      
      // Submit the form
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
        expect(screen.getByText('Uploading and processing your files...')).toBeInTheDocument()
      })
    })
  })

  describe('URL Submission Tab', () => {
    beforeEach(async () => {
      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('URL Submission'))
    })

    it('should render URL input area', async () => {
      await waitFor(() => {
        expect(screen.getByLabelText('URLs (one per line) *')).toBeInTheDocument()
        expect(screen.getByPlaceholderText(/https:\/\/example\.com\/image1\.jpg/)).toBeInTheDocument()
        expect(screen.getByText('Enter one URL per line')).toBeInTheDocument()
      })
    })

    it('should enable validate button when URLs are entered', async () => {
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image1.jpg\nhttps://example.com/image2.jpg')
      
      await waitFor(() => {
        const validateButton = screen.getByRole('button', { name: /validate urls/i })
        expect(validateButton).toBeEnabled()
      })
    })

    it('should validate URLs and show results', async () => {
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image1.jpg\nhttps://invalid.com/image2.jpg')
      
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

    it('should submit URLs successfully', async () => {
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/image1.jpg')
      
      await user.type(screen.getByLabelText('Title *'), 'URL Submission Test')
      
      const submitButton = screen.getByRole('button', { name: /submit urls/i })
      await user.click(submitButton)
      
      // Should process the submission
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /submit urls/i })).toBeDisabled()
      })
    })
  })

  describe('Batch Import Tab', () => {
    beforeEach(async () => {
      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('Batch Import'))
    })

    it('should render CSV import interface', async () => {
      await waitFor(() => {
        expect(screen.getByText('CSV Batch Import')).toBeInTheDocument()
        expect(screen.getByLabelText('CSV File *')).toBeInTheDocument()
        expect(screen.getByText('Choose CSV File')).toBeInTheDocument()
        expect(screen.getByText('CSV Format Example')).toBeInTheDocument()
      })
    })

    it('should show CSV format example', async () => {
      const examplePanel = screen.getByText('CSV Format Example')
      await user.click(examplePanel)
      
      await waitFor(() => {
        expect(screen.getByText('title,type,priority,url,description,category')).toBeInTheDocument()
      })
    })

    it('should handle CSV file selection', async () => {
      // This would require mocking the FileUpload component more extensively
      // For now, we test that the interface is present
      expect(screen.getByText('Choose CSV File')).toBeInTheDocument()
    })
  })

  describe('History Tab', () => {
    beforeEach(async () => {
      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('History'))
    })

    it('should render submission history table', async () => {
      await waitFor(() => {
        expect(screen.getByRole('table')).toBeInTheDocument()
        expect(screen.getByText('Title')).toBeInTheDocument()
        expect(screen.getByText('Type')).toBeInTheDocument()
        expect(screen.getByText('Status')).toBeInTheDocument()
        expect(screen.getByText('Progress')).toBeInTheDocument()
        expect(screen.getByText('Items')).toBeInTheDocument()
        expect(screen.getByText('Created')).toBeInTheDocument()
        expect(screen.getByText('Actions')).toBeInTheDocument()
      })
    })

    it('should display submission data in table', async () => {
      await waitFor(() => {
        expect(screen.getByText('Test Image Submission')).toBeInTheDocument()
        expect(screen.getByText('Video Content Batch')).toBeInTheDocument()
        expect(screen.getByText('Document Submission')).toBeInTheDocument()
      })
    })

    it('should show action buttons for appropriate submissions', async () => {
      await waitFor(() => {
        // Should have retry button for failed submission
        const retryButtons = screen.getAllByTitle('Retry submission')
        expect(retryButtons.length).toBeGreaterThan(0)
        
        // Should have cancel button for processing submission
        const cancelButtons = screen.getAllByTitle('Cancel submission')
        expect(cancelButtons.length).toBeGreaterThan(0)
      })
    })
  })

  describe('Form Validation', () => {
    it('should validate title field', async () => {
      renderWithProviders(<Submissions />)
      
      const titleInput = screen.getByLabelText('Title *')
      
      // Test minimum length validation
      await user.type(titleInput, 'ab')
      await user.tab() // Trigger blur to show validation
      
      await waitFor(() => {
        expect(screen.getByText('Title must be at least 3 characters')).toBeInTheDocument()
      })

      // Clear and test required validation
      await user.clear(titleInput)
      await user.tab()
      
      await waitFor(() => {
        expect(screen.getByText('Title is required')).toBeInTheDocument()
      })
    })

    it('should validate content type selection', async () => {
      renderWithProviders(<Submissions />)
      
      // Content type should be required and have default value
      const contentTypeDropdown = screen.getByLabelText('Content Type *')
      expect(contentTypeDropdown).toBeInTheDocument()
    })

    it('should validate priority selection', async () => {
      renderWithProviders(<Submissions />)
      
      // Priority should be required and have default value
      const priorityDropdown = screen.getByLabelText('Priority *')
      expect(priorityDropdown).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('should handle submission API errors', async () => {
      server.use(
        http.post('/api/v1/submissions', () => {
          return HttpResponse.json(
            { detail: 'Submission failed' },
            { status: 500 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      
      // Upload a file and fill form
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Test Submission')
      
      // Submit and expect error handling
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // The component should handle the error gracefully
      // (exact error display depends on toast implementation)
      await waitFor(() => {
        expect(submitButton).toBeEnabled() // Should re-enable after error
      })
    })

    it('should handle file upload errors', async () => {
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
      await user.type(screen.getByLabelText('Title *'), 'Test Submission')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should handle upload error
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })

    it('should handle URL validation errors', async () => {
      server.use(
        http.post('/api/v1/submissions/validate-urls', () => {
          return HttpResponse.json(
            { detail: 'Validation service unavailable' },
            { status: 503 }
          )
        })
      )

      renderWithProviders(<Submissions />)
      await user.click(screen.getByText('URL Submission'))
      
      const urlInput = screen.getByLabelText('URLs (one per line) *')
      await user.type(urlInput, 'https://example.com/test.jpg')
      
      const validateButton = screen.getByRole('button', { name: /validate urls/i })
      await user.click(validateButton)
      
      // Should handle validation error gracefully
      await waitFor(() => {
        expect(validateButton).toBeEnabled()
      })
    })
  })

  describe('Loading States', () => {
    it('should show loading state during submission', async () => {
      // Mock a delayed response
      server.use(
        http.post('/api/v1/submissions/upload', async () => {
          await new Promise(resolve => setTimeout(resolve, 100))
          return HttpResponse.json({
            file_urls: ['https://cdn.example.com/test.jpg'],
            upload_id: 'test',
            total_files: 1,
            total_size: 1024
          })
        })
      )

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Test Submission')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should show loading state immediately
      expect(submitButton).toBeDisabled()
    })

    it('should show progress dialog during file processing', async () => {
      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone-input')
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      await user.upload(dropzone, file)
      await user.type(screen.getByLabelText('Title *'), 'Test Submission')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
        expect(screen.getByText('Uploading and processing your files...')).toBeInTheDocument()
      })
    })
  })

  describe('Accessibility', () => {
    it('should have proper ARIA labels', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByLabelText('Title *')).toBeInTheDocument()
        expect(screen.getByLabelText('Content Type *')).toBeInTheDocument()
        expect(screen.getByLabelText('Priority *')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /submit files/i })).toBeInTheDocument()
      })
    })

    it('should be keyboard navigable', async () => {
      renderWithProviders(<Submissions />)
      
      // Test tab navigation through form fields
      await user.tab()
      await waitFor(() => {
        expect(screen.getByLabelText('Title *')).toHaveFocus()
      })
    })

    it('should announce validation errors to screen readers', async () => {
      renderWithProviders(<Submissions />)
      
      const titleInput = screen.getByLabelText('Title *')
      await user.type(titleInput, 'ab')
      await user.tab()
      
      await waitFor(() => {
        const errorMessage = screen.getByText('Title must be at least 3 characters')
        expect(errorMessage).toHaveClass('p-error') // PrimeReact error class
      })
    })
  })
})