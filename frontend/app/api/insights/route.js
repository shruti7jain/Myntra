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
export const revalidate = 0;

export async function GET() {
  try {
    // -------------------------------------------------------------------------
    // READ INSIGHTS TABLE
    // The insights table is populated by process_insights.py and contains
    // pre-aggregated mention counts per theme. All counts (friction, noise,
    // total) come from this single snapshot to ensure internal consistency.
    // -------------------------------------------------------------------------
    const { data: insightsData, error: insightsErr } = await supabase
      .from('insights')
      .select('*');

    if (insightsErr) {
      return NextResponse.json({ error: insightsErr.message }, { status: 500 });
    }

    const CANONICAL_LABELS = {
      fit_sizing_anxiety:         'Fit & Sizing Uncertainty',
      fabric_quality_ambiguity:   'Fabric / Quality Uncertainty',
      visual_reality_discrepancy: 'Photo → Reality Uncertainty',
      occasion_timing_delay:      'Occasion / Timing / Postponement',
      styling_pairing_doubt:      'Styling / Pairing Uncertainty',
      choice_paralysis_shortlist: 'Comparison / Choice Overload',
      social_validation_delay:    'Social / External Validation',
      price_deal_timing:          'Price / Deal Timing',
      unrelated_other:            'Out-of-Scope / Noise',
    };

    const FRICTION_THEME_KEYS = new Set([
      'fit_sizing_anxiety',
      'fabric_quality_ambiguity',
      'visual_reality_discrepancy',
      'occasion_timing_delay',
      'styling_pairing_doubt',
      'choice_paralysis_shortlist',
      'social_validation_delay',
      'price_deal_timing',
    ]);

    const themeRows = (insightsData || []).filter((row) => row && row.theme);
    const noiseRow = themeRows.find((row) => row.theme === 'unrelated_other');
    const nonNoiseRows = themeRows.filter((row) => FRICTION_THEME_KEYS.has(row.theme));

    // -------------------------------------------------------------------------
    // CONSISTENT POPULATION: all metrics derived from insights table snapshot.
    // friction_count + noise_count + unclassified_count = total_raw_analyzed
    // -------------------------------------------------------------------------
    const totalFrictionCount = nonNoiseRows.reduce(
      (sum, row) => sum + (Number(row.mention_count) || 0), 0
    );
    const noiseCount = Number(noiseRow?.mention_count || 0);

    // Read last_classified_at from any theme row (they all share the same run timestamp)
    const anyRow = themeRows[0] || {};
    const lastClassifiedAt = anyRow.last_classified_at || anyRow.updated_at || null;

    // -------------------------------------------------------------------------
    // PLATFORM COUNTS (from raw_feedback — for source mix display only)
    // These are live and may differ from insights snapshot if ingestion ran
    // without a subsequent normalization. They are surfaced as source_mix only,
    // NOT used to compute total_raw_analyzed.
    // -------------------------------------------------------------------------
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
    // Live raw count (may be ahead of insights if normalization hasn't run yet)
    const liveRawCount = platformCountResults.reduce((sum, p) => sum + p.count, 0);

    // Insights-based total (consistent with friction and noise counts)
    const totalRawAnalyzed = totalFrictionCount + noiseCount;

    // Unclassified = live count that hasn't been reflected in insights yet
    const unclassifiedCount = Math.max(0, liveRawCount - totalRawAnalyzed);

    // Data is stale if last classification is > 24 hours ago
    const dataIsCurrent = lastClassifiedAt
      ? (Date.now() - new Date(lastClassifiedAt).getTime()) < 24 * 60 * 60 * 1000
      : false;

    // -------------------------------------------------------------------------
    // BUILD INSIGHT OBJECTS FOR FRICTION THEMES
    // -------------------------------------------------------------------------
    const insights = nonNoiseRows
      .map((row) => {
        const count = Number(row.mention_count) || 0;
        const pctExact = totalFrictionCount > 0 ? (count / totalFrictionCount) * 100 : 0;
        const label = normalizeText(row.theme_label || CANONICAL_LABELS[row.theme]);
        return {
          id: row.theme,
          theme: normalizeText(row.theme),
          theme_label: label,
          label,
          mention_count: count,
          count,
          pct: Number(pctExact.toFixed(1)),
          pct_exact: pctExact,
          pct_formatted: `${Number(pctExact.toFixed(1))}%`,
          sample_quotes_attributed: row.sample_quotes_attributed || null,
        };
      })
      .sort((a, b) => b.count - a.count);

    // -------------------------------------------------------------------------
    // INTENT BREAKDOWN (aggregated across all theme rows)
    // -------------------------------------------------------------------------
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

    const totalIntentSignals = Object.values(aggregatedIntents).reduce(
      (sum, value) => sum + value, 0
    );

    const INTENT_DISPLAY = [
      { id: 'high_intent_blocked',    label: 'High intent, blocked by uncertainty',   count: aggregatedIntents.high_intent_blocked },
      { id: 'occasion_waiting',       label: 'Waiting for an occasion or event',       count: aggregatedIntents.occasion_waiting },
      { id: 'price_monitoring',       label: 'Monitoring for a price drop or deal',    count: aggregatedIntents.price_monitoring },
      { id: 'bookmarking_inspiration',label: 'Bookmarking / inspiration only',         count: aggregatedIntents.bookmarking_inspiration },
      { id: 'comparison_shortlisting',label: 'Comparing options before deciding',      count: aggregatedIntents.comparison_shortlisting },
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
      // ---- Core discovery metrics (all from same insights snapshot) ----
      total_raw_analyzed: totalRawAnalyzed,
      total_friction_count: totalFrictionCount,
      goal_relevant_signals: totalFrictionCount,
      noise_count: noiseCount,
      filtered_out_of_scope: noiseCount,
      unclassified_count: unclassifiedCount,     // records ingested but not yet classified
      total_intent_signals: totalIntentSignals,

      // ---- Freshness indicators ----
      last_classified_at: lastClassifiedAt,
      data_is_current: dataIsCurrent,
      live_raw_count: liveRawCount,              // current raw_feedback row count
      insights_snapshot_total: totalRawAnalyzed, // what the insights table represents

      // ---- Discovery insights ----
      insights,
      intents,

      // ---- Source distribution (from live raw_feedback) ----
      platforms,
      source_mix: platforms.map((p) => `${p.name}: ${p.count}`).join(', '),

      // ---- Metadata ----
      updated_at: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
