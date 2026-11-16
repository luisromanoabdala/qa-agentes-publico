import { defineConfig, devices } from '@playwright/test';

// Suite contra un AMBIENTE DESPLEGADO (no levanta servidor). Variables en .env.qa (ver README).
const baseURL = process.env.QA_BASE_URL;
if (!baseURL) throw new Error('Falta QA_BASE_URL (cargar .env.qa)');

export default defineConfig({
	testDir: './e2e-ambiente',
	fullyParallel: true,
	forbidOnly: !!process.env.CI,
	// Reintento solo en CI: Playwright marca el test como "flaky" en el reporte y conserva la traza del intento fallido.
	retries: process.env.CI ? 1 : 0,
	reporter: [
		['list'],
		['html', { outputFolder: 'reports/ambiente', open: 'never' }],
		['junit', { outputFile: 'reports/ambiente/junit.xml' }],
		['json', { outputFile: 'reports/ambiente/results.json' }]
	],
	use: {
		baseURL,
		locale: 'es-AR',
		timezoneId: 'America/Argentina/Tucuman',
		trace: 'retain-on-failure',
		screenshot: 'only-on-failure',
		video: 'retain-on-failure'
	},
	projects: [
		{ name: 'smoke', grep: /@smoke/, use: { ...devices['Desktop Chrome'] } },
		{ name: 'regresion', grepInvert: /@solo-lectura-prod/, use: { ...devices['Desktop Chrome'] } },
		{ name: 'celular', grep: /@celular/, use: { ...devices['Pixel 7'] } }
	]
});
