import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import App from './App'

describe('invoice review prototype', () => {
  it('labels synthetic sample values and warns recording is not approval or payment', () => {
    render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: /Load sample/i })[0])
    expect(screen.getAllByText(/Synthetic sample values/).length).toBeGreaterThan(0)
    expect(screen.getByText(/does not write a spreadsheet row or approve\/pay/i)).toBeInTheDocument()
  })

  it('requires explicit action to mark the demo record and explains its limits', () => {
    render(<App />)
    fireEvent.click(screen.getAllByRole('button', { name: /Load sample/i })[0])
    fireEvent.click(screen.getAllByRole('button', { name: /Confirm & record/i })[0])
    expect(screen.getByRole('button', { name: /Demo state updated/i })).toBeDisabled()
    expect(screen.getByText(/no spreadsheet row was written/i)).toBeInTheDocument()
  })

  it('leaves uploaded invoice fields blank, unverified, and unrecordable', async () => {
    render(<App />)
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['%PDF-1.4\n%%EOF'], 'invoice.pdf', { type: 'application/pdf' })
    fireEvent.change(fileInput, { target: { files: [file] } })
    await waitFor(() => expect(screen.getByText(/The API is unavailable|not previewed or extracted/i)).toBeInTheDocument())
    expect(screen.getByRole('textbox', { name: /Vendor name/i })).toHaveValue('')
    expect(screen.getAllByRole('button', { name: /Confirm & record/i })[0]).toBeDisabled()
    expect(screen.getByText(/No extraction was performed/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Not checked/i })).toBeInTheDocument()
  })
})
