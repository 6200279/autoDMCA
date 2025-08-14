/**
 * Tests for LoadingSpinner component
 * Tests various states, props, and rendering behaviors
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@test/utils'
import LoadingSpinner from './LoadingSpinner'

describe('LoadingSpinner', () => {
  it('renders with default props', () => {
    render(<LoadingSpinner />)
    
    expect(screen.getByText('Loading...')).toBeInTheDocument()
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
  })

  it('renders with custom message', () => {
    const customMessage = 'Processing your request...'
    render(<LoadingSpinner message={customMessage} />)
    
    expect(screen.getByText(customMessage)).toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })

  it('renders without message when message is empty', () => {
    render(<LoadingSpinner message="" />)
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument()
    expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
  })

  it('renders with small size', () => {
    render(<LoadingSpinner size="small" />)
    
    const spinner = screen.getByRole('progressbar')
    expect(spinner).toHaveStyle({ width: '2rem', height: '2rem' })
  })

  it('renders with medium size by default', () => {
    render(<LoadingSpinner />)
    
    const spinner = screen.getByRole('progressbar')
    expect(spinner).toHaveStyle({ width: '3rem', height: '3rem' })
  })

  it('renders with large size', () => {
    render(<LoadingSpinner size="large" />)
    
    const spinner = screen.getByRole('progressbar')
    expect(spinner).toHaveStyle({ width: '4rem', height: '4rem' })
  })

  it('renders in fullScreen mode', () => {
    render(<LoadingSpinner fullScreen />)
    
    const fullScreenContainer = screen.getByText('Loading...').closest('.fixed')
    expect(fullScreenContainer).toBeInTheDocument()
    expect(fullScreenContainer).toHaveClass('fixed', 'top-0', 'left-0', 'w-full', 'h-full')
    expect(fullScreenContainer).toHaveStyle({ zIndex: '9999' })
  })

  it('renders in normal mode by default', () => {
    render(<LoadingSpinner />)
    
    const container = screen.getByText('Loading...').closest('.flex')
    expect(container).not.toHaveClass('fixed')
    expect(container).toHaveClass('flex', 'align-items-center', 'justify-content-center', 'p-4')
  })

  it('has correct animation properties', () => {
    render(<LoadingSpinner />)
    
    const spinner = screen.getByRole('progressbar')
    expect(spinner).toHaveAttribute('data-pc-name', 'progressspinner')
  })

  it('renders spinner with correct stroke width', () => {
    render(<LoadingSpinner />)
    
    const spinner = screen.getByRole('progressbar')
    // PrimeReact ProgressSpinner should have the strokeWidth prop applied
    expect(spinner.querySelector('circle')).toHaveAttribute('stroke-width', '4')
  })

  it('applies custom message styling', () => {
    render(<LoadingSpinner message="Custom message" />)
    
    const message = screen.getByText('Custom message')
    expect(message).toHaveClass('text-600', 'text-center', 'm-0', 'font-medium')
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      render(<LoadingSpinner message="Loading content" />)
      
      const spinner = screen.getByRole('progressbar')
      expect(spinner).toBeInTheDocument()
    })

    it('message is associated with spinner', () => {
      render(<LoadingSpinner message="Loading important data" />)
      
      const message = screen.getByText('Loading important data')
      expect(message).toBeInTheDocument()
      
      // Message should be visible to screen readers
      expect(message.tagName.toLowerCase()).toBe('p')
    })
  })

  describe('Visual Structure', () => {
    it('has correct layout classes for content centering', () => {
      render(<LoadingSpinner />)
      
      const contentContainer = screen.getByText('Loading...').closest('.flex-column')
      expect(contentContainer).toHaveClass(
        'flex',
        'flex-column',
        'align-items-center',
        'justify-content-center',
        'gap-3'
      )
    })

    it('maintains consistent spacing between spinner and message', () => {
      render(<LoadingSpinner message="Test message" />)
      
      const contentContainer = screen.getByText('Test message').closest('.flex-column')
      expect(contentContainer).toHaveClass('gap-3')
    })
  })

  describe('Edge Cases', () => {
    it('handles undefined message prop', () => {
      render(<LoadingSpinner message={undefined} />)
      
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })

    it('handles null message prop', () => {
      render(<LoadingSpinner message={null as any} />)
      
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument()
    })

    it('handles very long messages', () => {
      const longMessage = 'This is a very long loading message that might wrap to multiple lines and should still be handled gracefully by the component'
      render(<LoadingSpinner message={longMessage} />)
      
      expect(screen.getByText(longMessage)).toBeInTheDocument()
      expect(screen.getByText(longMessage)).toHaveClass('text-center')
    })
  })
})