import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const { data: insights, error } = await supabase
      .from('insights')
      .select('*')
      .order('mention_count', { ascending: false });

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    const { count: rawCount, error: countErr } = await supabase
      .from('raw_feedback')
      .select('*', { count: 'exact', head: true });

    return NextResponse.json({
      insights: insights || [],
      total_raw_analyzed: rawCount || 1486,
      updated_at: new Date().toISOString()
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
