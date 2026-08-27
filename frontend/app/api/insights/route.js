import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

export const dynamic = 'force-dynamic';
export const revalidate = 0;

export async function GET() {
  try {
    const { data: insightsData, error: insightsErr } = await supabase
      .from('insights')
      .select('*');

    if (insightsErr) {
      return NextResponse.json({ error: insightsErr.message }, { status: 500 });
    }

    const platformNames = ['playstore', 'appstore', 'reddit', 'youtube'];
    const PLATFORM_DISPLAY = {
      playstore: 'Play Store',
      appstore: 'App Store',
      reddit: 'Reddit',
      youtube: 'YouTube',
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

    const CANONICAL_LABELS = {
      fit_sizing_anxiety: 'Fit & Sizing Uncertainty',
      fabric_quality_ambiguity: 'Fabric / Quality Uncertainty',
      visual_reality_discrepancy: 'Photo → Reality Uncertainty',
      occasion_timing_delay: 'Occasion / Timing / Postponement',
      styling_pairing_doubt: 'Styling / Pairing Uncertainty',
      choice_paralysis_shortlist: 'Comparison / Choice Overload',
      social_validation_delay: 'Social / External Validation',
      price_deal_timing: 'Price / Deal Timing',
      unrelated_other: 'Out-of-Scope / Noise',
    };

    const themeRows = (insightsData || []).filter((row) => row && row.theme);
    const noiseRow = themeRows.find((row) => row.theme === 'unrelated_other');
    const nonNoiseRows = themeRows.filter((row) => row.theme !== 'unrelated_other');

    let totalFrictionCount = nonNoiseRows.reduce((sum, row) => sum + (Number(row.mention_count) || 0), 0);
    let noiseCount = Number(noiseRow?.mention_count || 0);
    if (noiseCount === 0 && totalRawAnalyzed > 0) {
      noiseCount = Math.max(0, totalRawAnalyzed - totalFrictionCount);
    }

    const goalRelevantSignals = totalFrictionCount;
    const filteredOutOfScope = noiseCount;

    const insights = nonNoiseRows
      .map((row) => {
        const count = Number(row.mention_count) || 0;
        const pctExact = totalFrictionCount > 0 ? (count / totalFrictionCount) * 100 : 0;
        return {
          id: row.theme,
          theme: row.theme,
          theme_label: row.theme_label || CANONICAL_LABELS[row.theme],
          label: row.theme_label || CANONICAL_LABELS[row.theme],
          mention_count: count,
          count,
          pct: Number(pctExact.toFixed(1)),
          pct_exact: pctExact,
          pct_formatted: `${Number(pctExact.toFixed(1))}%`,
        };
      })
      .sort((a, b) => b.count - a.count);

    const aggregatedIntents = {
      high_intent_blocked: 0,
      occasion_waiting: 0,
      price_monitoring: 0,
      bookmarking_inspiration: 0,
      comparison_shortlisting: 0,
    };

    themeRows.forEach((row) => {
      const ib = row.intent_breakdown || {};
      Object.keys(aggregatedIntents).forEach((key) => {
        aggregatedIntents[key] += Number(ib[key] || 0);
      });
    });

    const totalIntentSignals = Object.values(aggregatedIntents).reduce((sum, value) => sum + value, 0);
    const INTENT_DISPLAY = [
      { id: 'high_intent_blocked', label: 'High intent, blocked by uncertainty', count: aggregatedIntents.high_intent_blocked },
      { id: 'occasion_waiting', label: 'Waiting for an occasion or event', count: aggregatedIntents.occasion_waiting },
      { id: 'price_monitoring', label: 'Monitoring for a price drop', count: aggregatedIntents.price_monitoring },
      { id: 'bookmarking_inspiration', label: 'Bookmarking / inspiration only', count: aggregatedIntents.bookmarking_inspiration },
      { id: 'comparison_shortlisting', label: 'Comparing options before deciding', count: aggregatedIntents.comparison_shortlisting },
    ];

    const intents = INTENT_DISPLAY.map((item) => {
      const pctExact = totalIntentSignals > 0 ? (item.count / totalIntentSignals) * 100 : 0;
      return {
        ...item,
        pct: Number(pctExact.toFixed(1)),
        pct_formatted: `${Number(pctExact.toFixed(1))}%`,
        has_evidence: item.count > 0,
      };
    });

    return NextResponse.json({
      insights,
      platforms,
      intents,
      total_raw_analyzed: totalRawAnalyzed,
      total_friction_count: totalFrictionCount,
      goal_relevant_signals: goalRelevantSignals,
      noise_count: noiseCount,
      filtered_out_of_scope: filteredOutOfScope,
      total_intent_signals: totalIntentSignals,
      source_mix: platforms.map((p) => `${p.name}: ${p.count}`).join(', '),
      updated_at: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
