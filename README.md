# Commission Engine for ERPNext

A production-ready multi-level sales commission system for ERPNext v16 that automates
the entire CRM-to-commission workflow—from lead conversion to commission payout.

## Features

### Core Commission Flow
- **Automated Commission Generation** — Commission Entries auto-created when Sales Invoice is submitted
- **Separate Entries per Person** — Salesperson and Manager each get their own independent entry with separate payments
- **First vs Recurring Detection** — Different rates for first invoice vs subsequent invoices per customer
- **Credit Note Handling** — Negative reversal entries auto-created when credit notes/returns are submitted
- **Clawback** — If an invoice is cancelled after commission is already paid, a reversal entry + reversal Journal Entry is auto-created
- **Amended Invoice Support** — When an invoice is amended, old commission entries are cancelled and new ones are created

### Commission Settings
- **Global Default Rates** — One-Time and Recurring rates for Salesperson and Manager
- **Individual Rate Overrides** — Override rates per Sales Person via the override table
- **Tiered Commission Rates** — Define rate tiers based on cumulative monthly sales (e.g., 9% up to $10K, 12% above)
- **Minimum Threshold** — Skip commission entries below a specified amount
- **Maximum Cap** — Cap commission amount per entry at a maximum value
- **Multi-Currency** — Tracks invoice currency and exchange rate on each entry

### Approval Workflow
- **Configurable Approval** — Toggle `Enable Approval Workflow` in Commission Settings
- **Status Flow**: `Pending → Approved → Paid` (or `Pending → Paid` when approval is off)
- **Approval Tracking** — Records who approved and when
- **Bulk Approve** — Approve multiple entries from the list view

### Commission Period Locking
- **Commission Period** doctype (`/app/commission-period`)
- Lock a month (e.g., 2026-03-01) to prevent modifications to entries in that period
- Auto-summary stats (total entries, total commission, total paid)
- Reversals and clawbacks bypass the period lock (so they can always be created)

### Accounting Integration
- **Auto Journal Entry** — On payment, a Journal Entry is auto-created (Debit: Expense, Credit: Payable)
- **Reversal JE** — Negative Journal Entries for clawback/return scenarios
- **Commission Accounts** — Auto-created on install (`Commission Expense` + `Commission Payable`)

### CRM Integration
- **Lead → Customer** — When a Customer is created from a Lead, the Lead Owner's Sales Person is auto-tagged
- **Sales Person Resolution** — User → Employee → Sales Person (with fallback name matching)
- **Manager Resolution** — Auto-resolved from the Sales Person tree hierarchy (parent node)
- **Subscription Support** — Subscription-generated invoices auto-inherit the customer's sales_team via `validate` hook

### Role-Based Access Control
- **Sales User** — Can only see their own commission entries
- **Sales Manager** — Can see their own + team members' entries (via NestedSet hierarchy)
- **Accounts User / System Manager** — Can see all entries

### UI Features
- **Rich Dashboard** — Stat cards showing Invoice Amount, Commission, and Status on each entry
- **Role Badges** — 🔵 Salesperson / 🟠 Manager badges in list view and form
- **5 Status Indicators** — ⏳ Pending, ✔️ Approved, ✅ Paid, ❌ Cancelled, ↩️ Reversed
- **Payment Dialog** — Detailed confirmation dialog showing payout breakdown + JE preview
- **Bulk Actions** — Bulk Approve and Bulk Mark as Paid from list view
- **Quick Filters** — One-click filters for status, role, and type
- **Email Notifications** — Auto-sends email to the payee when their commission is paid

### Reports
- **Commission Summary** — Filterable report with chart, grouped by Sales Person
- **Filters**: Date range, Sales Person, Role, Commission Type, Status, Company
- **Summary Cards**: Salesperson total, Manager total, Grand Total, Pending, Approved
- **Export**: Standard ERPNext CSV/Excel export

## Installation

```bash
cd /path/to/frappe-bench
bench get-app https://github.com/codepromaxtech/erpnext_crm_commission_engine.git
bench --site your-site install-app commission_engine
bench --site your-site migrate
bench build --app commission_engine
sudo supervisorctl restart all
```

## Configuration

1. Navigate to **Commission Settings** (`/app/commission-settings`)
2. Set **One-Time** and **Recurring** commission rates for Salesperson and Manager
3. Configure **Commission Expense Account** and **Commission Payable Account**
4. Optionally enable:
   - **Approval Workflow** — require approval before payment
   - **Tiered Commission** — rate tiers based on cumulative sales
   - **Minimum Threshold** — skip tiny commissions
   - **Maximum Cap** — cap large commissions

## Prerequisites

For the commission engine to work correctly:

1. **Sales Person Tree** — At least one Sales Person must exist in the Sales Person tree
2. **Employee Link** — Each Sales Person should be linked to an Employee
3. **User Link** — Each Employee should have a `user_id` (ERPNext user)
4. **Customer Sales Team** — Each Customer should have a Sales Person in the `sales_team` child table

## Doctypes

| Doctype | Type | Description |
|---------|------|-------------|
| Commission Settings | Single | Global configuration (rates, accounts, thresholds) |
| Commission Entry | Document | Individual commission record per person per invoice |
| Commission Rate Override | Child Table | Per-person rate overrides in Commission Settings |
| Commission Tier | Child Table | Tiered rate definitions in Commission Settings |
| Commission Period | Document | Monthly period locking (Open/Locked) |

## API

| Endpoint | Description |
|----------|-------------|
| `commission_engine.api.bulk_mark_as_paid` | Bulk pay multiple entries |
| `commission_engine.api.bulk_approve` | Bulk approve multiple entries |
| `commission_engine.api.get_commission_dashboard` | Dashboard data for workspace |
| `commission_engine.customer_hooks.resolve_sales_person_from_lead` | Resolve Lead Owner to Sales Person |

## License

MIT
