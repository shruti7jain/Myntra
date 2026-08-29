import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

const normalizeText = (value) => {
  if (typeof value !== 'string') return value;

  return value
    .replace(/\u00a0/g, ' ')
    .replace(/[\u00C2\u00E2]\u2019/g, "'")
    .replace(/[\u00C2\u00E2]\u2018/g, "'")
    .replace(/[\u00C2\u00E2]\u201C/g, '"')
    .replace(/[\u00C2\u00E2]\u201D/g, '"')
    .replace(/[\u00C2\u00E2]\u2013/g, '-')
    .replace(/[\u00C2\u00E2]\u2014/g, '-')
    .replace(/[\u00C2\u00E2]/g, '')
    .replace(/\u00C3/g, 'A');
};

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = Math.min(Math.max(parseInt(searchParams.get('limit') || '2000', 10) || 2000, 1), 2000);
    const page = parseInt(searchParams.get('page') || '1', 10);
    const offset = (page - 1) * limit;

    const { data: verbatims, error } = await supabase
      .from('raw_feedback')
      .select('text, platform, theme')
      .eq('is_processed', true)
      .not('theme', 'is', null)
      .neq('theme', 'unrelated_other')
      .order('id', { ascending: false })
      .range(offset, offset + limit - 1);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    // Map themes to canonical labels
    const CANONICAL_LABELS = {
      "fabric_quality_ambiguity": "Fabric Quality",
      "visual_reality_discrepancy": "Photo Mismatch",
      "fit_sizing_anxiety": "Fit & Sizing",
      "occasion_timing_delay": "Occasion Timing",
      "styling_pairing_doubt": "Styling Doubt",
      "choice_paralysis_shortlist": "Choice Paralysis",
      "social_validation_delay": "Social Validation",
    };

    const formattedVerbatims = verbatims.map(v => {
      let plat = v.platform;
      if (plat === 'playstore') plat = 'Play Store';
      if (plat === 'appstore') plat = 'App Store';
      if (plat === 'reddit') plat = 'Reddit';
      if (plat === 'youtube') plat = 'YouTube';

      return {
        text: normalizeText(v.text),
        platform: normalizeText(plat),
        theme: normalizeText(CANONICAL_LABELS[v.theme] || v.theme)
      };
    });

    return NextResponse.json({
      verbatims: formattedVerbatims,
      page,
      limit
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
