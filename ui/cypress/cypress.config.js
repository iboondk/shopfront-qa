import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'cypress';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '../..');

export default defineConfig({
  projectRoot: repoRoot,
  e2e: {
    baseUrl: process.env.BASE_URL || 'http://127.0.0.1:3100',
    specPattern: 'ui/cypress/e2e/**/*.cy.js',
    supportFile: false,
    video: false,
    screenshotsFolder: 'test-results/cypress/screenshots',
  },
  retries: {
    runMode: process.env.CI ? 2 : 0,
    openMode: 0,
  },
  reporter: 'junit',
  reporterOptions: {
    mochaFile: `reports/raw/cypress/${process.env.RUN_ID || 'local'}/junit-[hash].xml`,
    testCaseSwitchClassnameAndName: false,
  },
});
