import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { TaskStatusBadge } from './TaskStatusBadge'

describe('TaskStatusBadge', () => {
  it('renders human-readable status labels', () => {
    render(<TaskStatusBadge status="awaiting_approval" />)
    expect(screen.getByText('awaiting approval')).toBeInTheDocument()
  })

  it('covers all task states', () => {
    const states = [
      'pending',
      'planning',
      'awaiting_approval',
      'running',
      'paused',
      'completed',
      'failed',
      'cancelled',
    ] as const
    for (const status of states) {
      const { unmount } = render(<TaskStatusBadge status={status} />)
      expect(screen.getByText(status.replace(/_/g, ' '))).toBeInTheDocument()
      unmount()
    }
  })
})