import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, devices } from '@playwright/test';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '../..');
const baseURL = process.env.BASE_URL || 'http://127.0.0.1:3100';

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL,
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
      },
    },
  ],
  webServer: process.env.BASE_URL
    ? undefined
    : {
        command: 'node stub/server.mjs',
        url: baseURL + '/health',
        reuseExistingServer: true,
        cwd: repoRoot,
        env: { PORT: '3100' },
      },
  reporter: [
    ['list'],
    [
      'junit',
      {
        outputFile: `${repoRoot}/reports/raw/playwright/${process.env.RUN_ID || 'local'}/junit.xml`,
      },
    ],
  ],
  outputDir: repoRoot + '/test-results/playwright',
  snapshotPathTemplate: '{testDir}/../__screenshots__/{platform}/{arg}{ext}',
  expect: {
    toHaveScreenshot: {
      maxDiffPixelRatio: 0.01,
      animations: 'disabled',
    },
  },
});
