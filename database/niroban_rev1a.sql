-- Niroban Rev 1A database schema
-- Run in Supabase SQL Editor.

create table if not exists tender_opportunities (
    id uuid primary key default gen_random_uuid(),

    customer_name text not null default 'Gostaresh Energy',

    title text not null,
    opportunity_type text not null check (
        opportunity_type in ('tender', 'price_inquiry', 'inquiry')
    ),

    company_name text,
    province text,
    region_priority text check (
        region_priority in ('south', 'semnan', 'other')
    ),

    matched_keyword text,
    publish_date date,
    deadline_date date,

    source_url text,
    notes text,

    status text not null default 'new' check (
        status in ('new', 'reviewed', 'relevant', 'not_relevant', 'applied', 'missed')
    ),

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table if not exists tender_search_rules (
    id uuid primary key default gen_random_uuid(),

    customer_name text not null default 'Gostaresh Energy',

    keyword_en text,
    keyword_fa text not null,

    opportunity_type text check (
        opportunity_type in ('tender', 'price_inquiry', 'inquiry', 'all')
    ) default 'all',

    region_priority text check (
        region_priority in ('south', 'semnan', 'other', 'all')
    ) default 'all',

    active boolean default true,

    created_at timestamptz default now()
);

insert into tender_search_rules 
(keyword_en, keyword_fa, opportunity_type, region_priority)
values
('relay', 'رله', 'all', 'all'),
('feeder', 'فیدر', 'all', 'all'),
('substation', 'پست برق', 'all', 'all'),
('capacitor', 'خازن', 'all', 'all'),
('protection relay', 'رله حفاظتی', 'all', 'all'),
('capacitor bank', 'بانک خازنی', 'all', 'all')
on conflict do nothing;
