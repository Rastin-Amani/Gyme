/// <reference path="../pb_data/types.d.ts" />
//
// Billing schema for Gyme — active-trainee seats + PayRam credit packs.
//
// Targets PocketBase >= 0.23 (the `fields` collection API and the
// `_superusers` auth collection). If you run an older PocketBase, create these
// collections through the admin UI using the exact field list in
// docs/billing.md (Part "PocketBase schema"); the app does not care which
// mechanism created them.
//
// SECURITY: every billing collection is admin-only. All four rules are `null`,
// which means "superusers only" — the browser can never read or write invoices,
// events, credits, or products directly. The FastAPI server uses the superuser
// client (PB_ADMIN_EMAIL / PB_ADMIN_PASSWORD) for every billing operation.
//
migrate(
    (app) => {
        const tenantsId = app.findCollectionByNameOrId("tenants").id;

        // --- billing_products: purchasable seat packs (trusted prices) -------
        const products = new Collection({
            type: "base",
            name: "billing_products",
            listRule: null,
            viewRule: null,
            createRule: null,
            updateRule: null,
            deleteRule: null,
            fields: [
                { name: "key", type: "text", required: true, min: 1, max: 64 },
                { name: "name", type: "text", required: true, max: 120 },
                { name: "description", type: "text", max: 500 },
                { name: "active", type: "bool" },
                { name: "price_usd", type: "number", required: true, min: 0 },
                { name: "seats", type: "number", required: true, min: 1 },
                { name: "currency", type: "text", max: 8 },
                { name: "sort_order", type: "number" },
                { name: "created", type: "autodate", onCreate: true, onUpdate: false },
                { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
            ],
            indexes: [
                "CREATE UNIQUE INDEX `idx_billing_products_key` ON `billing_products` (`key`)",
            ],
        });
        app.save(products);

        // --- billing_invoices: internal invoices + provider references -------
        const invoices = new Collection({
            type: "base",
            name: "billing_invoices",
            listRule: null,
            viewRule: null,
            createRule: null,
            updateRule: null,
            deleteRule: null,
            fields: [
                {
                    name: "tenant",
                    type: "relation",
                    required: true,
                    maxSelect: 1,
                    collectionId: tenantsId,
                    cascadeDelete: false,
                },
                { name: "invoice_ref", type: "text", required: true, min: 1, max: 64 },
                { name: "user", type: "text", max: 32 },
                { name: "product_key", type: "text", max: 64 },
                { name: "product_name", type: "text", max: 120 },
                { name: "seats", type: "number", min: 0 },
                { name: "amount_usd", type: "number", min: 0 },
                { name: "currency", type: "text", max: 8 },
                { name: "status", type: "text", max: 24 },
                { name: "provider", type: "text", max: 24 },
                { name: "provider_ref", type: "text", max: 128 },
                { name: "checkout_url", type: "url", max: 500 },
                { name: "provider_status", type: "text", max: 32 },
                { name: "paid_amount_usd", type: "number", min: 0 },
                { name: "error", type: "text", max: 500 },
                { name: "fulfilled_at", type: "text", max: 32 },
                { name: "created", type: "autodate", onCreate: true, onUpdate: false },
                { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
            ],
            indexes: [
                "CREATE UNIQUE INDEX `idx_billing_invoices_ref` ON `billing_invoices` (`invoice_ref`)",
                "CREATE INDEX `idx_billing_invoices_tenant` ON `billing_invoices` (`tenant`)",
                "CREATE INDEX `idx_billing_invoices_provider_ref` ON `billing_invoices` (`provider_ref`)",
                "CREATE INDEX `idx_billing_invoices_status` ON `billing_invoices` (`status`)",
            ],
        });
        app.save(invoices);

        // --- billing_events: webhook idempotency ledger ----------------------
        const events = new Collection({
            type: "base",
            name: "billing_events",
            listRule: null,
            viewRule: null,
            createRule: null,
            updateRule: null,
            deleteRule: null,
            fields: [
                { name: "provider", type: "text", max: 24 },
                { name: "dedup_key", type: "text", required: true, min: 1, max: 200 },
                { name: "invoice_ref", type: "text", max: 64 },
                { name: "reference_id", type: "text", max: 128 },
                { name: "status", type: "text", max: 32 },
                { name: "processed", type: "bool" },
                { name: "error", type: "text", max: 500 },
                { name: "created", type: "autodate", onCreate: true, onUpdate: false },
                { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
            ],
            indexes: [
                "CREATE UNIQUE INDEX `idx_billing_events_dedup` ON `billing_events` (`dedup_key`)",
                "CREATE INDEX `idx_billing_events_reference` ON `billing_events` (`reference_id`)",
            ],
        });
        app.save(events);

        // --- credit_transactions: append-only seat-credit ledger -------------
        const ledger = new Collection({
            type: "base",
            name: "credit_transactions",
            listRule: null,
            viewRule: null,
            createRule: null,
            updateRule: null,
            deleteRule: null,
            fields: [
                {
                    name: "tenant",
                    type: "relation",
                    required: true,
                    maxSelect: 1,
                    collectionId: tenantsId,
                    cascadeDelete: false,
                },
                { name: "invoice_ref", type: "text", max: 64 },
                { name: "delta", type: "number", required: true },
                { name: "type", type: "text", max: 24 },
                { name: "status", type: "text", max: 16 },
                { name: "idempotency_key", type: "text", required: true, min: 1, max: 200 },
                { name: "note", type: "text", max: 200 },
                { name: "created", type: "autodate", onCreate: true, onUpdate: false },
                { name: "updated", type: "autodate", onCreate: true, onUpdate: true },
            ],
            indexes: [
                "CREATE UNIQUE INDEX `idx_credit_tx_idem` ON `credit_transactions` (`idempotency_key`)",
                "CREATE INDEX `idx_credit_tx_tenant` ON `credit_transactions` (`tenant`)",
                "CREATE INDEX `idx_credit_tx_invoice` ON `credit_transactions` (`invoice_ref`)",
            ],
        });
        app.save(ledger);

        // --- Seed two editable default seat packs (change in the admin UI) ---
        const defaults = [
            {
                key: "seats-10",
                name: "10 seats",
                description: "Add 10 active trainee seats to your gym.",
                seats: 10,
                price_usd: 29,
                sort_order: 1,
            },
            {
                key: "seats-30",
                name: "30 seats",
                description: "Add 30 active trainee seats to your gym.",
                seats: 30,
                price_usd: 69,
                sort_order: 2,
            },
        ];
        for (const d of defaults) {
            const record = new Record(products);
            record.set("key", d.key);
            record.set("name", d.name);
            record.set("description", d.description);
            record.set("active", true);
            record.set("seats", d.seats);
            record.set("price_usd", d.price_usd);
            record.set("currency", "USD");
            record.set("sort_order", d.sort_order);
            app.save(record);
        }
    },
    (app) => {
        // Rollback: drop the billing collections (does not touch tenants/users).
        for (const name of [
            "credit_transactions",
            "billing_events",
            "billing_invoices",
            "billing_products",
        ]) {
            try {
                app.delete(app.findCollectionByNameOrId(name));
            } catch (e) {
                // already gone
            }
        }
    },
);
