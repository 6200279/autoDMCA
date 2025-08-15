import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi, describe, beforeEach, afterEach, it, expect } from 'vitest'

import BillingDashboard from '@/components/billing/BillingDashboard'
import { AuthProvider } from '@/contexts/AuthContext'

// Mock Stripe
vi.mock('@stripe/react-stripe-js', () => ({
  Elements: ({ children }: any) => children,
  useStripe: () => ({
    confirmPayment: vi.fn(),
    createPaymentMethod: vi.fn(),
  }),
  useElements: () => ({
    getElement: vi.fn(),
  }),
  CardElement: () => <div data-testid="card-element">Card Element</div>,
}))

// Mock API responses
const mockSubscription = {
  id: 'sub_123',
  status: 'active',
  plan: 'premium',
  current_period_start: '2024-01-01T00:00:00Z',
  current_period_end: '2024-02-01T00:00:00Z',
  cancel_at_period_end: false,
  price: 2999,
  currency: 'usd',
}

const mockUsage = {
  current_period: {
    scans: 150,
    takedowns: 5,
    monitoring_profiles: 3,
  },
  limits: {
    scans: 1000,
    takedowns: 50,
    monitoring_profiles: 10,
  },
}

const mockInvoices = [
  {
    id: 'inv_001',
    amount: 2999,
    currency: 'usd',
    status: 'paid',
    created: '2024-01-01T00:00:00Z',
    period_start: '2024-01-01T00:00:00Z',
    period_end: '2024-02-01T00:00:00Z',
  },
  {
    id: 'inv_002',
    amount: 2999,
    currency: 'usd',
    status: 'paid',
    created: '2023-12-01T00:00:00Z',
    period_start: '2023-12-01T00:00:00Z',
    period_end: '2024-01-01T00:00:00Z',
  },
]

