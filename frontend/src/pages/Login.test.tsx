/**
 * Tests for Login page component
 * Tests form validation, authentication flow, and user interactions
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { render, mockNavigate, createUnauthenticatedState } from '@test/utils'
import Login from './Login'

// Mock the useAuth hook
const mockLogin = vi.fn()
const mockAuthContext = {
  ...createUnauthenticatedState(),
  login: mockLogin,
}

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => mockAuthContext,
}))

describe('Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockLogin.mockClear()
    mockNavigate.mockClear()
  })

  it('renders login form with all required fields', () => {
    render(<Login />, { authValue: createUnauthenticatedState() })
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /remember me/i })).toBeInTheDocument()
  })

  it('renders welcome messages and branding', () => {
    render(<Login />, { authValue: createUnauthenticatedState() })
    
    expect(screen.getByText(/welcome back/i)).toBeInTheDocument()
    expect(screen.getByText(/content protection platform/i)).toBeInTheDocument()
  })

  it('renders links to register and forgot password', () => {
    render(<Login />, { authValue: createUnauthenticatedState() })
    
    expect(screen.getByRole('link', { name: /create account/i })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /forgot.*password/i })).toBeInTheDocument()
  })

  describe('Form Validation', () => {
    it('shows email validation error for invalid email', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'invalid-email')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/please enter a valid email address/i)).toBeInTheDocument()
      })
    })

    it('shows email required error when email is empty', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      })
    })

    it('shows password validation error for short password', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, '123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/password must be at least 8 characters/i)).toBeInTheDocument()
      })
    })

    it('shows password required error when password is empty', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(/password is required/i)).toBeInTheDocument()
      })
    })

    it('does not show validation errors for valid inputs', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      
      expect(screen.queryByText(/please enter a valid email address/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/password must be at least 8 characters/i)).not.toBeInTheDocument()
    })
  })

  describe('Authentication Flow', () => {
    it('submits form with valid credentials', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue({ success: true })
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'validPassword123',
          rememberMe: false,
        })
      })
    })

    it('submits form with remember me checked', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue({ success: true })
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const rememberMeCheckbox = screen.getByRole('checkbox', { name: /remember me/i })
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      await user.click(rememberMeCheckbox)
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'validPassword123',
          rememberMe: true,
        })
      })
    })

    it('shows loading state during authentication', async () => {
      const user = userEvent.setup()
      let resolveLogin: (value: any) => void
      const loginPromise = new Promise(resolve => {
        resolveLogin = resolve
      })
      mockLogin.mockReturnValue(loginPromise)
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      await user.click(submitButton)
      
      // Should show loading state
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
      expect(submitButton).toBeDisabled()
      
      // Resolve the login
      resolveLogin({ success: true })
      
      await waitFor(() => {
        expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
      })
    })

    it('handles authentication error', async () => {
      const user = userEvent.setup()
      const errorMessage = 'Invalid credentials'
      mockLogin.mockRejectedValue(new Error(errorMessage))
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongPassword')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText(errorMessage)).toBeInTheDocument()
      })
      
      // Form should be re-enabled
      expect(submitButton).not.toBeDisabled()
    })

    it('navigates to dashboard after successful login', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue({ success: true })
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
      })
    })

    it('navigates to intended destination after login', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue({ success: true })
      
      // Mock location state with intended destination
      const mockLocationState = { from: { pathname: '/protected-route' } }
      
      render(<Login />, { 
        authValue: createUnauthenticatedState(),
        initialEntries: ['/login']
      })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalled()
      })
    })
  })

  describe('User Interactions', () => {
    it('toggles remember me checkbox', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const rememberMeCheckbox = screen.getByRole('checkbox', { name: /remember me/i })
      
      expect(rememberMeCheckbox).not.toBeChecked()
      
      await user.click(rememberMeCheckbox)
      expect(rememberMeCheckbox).toBeChecked()
      
      await user.click(rememberMeCheckbox)
      expect(rememberMeCheckbox).not.toBeChecked()
    })

    it('shows password when toggle is clicked', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement
      expect(passwordInput.type).toBe('password')
      
      // PrimeReact Password component should have a toggle button
      const toggleButton = screen.getByRole('button', { name: /show password/i })
      await user.click(toggleButton)
      
      expect(passwordInput.type).toBe('text')
    })

    it('handles keyboard navigation', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      // Tab through form elements
      await user.tab()
      expect(emailInput).toHaveFocus()
      
      await user.tab()
      expect(passwordInput).toHaveFocus()
      
      await user.tab()
      expect(screen.getByRole('checkbox')).toHaveFocus()
      
      await user.tab()
      expect(submitButton).toHaveFocus()
    })

    it('submits form when Enter is pressed in password field', async () => {
      const user = userEvent.setup()
      mockLogin.mockResolvedValue({ success: true })
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      await user.keyboard('{Enter}')
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalled()
      })
    })
  })

  describe('Accessibility', () => {
    it('has proper form labels and ARIA attributes', () => {
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      
      expect(emailInput).toHaveAttribute('type', 'email')
      expect(emailInput).toHaveAttribute('aria-required', 'true')
      expect(passwordInput).toHaveAttribute('aria-required', 'true')
    })

    it('associates error messages with form fields', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      await user.click(submitButton)
      
      await waitFor(() => {
        const emailError = screen.getByText(/email is required/i)
        const passwordError = screen.getByText(/password is required/i)
        
        expect(emailError).toBeInTheDocument()
        expect(passwordError).toBeInTheDocument()
      })
    })

    it('has proper heading structure', () => {
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const mainHeading = screen.getByRole('heading', { level: 1 })
      expect(mainHeading).toHaveTextContent(/welcome back/i)
    })

    it('provides clear focus indicators', async () => {
      const user = userEvent.setup()
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      
      await user.click(emailInput)
      expect(emailInput).toHaveFocus()
    })
  })

  describe('Edge Cases', () => {
    it('prevents double submission', async () => {
      const user = userEvent.setup()
      let resolveCount = 0
      mockLogin.mockImplementation(() => {
        resolveCount++
        return new Promise(resolve => {
          setTimeout(() => resolve({ success: true }), 100)
        })
      })
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'validPassword123')
      
      // Click submit multiple times rapidly
      await user.click(submitButton)
      await user.click(submitButton)
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledTimes(1)
      }, { timeout: 200 })
    })

    it('clears error message when user starts typing', async () => {
      const user = userEvent.setup()
      mockLogin.mockRejectedValue(new Error('Invalid credentials'))
      
      render(<Login />, { authValue: createUnauthenticatedState() })
      
      const emailInput = screen.getByLabelText(/email/i)
      const passwordInput = screen.getByLabelText(/password/i)
      const submitButton = screen.getByRole('button', { name: /sign in/i })
      
      await user.type(emailInput, 'test@example.com')
      await user.type(passwordInput, 'wrongPassword')
      await user.click(submitButton)
      
      await waitFor(() => {
        expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
      })
      
      // Start typing in email field
      await user.type(emailInput, '2')
      
      await waitFor(() => {
        expect(screen.queryByText('Invalid credentials')).not.toBeInTheDocument()
      })
    })
  })
})