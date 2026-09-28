/**
 * Expected backend contract for the Svelte frontend.
 * All paths here are relative to the same-origin /api/v1 proxy. Responses are
 * JSON objects (or {items, total, page, per_page}) and errors use {detail}.
 * Auth endpoints set/clear an HttpOnly `pb_auth` cookie; tokens never enter UI JS.
 *
	 * GET auth/me, dashboard?timeframe=all|month|week, trainees, trainees/:id,
	 * coaches, coaches/:id, plans, plans/:id, items?plan_id=:id&plan_type=:type,
	 * items/:id?plan_type=training|diet|steroid,
 * progress-logs/:id, user/dashboard, user/plans, user/plans/:id.
 * POST auth/login, auth/logout, auth/change-password, trainees, coaches, plans,
 * templates/:id/apply, items, progress-logs, user/plans/:id/done.
 * PATCH auth/profile, trainees/:id, coaches/:id, plans/:id, items/:id,
 * progress-logs/:id. DELETE trainees/:id, coaches/:id, plans/:id, items/:id.
 *
	 * Records keep PocketBase's snake_case fields and may include expanded user,
	 * coach or trainee relations under `expand`. Trainee details include plans and
	 * progress_logs; plan details include items; user/dashboard groups plans by type.
	 * Lists can be bare arrays or paginated.
 */
export type Role = 'owner' | 'coach' | 'trainee';
export type Locale = 'en' | 'es' | 'tr' | 'hy';
export type PlanType = 'training' | 'diet' | 'steroid';

export interface User {
	id: string;
	role: Role;
	first_name?: string;
	last_name?: string;
	email?: string;
	phone?: string;
	[key: string]: unknown;
}

export interface RecordData {
	id: string;
	name?: string;
	title?: string;
	type?: PlanType;
	status?: string;
	items?: RecordData[] | { items?: RecordData[] };
	expand?: Record<string, any>;
	[key: string]: any;
}

export interface Page<T> {
	items: T[];
	total?: number;
	page?: number;
	per_page?: number;
}

export interface LoginInput { identity: string; password: string }
export interface ChangePasswordInput { old_password: string; new_password: string; confirm_password: string }
export interface ProfileInput { first_name: string; last_name: string; phone?: string }
export interface TraineeInput extends ProfileInput {
	email: string;
	birthdate?: string;
	gender?: 'male' | 'female';
	blood_type?: string;
	training_history?: string;
	steroid_history?: string;
	supplement_history?: string;
	limitations?: string;
	notes?: string;
}
export interface CoachInput extends ProfileInput { email: string }
export interface PlanInput {
	type: PlanType;
	trainee?: string;
	coach?: string;
	start_date?: string;
	end_date?: string;
	days_per_week?: number;
	status?: 'active' | 'inactive';
	notes?: string;
	is_template?: boolean;
	template_name?: string;
}
export interface PlanItemInput {
	plan: string;
	plan_type: PlanType;
	item_name?: string;
	meal_name?: string;
	food_name?: string;
	name?: string;
	seq?: number;
	order?: number;
	sets?: number;
	reps?: number;
	weight?: number;
	rest_seconds?: number;
	quantity?: string;
	dosage?: string;
	frequency?: string;
	category?: string;
	notes?: string;
}
export interface ProgressLogInput {
	trainee: string;
	height: number;
	weight: number;
	chest?: number;
	waist?: number;
	hip?: number;
	arms?: number;
	bmi?: number;
	bfp?: number;
	bmr?: number;
	tdee?: number;
	lbm?: number;
	whr?: number;
	notes?: string;
	progress_photos?: File[];
}

export interface ApiEnvelope<T> {
	data?: T;
	items?: T extends unknown[] ? T[number][] : never;
	[key: string]: unknown;
}

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string,
		public payload?: unknown
	) {
		super(message);
		this.name = 'ApiError';
	}
}

export function unwrap<T>(value: any): T {
	if (value && typeof value === 'object' && 'data' in value) return value.data as T;
	return value as T;
}

export function records(value: any): RecordData[] {
	const result = unwrap<any>(value);
	if (Array.isArray(result)) return stripSecrets(result);
	if (Array.isArray(result?.items)) return stripSecrets(result.items);
	if (Array.isArray(result?.records)) return stripSecrets(result.records);
	return [];
}

export function record(value: any): RecordData | null {
	const result = unwrap<any>(value);
	if (result && typeof result === 'object' && !Array.isArray(result)) {
		return stripSecrets(result.record ?? result.item ?? result) as RecordData;
	}
	return null;
}

export function safeUser(value: any): User | null {
	const source = unwrap<any>(value);
	const user = record(source?.user ?? source);
	if (!user || !user.id || !user.role) return null;
	return Object.fromEntries(['id', 'role', 'first_name', 'last_name', 'email', 'phone'].filter((key) => user[key] !== undefined).map((key) => [key, user[key]])) as User;
}

export function stripSecrets<T>(value: T): T {
	if (Array.isArray(value)) return value.map(stripSecrets) as T;
	if (!value || typeof value !== 'object') return value;
	return Object.fromEntries(Object.entries(value).filter(([key]) => !/(?:token|password|secret|auth_store)/i.test(key)).map(([key, item]) => [key, stripSecrets(item)])) as T;
}

export async function api<T = unknown>(
	fetcher: typeof fetch,
	path: string,
	init: RequestInit = {}
): Promise<{ data: T; response: Response }> {
	const headers = new Headers(init.headers);
	if (init.body && !(init.body instanceof FormData) && !headers.has('content-type')) {
		headers.set('content-type', 'application/json');
	}
	const response = await fetcher(`/api/v1/${path.replace(/^\//, '')}`, {
		...init,
		headers,
		credentials: 'same-origin'
	});
	const text = response.status === 204 ? '' : await response.text();
	let data: any = undefined;
	if (text) {
		try {
			data = JSON.parse(text);
		} catch {
			data = text;
		}
	}
	if (!response.ok) {
		const message = typeof data === 'string' ? data : data?.detail ?? data?.message ?? `Request failed (${response.status})`;
		throw new ApiError(response.status, String(message), data);
	}
	return { data: unwrap<T>(data), response };
}

export function formObject(form: FormData): Record<string, FormDataEntryValue | string> {
	const result: Record<string, FormDataEntryValue | string> = {};
	for (const [key, value] of form.entries()) {
		if (value instanceof File && !value.name) continue;
		if (key in result) {
			const previous = result[key];
			result[key] = Array.isArray(previous) ? [...previous, value] : [previous as FormDataEntryValue, value] as any;
		} else result[key] = value;
	}
	return result;
}

export function fullName(value: any): string {
	const entity = value?.expand?.user ?? value?.expand?.coach ?? value?.user ?? value;
	return [entity?.first_name, entity?.last_name].filter(Boolean).join(' ') || entity?.name || entity?.email || '—';
}