// Mock services
vi.mock('@/services/api', () => ({
  billingAPI: {
    getSubscription: vi.fn(() => Promise.resolve(mockSubscription)),
    getUsage: vi.fn(() => Promise.resolve(mockUsage)),
    getInvoices: vi.fn(() => Promise.resolve(mockInvoices)),
    createPaymentIntent: vi.fn(() => Promise.resolve({
      client_secret: 'pi_test_client_secret',
    })),
    updateSubscription: vi.fn(() => Promise.resolve(mockSubscription)),
    cancelSubscription: vi.fn(() => Promise.resolve({
      ...mockSubscription,
      cancel_at_period_end: true,
    })),
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

describe('BillingDashboard Component', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(() => {
    user = userEvent.setup()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders billing dashboard correctly', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /billing/i })).toBeInTheDocument()
    })

    expect(screen.getByText(/subscription/i)).toBeInTheDocument()
    expect(screen.getByText(/usage/i)).toBeInTheDocument()
    expect(screen.getByText(/invoices/i)).toBeInTheDocument()
  })

  it('displays current subscription information', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/premium plan/i)).toBeInTheDocument()
      expect(screen.getByText(/active/i)).toBeInTheDocument()
      expect(screen.getByText(/\$29\.99/)).toBeInTheDocument()
    })

    // Check billing period
    expect(screen.getByText(/next billing: february 1, 2024/i)).toBeInTheDocument()
  })

  it('shows usage statistics with progress bars', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/150 \/ 1,000/)).toBeInTheDocument() // Scans
      expect(screen.getByText(/5 \/ 50/)).toBeInTheDocument() // Takedowns
      expect(screen.getByText(/3 \/ 10/)).toBeInTheDocument() // Profiles
    })

    // Check progress bars
    const progressBars = screen.getAllByRole('progressbar')
    expect(progressBars).toHaveLength(3)

    // Verify progress percentages
    expect(progressBars[0]).toHaveAttribute('aria-valuenow', '15') // 150/1000 = 15%
    expect(progressBars[1]).toHaveAttribute('aria-valuenow', '10') // 5/50 = 10%
    expect(progressBars[2]).toHaveAttribute('aria-valuenow', '30') // 3/10 = 30%
  })

  it('displays invoice history table', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('table')).toBeInTheDocument()
    })

    const table = screen.getByRole('table')
    
    // Check table headers
    expect(within(table).getByText(/invoice/i)).toBeInTheDocument()
    expect(within(table).getByText(/amount/i)).toBeInTheDocument()
    expect(within(table).getByText(/status/i)).toBeInTheDocument()
    expect(within(table).getByText(/date/i)).toBeInTheDocument()

    // Check invoice data
    expect(within(table).getByText('inv_001')).toBeInTheDocument()
    expect(within(table).getByText('inv_002')).toBeInTheDocument()
    expect(within(table).getAllByText('$29.99')).toHaveLength(2)
    expect(within(table).getAllByText(/paid/i)).toHaveLength(2)
  })

  it('allows upgrading subscription plan', async () => {
    const { billingAPI } = await import('@/services/api')
    const mockUpdateSubscription = vi.mocked(billingAPI.updateSubscription)

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /upgrade plan/i })).toBeInTheDocument()
    })

    const upgradeButton = screen.getByRole('button', { name: /upgrade plan/i })
    await user.click(upgradeButton)

    // Should open upgrade modal
    await waitFor(() => {
      expect(screen.getByText(/choose your plan/i)).toBeInTheDocument()
    })

    // Select enterprise plan
    const enterpriseOption = screen.getByRole('radio', { name: /enterprise/i })
    await user.click(enterpriseOption)

    const confirmButton = screen.getByRole('button', { name: /confirm upgrade/i })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(mockUpdateSubscription).toHaveBeenCalledWith({
        plan: 'enterprise',
      })
    })
  })

  it('allows canceling subscription', async () => {
    const { billingAPI } = await import('@/services/api')
    const mockCancelSubscription = vi.mocked(billingAPI.cancelSubscription)

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /cancel subscription/i })).toBeInTheDocument()
    })

    const cancelButton = screen.getByRole('button', { name: /cancel subscription/i })
    await user.click(cancelButton)

    // Should show confirmation dialog
    await waitFor(() => {
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument()
    })

    const confirmCancelButton = screen.getByRole('button', { name: /yes, cancel/i })
    await user.click(confirmCancelButton)

    await waitFor(() => {
      expect(mockCancelSubscription).toHaveBeenCalled()
    })
  })

  it('handles payment method updates', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /update payment method/i })).toBeInTheDocument()
    })

    const updatePaymentButton = screen.getByRole('button', { name: /update payment method/i })
    await user.click(updatePaymentButton)

    // Should show payment method form
    await waitFor(() => {
      expect(screen.getByTestId('card-element')).toBeInTheDocument()
    })

    const saveButton = screen.getByRole('button', { name: /save payment method/i })
    expect(saveButton).toBeInTheDocument()
  })

  it('downloads invoices when download button is clicked', async () => {
    const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.createObjectURL = mockCreateObjectURL

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /download/i })).toHaveLength(2)
    })

    const downloadButtons = screen.getAllByRole('button', { name: /download/i })
    await user.click(downloadButtons[0])

    // Should trigger download
    expect(mockCreateObjectURL).toHaveBeenCalled()
  })

  it('shows usage warnings when approaching limits', async () => {
    const { billingAPI } = await import('@/services/api')
    vi.mocked(billingAPI.getUsage).mockResolvedValue({
      current_period: {
        scans: 900, // 90% of limit
        takedowns: 45, // 90% of limit
        monitoring_profiles: 9, // 90% of limit
      },
      limits: {
        scans: 1000,
        takedowns: 50,
        monitoring_profiles: 10,
      },
    })

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/900 \/ 1,000/)).toBeInTheDocument()
    })

    // Should show warning messages
    expect(screen.getByText(/approaching scan limit/i)).toBeInTheDocument()
    expect(screen.getByText(/approaching takedown limit/i)).toBeInTheDocument()
    expect(screen.getByText(/approaching profile limit/i)).toBeInTheDocument()
  })

  it('handles billing errors gracefully', async () => {
    const { billingAPI } = await import('@/services/api')
    vi.mocked(billingAPI.getSubscription).mockRejectedValue(new Error('Billing API Error'))

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/error loading billing information/i)).toBeInTheDocument()
    })

    // Should show retry button
    expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
  })

  it('shows different states for subscription statuses', async () => {
    const { billingAPI } = await import('@/services/api')
    
    // Test canceled subscription
    vi.mocked(billingAPI.getSubscription).mockResolvedValue({
      ...mockSubscription,
      status: 'canceled',
      cancel_at_period_end: true,
    })

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/canceled/i)).toBeInTheDocument()
      expect(screen.getByText(/access until february 1, 2024/i)).toBeInTheDocument()
    })

    // Should show reactivate button
    expect(screen.getByRole('button', { name: /reactivate/i })).toBeInTheDocument()
  })

  it('formats currency amounts correctly', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      // Check various currency formats
      expect(screen.getByText(/\$29\.99/)).toBeInTheDocument()
    })

    // Check invoice amounts
    const table = screen.getByRole('table')
    expect(within(table).getAllByText('$29.99')).toHaveLength(2)
  })

  it('shows loading states during API calls', async () => {
    const { billingAPI } = await import('@/services/api')
    
    // Mock delayed responses
    vi.mocked(billingAPI.getSubscription).mockImplementation(
      () => new Promise(resolve => setTimeout(() => resolve(mockSubscription), 1000))
    )

    render(<BillingDashboard />, { wrapper: createWrapper() })

    // Should show loading skeleton
    expect(screen.getByText(/loading/i) || screen.getByRole('status')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/premium plan/i)).toBeInTheDocument()
    }, { timeout: 2000 })
  })

  it('handles subscription without payment method', async () => {
    const { billingAPI } = await import('@/services/api')
    vi.mocked(billingAPI.getSubscription).mockResolvedValue({
      ...mockSubscription,
      status: 'incomplete',
      payment_method: null,
    })

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/payment method required/i)).toBeInTheDocument()
    })

    // Should show add payment method button
    expect(screen.getByRole('button', { name: /add payment method/i })).toBeInTheDocument()
  })

  it('displays proper accessibility attributes', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /billing/i })).toBeInTheDocument()
    })

    // Check progress bars have proper labels
    const progressBars = screen.getAllByRole('progressbar')
    progressBars.forEach(bar => {
      expect(bar).toHaveAttribute('aria-label')
      expect(bar).toHaveAttribute('aria-valuenow')
      expect(bar).toHaveAttribute('aria-valuemin', '0')
      expect(bar).toHaveAttribute('aria-valuemax', '100')
    })

    // Check table accessibility
    const table = screen.getByRole('table')
    expect(table).toHaveAttribute('aria-label', 'Invoice history')
  })

  it('supports keyboard navigation', async () => {
    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /upgrade plan/i })).toBeInTheDocument()
    })

    // Tab through interactive elements
    await user.tab()
    expect(screen.getByRole('button', { name: /upgrade plan/i })).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: /update payment method/i })).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('button', { name: /cancel subscription/i })).toHaveFocus()
  })

  it('auto-refreshes billing data periodically', async () => {
    const { billingAPI } = await import('@/services/api')
    const mockGetSubscription = vi.mocked(billingAPI.getSubscription)

    vi.useFakeTimers()

    render(<BillingDashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(mockGetSubscription).toHaveBeenCalledTimes(1)
    })

    // Fast-forward 5 minutes
    vi.advanceTimersByTime(5 * 60 * 1000)

    await waitFor(() => {
      expect(mockGetSubscription).toHaveBeenCalledTimes(2)
    })

    vi.useRealTimers()
  })
})