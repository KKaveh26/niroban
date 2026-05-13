-- Niroban Rev 1D: optional source configuration table
-- Run this after Rev 1A and Rev 1C tables are already created.

create table if not exists tender_sources (
    id uuid primary key default gen_random_uuid(),
    customer_name text not null default 'Gostaresh Energy',
    name text not null default 'Setad Iran',
    source_url text not null default 'https://setadiran.ir/setad/cms',
    login_required boolean not null default true,
    scan_mode text not null default 'semi_automatic' check (
        scan_mode in ('manual', 'semi_automatic', 'automatic')
    ),
    active boolean not null default true,
    notes text,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

insert into tender_sources (customer_name, name, source_url, login_required, scan_mode, active, notes)
select
    'Gostaresh Energy',
    'Setad Iran',
    'https://setadiran.ir/setad/cms',
    true,
    'semi_automatic',
    true,
    'Private/login-based tender and inquiry website. Captcha or OTP must be completed manually by an authorized user.'
where not exists (
    select 1 from tender_sources
    where customer_name = 'Gostaresh Energy'
      and source_url = 'https://setadiran.ir/setad/cms'
);
