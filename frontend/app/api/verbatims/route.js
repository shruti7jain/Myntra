import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50', 10);
    const page = parseInt(searchParams.get('page') || '1', 10);
    const offset = (page - 1) * limit;

    const { data: verbatims, error } = await supabase
      .from('raw_feedback')
      .select('text, platform, theme')
      .eq('is_processed', true)
      .neq('theme', 'unrelated_other')
      .not('theme', 'is', null)
      .or('rating.lte.3,rating.is.null')
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
        text: v.text,
        platform: plat,
        theme: CANONICAL_LABELS[v.theme] || v.theme
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
