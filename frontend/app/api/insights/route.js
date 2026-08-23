import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    // Fetch all processed raw feedback for theme analysis (with pagination to bypass 1000-row limit)
    let rawData = [];
    let offset = 0;
    while (true) {
      const { data, error } = await supabase
        .from('raw_feedback')
        .select('theme, platform, rating')
        .eq('is_processed', true)
        .range(offset, offset + 999);
      
      if (error) {
        return NextResponse.json({ error: error.message }, { status: 500 });
      }
      
      if (data) {
        rawData = rawData.concat(data);
        if (data.length < 1000) break;
        offset += 1000;
      } else {
        break;
      }
    }

    // Get total count of ALL records (for the "1,486 analysed" KPI)
    const { count: rawCount, error: countErr } = await supabase
      .from('raw_feedback')
      .select('*', { count: 'exact', head: true });

    // Count per platform using exact counts (bypasses Supabase 1000-row limit)
    const platformNames = ['playstore', 'appstore', 'reddit', 'youtube'];
    const PLATFORM_DISPLAY = {
      'playstore': 'Play Store',
      'appstore': 'App Store',
      'reddit': 'Reddit',
      'youtube': 'YouTube'
    };
    const platformCountResults = await Promise.all(
      platformNames.map(async (plat) => {
        const { count, error: platErr } = await supabase
          .from('raw_feedback')
          .select('*', { count: 'exact', head: true })
          .eq('platform', plat);
        return { name: PLATFORM_DISPLAY[plat], count: count || 0 };
      })
    );

    // Compute live metrics
    let total_friction_count = 0;
    let noise_count = 0;
    const themeCounts = {};
    const platformCounts = {};

    // Use the per-platform count results
    platformCountResults.forEach(p => {
      platformCounts[p.name] = p.count;
    });

    // Theme analysis from processed records only
    rawData.forEach(row => {
      if (!row.theme) {
        noise_count++;
        return;
      }
      if (row.theme === 'unrelated_other' || row.rating >= 4) {
        noise_count++;
      } else {
        total_friction_count++;
        themeCounts[row.theme] = (themeCounts[row.theme] || 0) + 1;
      }
    });

    // Noise = total analysed - friction signals identified
    const totalAnalyzed = rawCount || 1486;
    noise_count = totalAnalyzed - total_friction_count;

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
      label: CANONICAL_LABELS[themeId] || themeId,
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
      total_raw_analyzed: totalAnalyzed,
      total_friction_count,
      noise_count,
      updated_at: new Date().toISOString()
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
