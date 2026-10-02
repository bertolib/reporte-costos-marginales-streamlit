create table if not exists public.cmg_15min_report_data (
    fecha date not null,
    hora smallint not null check (hora between 0 and 23),
    minutos smallint not null check (minutos in (0, 15, 30, 45)),
    "timestamp" timestamp without time zone not null,
    cmg_mej_110_usd_mwh numeric,
    cmg_chaca_110_clp_kwh numeric,
    cmg_chacaya_110_usd_mwh numeric,
    alto_jahuel_220_usd_mwh numeric,
    charrua_220_usd_mwh numeric,
    source_file text not null,
    version text,
    loaded_at timestamp with time zone not null default now(),
    primary key (fecha, hora, minutos)
);

create index if not exists idx_cmg_15min_report_data_timestamp
    on public.cmg_15min_report_data ("timestamp");

create or replace view public.cmg_hourly_report_data as
select
    fecha,
    hora + 1 as hora,
    avg(cmg_mej_110_usd_mwh) as cmg_mej_110_usd_mwh,
    avg(cmg_chaca_110_clp_kwh) as cmg_chaca_110_clp_kwh,
    avg(cmg_chacaya_110_usd_mwh) as cmg_chacaya_110_usd_mwh,
    avg(alto_jahuel_220_usd_mwh) as alto_jahuel_220_usd_mwh,
    avg(charrua_220_usd_mwh) as charrua_220_usd_mwh
from public.cmg_15min_report_data
group by
    fecha,
    hora + 1;
