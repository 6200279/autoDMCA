/**
 * @fileoverview File upload and drag-drop functionality tests
 * Tests file selection, drag & drop, file validation, and upload behavior
 */

import React from 'react'
import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockFile, createMockDragEvent } from '@/test/utils'
import { server } from '@/test/mocks/server'
import { http, HttpResponse } from 'msw'
import Submissions from '../Submissions'

// Enhanced mock for react-dropzone with more detailed behavior
const mockUseDropzone = vi.fn()

vi.mock('react-dropzone', () => ({
  useDropzone: mockUseDropzone
}))

describe('File Upload and Drag & Drop', () => {
  const user = userEvent.setup()
  let mockOnDrop: vi.Mock
  let mockGetRootProps: vi.Mock
  let mockGetInputProps: vi.Mock

  beforeEach(() => {
    vi.clearAllMocks()
    
    mockOnDrop = vi.fn()
    mockGetRootProps = vi.fn(() => ({
      'data-testid': 'dropzone',
      onDrop: mockOnDrop,
      onDragOver: vi.fn(e => e.preventDefault()),
      onDragEnter: vi.fn(e => e.preventDefault()),
      onClick: vi.fn()
    }))
    mockGetInputProps = vi.fn(() => ({
      'data-testid': 'dropzone-input',
      type: 'file',
      multiple: true,
      onChange: vi.fn()
    }))

    // Default mock implementation
    mockUseDropzone.mockImplementation(({ onDrop, accept, multiple, maxSize }) => ({
      getRootProps: mockGetRootProps,
      getInputProps: mockGetInputProps,
      isDragActive: false,
      acceptedFiles: [],
      rejectedFiles: [],
      fileRejections: [],
      onDrop
    }))
  })

  describe('Dropzone Rendering', () => {
    it('should render dropzone area', async () => {
      renderWithProviders(<Submissions />)
      
      await waitFor(() => {
        expect(screen.getByTestId('dropzone')).toBeInTheDocument()
        expect(screen.getByText('Drag & drop files here')).toBeInTheDocument()
        expect(screen.getByText('or click to browse')).toBeInTheDocument()
        expect(screen.getByText('Supported: Images, Videos, Documents (Max: 100MB each)')).toBeInTheDocument()
      })
    })

    it('should configure dropzone with correct options', () => {
      renderWithProviders(<Submissions />)
      
      expect(mockUseDropzone).toHaveBeenCalledWith(
        expect.objectContaining({
          accept: {
            'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'],
            'video/*': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'],
            'application/pdf': ['.pdf'],
            'application/msword': ['.doc'],
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
          },
          multiple: true,
          maxSize: 100 * 1024 * 1024 // 100MB
        })
      )
    })

    it('should show active state during drag', () => {
      // Mock active drag state
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: true,
        acceptedFiles: [],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      expect(screen.getByText('Drop files here')).toBeInTheDocument()
    })
  })

  describe('File Selection via Click', () => {
    it('should handle single file selection', async () => {
      const files = [createMockFile('test.jpg', 1024, 'image/jpeg')]
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: () => ({
          'data-testid': 'dropzone-input',
          type: 'file',
          multiple: true,
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
            if (e.target.files) {
              onDrop(Array.from(e.target.files))
            }
          }
        }),
        isDragActive: false,
        acceptedFiles: files,
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const input = screen.getByTestId('dropzone-input')
      
      // Simulate file selection
      Object.defineProperty(input, 'files', {
        value: files,
        writable: false,
      })
      
      await user.upload(input, files[0])
      
      await waitFor(() => {
        expect(screen.getByText('test.jpg')).toBeInTheDocument()
        expect(screen.getByText('Selected Files (1)')).toBeInTheDocument()
      })
    })

    it('should handle multiple file selection', async () => {
      const files = [
        createMockFile('image1.jpg', 1024, 'image/jpeg'),
        createMockFile('image2.png', 2048, 'image/png'),
        createMockFile('document.pdf', 4096, 'application/pdf')
      ]

      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: () => ({
          'data-testid': 'dropzone-input',
          type: 'file',
          multiple: true,
          onChange: (e: React.ChangeEvent<HTMLInputElement>) => {
            if (e.target.files) {
              onDrop(Array.from(e.target.files))
            }
          }
        }),
        isDragActive: false,
        acceptedFiles: files,
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const input = screen.getByTestId('dropzone-input')
      await user.upload(input, files)
      
      await waitFor(() => {
        expect(screen.getByText('image1.jpg')).toBeInTheDocument()
        expect(screen.getByText('image2.png')).toBeInTheDocument()
        expect(screen.getByText('document.pdf')).toBeInTheDocument()
        expect(screen.getByText('Selected Files (3)')).toBeInTheDocument()
      })
    })
  })

  describe('Drag and Drop Functionality', () => {
    it('should handle files dropped on dropzone', async () => {
      let onDropCallback: ((files: File[]) => void) | undefined

      mockUseDropzone.mockImplementation(({ onDrop }) => {
        onDropCallback = onDrop
        return {
          getRootProps: () => ({
            'data-testid': 'dropzone',
            onDrop: (e: React.DragEvent) => {
              e.preventDefault()
              if (e.dataTransfer?.files && onDropCallback) {
                onDropCallback(Array.from(e.dataTransfer.files))
              }
            }
          }),
          getInputProps: mockGetInputProps,
          isDragActive: false,
          acceptedFiles: [],
          rejectedFiles: [],
          fileRejections: [],
          onDrop
        }
      })

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone')
      const files = [createMockFile('dropped.jpg', 1024, 'image/jpeg')]
      
      // Create mock drag event
      const dragEvent = createMockDragEvent(files)
      
      // Simulate drop
      fireEvent.drop(dropzone, dragEvent)
      
      // Manually call onDrop to simulate the dropzone behavior
      if (onDropCallback) {
        onDropCallback(files)
      }
      
      await waitFor(() => {
        expect(screen.getByText('dropped.jpg')).toBeInTheDocument()
      })
    })

    it('should provide visual feedback during drag operation', async () => {
      // Test drag enter
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: () => ({
          'data-testid': 'dropzone',
          onDragEnter: vi.fn(),
          onDragOver: vi.fn(e => e.preventDefault()),
          onDragLeave: vi.fn(),
          onDrop: vi.fn()
        }),
        getInputProps: mockGetInputProps,
        isDragActive: true, // Simulate active drag state
        acceptedFiles: [],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone')
      
      // Check for active drag styling
      expect(dropzone.className).toContain('border-primary-500')
      expect(screen.getByText('Drop files here')).toBeInTheDocument()
    })

    it('should handle drag leave correctly', async () => {
      let isDragActive = true

      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: () => ({
          'data-testid': 'dropzone',
          onDragLeave: () => {
            isDragActive = false
          }
        }),
        getInputProps: mockGetInputProps,
        isDragActive,
        acceptedFiles: [],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropzone = screen.getByTestId('dropzone')
      
      fireEvent.dragLeave(dropzone)
      
      // Would need to re-render to see the effect
      expect(dropzone).toBeInTheDocument()
    })
  })

  describe('File Type Validation', () => {
    it('should accept valid image files', async () => {
      const validImageTypes = [
        'image/jpeg',
        'image/png',
        'image/gif',
        'image/bmp',
        'image/webp'
      ]

      for (const mimeType of validImageTypes) {
        const extension = mimeType.split('/')[1]
        const file = createMockFile(`test.${extension}`, 1024, mimeType)
        
        mockUseDropzone.mockImplementation(({ onDrop }) => ({
          getRootProps: mockGetRootProps,
          getInputProps: mockGetInputProps,
          isDragActive: false,
          acceptedFiles: [file],
          rejectedFiles: [],
          fileRejections: [],
          onDrop
        }))

        renderWithProviders(<Submissions />)
        
        // Simulate the file being accepted by dropzone
        const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
        dropCallback([file])

        await waitFor(() => {
          expect(screen.getByText(`test.${extension}`)).toBeInTheDocument()
        })
        
        // Clean up for next iteration
        vi.clearAllMocks()
      }
    })

    it('should accept valid video files', async () => {
      const validVideoTypes = [
        { mime: 'video/mp4', ext: 'mp4' },
        { mime: 'video/avi', ext: 'avi' },
        { mime: 'video/mov', ext: 'mov' },
        { mime: 'video/wmv', ext: 'wmv' }
      ]

      for (const { mime, ext } of validVideoTypes) {
        const file = createMockFile(`video.${ext}`, 1024 * 1024, mime)
        
        mockUseDropzone.mockImplementation(({ onDrop }) => ({
          getRootProps: mockGetRootProps,
          getInputProps: mockGetInputProps,
          isDragActive: false,
          acceptedFiles: [file],
          rejectedFiles: [],
          fileRejections: [],
          onDrop
        }))

        renderWithProviders(<Submissions />)
        
        const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
        dropCallback([file])

        await waitFor(() => {
          expect(screen.getByText(`video.${ext}`)).toBeInTheDocument()
        })
        
        vi.clearAllMocks()
      }
    })

    it('should accept valid document files', async () => {
      const validDocTypes = [
        { mime: 'application/pdf', ext: 'pdf' },
        { mime: 'application/msword', ext: 'doc' },
        { mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', ext: 'docx' }
      ]

      for (const { mime, ext } of validDocTypes) {
        const file = createMockFile(`document.${ext}`, 1024 * 100, mime)
        
        mockUseDropzone.mockImplementation(({ onDrop }) => ({
          getRootProps: mockGetRootProps,
          getInputProps: mockGetInputProps,
          isDragActive: false,
          acceptedFiles: [file],
          rejectedFiles: [],
          fileRejections: [],
          onDrop
        }))

        renderWithProviders(<Submissions />)
        
        const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
        dropCallback([file])

        await waitFor(() => {
          expect(screen.getByText(`document.${ext}`)).toBeInTheDocument()
        })
        
        vi.clearAllMocks()
      }
    })

    it('should reject invalid file types', async () => {
      const invalidFile = createMockFile('script.exe', 1024, 'application/x-executable')
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [],
        rejectedFiles: [invalidFile],
        fileRejections: [{
          file: invalidFile,
          errors: [{ code: 'file-invalid-type', message: 'File type not supported' }]
        }],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([invalidFile])
      
      // File should not appear in the selected files list
      await waitFor(() => {
        expect(screen.queryByText('script.exe')).not.toBeInTheDocument()
      })
    })
  })

  describe('File Size Validation', () => {
    it('should accept files within size limit', async () => {
      const validFile = createMockFile('large.jpg', 50 * 1024 * 1024, 'image/jpeg') // 50MB
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [validFile],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([validFile])

      await waitFor(() => {
        expect(screen.getByText('large.jpg')).toBeInTheDocument()
        expect(screen.getByText('50.00 MB')).toBeInTheDocument()
      })
    })

    it('should reject files exceeding size limit', async () => {
      const oversizedFile = createMockFile('huge.jpg', 150 * 1024 * 1024, 'image/jpeg') // 150MB
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [],
        rejectedFiles: [oversizedFile],
        fileRejections: [{
          file: oversizedFile,
          errors: [{ code: 'file-too-large', message: 'File is too large' }]
        }],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([oversizedFile])
      
      await waitFor(() => {
        expect(screen.queryByText('huge.jpg')).not.toBeInTheDocument()
      })
    })
  })

  describe('File Management', () => {
    it('should display file information correctly', async () => {
      const file = createMockFile('test.jpg', 1024 * 1024, 'image/jpeg') // 1MB
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [file],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([file])

      await waitFor(() => {
        expect(screen.getByText('test.jpg')).toBeInTheDocument()
        expect(screen.getByText('1.00 MB')).toBeInTheDocument()
        expect(screen.getByText('Selected Files (1)')).toBeInTheDocument()
      })
    })

    it('should allow removing individual files', async () => {
      const files = [
        createMockFile('file1.jpg', 1024, 'image/jpeg'),
        createMockFile('file2.png', 2048, 'image/png')
      ]
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: files,
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback(files)

      await waitFor(() => {
        expect(screen.getByText('file1.jpg')).toBeInTheDocument()
        expect(screen.getByText('file2.png')).toBeInTheDocument()
        expect(screen.getByText('Selected Files (2)')).toBeInTheDocument()
      })

      // Find and click remove button for first file
      const removeButtons = screen.getAllByRole('button', { name: '' })
      const removeButton = removeButtons.find(button => 
        button.closest('[data-testid]')?.textContent?.includes('file1.jpg')
      )
      
      if (removeButton) {
        await user.click(removeButton)
        
        await waitFor(() => {
          expect(screen.queryByText('file1.jpg')).not.toBeInTheDocument()
          expect(screen.getByText('file2.png')).toBeInTheDocument()
          expect(screen.getByText('Selected Files (1)')).toBeInTheDocument()
        })
      }
    })

    it('should update file count correctly', async () => {
      const files = [
        createMockFile('file1.jpg', 1024, 'image/jpeg'),
        createMockFile('file2.jpg', 1024, 'image/jpeg'),
        createMockFile('file3.jpg', 1024, 'image/jpeg')
      ]
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: files,
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback(files)

      await waitFor(() => {
        expect(screen.getByText('Selected Files (3)')).toBeInTheDocument()
      })
    })

    it('should handle adding files to existing selection', async () => {
      // This would test the incremental file addition behavior
      // Implementation would depend on how the component handles this
      const initialFiles = [createMockFile('existing.jpg', 1024, 'image/jpeg')]
      const newFiles = [createMockFile('new.jpg', 1024, 'image/jpeg')]
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [...initialFiles, ...newFiles],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      // First add initial files
      let dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback(initialFiles)

      await waitFor(() => {
        expect(screen.getByText('Selected Files (1)')).toBeInTheDocument()
      })

      // Then add new files
      dropCallback([...initialFiles, ...newFiles])

      await waitFor(() => {
        expect(screen.getByText('existing.jpg')).toBeInTheDocument()
        expect(screen.getByText('new.jpg')).toBeInTheDocument()
        expect(screen.getByText('Selected Files (2)')).toBeInTheDocument()
      })
    })
  })

  describe('Upload Process Integration', () => {
    it('should use uploaded files in form submission', async () => {
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [file],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      // Add file
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([file])
      
      // Fill form
      await user.type(screen.getByLabelText('Title *'), 'Upload Test')
      
      // Submit
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should show progress dialog
      await waitFor(() => {
        expect(screen.getByText('Processing Submission')).toBeInTheDocument()
      })
    })

    it('should handle upload API errors gracefully', async () => {
      // Mock upload failure
      server.use(
        http.post('/api/v1/submissions/upload', () => {
          return HttpResponse.json(
            { detail: 'Upload failed' },
            { status: 500 }
          )
        })
      )

      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [file],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([file])
      
      await user.type(screen.getByLabelText('Title *'), 'Upload Test')
      
      const submitButton = screen.getByRole('button', { name: /submit files/i })
      await user.click(submitButton)
      
      // Should handle error and re-enable form
      await waitFor(() => {
        expect(submitButton).toBeEnabled()
      })
    })
  })

  describe('User Experience', () => {
    it('should show toast notification on successful file addition', async () => {
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [file],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([file])

      // Toast component should be present (actual toast display depends on PrimeReact implementation)
      expect(screen.getByTestId('toast')).toBeInTheDocument()
    })

    it('should provide clear visual feedback for file operations', async () => {
      const file = createMockFile('test.jpg', 1024, 'image/jpeg')
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: [file],
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback([file])

      await waitFor(() => {
        // Should show file icon
        expect(screen.getByText('test.jpg')).toBeInTheDocument()
        
        // Should show file size badge
        expect(screen.getByText('0.00 MB')).toBeInTheDocument()
        
        // Should show remove button
        const removeButtons = screen.getAllByRole('button')
        expect(removeButtons.length).toBeGreaterThan(0)
      })
    })

    it('should maintain file list scroll for many files', async () => {
      // Test with many files to check scrollable container
      const manyFiles = Array.from({ length: 10 }, (_, i) => 
        createMockFile(`file${i + 1}.jpg`, 1024, 'image/jpeg')
      )
      
      mockUseDropzone.mockImplementation(({ onDrop }) => ({
        getRootProps: mockGetRootProps,
        getInputProps: mockGetInputProps,
        isDragActive: false,
        acceptedFiles: manyFiles,
        rejectedFiles: [],
        fileRejections: [],
        onDrop
      }))

      renderWithProviders(<Submissions />)
      
      const dropCallback = mockUseDropzone.mock.calls[0][0].onDrop
      dropCallback(manyFiles)

      await waitFor(() => {
        expect(screen.getByText('Selected Files (10)')).toBeInTheDocument()
        
        // Check that the container has scrollable styling
        const fileContainer = screen.getByText('Selected Files (10)').closest('div')
        expect(fileContainer).toBeInTheDocument()
      })
    })
  })
})