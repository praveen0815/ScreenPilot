import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import { ErrorBanner } from './ErrorBanner'

describe('ErrorBanner', () => {
  it('shows message and optional retry', () => {
    const onRetry = vi.fn()
    render(<ErrorBanner message="Network failed." onRetry={onRetry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Network failed.')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('omits retry without callback', () => {
    render(<ErrorBanner message="Missing task." />)
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument()
  })
})