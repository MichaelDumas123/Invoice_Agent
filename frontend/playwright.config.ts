import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:5174', trace: 'retain-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: 'cd ../backend && uv run uvicorn invoice_assistant.api.main:app --app-dir src --host 127.0.0.1 --port 8001',
      url: 'http://127.0.0.1:8001/health',
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: 'VITE_API_PROXY_TARGET=http://127.0.0.1:8001 npm run dev',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: false,
    },
  ],
})
