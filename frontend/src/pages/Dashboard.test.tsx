import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { vi, describe, beforeEach, afterEach, it, expect } from 'vitest'

import Dashboard from '@/pages/Dashboard'
import { AuthProvider } from '@/contexts/AuthContext'

// Mock API responses
const mockDashboardStats = {
  total_profiles: 3,
  active_monitoring: 2,
  total_infringements: 25,
  resolved_cases: 20,
  success_rate: 80,
  recent_activity: [
    {
      id: 1,
      type: 'infringement_detected',
      description: 'New infringement detected on Instagram',
      timestamp: '2024-01-15T12:00:00Z',
    },
    {
      id: 2,
      type: 'takedown_successful',
      description: 'Takedown request successful',
      timestamp: '2024-01-15T11:00:00Z',
    },
  ],
}

const mockAnalyticsData = {
  timeline: [
    { date: '2024-01-01', infringements: 5, takedowns: 2 },
    { date: '2024-01-02', infringements: 3, takedowns: 1 },
    { date: '2024-01-03', infringements: 7, takedowns: 3 },
  ],
  summary: {
    total_infringements: 15,
    total_takedowns: 6,
    success_rate: 83.3,
  },
}

// Mock services
vi.mock('@/services/api', () => ({
  dashboardAPI: {
    getStats: vi.fn(() => Promise.resolve(mockDashboardStats)),
    getAnalytics: vi.fn(() => Promise.resolve(mockAnalyticsData)),
  },
  profileAPI: {
    getProfiles: vi.fn(() => Promise.resolve({
      items: [
        { id: 1, stage_name: 'Creator 1', monitoring_enabled: true },
        { id: 2, stage_name: 'Creator 2', monitoring_enabled: true },
        { id: 3, stage_name: 'Creator 3', monitoring_enabled: false },
      ],
      total: 3,
    })),
  },
}))

