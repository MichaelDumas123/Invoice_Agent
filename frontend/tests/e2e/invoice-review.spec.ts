import { expect, test } from '@playwright/test'

function syntheticPdf(): Buffer {
  const stream = 'BT /F1 12 Tf 20 90 Td (Synthetic test invoice only) Tj ET'
  const objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 180] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}\nendstream`,
  ]
  let body = '%PDF-1.4\n'
  const offsets = [0]
  for (const [index, object] of objects.entries()) {
    offsets.push(Buffer.byteLength(body, 'binary'))
    body += `${index + 1} 0 obj\n${object}\nendobj\n`
  }
  const xrefOffset = Buffer.byteLength(body, 'binary')
  body += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`
  body += offsets.slice(1).map((offset) => `${offset.toString().padStart(10, '0')} 00000 n \n`).join('')
  body += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`
  return Buffer.from(body, 'binary')
}

test('review sample invoice and explicitly record demo log only', async ({ page }) => {
  page.on('dialog', (dialog) => dialog.accept())
  await page.goto('/')
  await page.getByRole('button', { name: /Load sample/i }).first().click()
  await expect(page.getByRole('heading', { name: /Let’s get this invoice right/i })).toBeVisible()
  await expect(page.getByText('Synthetic sample values — not extracted from an invoice.')).toBeVisible()
  await expect(page.getByText(/does not write a spreadsheet row or approve\/pay/i)).toBeVisible()
  await page.getByRole('textbox', { name: /Ask about this invoice/i }).fill('Can you verify this invoice?')
  await page.getByRole('button', { name: /Send message/i }).click()
  await expect(page.getByText(/This demo uses synthetic sample values only/i)).toBeVisible()
  await page.getByRole('button', { name: /Confirm & record/i }).click()
  await expect(page.getByRole('button', { name: /Demo state updated/i })).toBeDisabled()
  await expect(page.getByRole('status')).toContainText(/no spreadsheet row was written/i)
})

test('upload renders a safe preview without extracting or recording invoice data', async ({ page }) => {
  await page.goto('/')
  await page.getByLabel('Upload invoice file').setInputFiles({
    name: 'synthetic-preview.pdf',
    mimeType: 'application/pdf',
    buffer: syntheticPdf(),
  })

  await expect(page.getByText(/Pages rendered; OCR and extraction are disabled/i)).toBeVisible()
  await expect(page.getByAltText('Safely rendered invoice page 1')).toBeVisible()
  await expect(page.getByRole('textbox', { name: 'Vendor name' })).toHaveValue('')
  await expect(page.getByRole('button', { name: /Confirm & record/i })).toBeDisabled()
  await expect(page.getByText(/No extraction was performed for the uploaded file/i)).toBeVisible()
})
