import { test as base, expect, type Page } from '@playwright/test';
import { randomUUID } from 'node:crypto';

/** Credenciales por rol desde el entorno: QA_USER_<ROL>_EMAIL / _PASSWORD. Nunca valores en el código. */
export function credenciales(rol: string) {
	const k = rol.toUpperCase();
	const email = process.env[`QA_USER_${k}_EMAIL`];
	const password = process.env[`QA_USER_${k}_PASSWORD`];
	if (!email || !password) throw new Error(`Faltan QA_USER_${k}_EMAIL / QA_USER_${k}_PASSWORD`);
	return { email, password };
}

type Fixtures = {
	/** Identificador corto para marcar datos sintéticos creados por este test. */
	runId: string;
	/** Registrar acciones de limpieza; se ejecutan siempre al final del test, en orden inverso. */
	limpieza: (accion: () => Promise<void>) => void;
	/** Login por UI con un rol. Ajustar labels/botón a la app real. */
	ingresarComo: (rol: string) => Promise<Page>;
};

export const test = base.extend<Fixtures>({
	runId: async ({}, use) => use(`qa${randomUUID().slice(0, 8)}`),
	limpieza: async ({}, use) => {
		const acciones: Array<() => Promise<void>> = [];
		await use((a) => acciones.push(a));
		for (const a of acciones.reverse()) await a();
	},
	ingresarComo: async ({ page }, use) => {
		await use(async (rol) => {
			const { email, password } = credenciales(rol);
			await page.goto(process.env.QA_LOGIN_PATH ?? '/');
			await page.getByLabel(/email|correo/i).fill(email);
			await page.getByLabel(/contraseña/i).fill(password);
			await page.getByRole('button', { name: /ingresar|iniciar sesión|entrar/i }).click();
			return page;
		});
	}
});

export { expect };
