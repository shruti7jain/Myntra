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
    // 1. Fetch metadata from insights table to get last_classified_at
    const { data: insightsMeta } = await supabase
      .from('insights')
      .select('updated_at')
      .limit(1);
    const lastClassifiedAt = insightsMeta?.[0]?.updated_at || new Date().toISOString();

    // 2. Fetch all raw feedback to perform dynamic, clean aggregation with hard rating exclusion filters
    let allRecords = [];
    let offset = 0;
    const limit = 1000;
    while (true) {
      const { data, error } = await supabase
        .from('raw_feedback')
        .select('id, platform, theme, rating, text, keyword_matched, url')
        .range(offset, offset + limit - 1);
      
      if (error) {
        return NextResponse.json({ error: error.message }, { status: 500 });
      }
      if (!data || data.length === 0) break;
      allRecords = allRecords.concat(data);
      offset += limit;
      if (data.length < limit) break;
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

    const THEME_TO_INTENT = {
      fit_sizing_anxiety:         'high_intent_blocked',
      fabric_quality_ambiguity:   'high_intent_blocked',
      visual_reality_discrepancy: 'high_intent_blocked',
      occasion_timing_delay:      'occasion_waiting',
      styling_pairing_doubt:      'high_intent_blocked',
      choice_paralysis_shortlist: 'comparison_shortlisting',
      social_validation_delay:    'high_intent_blocked',
      price_deal_timing:          'price_monitoring',
      unrelated_other:            'noise',
    };

    const hasExplicitFashionFrictionContext = (text) => {
      if (!text) return false;
      const tLower = text.toLowerCase();
      
      const isFit = ["tight", "loose", "sizing", "fit", "size chart", "wrong size", "large", "small"].some(w => tLower.includes(w));
      const isFabric = ["fabric", "material", "stitching", "see-through", "transparent", "thin", "color fade", "colour fade", "shrink", "poor quality", "bad quality"].some(w => tLower.includes(w));
      const isPhoto = ["photo", "reality", "different from picture", "look different", "mismatch", "image vs", "colour difference"].some(w => tLower.includes(w));
      const isAuthenticity = ["fake", "duplicate", "copy", "counterfeit", "not genuine"].some(w => tLower.includes(w));
      const isPrice = ["price", "expensive", "cheap", "costly", "value for money"].some(w => tLower.includes(w));
      const isPolicy = ["non-returnable", "cannot return", "exchange option", "return request declined", "return window closed", "delivery delay"].some(w => tLower.includes(w));
      
      if (!(isFit || isFabric || isPhoto || isAuthenticity || isPrice || isPolicy)) {
        return false;
      }
      
      const positiveWords = ["perfect", "excellent", "amazing", "good", "satisfied", "love", "like", "awesome", "best", "smooth", "happy", "fabulous", "nice", "premium", "comfortable", "beautiful", "neat", "recommend", "great"];
      const isPositiveText = positiveWords.some(w => tLower.includes(w)) && !["bad", "poor", "worst", "fake", "scam", "cheat", "disappointed", "tight", "loose", "wrong", "mismatch"].some(w => tLower.includes(w));
      if (isPositiveText) {
        return false;
      }
      
      return true;
    };

    const isExcludedByRating = (platform, rating, text) => {
      if (platform === 'playstore' || platform === 'appstore') {
        if (rating === null || rating === undefined) {
          return !hasExplicitFashionFrictionContext(text);
        }
        const val = parseFloat(rating);
        if (isNaN(val)) {
          return !hasExplicitFashionFrictionContext(text);
        }
        if (val >= 4.0) return true;
      } else if (rating !== null && rating !== undefined) {
        const val = parseFloat(rating);
        if (!isNaN(val) && val >= 4.0) return true;
      }
      return false;
    };

    const getCategory = (text) => {
      if (!text) return 'General Fashion';
      const lower = text.toLowerCase();
      if (["kurti", "kurta", "saree", "ethnic", "lehenga", "suit", "dupatta", "salwar", "anouk"].some(w => lower.includes(w))) {
        return 'Ethnic Wear';
      }
      if (["dress", "gown", "maxi", "bodycon"].some(w => lower.includes(w))) {
        return 'Dresses';
      }
      if (["shoe", "sneaker", "heel", "sandal", "footwear", "boots", "loafer"].some(w => lower.includes(w))) {
        return 'Footwear';
      }
      if (["jean", "top", "shirt", "tshirt", "t-shirt", "jacket", "trousers", "denim", "blazer", "skirt"].some(w => lower.includes(w))) {
        return 'Western Wear';
      }
      return 'General Fashion';
    };

    // Aggregation maps
    const themeCounts = {};
    const themeQuotes = {};
    const themeSegments = {};
    const platformCounts = { playstore: 0, appstore: 0, reddit: 0, youtube: 0 };

    const intentCounts = {
      high_intent_blocked: 0,
      occasion_waiting: 0,
      price_monitoring: 0,
      bookmarking_inspiration: 0,
      comparison_shortlisting: 0,
      noise: 0
    };

    // Initialize maps
    Object.keys(CANONICAL_LABELS).forEach(k => {
      themeCounts[k] = 0;
      themeQuotes[k] = [];
      themeSegments[k] = {
        'Ethnic Wear': 0, 'Western Wear': 0, 'Dresses': 0,
        'Footwear': 0, 'General Fashion': 0
      };
    });

    let totalRawAnalyzed = 0;
    let totalFrictionCount = 0;
    let noiseCount = 0;
    let unclassifiedCount = 0;

    allRecords.forEach(r => {
      const platform = r.platform || 'unknown';
      if (platformCounts[platform] !== undefined) {
        platformCounts[platform]++;
      }

      let theme = r.theme;
      const rating = r.rating;
      const text = r.text || '';
      const url = r.url || '';

      if (theme === null || theme === undefined) {
        unclassifiedCount++;
        return;
      }

      // Safeguard: exclude rating >= 4 or rating = null for reviews
      if (isExcludedByRating(platform, rating, text)) {
        theme = 'unrelated_other';
      }

      themeCounts[theme]++;
      totalRawAnalyzed++;

      if (FRICTION_THEME_KEYS.has(theme)) {
        totalFrictionCount++;
      } else {
        noiseCount++;
      }

      // Segment breakdown
      const cat = getCategory(text);
      themeSegments[theme][cat]++;

      // Quote collection
      if (themeQuotes[theme].length < 8 && text.length > 25) {
        const sentences = text.split(/[.!?]/).map(s => s.trim()).filter(s => s.length > 20);
        const quote = sentences.length > 0 ? sentences[0] : text.substring(0, 200).trim();
        if (!themeQuotes[theme].some(q => q.text === quote)) {
          themeQuotes[theme].push({
            text: normalizeText(quote.substring(0, 200)),
            platform: platform === 'playstore' ? 'Play Store' : (platform === 'appstore' ? 'App Store' : platform.charAt(0).toUpperCase() + platform.slice(1)),
            url: url
          });
        }
      }

      // Intent breakdown
      const intent = THEME_TO_INTENT[theme] || 'no_clear_intent';
      if (intentCounts[intent] !== undefined) {
        intentCounts[intent]++;
      }
    });

    // Formatting insights array
    const insights = Object.keys(CANONICAL_LABELS)
      .filter(k => k !== 'unrelated_other')
      .map(k => {
        const count = themeCounts[k];
        const pctExact = totalFrictionCount > 0 ? (count / totalFrictionCount) * 100 : 0;
        const label = CANONICAL_LABELS[k];
        return {
          id: k,
          theme: k,
          theme_label: label,
          label: label,
          mention_count: count,
          count: count,
          pct: Number(pctExact.toFixed(1)),
          pct_exact: pctExact,
          pct_formatted: `${Number(pctExact.toFixed(1))}%`,
          sample_quotes_attributed: JSON.stringify(themeQuotes[k]),
        };
      })
      .sort((a, b) => b.count - a.count);

    const totalIntentSignals = intentCounts.high_intent_blocked +
                               intentCounts.occasion_waiting +
                               intentCounts.price_monitoring +
                               intentCounts.bookmarking_inspiration +
                               intentCounts.comparison_shortlisting;

    const INTENT_DISPLAY = [
      { id: 'high_intent_blocked',    label: 'High intent, blocked by uncertainty',   count: intentCounts.high_intent_blocked },
      { id: 'occasion_waiting',       label: 'Waiting for an occasion or event',       count: intentCounts.occasion_waiting },
      { id: 'price_monitoring',       label: 'Monitoring for a price drop or deal',    count: intentCounts.price_monitoring },
      { id: 'bookmarking_inspiration',label: 'Bookmarking / inspiration only',         count: intentCounts.bookmarking_inspiration },
      { id: 'comparison_shortlisting',label: 'Comparing options before deciding',      count: intentCounts.comparison_shortlisting },
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

    const PLATFORM_DISPLAY = {
      playstore: 'Play Store',
      appstore: 'App Store',
      reddit: 'Reddit',
      youtube: 'YouTube',
    };

    const platforms = Object.keys(platformCounts).map(k => ({
      name: PLATFORM_DISPLAY[k] || k,
      count: platformCounts[k]
    })).sort((a, b) => b.count - a.count);

    const liveRawCount = allRecords.length;
    const dataIsCurrent = (Date.now() - new Date(lastClassifiedAt).getTime()) < 24 * 60 * 60 * 1000;

    return NextResponse.json({
      total_raw_analyzed: totalRawAnalyzed,
      total_friction_count: totalFrictionCount,
      goal_relevant_signals: totalFrictionCount,
      noise_count: noiseCount,
      filtered_out_of_scope: noiseCount,
      unclassified_count: unclassifiedCount,
      total_intent_signals: totalIntentSignals,

      last_classified_at: lastClassifiedAt,
      data_is_current: dataIsCurrent,
      live_raw_count: liveRawCount,
      insights_snapshot_total: totalRawAnalyzed,

      insights,
      intents,
      platforms,
      source_mix: platforms.map((p) => `${p.name}: ${p.count}`).join(', '),
      updated_at: new Date().toISOString(),
    });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
