import Groq from 'groq-sdk';
import { NextResponse } from 'next/server';
import { supabase } from '../../../lib/supabase';

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

    const systemPrompt = `You are the Myntra Wishlist → Purchase Discovery Copilot. Your job is to help the Growth Team understand why a user adds a fashion item to a wishlist but does not purchase it.

LIVE VoC DATA (${totalAnalyzed.toLocaleString()} verbatims analysed across Play Store, App Store, Reddit, YouTube):

${contextStr}

STRICT RULES:
1. Ground ALL answers exclusively on the empirical data above. Never invent statistics, themes, or quotes.
2. If asked about data not present in the context, say "This is not captured in the current dataset" — do not guess.
3. The core research object is WISHLIST → PURCHASE FRICTION, not general app friction. Keep all answers tied to saved-item hesitation, decision delay, or abandonment.
4. Keep a clear distinction between OBSERVED DATA, ENGINE SIGNAL, INFERENCE, and HYPOTHESIS.
5. Use language such as "purchase-friction signal", "wishlist-relevant signal", "signals consistent with", and "requires primary research validation" where appropriate.
6. Be concise, structured, and PM-oriented: use bullet points and clear headings.
7. Never claim a causal relationship or population prevalence without direct evidence.
8. Strategic constraint: ZERO MONETARY INCENTIVES. Focus on confidence uncertainty, timing, style fit, and decision-making friction, not discounts or coupons.`;

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

    if (queryLower.includes('reddit') || queryLower.includes('youtube') || queryLower.includes('social validation') || queryLower.includes('peer opinion')) {
      const socialCount = socialTheme ? socialTheme.mention_count : 0;
      const socialPct = socialTheme ? socialTheme.pct_of_total : 0;
      reply =
        `**DATA FINDING:** Social validation / peer opinion delay is ${socialCount} mention${socialCount === 1 ? '' : 's'} in the current corpus, which is ${socialPct}% of friction signals.\n\n` +
        (socialTheme ? `Customer verbatim: "${getQuote(socialTheme) || 'N/A'}"\n\n` : '') +
        `**INFERENCE:** This does not provide strong evidence that users leave Myntra for Reddit or YouTube as a primary conversion path in the current dataset.\n\n` +
        `**HYPOTHESIS:** If a future corpus shows stronger direct evidence, it would be a separate external-validation hypothesis rather than a core friction signal.`;

    } else if (queryLower.includes('ethnic') || queryLower.includes('kurti') || queryLower.includes('kurta')) {
      if (fitTheme) {
        const q = getQuote(fitTheme);
        reply =
          `**DATA FINDING:** ${fitTheme.theme_label} — ${fitTheme.mention_count} mentions (${fitTheme.pct_of_total}% of friction signals).\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**INFERENCE:** This is a strong wishlist-relevant uncertainty signal in the current corpus.\n\n` +
          `**HYPOTHESIS:** Fit confidence may be an important blocker in the saved-item decision moment, but this should be validated with direct user research.`;
      } else {
        reply = 'This is not captured in the current dataset.';
      }

    } else if (queryLower.includes('fabric') || queryLower.includes('quality') || queryLower.includes('material') || queryLower.includes('see through')) {
      if (fabricTheme) {
        const q = getQuote(fabricTheme);
        reply =
          `**DATA FINDING:** ${fabricTheme.theme_label} — ${fabricTheme.mention_count} mentions (${fabricTheme.pct_of_total}% of friction signals).\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**INFERENCE:** Fabric uncertainty appears to reduce confidence before purchase.\n\n` +
          `**HYPOTHESIS:** Material confidence may be a discovery-stage opportunity area, but it is not yet a confirmed solution path.`;
      } else {
        reply = 'This is not captured in the current dataset.';
      }

    } else if (queryLower.includes('photo') || queryLower.includes('color') || queryLower.includes('colour') || queryLower.includes('reality') || queryLower.includes('image')) {
      if (photoTheme) {
        const q = getQuote(photoTheme);
        reply =
          `**DATA FINDING:** ${photoTheme.theme_label} — ${photoTheme.mention_count} mentions (${photoTheme.pct_of_total}% of friction signals).\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**INFERENCE:** Photo-to-reality mismatch is a recurring confidence signal in the discovery corpus.\n\n` +
          `**HYPOTHESIS:** This may represent a meaningful product-confidence gap, but the public data cannot prove the final product response.`;
      } else {
        reply = 'This is not captured in the current dataset.';
      }

    } else if (queryLower.includes('size') || queryLower.includes('fit') || queryLower.includes('fitting') || queryLower.includes('shoulder') || queryLower.includes('bust')) {
      if (fitTheme) {
        const q = getQuote(fitTheme);
        reply =
          `**DATA FINDING:** ${fitTheme.theme_label} — ${fitTheme.mention_count} mentions (${fitTheme.pct_of_total}% of friction signals).\n\n` +
          (q ? `Customer verbatim: "${q}"\n\n` : '') +
          `**INFERENCE:** Fit uncertainty is the strongest goal-relevant signal in the current discovery corpus.\n\n` +
          `**HYPOTHESIS:** This suggests that confidence at the saved-item decision stage is a promising discovery opportunity, but the public data does not confirm the final solution.`;
      } else {
        reply = 'This is not captured in the current dataset.';
      }

    } else if (queryLower.includes('intent') || queryLower.includes('bookmark') || queryLower.includes('wishlist use') || queryLower.includes('saving')) {
      reply =
        `**DATA FINDING:** Wishlist intent is estimated from relevant public conversation signals, not observed checkout behaviour.\n\n` +
        `The engine distinguishes between high-intent blocked decisions and status-based bookmarking.\n\n` +
        `**INFERENCE:** The most conversion-relevant group is users who express high intent but remain blocked by uncertainty.\n\n` +
        `**HYPOTHESIS:** This should be validated with wishlist-to-purchase behavioural data before drawing stronger conversion conclusions.`;

    } else {
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
        `**DATA FINDING:** Top friction themes in the current corpus:\n\n` +
        topList +
        `\n\n**INFERENCE:** These themes indicate likely decision blockers in the available public conversation data, not universal user behaviour across all Myntra shoppers.`;
    }

    return NextResponse.json({ reply });

  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
