import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL || "https://prfwlmnqsmnkrgkjzbly.supabase.co";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || process.env.SUPABASE_SERVICE_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByZndsbW5xc21ua3Jna2p6Ymx5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NzE1NDExOSwiZXhwIjoyMTAyNzMwMTE5fQ.HTPad1nhgStqtArm1S2J21_StVBK8a_UQ1iGe-Y91mA";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
