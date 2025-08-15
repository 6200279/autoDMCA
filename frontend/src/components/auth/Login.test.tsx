import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi, describe, beforeEach, afterEach, it, expect } from 'vitest'

import Login from '@/pages/Login'
import { AuthProvider } from '@/contexts/AuthContext'

// Mock react-router-dom navigation
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  }
})

// Mock API
vi.mock('@/services/api', () => ({
  authAPI: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}))

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          {children}
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('Login Component', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(() => {
    user = userEvent.setup()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form correctly', () => {
    render(<Login />, { wrapper: createWrapper() })

    expect(screen.getByRole('heading', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(screen.getByText(/don't have an account/i)).toBeInTheDocument()
  })

  it('validates email field correctly', async () => {
    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    // Test empty email
    await user.click(submitButton)
    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    })

    // Test invalid email format
    await user.type(emailInput, 'invalid-email')
    await user.click(submitButton)
    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument()
    })

    // Test valid email
    await user.clear(emailInput)
    await user.type(emailInput, 'test@example.com')
    await waitFor(() => {
      expect(screen.queryByText(/please enter a valid email/i)).not.toBeInTheDocument()
    })
  })

  it('validates password field correctly', async () => {
    render(<Login />, { wrapper: createWrapper() })

    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    // Test empty password
    await user.click(submitButton)
    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    })

    // Test minimum length
    await user.type(passwordInput, '123')
    await user.click(submitButton)
    await waitFor(() => {
      expect(screen.getByText(/password must be at least 6 characters/i)).toBeInTheDocument()
    })
  })

  it('shows/hides password when toggle button is clicked', async () => {
    render(<Login />, { wrapper: createWrapper() })

    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement
    const toggleButton = screen.getByRole('button', { name: /toggle password visibility/i })

    // Initially password should be hidden
    expect(passwordInput.type).toBe('password')

    // Click to show password
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('text')

    // Click to hide password
    await user.click(toggleButton)
    expect(passwordInput.type).toBe('password')
  })

  it('submits form with valid data', async () => {
    const { authAPI } = await import('@/services/api')
    const mockLogin = vi.mocked(authAPI.login)
    
    mockLogin.mockResolvedValue({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      user: {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
      },
    })

    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('displays error message on login failure', async () => {
    const { authAPI } = await import('@/services/api')
    const mockLogin = vi.mocked(authAPI.login)
    
    mockLogin.mockRejectedValue(new Error('Invalid credentials'))

    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'wrongpassword')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
    })
  })

  it('shows loading state during submission', async () => {
    const { authAPI } = await import('@/services/api')
    const mockLogin = vi.mocked(authAPI.login)
    
    // Mock a delayed response
    mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    // Should show loading state
    expect(screen.getByText(/signing in/i)).toBeInTheDocument()
    expect(submitButton).toBeDisabled()
  })

  it('prevents multiple submissions', async () => {
    const { authAPI } = await import('@/services/api')
    const mockLogin = vi.mocked(authAPI.login)
    
    mockLogin.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 1000)))

    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')

    // Click multiple times
    await user.click(submitButton)
    await user.click(submitButton)
    await user.click(submitButton)

    // Should only call login once
    expect(mockLogin).toHaveBeenCalledTimes(1)
  })

  it('handles network errors gracefully', async () => {
    const { authAPI } = await import('@/services/api')
    const mockLogin = vi.mocked(authAPI.login)
    
    mockLogin.mockRejectedValue(new Error('Network Error'))

    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument()
    })
  })

  it('redirects to register page when register link is clicked', async () => {
    render(<Login />, { wrapper: createWrapper() })

    const registerLink = screen.getByRole('link', { name: /sign up/i })
    await user.click(registerLink)

    expect(mockNavigate).toHaveBeenCalledWith('/register')
  })

  it('redirects to forgot password page when link is clicked', async () => {
    render(<Login />, { wrapper: createWrapper() })

    const forgotPasswordLink = screen.getByRole('link', { name: /forgot password/i })
    await user.click(forgotPasswordLink)

    expect(mockNavigate).toHaveBeenCalledWith('/forgot-password')
  })

  it('clears form on successful login', async () => {
    const { authAPI } = await import('@/services/api')
    const mockLogin = vi.mocked(authAPI.login)
    
    mockLogin.mockResolvedValue({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      user: {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
      },
    })

    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.click(submitButton)

    await waitFor(() => {
      expect(emailInput.value).toBe('')
      expect(passwordInput.value).toBe('')
    })
  })

  it('focuses email input on mount', () => {
    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    expect(emailInput).toHaveFocus()
  })

  it('allows form submission with Enter key', async () => {
    const { authAPI } = await import('@/services/api')
    const mockLogin = vi.mocked(authAPI.login)
    
    mockLogin.mockResolvedValue({
      access_token: 'mock-token',
      refresh_token: 'mock-refresh-token',
      user: {
        id: 1,
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
      },
    })

    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')
    await user.keyboard('{Enter}')

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
      })
    })
  })

  it('displays proper accessibility attributes', () => {
    render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i)
    const passwordInput = screen.getByLabelText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    expect(emailInput).toHaveAttribute('type', 'email')
    expect(emailInput).toHaveAttribute('autocomplete', 'email')
    expect(passwordInput).toHaveAttribute('type', 'password')
    expect(passwordInput).toHaveAttribute('autocomplete', 'current-password')
    expect(submitButton).toHaveAttribute('type', 'submit')
  })

  it('maintains form state during re-renders', async () => {
    const { rerender } = render(<Login />, { wrapper: createWrapper() })

    const emailInput = screen.getByLabelText(/email/i) as HTMLInputElement
    const passwordInput = screen.getByLabelText(/password/i) as HTMLInputElement

    await user.type(emailInput, 'test@example.com')
    await user.type(passwordInput, 'password123')

    // Re-render component
    rerender(<Login />)

    expect(emailInput.value).toBe('test@example.com')
    expect(passwordInput.value).toBe('password123')
  })
})