-- Create a table to store OTPs temporarily
create table public.phonenum_otps (
  phone_number text not null primary key,
  otp text not null,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Enable Row Level Security (RLS)
alter table public.phonenum_otps enable row level security;

-- Create a policy that allows the service_role (backend) to do everything
create policy "Enable all access for service_role"
on public.phonenum_otps
for all
to service_role
using (true)
with check (true);

-- Optional: Create a policy to deny public access (default is deny anyway if not enabled)
-- But ensuring no anon access is good practice
create policy "Deny public access"
on public.phonenum_otps
for all
to anon, authenticated
using (false);
