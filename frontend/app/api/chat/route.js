import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';
import Groq from 'groq-sdk';

export async function POST(req) {
  try {
    const { message } = await req.json();

    if (!message || !message.trim()) {
      return NextResponse.json({ error: 'Message is required' }, { status: 400 });
    }

    // -------------------------------------------------------------------------
    // 1. Fetch current live insights from Supabase as grounding context
    // -------------------------------------------------------------------------
    const { data: insights, error } = await supabase
      .from('insights')
      .select('*')
      .order('mention_count', { ascending: false });

    if (error) {
      console.error('Supabase error in chat route:', error.message);
    }

    if (!insights || insights.length === 0) {
      return NextResponse.json({
        reply:
          'The discovery database has not been populated yet. ' +
          'Please run the ingestion pipeline (scripts/ingestion/run_all_ingestion.py) ' +
          'followed by the normalization script (scripts/normalization/process_insights.py) to load VoC data.',
      });
    }

    const frictionInsights = insights.filter((i) => i.theme !== 'unrelated_other');
    const totalAnalyzed = insights.reduce((sum, i) => sum + (i.mention_count || 0), 0);

    // Build context string from live DB data only — no hardcoded values
    const contextStr = frictionInsights
      .map((i) => {
        const topQuote =
          Array.isArray(i.sample_quotes) && i.sample_quotes.length > 0
            ? typeof i.sample_quotes[0] === 'string'
              ? i.sample_quotes[0]
              : i.sample_quotes[0]?.text || 'N/A'
            : 'N/A';
        const segBreakdown = i.segment_breakdown
          ? Object.entries(i.segment_breakdown)
              .filter(([, v]) => v > 0)
              .sort(([, a], [, b]) => b - a)
              .slice(0, 3)
              .map(([k, v]) => `${k}: ${v}`)
              .join(', ')
          : 'N/A';
        return (
          `Theme: ${i.theme_label}\n` +
          `  - Key: ${i.theme}\n` +
          `  - Mention count: ${i.mention_count} (${i.pct_of_total}% of friction signals)\n` +
          `  - Top categories: ${segBreakdown}\n` +
          `  - Sample customer verbatim: "${topQuote}"`
        );
      })
      .join('\n\n');

    const systemPrompt = `You are the Myntra Wishlist AI Discovery Copilot. You help Product Managers on the Growth Team understand why users add fashion items to their wishlist but don't purchase within 30 days.

LIVE VoC DATA (${totalAnalyzed.toLocaleString()} verbatims analysed across Play Store, App Store, Reddit, YouTube):

${contextStr}

STRICT RULES:
1. Ground ALL answers exclusively on the empirical data above. Never invent statistics, themes, or quotes.
2. If asked about data not present in the context, say "This is not captured in the current dataset" — don't guess.
3. Strategic constraint: ZERO MONETARY INCENTIVES (no discounts, coupons, cashback). Focus on non-monetary levers: size/fit clarity, fabric tactile confidence, photo-reality alignment, occasion timing, styling context, and social validation features.
4. Be concise, structured, and speak directly to a Product Manager — use bullet points and clear headings.
5. When quoting a customer, label it clearly as "Customer verbatim:" and only use quotes from the data provided above.
6. Distinguish between observed evidence (from the VoC data) and your recommendations (labeled as "PM Recommendation:").`;

    // -------------------------------------------------------------------------
    // 2. Try Groq LLM first
    // -------------------------------------------------------------------------
    const apiKey = process.env.GROQ_API_KEY;

    if (apiKey && apiKey.startsWith('gsk_') && apiKey.length > 20) {
      try {
        const groq = new Groq({ apiKey });
        const completion = await groq.chat.completions.create({
          model: 'groq/compound',
          messages: [
            { role: 'system', content: systemPrompt },
            { role: 'user', content: message },
          ],
          temperature: 0.15,
          max_tokens: 700,
        });

        const reply = completion.choices[0]?.message?.content;
        if (reply && reply.trim().length > 0) {
          return NextResponse.json({ reply });
        }
      } catch (err) {
        console.warn('Groq API call failed in chat route:', err.message);
        // Fall through to structured fallback
      }
    }

    // -------------------------------------------------------------------------
    // 3. Structured fallback — dynamically constructed from LIVE Supabase data
    //    No hardcoded quotes, numbers, or fabricated examples.
    // -------------------------------------------------------------------------
    const queryLower = message.toLowerCase();

    const findTheme = (key) =>
      frictionInsights.find((i) => i.theme === key) || null;

    // Helper: get real first quote from a theme (no fabrication)
    const getQuote = (themeObj) => {
      if (!themeObj) return null;
      const quotes = themeObj.sample_quotes || [];
      if (quotes.length === 0) return null;
      return typeof quotes[0] === 'string' ? quotes[0] : quotes[0]?.text || null;
    };

    const fabricTheme   = findTheme('fabric_quality_ambiguity');
    const fitTheme      = findTheme('fit_sizing_anxiety');
    const photoTheme    = findTheme('visual_reality_discrepancy');
    const occasionTheme = findTheme('occasion_timing_delay');
    const socialTheme   = findTheme('social_validation_delay');
    const stylingTheme  = findTheme('styling_pairing_doubt');
    const choiceTheme   = findTheme('choice_paralysis_shortlist');

    let reply = '';

    if (queryLower.includes('ethnic') || queryLower.includes('kurti') || queryLower.includes('kurta')) {
      if (fitTheme) {
        const q = getQuote(fitTheme);
        reply =
          `**${fitTheme.theme_label} — Ethnic Wear Focus**\n\n` +
          `Signal: ${fitTheme.mention_count} mentions (${fitTheme.pct_of_total}% of friction)\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**PM Recommendation:** Ethnic Wear (kurtas, kurtis) has the highest sizing ambiguity due to brand-specific size charts. ` +
          `Surface a body-measurement match confidence score on wishlisted ethnic items, calibrated from past non-returned orders in the same size.`;
      } else {
        reply = 'No specific ethnic wear friction data is captured in the current dataset. Run the ingestion pipeline to populate more data.';
      }

    } else if (queryLower.includes('fabric') || queryLower.includes('quality') || queryLower.includes('material') || queryLower.includes('see through')) {
      if (fabricTheme) {
        const q = getQuote(fabricTheme);
        reply =
          `**${fabricTheme.theme_label}**\n\n` +
          `Signal: ${fabricTheme.mention_count} mentions (${fabricTheme.pct_of_total}% of friction)\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**PM Recommendation:** Fabric tactile ambiguity is a top purchase blocker. ` +
          `Add a 1–5 Sheerness Scale, GSM thickness badge, and buyer wash-durability tags from verified purchasers. ` +
          `Unedited customer try-on photos with fabric close-ups directly reduce this friction.`;
      } else {
        reply = 'No fabric quality friction data is captured yet. Run the ingestion pipeline first.';
      }

    } else if (queryLower.includes('photo') || queryLower.includes('color') || queryLower.includes('colour') || queryLower.includes('reality') || queryLower.includes('image')) {
      if (photoTheme) {
        const q = getQuote(photoTheme);
        reply =
          `**${photoTheme.theme_label}**\n\n` +
          `Signal: ${photoTheme.mention_count} mentions (${photoTheme.pct_of_total}% of friction)\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**PM Recommendation:** Studio lighting creates a gap between the product photo and real appearance. ` +
          `Enable customer photo reviews tagged by natural daylight vs. indoor lighting to eliminate color and finish doubt.`;
      } else {
        reply = 'No photo-reality discrepancy data captured yet. Run ingestion first.';
      }

    } else if (queryLower.includes('size') || queryLower.includes('fit') || queryLower.includes('fitting') || queryLower.includes('shoulder') || queryLower.includes('bust')) {
      if (fitTheme) {
        const q = getQuote(fitTheme);
        reply =
          `**${fitTheme.theme_label}**\n\n` +
          `Signal: ${fitTheme.mention_count} mentions (${fitTheme.pct_of_total}% of friction)\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**PM Recommendation:** Shoulder/bust proportions vary significantly across brands. ` +
          `Introduce an AI body-measurement TrueFit confidence score on wishlisted items, using past non-returned order data as calibration.`;
      } else {
        reply = 'No fit/sizing friction data captured yet. Run ingestion first.';
      }

    } else if (queryLower.includes('intent') || queryLower.includes('bookmark') || queryLower.includes('wishlist use') || queryLower.includes('saving')) {
      reply =
        `**Wishlist Intent Breakdown**\n\n` +
        `The discovery engine classifies wishlist behaviour into these intent types:\n` +
        `• **high_intent_blocked** — User wants to buy but is blocked by uncertainty\n` +
        `• **comparison_shortlisting** — User is comparing multiple options\n` +
        `• **occasion_waiting** — User will buy when a specific event arrives\n` +
        `• **price_monitoring** — User watches for a price drop\n` +
        `• **bookmarking_inspiration** — Saved for inspiration, low purchase intent\n\n` +
        `**PM Recommendation:** Target high_intent_blocked and occasion_waiting users first — ` +
        `they have the highest conversion potential within 30 days without monetary incentives.`;

    } else {
      // General executive summary from live data
      const topList = frictionInsights
        .slice(0, 4)
        .map((t, i) => {
          const q = getQuote(t);
          return (
            `${i + 1}. **${t.theme_label}** — ${t.mention_count} mentions (${t.pct_of_total}%)` +
            (q ? `\n   Evidence: "${q.slice(0, 100)}${q.length > 100 ? '...' : ''}"` : '')
          );
        })
        .join('\n\n');

      reply =
        `**Executive Discovery Summary — ${totalAnalyzed.toLocaleString()} VoC Records**\n\n` +
        `Top friction themes blocking wishlist-to-purchase conversion:\n\n` +
        topList +
        `\n\n**PM Recommendation:** Address the top 2 themes first — they collectively represent the majority of non-monetary friction. ` +
        `Validate through 5–6 user interviews (Part 3) before building a solution.`;
    }

    return NextResponse.json({ reply });

  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
