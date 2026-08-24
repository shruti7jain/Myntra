import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    // 1. Fetch aggregated themes, percentages, and intent breakdowns from insights table
    const { data: insightsData, error: insightsErr } = await supabase
      .from('insights')
      .select('*');

    if (insightsErr) {
      return NextResponse.json({ error: insightsErr.message }, { status: 500 });
    }

    // 2. Exact platform counts
    const platformNames = ['playstore', 'appstore', 'reddit', 'youtube'];
    const PLATFORM_DISPLAY = {
      'playstore': 'Play Store',
      'appstore': 'App Store',
      'reddit': 'Reddit',
      'youtube': 'YouTube'
    };

    const platformCountResults = await Promise.all(
      platformNames.map(async (plat) => {
        const { count } = await supabase
          .from('raw_feedback')
          .select('*', { count: 'exact', head: true })
          .eq('platform', plat);
        return { name: PLATFORM_DISPLAY[plat], count: count || 0 };
      })
    );

    const platforms = platformCountResults.sort((a, b) => b.count - a.count);
    const totalRawAnalyzed = platformCountResults.reduce((sum, p) => sum + p.count, 0);

    // 3. Compute friction vs noise from canonical insights data
    const CANONICAL_LABELS = {
      "fabric_quality_ambiguity": "Fabric Quality & Tactile Ambiguity",
      "visual_reality_discrepancy": "Product Photo vs. Reality Mismatch",
      "fit_sizing_anxiety": "Fit & Sizing Inconsistency",
      "occasion_timing_delay": "Occasion Timing & Postponement",
      "styling_pairing_doubt": "Styling & Wardrobe Pairing Uncertainty",
      "choice_paralysis_shortlist": "Choice Overload & Comparison Fatigue",
      "social_validation_delay": "Social Validation & Peer Opinion Delay",
    };

    let totalFrictionCount = 0;
    let noiseCount = 0;
    const aggregatedIntents = {
      high_intent_blocked: 0,
      occasion_waiting: 0,
      price_monitoring: 0,
      bookmarking_inspiration: 0,
      comparison_shortlisting: 0,
    };

    const insights = [];

    (insightsData || []).forEach((row) => {
      const themeKey = row.theme;
      if (themeKey === 'unrelated_other') {
        noiseCount = row.mention_count || 0;
      } else if (CANONICAL_LABELS[themeKey]) {
        totalFrictionCount += row.mention_count || 0;
        insights.push({
          id: themeKey,
          theme: themeKey,
          theme_label: row.theme_label || CANONICAL_LABELS[themeKey],
          label: row.theme_label || CANONICAL_LABELS[themeKey],
          mention_count: row.mention_count || 0,
          count: row.mention_count || 0,
          pct: row.pct_of_total ? Math.round(row.pct_of_total) : 0,
          pct_exact: row.pct_of_total || 0,
        });
      }

      // Aggregate intent breakdown
      const ib = row.intent_breakdown || {};
      Object.keys(aggregatedIntents).forEach((key) => {
        aggregatedIntents[key] += ib[key] || 0;
      });
    });

    // Sort insights by mention_count descending
    insights.sort((a, b) => b.mention_count - a.mention_count);

    // Reconcile total friction vs noise
    if (noiseCount === 0 && totalRawAnalyzed > 0) {
      noiseCount = totalRawAnalyzed - totalFrictionCount;
    }

    // 4. Intent breakdown
    const totalNonNoiseIntent = Object.values(aggregatedIntents).reduce((sum, v) => sum + v, 0);
    const INTENT_DISPLAY = [
      { id: 'high_intent_blocked', label: 'High intent, blocked by uncertainty', count: aggregatedIntents.high_intent_blocked },
      { id: 'occasion_waiting', label: 'Waiting for an occasion or event', count: aggregatedIntents.occasion_waiting },
      { id: 'price_monitoring', label: 'Monitoring for a price drop', count: aggregatedIntents.price_monitoring },
      { id: 'bookmarking_inspiration', label: 'Bookmarking / inspiration only', count: aggregatedIntents.bookmarking_inspiration },
      { id: 'comparison_shortlisting', label: 'Comparing options before deciding', count: aggregatedIntents.comparison_shortlisting },
    ];

    const intents = INTENT_DISPLAY.map((item) => ({
      ...item,
      pct: totalNonNoiseIntent > 0 ? Math.round((item.count / totalNonNoiseIntent) * 100) : 0,
      pct_formatted: totalNonNoiseIntent > 0 ? `${Math.round((item.count / totalNonNoiseIntent) * 100)}%` : '0%',
      has_evidence: item.count > 0,
    }));

    return NextResponse.json({
      insights,
      platforms,
      intents,
      total_raw_analyzed: totalRawAnalyzed,
      total_friction_count: totalFrictionCount,
      noise_count: noiseCount,
      updated_at: new Date().toISOString()
    });

  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
