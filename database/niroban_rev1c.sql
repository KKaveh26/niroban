-- Niroban Rev 1C: Daily tender monitoring workflow
-- Run this after Rev 1A tables are already created.

create table if not exists tender_scan_logs (
    id uuid primary key default gen_random_uuid(),

    customer_name text not null default 'Gostaresh Energy',

    scan_date date not null default current_date,

    source_name text not null default 'Private Tender Website',
    source_url text,

    scan_mode text not null default 'manual' check (
        scan_mode in ('manual', 'semi_automatic', 'automatic')
    ),

    status text not null default 'pending' check (
        status in ('pending', 'success', 'failed', 'login_required', 'captcha_required')
    ),

    checked_opportunity_types text[] default array['tender', 'price_inquiry', 'inquiry'],
    checked_keywords text[] default array['relay', 'feeder', 'substation', 'capacitor'],
    checked_regions text[] default array['south', 'semnan', 'all_iran'],

    total_found integer default 0,
    new_opportunities integer default 0,
    relevant_opportunities integer default 0,

    notes text,

    started_at timestamptz default now(),
    finished_at timestamptz,
    created_at timestamptz default now()
);

create index if not exists idx_tender_scan_logs_scan_date
on tender_scan_logs (scan_date desc);

create index if not exists idx_tender_scan_logs_status
on tender_scan_logs (status);
