import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import type { ApprovalRequest } from '../../types/api'
import { ApprovalCard } from './ApprovalCard'

const approval: ApprovalRequest = {
  id: 'a-1',
  category: 'purchase',
  status: 'pending',
  detail: 'Confirm checkout',
  display_json: JSON.stringify({
    steps: [{ sequence: 1, description: 'Pay invoice', tool_name: 'mock.pay', risk: 'high' }],
  }),
  expires_at: '2026-01-01T00:00:00Z',
  decided_at: null,
  rejection_reason: null,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('ApprovalCard', () => {
  it('renders plan steps and fires approve', () => {
    const onApprove = vi.fn()
    const onReject = vi.fn()
    render(<ApprovalCard approval={approval} onApprove={onApprove} onReject={onReject} />)
    expect(screen.getByText('Pay invoice')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Approve plan' }))
    expect(onApprove).toHaveBeenCalledOnce()
  })

  it('submits reject reason', () => {
    const onReject = vi.fn()
    render(<ApprovalCard approval={approval} onApprove={vi.fn()} onReject={onReject} />)
    fireEvent.change(screen.getByLabelText('Rejection reason'), { target: { value: 'Too risky' } })
    fireEvent.click(screen.getByRole('button', { name: 'Reject' }))
    expect(onReject).toHaveBeenCalledWith('Too risky')
  })
})