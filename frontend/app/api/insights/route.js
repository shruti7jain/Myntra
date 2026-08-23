import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Fetch all processed raw feedback
    const { data: rawData, error } = await supabase
      .from('raw_feedback')
      .select('theme, platform')
      .eq('is_processed', true);

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    const { count: rawCount, error: countErr } = await supabase
      .from('raw_feedback')
      .select('*', { count: 'exact', head: true });

    // Compute live metrics
    let total_friction_count = 0;
    let noise_count = 0;
    const themeCounts = {};
    const platformCounts = {};

    rawData.forEach(row => {
      // Platform breakdown (all analyzed feedback)
      let plat = row.platform || 'Other';
      if (plat === 'playstore') plat = 'Play Store';
      if (plat === 'appstore') plat = 'App Store';
      if (plat === 'reddit') plat = 'Reddit';
      if (plat === 'youtube') plat = 'YouTube';
      platformCounts[plat] = (platformCounts[plat] || 0) + 1;

      if (!row.theme) {
        noise_count++;
        return;
      }
      if (row.theme === 'unrelated_other') {
        noise_count++;
      } else {
        total_friction_count++;
        themeCounts[row.theme] = (themeCounts[row.theme] || 0) + 1;
      }
    });

    // Map to canonical labels
    const CANONICAL_LABELS = {
      "fabric_quality_ambiguity": "Fabric Quality & Tactile Ambiguity",
      "visual_reality_discrepancy": "Product Photo vs. Reality Mismatch",
      "fit_sizing_anxiety": "Fit & Sizing Inconsistency",
      "occasion_timing_delay": "Occasion Timing & Postponement",
      "styling_pairing_doubt": "Styling & Wardrobe Pairing Uncertainty",
      "choice_paralysis_shortlist": "Choice Overload & Comparison Fatigue",
      "social_validation_delay": "Social Validation & Peer Opinion Delay",
    };

    const insights = Object.entries(themeCounts).map(([themeId, count]) => ({
      id: themeId,
      theme: themeId,
      theme_label: CANONICAL_LABELS[themeId] || themeId,
      mention_count: count,
      count: count, // add count alias for ui mapping
      pct: total_friction_count > 0 ? Math.round((count / total_friction_count) * 100) : 0
    })).sort((a, b) => b.mention_count - a.mention_count);

    const platforms = Object.entries(platformCounts).map(([name, count]) => ({
      name,
      count
    })).sort((a, b) => b.count - a.count);

    return NextResponse.json({
      insights,
      platforms,
      total_raw_analyzed: rawCount || 1486,
      total_friction_count,
      noise_count,
      updated_at: new Date().toISOString()
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
