import { useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  ArrowDownToLine,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleHelp,
  FileCheck2,
  FileSpreadsheet,
  FileText,
  Inbox,
  LockKeyhole,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Upload,
  X,
} from 'lucide-react'

type Invoice = {
  id: string
  vendor: string
  number: string
  date: string
  amount: string
  currency: string
  status: 'Review needed' | 'Ready' | 'Recorded'
  initial: string
  color: string
  detail: string
}

type ChatLine = { role: 'assistant' | 'user'; text: string }
type InvoiceFieldKey = 'vendor_name' | 'invoice_number' | 'invoice_date' | 'due_date' | 'po_number' | 'currency' | 'subtotal' | 'tax' | 'charges' | 'discount' | 'total'

const STARTER_INVOICE: Invoice = {
  id: 'INV-2026-0148',
  vendor: 'Northstar Office Co.',
  number: 'NS-2026-0148',
  date: 'Nov 18, 2026',
  amount: '2,480.00',
  currency: 'USD',
  status: 'Review needed',
  initial: 'N',
  color: 'coral',
  detail: 'Quarterly office supplies · 4 line items',
}

const ALLOWED_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/heic', 'image/heif']

function App() {
  const [invoice, setInvoice] = useState<Invoice>(STARTER_INVOICE)
  const [sampleMode, setSampleMode] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [chat, setChat] = useState<ChatLine[]>([
    { role: 'assistant', text: 'Upload a synthetic test invoice to exercise the API. Extraction is disabled in this prototype.' },
  ])
  const [chatText, setChatText] = useState('')
  const [notice, setNotice] = useState('')
  const [recorded, setRecorded] = useState(false)
  const [busy, setBusy] = useState(false)
  const workspaceId = 'demo-workspace'
  const [draftId, setDraftId] = useState('')
  const [documentId, setDocumentId] = useState('')
  const [documentStatus, setDocumentStatus] = useState('')
  const [pages, setPages] = useState<Array<{ page: number; status: string; error?: string }>>([])
  const [apiAvailable, setApiAvailable] = useState(false)
  const [draftVersion, setDraftVersion] = useState(1)
  const [fieldValues, setFieldValues] = useState<Record<InvoiceFieldKey, string>>({
    vendor_name: '', invoice_number: '', invoice_date: '', due_date: '', po_number: '', currency: '', subtotal: '', tax: '', charges: '', discount: '', total: '',
  })
  const [workbookId, setWorkbookId] = useState('')
  const [workbookVersion, setWorkbookVersion] = useState(0)
  const [mappingVersion, setMappingVersion] = useState(0)
  const [workbookName, setWorkbookName] = useState('')
  const [worksheet, setWorksheet] = useState('')
  const [headers, setHeaders] = useState<string[]>([])
  const [fieldMapping, setFieldMapping] = useState<Record<string, number>>({})
  const [mappingSaved, setMappingSaved] = useState(false)
  const [validationId, setValidationId] = useState('')
  const [validationItems, setValidationItems] = useState<Array<{ check: string; status: string; reason: string }>>([])
  const [historyItems, setHistoryItems] = useState<Array<{ id: string; filename: string; status: string; reference?: string }>>([])
  const [reviewReason, setReviewReason] = useState('')
  const workbookInputRef = useRef<HTMLInputElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const total = useMemo(() => Number(invoice.amount.replaceAll(',', '')), [invoice.amount])
  const subtotal = (total / 1.08).toFixed(2)
  const tax = (total - Number(subtotal)).toFixed(2)

  function loadSample() {
    setSampleMode(true)
    setFile(null)
    setDraftId('')
    setDocumentId('')
    setDocumentStatus('')
    setPages([])
    setApiAvailable(false)
    setRecorded(false)
    setWorkbookId('')
    setWorkbookVersion(0)
    setWorkbookName('')
    setWorksheet('')
    setHeaders([])
    setFieldMapping({})
    setMappingSaved(false)
    setMappingVersion(0)
    setValidationId('')
    setValidationItems([])
    setInvoice(STARTER_INVOICE)
    setFieldValues({ vendor_name: STARTER_INVOICE.vendor, invoice_number: STARTER_INVOICE.number, invoice_date: '2026-11-18', due_date: '', po_number: '', currency: 'USD', subtotal: '2296.30', tax: '183.70', charges: '0.00', discount: '0.00', total: '2480.00' })
    setChat([{ role: 'assistant', text: 'Synthetic sample values only. Verify with an actual source before recording.' }])
    setNotice('Synthetic sample loaded. No invoice document is attached.')
  }

  function updateField(key: InvoiceFieldKey, value: string) {
    setFieldValues((current) => ({ ...current, [key]: value }))
    if (key === 'vendor_name') setInvoice((current) => ({ ...current, vendor: value }))
    if (key === 'invoice_number') setInvoice((current) => ({ ...current, number: value }))
    if (key === 'invoice_date') setInvoice((current) => ({ ...current, date: value }))
    if (key === 'currency') setInvoice((current) => ({ ...current, currency: value }))
    if (key === 'total') setInvoice((current) => ({ ...current, amount: value }))
  }

  async function commitField(key: InvoiceFieldKey) {
    if (!draftId || !apiAvailable) return
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/drafts/${draftId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-Demo-User': 'demo-operator',
          'X-Demo-Workspace': workspaceId,
          'X-Demo-Role': 'operator',
          'X-CSRF-Token': 'local-demo-csrf-token',
        },
        body: JSON.stringify({ field_name: key, value: fieldValues[key], expected_version: draftVersion }),
      })
      const body = (await response.json()) as { version?: number; detail?: string }
      if (!response.ok || !body.version) throw new Error(body.detail ?? 'Field could not be saved')
      setDraftVersion(body.version)
      setValidationId('')
      setValidationItems([])
      setRecorded(false)
      setNotice('Field saved. Run validation again before reviewer confirmation.')
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Field could not be saved. Reload the draft and retry.')
    }
  }

  async function uploadWorkbookFile(file: File) {
    const form = new FormData()
    form.append('file', file)
    const response = await fetch(`/api/v1/workspaces/${workspaceId}/workbooks`, {
      method: 'POST',
      headers: { 'X-Demo-User': 'demo-operator', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'operator', 'X-CSRF-Token': 'local-demo-csrf-token' },
      body: form,
    })
    const body = await response.json() as { id?: string; version?: number; name?: string; inspection?: { worksheets?: Array<{ name: string; headers: string[] }> }; detail?: string }
    if (!response.ok || !body.id) throw new Error(body.detail ?? 'Workbook could not be read')
    const sheet = body.inspection?.worksheets?.[0]
    setWorkbookId(body.id)
    setWorkbookVersion(body.version ?? 1)
    setWorkbookName(body.name ?? file.name)
    setWorksheet(sheet?.name ?? '')
    setHeaders(sheet?.headers ?? [])
    setMappingSaved(false)
    setMappingVersion(0)
    setFieldMapping({})
    setValidationId('')
    setValidationItems([])
    setNotice('Workbook imported as a snapshot. Your original file will not be modified.')
  }

  async function saveFieldMapping() {
    if (!workbookId || !worksheet) return
    const required = ['vendor_name', 'invoice_number', 'invoice_date', 'currency', 'total']
    if (required.some((field) => !fieldMapping[field])) {
      setNotice('Map vendor, invoice number, invoice date, currency, and total before saving.')
      return
    }
    try {
      const metadataResponse = await fetch(`/api/v1/workspaces/${workspaceId}/workbooks/${workbookId}`, { headers: { 'X-Demo-User': 'demo-operator', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'operator' } })
      const metadata = await metadataResponse.json() as { mapping_version?: number; detail?: string }
      if (!metadataResponse.ok) throw new Error(metadata.detail ?? 'Workbook could not be loaded')
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/workbooks/${workbookId}/mappings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Demo-User': 'demo-operator', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'operator', 'X-CSRF-Token': 'local-demo-csrf-token' },
        body: JSON.stringify({ worksheet, expected_version: metadata.mapping_version ?? 0, field_to_column: fieldMapping, required_fields: ['vendor_name', 'invoice_number', 'total'] }),
      })
      const body = await response.json() as { detail?: string }
      if (!response.ok) throw new Error(body.detail ?? 'Mapping could not be saved')
      setMappingSaved(true)
      setMappingVersion(mappingVersion + 1)
      setNotice('Column mapping saved for this workbook snapshot.')
    } catch (error) {
      setMappingSaved(false)
      setNotice(error instanceof Error ? error.message : 'Mapping could not be saved')
    }
  }

  async function runValidation() {
    if (!draftId || !apiAvailable) {
      setNotice('Upload a file first. Extraction is disabled; use the sample for the demo-only path.')
      return
    }
    try {
      if (!workbookId) {
        setNotice('Select a workbook before running final validation.')
        return
      }
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/drafts/${draftId}/validate?workbook_id=${encodeURIComponent(workbookId)}`, {
        method: 'POST',
        headers: { 'X-Demo-User': 'demo-operator', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'operator' },
      })
      const body = await response.json() as { id?: string; draft_version?: number; results?: Array<{ check: string; status: string; reason: string }>; detail?: string }
      if (!response.ok || !body.id) throw new Error(body.detail ?? 'Validation failed')
      setValidationId(body.id)
      if (body.draft_version) setDraftVersion(body.draft_version)
      setValidationItems(body.results ?? [])
      setNotice('Validation reflects entered values only. Uploaded documents were not extracted.')
    } catch (error) {
      setValidationId('')
      setValidationItems([])
      setNotice(error instanceof Error ? error.message : 'Validation failed')
    }
  }

  async function refreshHistory(): Promise<Array<{ id: string; filename: string; status: string; reference?: string }>> {
    const response = await fetch(`/api/v1/workspaces/${workspaceId}/history?limit=50&offset=0`, {
      headers: { 'X-Demo-User': 'demo-operator', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'operator' },
    })
    const body = await response.json() as { items?: Array<{ id: string; filename: string; status: string; reference?: string }>; detail?: string }
    if (!response.ok) throw new Error(body.detail ?? 'History could not be loaded')
    const items = body.items ?? []
    setHistoryItems(items)
    return items
  }

  async function recordUploadedInvoice() {
    if (!draftId || !workbookId || !validationId || !mappingSaved) {
      setNotice('Upload a log, save its column mapping, and run checks before reviewer confirmation.')
      return
    }
    if (!reviewReason.trim()) {
      setNotice('Enter the reviewer confirmation reason before recording this entry.')
      return
    }
    const blockers = validationItems.filter((item) => item.status === 'hard_stop')
    if (blockers.length) {
      setNotice('A policy hard stop blocks recording. Correct the invoice fields and rerun checks.')
      return
    }
    const acknowledgements = validationItems.filter((item) => item.status === 'warning' || item.status === 'inconclusive').map((item) => ({ warning_id: item.check, reason: reviewReason.trim() }))
    if (acknowledgements.length && !reviewReason.trim()) {
      setNotice('Enter a reason to acknowledge the listed warnings before submitting for recording.')
      return
    }
    setRecorded(true)
    setNotice('Recording request submitted. Waiting for the server confirmation…')
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/drafts/${draftId}/record-workbook`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Demo-User': 'demo-reviewer', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'reviewer', 'X-CSRF-Token': 'local-demo-csrf-token' },
        body: JSON.stringify({ draft_id: draftId, workbook_id: workbookId, validation_id: validationId, draft_version: draftVersion, workbook_version: workbookVersion, mapping_version: mappingVersion, reason: reviewReason.trim(), idempotency_key: `${draftId}:${draftVersion}:${workbookId}:${workbookVersion}:${mappingVersion}:${validationId}`, acknowledgements }),
      })
      const body = await response.json() as { status?: string; reference?: string; detail?: string }
      if (!response.ok) {
        setRecorded(false)
        setNotice(body.detail ?? 'Recording was rejected. Reload, correct the draft, and rerun checks.')
        return
      }
      setNotice(`Recorded as ${body.reference}. This is not invoice approval or payment.`)
      setInvoice((current) => ({ ...current, status: 'Recorded' }))
      await refreshHistory()
      await refreshDocumentStatus()
    } catch {
      setRecorded(false)
      setNotice('The server did not confirm the recording outcome. Reload workspace history before retrying.')
    }
  }

  async function handleFiles(files: FileList | null) {
    if (!files?.length) return
    const selected = files[0]
    if (selected.size > 10 * 1024 * 1024) {
      setNotice('This demo accepts files up to 10 MB. The file was not opened or processed.')
      return
    }
    if (!ALLOWED_TYPES.includes(selected.type) && !/\.(pdf|jpe?g|png|heic|heif)$/i.test(selected.name)) {
      setNotice('Unsupported file. Choose a PDF, JPEG, PNG, HEIC or HEIF invoice.')
      return
    }
    setFile(selected)
    setSampleMode(false)
    setDraftId('')
    setDocumentId('')
    setDocumentStatus('')
    setPages([])
    setApiAvailable(false)
    setRecorded(false)
    setDraftVersion(1)
    setFieldValues({ vendor_name: '', invoice_number: '', invoice_date: '', due_date: '', po_number: '', currency: '', subtotal: '', tax: '', charges: '', discount: '', total: '' })
    setValidationId('')
    setValidationItems([])
    setNotice('Validating the upload and rendering document pages…')
    setInvoice({
      ...STARTER_INVOICE,
      id: `DRAFT-${selected.name.slice(0, 18).toUpperCase()}`,
      vendor: '',
      number: '',
      amount: '0.00',
      status: 'Review needed',
      detail: `${selected.name} · ${formatSize(selected.size)} · not processed`,
    })
    const form = new FormData()
    form.append('file', selected)
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/documents`, {
        method: 'POST',
        headers: {
          'X-Demo-User': 'demo-operator',
          'X-Demo-Workspace': workspaceId,
          'X-Demo-Role': 'operator',
          'X-CSRF-Token': 'local-demo-csrf-token',
        },
        body: form,
      })
      if (!response.ok) throw new Error('Upload was rejected')
      const uploaded = (await response.json()) as { draft_id: string; document_id: string; notice: string; status?: string; pages?: Array<{ page: number; status: string; error?: string }> }
      setDraftId(uploaded.draft_id)
      setDocumentId(uploaded.document_id)
      setDocumentStatus(uploaded.status ?? 'processing')
      setPages(uploaded.pages ?? [])
      setApiAvailable(true)
      setFieldMapping({})
      setValidationId('')
      setValidationItems([])
      setNotice(uploaded.notice)
      setChat([{ role: 'assistant', text: uploaded.status === 'rendered_not_extracted' ? 'I rendered the pages, but OCR and invoice extraction are disabled. Please compare the source preview and enter values manually.' : 'The document could not be rendered. Invoice fields remain blank; correct the file or try another source.' }])
    } catch {
      setDraftId('')
      setDocumentId('')
      setDocumentStatus('')
      setPages([])
      setApiAvailable(false)
      setNotice('The API is unavailable. File is not processed; no data was extracted or sent to an AI provider.')
    }
  }

  async function sendMessage(event: React.FormEvent) {
    event.preventDefault()
    const message = chatText.trim()
    if (!message) return
    setChat((current) => [...current, { role: 'user', text: message }])
    setChatText('')
    setBusy(true)
    if (draftId && apiAvailable) {
      try {
        const response = await fetch(`/api/v1/workspaces/${workspaceId}/drafts/${draftId}/messages`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-Demo-User': 'demo-operator',
            'X-Demo-Workspace': workspaceId,
            'X-Demo-Role': 'operator',
            'X-CSRF-Token': 'local-demo-csrf-token',
          },
          body: JSON.stringify({ message }),
        })
        const responseBody = (await response.json()) as { message?: string; detail?: string }
        setChat((current) => [...current, { role: 'assistant', text: responseBody.message ?? responseBody.detail ?? 'The demo could not produce a response.' }])
      } catch {
        setChat((current) => [...current, { role: 'assistant', text: 'The API is unavailable. No AI inference was performed.' }])
      }
    } else {
      setChat((current) => [...current, { role: 'assistant', text: sampleMode ? 'This demo uses synthetic sample values only. Verify them against a source document before recording.' : 'Upload an invoice successfully to start a draft conversation. No AI inference is performed in this demo.' }])
    }
    setBusy(false)
  }

  async function refreshDocumentStatus() {
    if (!documentId) return
    try {
      const response = await fetch(`/api/v1/workspaces/${workspaceId}/documents/${documentId}`, {
        headers: { 'X-Demo-User': 'demo-operator', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'operator' },
      })
      const body = await response.json() as { status?: string; error?: string; detail?: string; pages?: Array<{ page: number; status: string; error?: string }> }
      if (!response.ok) throw new Error(body.detail ?? 'Document status unavailable')
      setDocumentStatus(body.status ?? 'unknown')
      if (body.pages) setPages(body.pages)
      if (body.error) setNotice(body.error)
    } catch (error) {
      setNotice(error instanceof Error ? error.message : 'Document status unavailable')
    }
  }

  function recordInvoice() {
    if (recorded) return
    if (!sampleMode) {
      setNotice('Recording is blocked in this prototype: extraction, validation, and workbook mapping are not complete.')
      return
    }
    setRecorded(true)
    setInvoice((current) => ({ ...current, status: 'Recorded' }))
    setNotice('Browser demo state only; no spreadsheet row was written. This is not invoice approval or payment.')
    setChat((current) => [...current, { role: 'assistant', text: 'This is only a browser demo state; no invoice row was written to a workbook. It has not been approved or paid.' }])
  }

  function downloadCsv() {
    const rows = [
      ['Vendor', 'Invoice number', 'Invoice date', 'PO number', 'Currency', 'Total', 'Status'],
      [invoice.vendor, invoice.number, invoice.date, sampleMode ? 'Not checked' : '', invoice.currency, sampleMode ? invoice.amount : '', invoice.status],
    ]
    const csv = rows.map((row) => row.map((value) => `"${value.replaceAll('"', '""')}"`).join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'invoice-log-demo.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-lockup">
          <div className="brand-mark"><span /><span /><span /></div>
          <span className="brand-name">ledgerly</span>
        </div>
        <button className="workspace-switcher" type="button" aria-label="Switch workspace">
          <span className="workspace-avatar">A</span>
          <span className="workspace-copy"><strong>Acme & Co.</strong><small>Accounts payable</small></span>
          <ChevronDown size={16} />
        </button>
        <button className="new-invoice" type="button" onClick={loadSample}>
          <Plus size={17} /> <span>Load sample</span> <kbd>⌘ K</kbd>
        </button>
        <nav className="side-nav" aria-label="Main navigation">
          <p className="nav-label">WORKSPACE</p>
          <a className="nav-item active" href="#inbox"><Inbox size={17} /><span>Invoice inbox</span><span className="nav-count">3</span></a>
          <button className="nav-item plain" type="button" onClick={() => void refreshHistory().then((items) => setNotice(`Loaded ${items.length} draft(s) from this demo workspace.`)).catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'History unavailable'))}><FileCheck2 size={17} /><span>History</span></button>
          <button className="nav-item plain" type="button" onClick={() => workbookInputRef.current?.click()}><FileSpreadsheet size={17} /><span>Invoice log</span></button>
          <p className="nav-label nav-label-spaced">YOUR WORK</p>
          <button className="nav-item plain" type="button" onClick={() => setNotice('Showing invoices assigned to you in this demo.')}><span className="nav-dot" /><span>Assigned to me</span></button>
          <button className="nav-item plain" type="button" onClick={() => setNotice('Showing all pending review in this demo.')}><span className="nav-dot muted" /><span>Needs review</span><span className="small-count">2</span></button>
        </nav>
        <div className="sidebar-bottom">
          <div className="privacy-card"><div className="privacy-icon"><ShieldCheck size={16} /></div><div><strong>Local demo mode</strong><p>No AI provider is connected.</p></div><CircleHelp size={14} /></div>
          <button className="profile-button" type="button"><span className="profile-avatar">JM</span><span><strong>Jordan Miller</strong><small>AP Specialist</small></span><MoreHorizontal size={18} /></button>
        </div>
      </aside>

      <main className="main-area" id="inbox">
        <header className="topbar">
          <div className="breadcrumbs"><span>Invoice inbox</span><span className="crumb-separator">/</span><strong>{sampleMode ? 'Synthetic sample' : file ? 'Uploaded file' : 'No invoice selected'}</strong><span className="demo-chip">DEMO</span></div>
          <div className="topbar-actions"><button className="icon-button" aria-label="Search" type="button"><Search size={18} /></button><span className="top-divider" /><button className="help-link" type="button"><CircleHelp size={17} /> Help</button><button className="top-avatar" aria-label="Jordan Miller profile" type="button">JM</button></div>
        </header>
        <div className="content-scroll">
          <div className="page-heading">
            <div><div className="eyebrow"><span className="eyebrow-dot" /> INVOICE REVIEW</div><h1>Let’s get this invoice right.</h1><p>Review the details below before adding it to your invoice log.</p></div>
            <div className={`status-pill ${recorded ? 'status-recorded' : ''}`}><span />{recorded ? (sampleMode ? 'Demo state updated' : 'Not recorded') : sampleMode ? 'Synthetic sample' : 'Needs your review'}</div>
          </div>
          {notice && <div className="notice-banner" role="status"><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss notice" type="button"><X size={15} /></button></div>}
          <div className="review-layout">
            <section className="left-column" aria-label="Invoice review details">
              <div className="card invoice-card">
                <div className="card-heading"><div><div className="section-kicker">INVOICE DETAILS</div><h2>What we found</h2></div><button className="subtle-icon-button" aria-label="More invoice options" type="button"><MoreHorizontal size={19} /></button></div>
                <div className="invoice-identity"><div className={`vendor-logo ${invoice.color}`}>{invoice.initial}</div><div className="vendor-copy"><div className="vendor-name">{invoice.vendor}</div><div className="vendor-subtitle">{invoice.detail}</div></div><button className="source-button" onClick={() => inputRef.current?.click()} type="button"><Paperclip size={15} />{file ? 'Replace file' : 'Add source'}</button></div>
                {!sampleMode && <div className="sample-warning" role="status"><AlertCircle size={15} /><span>No extraction was performed for the uploaded file. Fields are blank; recording stays blocked while required fields are missing.</span></div>}
                <div className="field-grid">
                  <Field label="Vendor name" value={sampleMode ? invoice.vendor : fieldValues.vendor_name} state={sampleMode ? 'Synthetic sample' : 'Not extracted'} warning={!sampleMode} onChange={(value) => updateField('vendor_name', value)} onCommit={() => void commitField('vendor_name')} />
                  <Field label="Invoice number" value={sampleMode ? invoice.number : fieldValues.invoice_number} state={sampleMode ? 'Synthetic sample' : 'Not extracted'} warning={!sampleMode} onChange={(value) => updateField('invoice_number', value)} onCommit={() => void commitField('invoice_number')} />
                  <Field label="Invoice date" value={sampleMode ? invoice.date : fieldValues.invoice_date} state={sampleMode ? 'Synthetic sample' : 'Not extracted'} warning={!sampleMode} onChange={(value) => updateField('invoice_date', value)} onCommit={() => void commitField('invoice_date')} />
                  <Field label="Due date" value={fieldValues.due_date} state="Not extracted" warning={!sampleMode} onChange={(value) => updateField('due_date', value)} onCommit={() => void commitField('due_date')} />
                  <Field label="Purchase order" value={fieldValues.po_number} state="Not extracted" warning={!sampleMode} onChange={(value) => updateField('po_number', value)} onCommit={() => void commitField('po_number')} />
                  <Field label="Currency" value={sampleMode ? invoice.currency : fieldValues.currency} state={sampleMode ? 'Synthetic sample' : 'Not extracted'} warning={!sampleMode} onChange={(value) => updateField('currency', value)} onCommit={() => void commitField('currency')} />
                </div>
                <div className="source-note"><Sparkles size={14} /><span>{sampleMode ? 'Synthetic sample values — not extracted from an invoice.' : 'Uploaded file is preview-only. No invoice values were extracted.'}</span><button aria-label="About extraction" type="button"><CircleHelp size={14} /></button></div>
              </div>

              <div className="card totals-card">
                <div className="card-heading compact"><div><div className="section-kicker">TOTAL CHECK</div><h2>{sampleMode ? 'The numbers add up' : 'Not checked'}</h2></div><span className={`check-badge ${sampleMode ? '' : 'unchecked-badge'}`}>{sampleMode ? <><Check size={14} /> DEMO CHECK</> : <><AlertCircle size={14} /> INCONCLUSIVE</>}</span></div>
                <div className="totals-list"><div><span>Subtotal</span><strong>{sampleMode ? `${invoice.currency} ${subtotal}` : fieldValues.subtotal || '—'}</strong></div><div><span>Tax</span><strong>{sampleMode ? `${invoice.currency} ${tax}` : fieldValues.tax || '—'}</strong></div><div className="total-row"><span>Invoice total</span><strong>{sampleMode ? `${invoice.currency} ${invoice.amount}` : fieldValues.total || '—'}</strong></div></div>
                <div className={sampleMode ? 'success-note' : 'inconclusive-note'}>{sampleMode ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}<span>{sampleMode ? 'Synthetic amounts reconcile; this is not a check of an uploaded invoice.' : 'No total check was run because invoice values were not extracted.'}</span></div>
              </div>

              <div className="card duplicate-card"><div className="duplicate-icon"><AlertCircle size={18} /></div><div className="duplicate-copy"><strong>{sampleMode ? 'Sample PO and duplicate checks' : 'Review validation results'}</strong><p>{sampleMode ? 'Demo values are not checked against external records.' : validationItems.length ? `${validationItems.filter((item) => item.status !== 'pass').length} check(s) need review or are inconclusive.` : 'Invoice values are unavailable; run validation after corrections.'}</p></div><button className="learn-more" type="button" onClick={() => void runValidation().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Validation failed'))} disabled={sampleMode || !workbookId}>Run checks <ArrowRight size={14} /></button></div>
              {!sampleMode && validationItems.length > 0 && <div className="card validation-results" aria-live="polite">{validationItems.map((item) => <div className="validation-result" key={item.check}><strong>{item.check.replaceAll(':', ' · ')}</strong><span className={`validation-status ${item.status}`}>{item.status.replaceAll('_', ' ')}</span><p>{item.reason}</p></div>)}</div>}
            </section>

            <aside className="right-column" aria-label="Source document and assistant">
              <div className="card document-card">
                <div className="document-header"><div><div className="section-kicker">SOURCE DOCUMENT</div><div className="document-title">{file?.name ?? (sampleMode ? 'northstar-invoice-0148.pdf' : 'No source uploaded')} <ChevronDown size={14} /></div></div><button className="download-button" aria-label="Download sample log" onClick={downloadCsv} type="button"><ArrowDownToLine size={16} /></button></div>
                <div className="document-toolbar"><span><FileText size={14} />{file ? `Uploaded · ${documentStatus || 'processing'}` : sampleMode ? 'Synthetic sample' : 'No document'}</span><div>{documentId && <button type="button" aria-label="Refresh document status" onClick={() => void refreshDocumentStatus()}>↻</button>}<button type="button" aria-label="Previous page" disabled>−</button><span>{file ? `${pages.length || '—'} page${pages.length === 1 ? '' : 's'}` : sampleMode ? '1 / 1' : '0 / 0'}</span><button type="button" aria-label="Next page" disabled>+</button></div></div>
                <div className="document-viewer">
                  {file ? documentId && pages.some((page) => page.status === 'processed') ? <img className="safe-page-preview" src={`/api/v1/workspaces/${workspaceId}/documents/${documentId}/pages/1/preview`} alt="Safely rendered invoice page 1" /> : <div className="file-preview-placeholder"><FileText size={28} /><strong>{pages.some((page) => page.status === 'failed') ? 'Page rendering failed' : 'Document is being processed'}</strong><span>{file.name} · {formatSize(file.size)}</span><small>The original is not displayed directly. Invoice fields are still unextracted.</small></div> : sampleMode ? <div className="paper-preview"><div className="paper-brand"><span>NORTHSTAR</span><small>OFFICE CO.</small></div><div className="paper-meta"><div><span>INVOICE</span><strong>NS-2026-0148</strong></div><div><span>DATE</span><strong>November 18, 2026</strong></div></div><div className="paper-rule" /><div className="paper-vendor"><strong>Bill to</strong><span>Acme & Co.</span><span>Accounts Payable</span><span>San Francisco, CA</span></div><div className="paper-table"><div><span>DESCRIPTION</span><span>QTY</span><span>AMOUNT</span></div><div><span>Workspace supplies</span><span>1</span><span>$1,680.00</span></div><div><span>Printer paper, A4</span><span>8</span><span>$320.00</span></div><div><span>Ink cartridges</span><span>4</span><span>$360.00</span></div><div><span>Shipping & handling</span><span>1</span><span>$120.00</span></div></div><div className="paper-total"><span>Subtotal</span><span>$2,296.30</span><span>Sales tax</span><span>$183.70</span><strong>TOTAL DUE</strong><strong>$2,480.00</strong></div><div className="paper-footer">Synthetic sample preview · not your invoice</div></div> : <div className="file-preview-placeholder"><FileText size={28} /><strong>No source document selected</strong><small>Load the synthetic sample or upload a supported file.</small></div>}
                </div>
                <div className="document-foot"><span><LockKeyhole size={13} /> Local development demo</span><button type="button" onClick={() => inputRef.current?.click()}><Upload size={14} /> Upload invoice</button></div>
                {pages.some((page) => page.status === 'failed') && <p className="page-error" role="alert">Some document pages could not be rendered. Review page status before continuing.</p>}
              </div>

                <div className="card workbook-setup-card">
                <div className="card-heading"><div><div className="section-kicker">INVOICE LOG</div><h2>{workbookName || 'Choose a workbook'}</h2><p className="workbook-snapshot-note">Imported workbooks are snapshots; the original is not modified.</p></div><FileSpreadsheet size={18} /></div>
                {!workbookId ? <div className="workbook-actions"><button className="secondary-button" type="button" onClick={() => workbookInputRef.current?.click()}><Upload size={14} /> Upload .xlsx snapshot</button><button className="secondary-button" type="button" onClick={async () => { try { const response = await fetch(`/api/v1/workspaces/${workspaceId}/workbooks?name=Invoice%20Log`, { method: 'POST', headers: { 'X-Demo-User': 'demo-operator', 'X-Demo-Workspace': workspaceId, 'X-Demo-Role': 'operator', 'X-CSRF-Token': 'local-demo-csrf-token' } }); const body = await response.json() as { id?: string; name?: string; version?: number; inspection?: { worksheets?: Array<{ name: string; headers: string[] }> }; detail?: string }; if (!response.ok || !body.id) throw new Error(body.detail ?? 'Workbook creation failed'); setWorkbookId(body.id); setWorkbookName(body.name ?? 'Invoice Log'); setWorkbookVersion(body.version ?? 1); const sheet = body.inspection?.worksheets?.[0]; setWorksheet(sheet?.name ?? ''); setHeaders(sheet?.headers ?? []); setFieldMapping({}); setMappingSaved(false); } catch (error) { setNotice(error instanceof Error ? error.message : 'Workbook creation failed') } }}>Create new log</button></div> : <div className="mapping-setup"><label>Worksheet<select value={worksheet} onChange={(event) => setWorksheet(event.target.value)}>{headers.length > 0 && <option value={worksheet}>{worksheet}</option>}</select></label><p className="mapping-columns">Columns: {headers.join(' · ') || 'No headers found'}</p>{(['vendor_name', 'invoice_number', 'invoice_date', 'po_number', 'currency', 'subtotal', 'tax', 'total'] as const).map((field) => <label className="mapping-row" key={field}><span>{field.replaceAll('_', ' ')}</span><select value={fieldMapping[field] ?? ''} onChange={(event) => setFieldMapping((current) => ({ ...current, [field]: Number(event.target.value) }))}><option value="">Unmapped</option>{headers.map((header, index) => <option key={`${index}-${header}`} value={index + 1}>{header || `Column ${index + 1}`}</option>)}</select></label>)}<button className="secondary-button" type="button" disabled={!worksheet || Object.keys(fieldMapping).length === 0} onClick={() => void saveFieldMapping().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Mapping failed'))}>{mappingSaved ? 'Mapping saved' : 'Save mapping'}</button>{workbookId && <button className="text-button" type="button" onClick={() => { window.open(`/api/v1/workspaces/${workspaceId}/workbooks/${workbookId}/download`, '_blank') }}>Download current snapshot</button>}</div>}
                </div>

              <div className="card assistant-card">
                <div className="assistant-heading"><div className="assistant-mark"><Sparkles size={15} /></div><div><strong>Ledgerly assistant</strong><small>{sampleMode ? 'Static synthetic demo' : 'No model connected'}</small></div><span className="online-dot" /></div>
                <div className="chat-history" aria-live="polite">{chat.map((line, index) => <div className={`chat-line ${line.role}`} key={`${index}-${line.role}`}><span className="chat-avatar">{line.role === 'assistant' ? <Sparkles size={13} /> : 'JM'}</span><p>{line.text}</p></div>)}{busy && <p className="typing">Checking the local demo…</p>}</div>
                <form className="chat-form" onSubmit={sendMessage}><input aria-label="Ask about this invoice" placeholder="Ask about this invoice…" value={chatText} onChange={(event) => setChatText(event.target.value)} /><button aria-label="Send message" disabled={busy || !chatText.trim()} type="submit"><Send size={15} /></button></form>
                <p className="assistant-disclaimer">No AI inference · verify important details yourself.</p>
              </div>
            </aside>
          </div>
          {!sampleMode && <section className="card history-card" aria-label="Invoice history"><div className="card-heading"><div><div className="section-kicker">WORKSPACE HISTORY</div><h2>Recent drafts</h2></div><button className="text-button" type="button" onClick={() => void refreshHistory().catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'History unavailable'))}>Refresh</button></div>{historyItems.length === 0 ? <p className="history-empty">Use the History control to load workspace drafts.</p> : historyItems.map((item) => <div className="history-row" key={item.id}><FileText size={14} /><span>{item.filename}</span><span>{item.reference ?? item.status.replaceAll('_', ' ')}</span></div>)}</section>}
          <footer className="review-footer"><div><LockKeyhole size={14} /><span>{sampleMode ? 'Sample action changes browser demo state only — it does not write a spreadsheet row or approve/pay this invoice.' : 'Reviewer confirmation records in the selected workbook only — it does not approve or pay this invoice.'}</span></div><div className="footer-actions">{!sampleMode && <input className="review-reason" aria-label="Warning acknowledgement reason" placeholder="Reason for warnings (if any)" value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} />}<button className="secondary-button" type="button" onClick={() => setNotice('Draft remains in local session state.')}>Save draft</button><button className="primary-button" type="button" disabled={recorded || (!sampleMode && (!draftId || !workbookId || !mappingSaved || !validationId))} onClick={() => sampleMode ? recordInvoice() : void recordUploadedInvoice()}>{recorded ? <><Check size={16} /> {sampleMode ? 'Demo state updated' : 'Recorded'}</> : <>Confirm &amp; record <ArrowRight size={16} /></>}</button></div></footer>
        </div>
      </main>
      <input ref={inputRef} className="visually-hidden" type="file" accept=".pdf,.jpg,.jpeg,.png,.heic,.heif,application/pdf,image/jpeg,image/png,image/heic,image/heif" onChange={(event) => void handleFiles(event.target.files)} aria-label="Upload invoice file" />
      <input ref={workbookInputRef} className="visually-hidden" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" onChange={(event) => { const selected = event.target.files?.[0]; if (selected) void uploadWorkbookFile(selected).catch((error: unknown) => setNotice(error instanceof Error ? error.message : 'Workbook upload failed')) }} aria-label="Upload invoice log workbook" />
    </div>
  )
}

function Field({ label, value, state, good = false, warning = false, onChange, onCommit }: { label: string; value: string; state: string; good?: boolean; warning?: boolean; onChange: (value: string) => void; onCommit?: () => void }) {
  return <label className="field"><span className="field-label">{label}</span><input value={value} onChange={(event) => onChange(event.target.value)} onBlur={onCommit} onKeyDown={(event) => { if (event.key === 'Enter') { event.currentTarget.blur() } }} /><span className={`field-state ${good ? 'good' : ''} ${warning ? 'warning' : ''}`}>{good ? <Check size={12} /> : warning ? <AlertCircle size={12} /> : <CircleHelp size={12} />}{state}</span></label>
}

function formatSize(bytes: number) {
  return bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default App