// Mock chart components to avoid canvas issues in tests
vi.mock('react-chartjs-2', () => ({
  Line: ({ data, options }: any) => (
    <div data-testid="line-chart" data-chart-data={JSON.stringify(data)} />
  ),
  Bar: ({ data, options }: any) => (
    <div data-testid="bar-chart" data-chart-data={JSON.stringify(data)} />
  ),
  Pie: ({ data, options }: any) => (
    <div data-testid="pie-chart" data-chart-data={JSON.stringify(data)} />
  ),
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

describe('Dashboard Component', () => {
  let user: ReturnType<typeof userEvent.setup>

  beforeEach(() => {
    user = userEvent.setup()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders dashboard layout correctly', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument()
    })

    // Check for main sections
    expect(screen.getByText(/overview/i)).toBeInTheDocument()
    expect(screen.getByText(/recent activity/i)).toBeInTheDocument()
    expect(screen.getByText(/analytics/i)).toBeInTheDocument()
  })

  it('displays stat cards with correct data', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('3')).toBeInTheDocument() // total_profiles
      expect(screen.getByText('2')).toBeInTheDocument() // active_monitoring  
      expect(screen.getByText('25')).toBeInTheDocument() // total_infringements
      expect(screen.getByText('20')).toBeInTheDocument() // resolved_cases
      expect(screen.getByText('80%')).toBeInTheDocument() // success_rate
    })

    expect(screen.getByText(/total profiles/i)).toBeInTheDocument()
    expect(screen.getByText(/active monitoring/i)).toBeInTheDocument()
    expect(screen.getByText(/total infringements/i)).toBeInTheDocument()
    expect(screen.getByText(/resolved cases/i)).toBeInTheDocument()
    expect(screen.getByText(/success rate/i)).toBeInTheDocument()
  })

  it('displays recent activity list', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/new infringement detected on instagram/i)).toBeInTheDocument()
      expect(screen.getByText(/takedown request successful/i)).toBeInTheDocument()
    })

    // Check activity timestamps
    expect(screen.getByText(/2024-01-15/)).toBeInTheDocument()
  })

  it('renders analytics chart', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByTestId('line-chart')).toBeInTheDocument()
    })

    const chart = screen.getByTestId('line-chart')
    const chartData = JSON.parse(chart.getAttribute('data-chart-data') || '{}')
    
    expect(chartData.labels).toContain('2024-01-01')
    expect(chartData.labels).toContain('2024-01-02')
    expect(chartData.labels).toContain('2024-01-03')
  })

  it('shows loading state initially', () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    expect(screen.getByText(/loading/i) || screen.getByRole('status')).toBeInTheDocument()
  })

  it('handles API errors gracefully', async () => {
    const { dashboardAPI } = await import('@/services/api')
    vi.mocked(dashboardAPI.getStats).mockRejectedValue(new Error('API Error'))

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/error loading dashboard data/i)).toBeInTheDocument()
    })
  })

  it('allows refreshing dashboard data', async () => {
    const { dashboardAPI } = await import('@/services/api')
    const mockGetStats = vi.mocked(dashboardAPI.getStats)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(mockGetStats).toHaveBeenCalledTimes(1)
    })

    const refreshButton = screen.getByRole('button', { name: /refresh/i })
    await user.click(refreshButton)

    await waitFor(() => {
      expect(mockGetStats).toHaveBeenCalledTimes(2)
    })
  })

  it('navigates to profiles page when quick action is clicked', async () => {
    const mockNavigate = vi.fn()
    vi.mocked(require('react-router-dom').useNavigate).mockReturnValue(mockNavigate)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/manage profiles/i)).toBeInTheDocument()
    })

    const manageProfilesButton = screen.getByRole('button', { name: /manage profiles/i })
    await user.click(manageProfilesButton)

    expect(mockNavigate).toHaveBeenCalledWith('/profiles')
  })

  it('displays correct period selector for analytics', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/last 30 days/i)).toBeInTheDocument()
    })

    const periodSelector = screen.getByRole('combobox', { name: /period/i })
    expect(periodSelector).toBeInTheDocument()

    await user.click(periodSelector)
    
    expect(screen.getByText(/last 7 days/i)).toBeInTheDocument()
    expect(screen.getByText(/last 90 days/i)).toBeInTheDocument()
  })

  it('updates analytics when period is changed', async () => {
    const { dashboardAPI } = await import('@/services/api')
    const mockGetAnalytics = vi.mocked(dashboardAPI.getAnalytics)

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(mockGetAnalytics).toHaveBeenCalledWith({ period: '30d' })
    })

    const periodSelector = screen.getByRole('combobox', { name: /period/i })
    await user.click(periodSelector)
    
    const sevenDaysOption = screen.getByText(/last 7 days/i)
    await user.click(sevenDaysOption)

    await waitFor(() => {
      expect(mockGetAnalytics).toHaveBeenCalledWith({ period: '7d' })
    })
  })

  it('displays empty state when no data is available', async () => {
    const { dashboardAPI } = await import('@/services/api')
    vi.mocked(dashboardAPI.getStats).mockResolvedValue({
      ...mockDashboardStats,
      total_profiles: 0,
      total_infringements: 0,
      recent_activity: [],
    })

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/no recent activity/i)).toBeInTheDocument()
    })

    expect(screen.getByText(/get started by creating your first profile/i)).toBeInTheDocument()
  })

  it('shows notification indicators for urgent items', async () => {
    const { dashboardAPI } = await import('@/services/api')
    vi.mocked(dashboardAPI.getStats).mockResolvedValue({
      ...mockDashboardStats,
      recent_activity: [
        {
          id: 1,
          type: 'urgent_infringement',
          description: 'High-confidence infringement detected',
          timestamp: '2024-01-15T12:00:00Z',
          priority: 'high',
        },
      ],
    })

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText(/high-confidence infringement detected/i)).toBeInTheDocument()
    })

    // Should have urgent indicator
    expect(screen.getByRole('alert') || screen.getByText(/urgent/i)).toBeInTheDocument()
  })

  it('formats numbers correctly in stat cards', async () => {
    const { dashboardAPI } = await import('@/services/api')
    vi.mocked(dashboardAPI.getStats).mockResolvedValue({
      ...mockDashboardStats,
      total_infringements: 1250,
      resolved_cases: 1100,
    })

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      // Should format large numbers with commas
      expect(screen.getByText('1,250')).toBeInTheDocument()
      expect(screen.getByText('1,100')).toBeInTheDocument()
    })
  })

  it('displays tooltips on stat cards', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument()
    })

    const infringementCard = screen.getByText(/total infringements/i).closest('[data-tooltip]')
    
    if (infringementCard) {
      await user.hover(infringementCard)
      
      await waitFor(() => {
        expect(screen.getByText(/number of detected infringements/i)).toBeInTheDocument()
      })
    }
  })

  it('handles real-time updates via WebSocket', async () => {
    const mockWebSocket = {
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      close: vi.fn(),
    }

    // Mock WebSocket
    global.WebSocket = vi.fn(() => mockWebSocket) as any

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(mockWebSocket.addEventListener).toHaveBeenCalledWith('message', expect.any(Function))
    })

    // Simulate receiving a WebSocket message
    const messageHandler = mockWebSocket.addEventListener.mock.calls.find(
      call => call[0] === 'message'
    )?.[1]

    if (messageHandler) {
      messageHandler({
        data: JSON.stringify({
          type: 'stats_update',
          data: { total_infringements: 26 },
        }),
      })

      await waitFor(() => {
        expect(screen.getByText('26')).toBeInTheDocument()
      })
    }
  })

  it('exports dashboard data when export button is clicked', async () => {
    const mockCreateObjectURL = vi.fn(() => 'blob:mock-url')
    global.URL.createObjectURL = mockCreateObjectURL

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /export/i })).toBeInTheDocument()
    })

    const exportButton = screen.getByRole('button', { name: /export/i })
    await user.click(exportButton)

    expect(mockCreateObjectURL).toHaveBeenCalled()
  })

  it('maintains responsive layout on different screen sizes', async () => {
    // Mock window dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 768,
    })

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument()
    })

    // Check that responsive classes are applied
    const container = screen.getByRole('main')
    expect(container).toHaveClass('responsive-layout')
  })

  it('auto-refreshes data at regular intervals', async () => {
    const { dashboardAPI } = await import('@/services/api')
    const mockGetStats = vi.mocked(dashboardAPI.getStats)

    vi.useFakeTimers()

    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(mockGetStats).toHaveBeenCalledTimes(1)
    })

    // Fast-forward 5 minutes
    vi.advanceTimersByTime(5 * 60 * 1000)

    await waitFor(() => {
      expect(mockGetStats).toHaveBeenCalledTimes(2)
    })

    vi.useRealTimers()
  })

  it('handles keyboard navigation correctly', async () => {
    render(<Dashboard />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /dashboard/i })).toBeInTheDocument()
    })

    // Tab through interactive elements
    await user.tab()
    expect(screen.getByRole('button', { name: /refresh/i })).toHaveFocus()

    await user.tab()
    expect(screen.getByRole('combobox', { name: /period/i })).toHaveFocus()
  })
})