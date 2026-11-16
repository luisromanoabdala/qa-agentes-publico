import { test, expect } from './fixtures';

// Smoke de SOLO LECTURA: no crea, modifica ni elimina datos. Apto para producción si la campaña lo autoriza.
test.describe('smoke del ambiente @smoke @solo-lectura-prod', () => {
	test('la API responde salud', async ({ request }) => {
		const api = process.env.QA_API_URL;
		test.skip(!api, 'QA_API_URL no definida');
		const r = await request.get(`${api}/health`);
		expect(r.status(), 'GET /health').toBe(200);
	});

	test('login con rol y acceso a la pantalla principal', async ({ ingresarComo }) => {
		const rol = process.env.QA_SMOKE_ROL ?? 'OWNER';
		const page = await ingresarComo(rol);
		// Ajustar al landmark real de la app tras el login (sin depender de textos de datos).
		await expect(page.getByRole('navigation').first()).toBeVisible();
		await expect(page).not.toHaveURL(/ingresar|login/);
	});
});
