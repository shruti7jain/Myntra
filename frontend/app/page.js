'use client';

import {
    AlertTriangle,
    Bot,
    CheckCircle2,
    FileText,
    LayoutDashboard,
    Loader2, RefreshCw,
    Send,
    Target
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
const OPPORTUNITIES = [
  { id: 'fit_sizing_anxiety', theme: 'fit_sizing_anxiety', label: 'Fit confidence gap', tag: 'Potential opportunity area', impact: 'High', what: 'Users appear to save products they want but hesitate because they cannot confidently predict fit before purchase.', why: 'The strongest signal in the discovery corpus is uncertainty around size and fit at the decision stage.', evidence: 'Cross-source evidence volume and repeated size-fit hesitation in public conversations.' },
  { id: 'fabric_quality_ambiguity', theme: 'fabric_quality_ambiguity', label: 'Fabric / quality uncertainty', tag: 'Potential opportunity area', impact: 'High', what: 'Material feel and visibility are not obvious from product presentation, creating uncertainty before a purchase decision.', why: 'Users often hesitate when they cannot tell whether the material will feel right or look cheap/sheer.', evidence: 'Repeat mentions of transparency, thickness, fabric feel and quality uncertainty.' },
  { id: 'occasion_timing_delay', theme: 'occasion_timing_delay', label: 'Occasion-based delay', tag: 'Potential opportunity area', impact: 'High', what: 'Some saved products appear to be parked for future events rather than immediate purchase intent.', why: 'Users may save an item for a wedding, holiday, or future need and delay the decision until timing becomes clearer.', evidence: 'Strong timing and postponement signals across public voice evidence.' },
  { id: 'visual_reality_discrepancy', theme: 'visual_reality_discrepancy', label: 'Photo-to-reality confidence gap', tag: 'Potential opportunity area', impact: 'Medium', what: 'Users express concern that the final product may not match the visual representation they saw.', why: 'Differences in colour, finish, material or styling can reduce purchase confidence even after initial interest.', evidence: 'Public discussions question whether the real item will look like the studio photos.' },
  { id: 'styling_pairing_doubt', theme: 'styling_pairing_doubt', label: 'Styling / wardrobe fit uncertainty', tag: 'Potential opportunity area', impact: 'Medium', what: 'Users may like a product but not know how it fits into their actual wardrobe or outfit plan.', why: 'Without a styling context, interest remains a saved item rather than an immediate purchase.', evidence: 'Recurrent concern about pairing and outfit confidence.' },
  { id: 'social_validation_delay', theme: 'social_validation_delay', label: 'External validation behaviour', tag: 'Potential opportunity area', impact: 'Medium', what: 'Users appear to seek reassurance from others before deciding, which may delay conversion.', why: 'The public corpus suggests a confidence-building loop outside the app, but this requires validation.', evidence: 'Reddit/YouTube/community reference patterns exist, but not enough to prove app abandonment.' },
  { id: 'choice_paralysis_shortlist', theme: 'choice_paralysis_shortlist', label: 'Comparison and shortlist overload', tag: 'Potential opportunity area', impact: 'Medium', what: 'Users may save multiple similar products and stall while comparing alternatives.', why: 'Decision fatigue and comparison delay can turn a wishlisted item into a parked item instead of a purchase.', evidence: 'Explicit comparison and shortlist hesitation appears in several conversations.' }
];

const HYPOTHESIS_SECTIONS = [
  {
    id: 'H1',
    title: 'H1 — THE DOUBT HAS A NAME',
    status: 'SUPPORTED',
    summary: 'Fit, fabric and photo-reality uncertainty are the clearest product-confidence blockers in the public evidence.',
    themes: ['fit_sizing_anxiety', 'fabric_quality_ambiguity', 'visual_reality_discrepancy'],
    note: 'Engine signal: confidence gap is visible. Primary research: which of these uncertainties actually drives non-purchase?'
  },
  {
    id: 'H2',
    title: 'H2 — CONFIDENCE MAY BE BUILT OUTSIDE THE APP',
    status: 'PARTIALLY SUPPORTED',
    summary: 'External validation behaviour appears in the corpus, but the existing data does not prove where users resolve uncertainty.',
    themes: ['social_validation_delay'],
    note: 'Engine signal: users seek reassurance externally. Primary research: where do they actually resolve that uncertainty?'
  },
  {
    id: 'H3',
    title: 'H3 — THE WISHLIST IS A PARKING LOT FOR DECISIONS',
    status: 'SUPPORTED',
    summary: 'A saved item often reflects delayed decisions, occasion timing, or comparison instead of immediate purchase intent.',
    themes: ['occasion_timing_delay', 'choice_paralysis_shortlist'],
    note: 'Engine signal: wishlist often indicates consideration, not commitment. Primary research: what state-of-intent is most predictive of purchase within 30 days?'
  }
];

const PLATFORM_BADGE = {
  'Play Store': 'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
  'App Store':  'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
  'Reddit':     'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
  'YouTube':    'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
};

const SUGGESTED_QUERIES = [
  'What are the strongest goal-relevant themes in the current corpus?',
  'Which wishlist-to-purchase signals are strongest across App Store vs Play Store?',
  'What evidence suggests fit or sizing uncertainty?',
  'What do users do when they feel uncertain about a saved product?',
  'Which themes appear to represent delayed purchase intent rather than immediate buying intent?',
];

function PBadge({ platform }) {
  const cls = PLATFORM_BADGE[platform] || 'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]';
  return (
    <span className={`px-2 py-0.5 rounded border text-[10px] font-bold ${cls}`}>
      {platform}
    </span>
  );
}

function MyntraWordmark() {
  return (
    <div className="flex items-center gap-2">
      <div>
        <p className="text-[14px] font-black text-[#282C3F] leading-none tracking-tight">Myntra AI Engine</p>
        <p className="text-[9px] font-black text-[#ff3f6c] uppercase tracking-[0.15em] leading-none mt-1">Discovery</p>
      </div>
    </div>
  );
}

export default function MyntraDiscoveryEngine() {
  const [tab, setTab] = useState('discovery');
  const [expandedOpp, setExpandedOpp] = useState(null);
  const [dbInsights, setDbInsights] = useState([]);
  const [totalAnalyzed, setTotalAnalyzed] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const [showAllQuotes, setShowAllQuotes] = useState(false);
  const [lastSynced, setLastSynced] = useState(null);
  const [themes, setThemes] = useState([]);
  const [intents, setIntents] = useState([]);
  const [platforms, setPlatforms] = useState([
    { name: 'Play Store', count: 0 },
    { name: 'Reddit', count: 0 },
    { name: 'App Store', count: 0 },
    { name: 'YouTube', count: 0 }
  ]);
  const [quotes, setQuotes] = useState([]);
  const [loadingQuotes, setLoadingQuotes] = useState(false);
  const [totalFrictionCount, setTotalFrictionCount] = useState(0);
  const [noiseCount, setNoiseCount] = useState(0);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am the Myntra Wishlist → Purchase Discovery Copilot. I analyse public conversations across App Store, Play Store, YouTube, and Reddit to identify purchase-decision signals, uncertainty, and delay patterns tied to saved fashion items.' }
  ]);
  const [input, setInput] = useState('');
  const [generating, setGenerating] = useState(false);
  const chatEnd = useRef(null);

  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`/api/insights?t=${Date.now()}`, { cache: 'no-store' });
        const d = await r.json();
        if (d.total_raw_analyzed) setTotalAnalyzed(d.total_raw_analyzed);
        if (d.insights?.length > 0) setDbInsights(d.insights);
        if (d.intents?.length > 0) setIntents(d.intents);
      } catch {}
    })();
  }, []);

  const sync = async () => {
    setSyncing(true);
    try {
      const r = await fetch(`/api/insights?t=${Date.now()}`, { cache: 'no-store' });
      const d = await r.json();
      if (d.total_raw_analyzed) setTotalAnalyzed(d.total_raw_analyzed);
      if (d.total_friction_count !== undefined) setTotalFrictionCount(d.total_friction_count);
      if (d.noise_count !== undefined) setNoiseCount(d.noise_count);
      if (d.platforms?.length > 0) setPlatforms(d.platforms);
      if (d.intents?.length > 0) setIntents(d.intents);
      if (d.insights?.length > 0) {
        setDbInsights(d.insights);
        setThemes(d.insights);
      }
      setLastSynced(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
    } catch {}
    setSyncing(false);
  };
  
  // Initial load
  useEffect(() => {
    sync();
    fetchQuotes();
  }, []);

  const fetchQuotes = async () => {
    setLoadingQuotes(true);
    try {
      const r = await fetch(`/api/verbatims?limit=1500`, { cache: 'no-store' });
      const d = await r.json();
      if (d.verbatims) setQuotes(d.verbatims);
    } catch {}
    setLoadingQuotes(false);
  };
  



  const sendMsg = async (force) => {
    const q = force || input;
    if (!q.trim() || generating) return;
    setMessages(p => [...p, { role: 'user', content: q }]);
    if (!force) setInput('');
    setGenerating(true);
    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q }),
      });
      const d = await r.json();
      setMessages(p => [...p, { role: 'assistant', content: d.reply || 'No response received.' }]);
    } catch {
      setMessages(p => [...p, { role: 'assistant', content: 'Could not reach AI Copilot. Please try again.' }]);
    }
    setGenerating(false);
  };



  const TABS = [
    { id: 'discovery', label: 'Discovery & Findings', icon: LayoutDashboard },
    { id: 'copilot',   label: 'AI Copilot',           icon: Bot },
  ];

  return (
    <div
      className="flex min-h-screen bg-[#f5f5f6] text-[#282C3F]"
      style={{ fontFamily: "'Inter', 'Helvetica Neue', sans-serif" }}
    >
      {/* ═══════════ SIDEBAR ═══════════ */}
      <aside className="w-52 flex-shrink-0 fixed top-0 left-0 h-full flex flex-col z-30 bg-white border-r border-[#e9e9eb]">

        {/* Logo */}
        <div className="px-5 py-4 border-b border-[#e9e9eb]">
          <MyntraWordmark />
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5">
          <p className="px-2 pt-3 pb-1.5 text-[9px] font-black uppercase tracking-widest text-[#94969f]">Sections</p>
          {TABS.map(n => (
            <button
              key={n.id}
              onClick={() => setTab(n.id)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all text-[12px] font-semibold ${
                tab === n.id
                  ? 'bg-[#fff0f3] text-[#ff3f6c] font-bold'
                  : 'text-[#535766] hover:bg-[#f5f5f6]'
              }`}
            >
              <n.icon className="w-3.5 h-3.5 flex-shrink-0" />
              {n.label}
            </button>
          ))}
        </nav>

        {/* Sources */}
        <div className="p-4 border-t border-[#e9e9eb]">
          <p className="text-[9px] font-black uppercase tracking-widest text-[#94969f] mb-2">Data Sources ({totalAnalyzed.toLocaleString()})</p>
          {platforms.map(s => (
            <div key={s.name} className="flex items-center justify-between text-[10px] text-[#535766] mb-1">
              <div className="flex items-center gap-1.5">
                <div className="w-1.5 h-1.5 rounded-full bg-[#ff3f6c] flex-shrink-0" />
                {s.name}
              </div>
              <span className="font-bold">{s.count}</span>
            </div>
          ))}
          <button
            onClick={sync}
            disabled={syncing}
            className={`w-full py-2.5 rounded-lg text-[10px] font-bold flex items-center justify-center gap-2 transition-all mt-4 ${
              syncing ? 'bg-[#e9e9eb] text-[#535766] cursor-not-allowed' : 'bg-[#282C3F] text-white hover:bg-[#000000]'
            }`}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing from Database...' : 'Sync Live Data'}
          </button>
          {lastSynced && (
            <p className="text-[9px] text-[#94969f] text-center mt-2 font-medium">
              Last synced: {lastSynced}
            </p>
          )}
        </div>
      </aside>

      {/* ═══════════ MAIN ═══════════ */}
      <main className="flex-1 ml-52 flex flex-col min-h-screen">

        {/* Header */}
        <header className="sticky top-0 z-20 bg-white border-b border-[#e9e9eb] px-8 py-3.5 flex items-center justify-between">
          <div>
            <h1 className="text-[15px] font-black text-[#282C3F]">
              {tab === 'discovery' && 'Why don\'t Myntra users buy what they\'ve wishlisted?'}
              {tab === 'copilot'   && 'AI PM Copilot'}
            </h1>
            <p className="text-[10px] text-[#94969f] mt-0.5">
              {tab === 'discovery' && `${totalAnalyzed ? totalAnalyzed.toLocaleString() : '...'} public user conversations · Play Store · App Store · Reddit · YouTube`}
              {tab === 'copilot'   && `Grounded in ${totalAnalyzed ? totalAnalyzed.toLocaleString() : '...'} VoC verbatims · Live database`}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1.5 rounded-full text-[10px] font-bold bg-[#fff0f3] text-[#ff3f6c] border border-[#ffcdd7] flex items-center gap-1.5 flex-shrink-0">
              <Target className="w-3 h-3" /> No Monetary Incentives
            </span>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 p-6">

          {/* ══════════════════════════════════════════
              DISCOVERY + FINDINGS (single page)
          ══════════════════════════════════════════ */}
          {tab === 'discovery' && (
            <div className="max-w-[980px] mx-auto space-y-5">

              {/* ── 3 KPIs ── */}
              <div className="grid grid-cols-3 gap-4">
                {[
                  { label: 'Public conversations analysed',  val: totalAnalyzed.toLocaleString(), sub: 'Across App Store, Play Store, YouTube and Reddit — discovery evidence only', icon: FileText },
                  { label: 'Goal-relevant purchase-friction signals',  val: totalFrictionCount.toLocaleString(), sub: 'Signals tied to saved-item hesitation, delay or abandonment', icon: AlertTriangle },
                  { label: 'Filtered out-of-scope / noise', val: noiseCount.toLocaleString(), sub: 'Generic complaints, app bugs, post-purchase issues, unrelated positives', icon: CheckCircle2 },
                ].map((k, i) => (
                  <div key={i} className="bg-white rounded-xl border border-[#e9e9eb] p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="p-1.5 rounded-lg bg-[#fff0f3]">
                        <k.icon className="w-3.5 h-3.5 text-[#ff3f6c]" />
                      </div>
                      <p className="text-[10px] font-bold text-[#94969f] uppercase tracking-wider">{k.label}</p>
                    </div>
                    <p className="text-2xl font-black text-[#282C3F]">{k.val}</p>
                    <p className="text-[10px] text-[#94969f] mt-1 leading-snug">{k.sub}</p>
                  </div>
                ))}
              </div>

              {/* ── Friction chart + Key findings ── */}
              <div className="grid grid-cols-5 gap-5">

                {/* Friction bars — 3/5 */}
                <div className="col-span-3 bg-white border border-[#e9e9eb] rounded-xl overflow-hidden">
                  <div className="px-5 py-4 border-b border-[#e9e9eb]">
                    <p className="text-[13px] font-bold text-[#282C3F]">Top Reasons Users Don't Buy From Their Wishlist</p>
                    <p className="text-[10px] text-[#94969f] mt-0.5">Ranked by mention volume across {totalFrictionCount.toLocaleString()} friction signals</p>
                  </div>
                  <div className="p-5 space-y-4">
                    {themes.map((t, i) => (
                      <div key={i}>
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2">
                            <span className="text-[10px] font-black text-[#d1d5db] w-3">{i + 1}</span>
                            <span className="text-[12px] font-bold text-[#282C3F]">{t.theme_label || t.label}</span>
                          </div>
                          <span className="text-[12px] font-black text-[#ff3f6c]">{t.pct}%</span>
                        </div>
                        <div className="ml-5 h-2 rounded-full bg-[#f5f5f6]">
                          <div
                            className="h-full rounded-full bg-[#ff3f6c] transition-all duration-700"
                            style={{ width: `${t.pct}%`, opacity: 1 - i * 0.12 }}
                          />
                        </div>
                        <p className="ml-5 text-[9px] text-[#94969f] mt-1">{(t.count || 0).toLocaleString()} of {totalFrictionCount.toLocaleString()} friction mentions</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Key findings — 2/5 */}
                <div className="col-span-2 flex flex-col gap-4">

                  <div className="flex-1 bg-[#fff8f9] border border-[#ffcdd7] rounded-xl p-4">
                    <p className="text-[11px] font-black text-[#94969f] uppercase tracking-wider mb-3">What we discovered (Top 3 Reasons)</p>
                    <div className="space-y-4">
                      {themes.slice(0, 3).map((t, i) => {
                        const descriptions = {
                          fit_sizing_anxiety: 'Users love the item but hesitate to risk ordering the wrong size. Inconsistent brand size charts create high sizing doubt and return anxiety.',
                          fabric_quality_ambiguity: 'Studio photography hides sheerness and material thinness. Users experience tactile uncertainty before committing to buy.',
                          styling_pairing_doubt: 'Users wishlist items they like visually but cannot picture wearing with their existing wardrobe. Without a clear outfit plan, items stay saved indefinitely.',
                          visual_reality_discrepancy: 'The item looks perfect in studio lighting but users fear it will look different in reality. Real customer photos help verify finish and color.',
                          occasion_timing_delay: 'Users save items for future events, but delay purchases until closer to the date, risking out-of-stock.',
                          choice_paralysis_shortlist: 'Users accumulate dozens of similar items and cannot decide which one is best, leading to complete wishlist abandonment.',
                          social_validation_delay: 'Users wait for friends or family to approve the item before checking out, often losing purchase momentum.'
                        };
                        return (
                          <div key={i} className="flex gap-2.5">
                            <div className="w-4 h-4 rounded-full bg-[#ff3f6c] text-white flex-shrink-0 flex items-center justify-center text-[9px] font-black mt-0.5">{i + 1}</div>
                            <div>
                              <p className="text-[11px] font-bold text-[#282C3F]">{t.theme_label} ({t.pct}%)</p>
                              <p className="text-[10px] text-[#535766] leading-relaxed mt-0.5">{descriptions[t.theme] || 'Users abandon their cart due to this specific friction point.'}</p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="bg-white border border-[#e9e9eb] rounded-xl p-4">
                    <p className="text-[11px] font-black text-[#94969f] uppercase tracking-wider mb-3">Not every wishlist save = purchase intent</p>
                    <p className="text-[9px] text-[#94969f] mb-2 -mt-1 italic">AI-estimated from {totalFrictionCount ? totalFrictionCount.toLocaleString() : 'live'} classified wishlist signals</p>
                    <div className="space-y-2">
                      {intents && intents.length > 0 ? (
                        intents
                          .filter((r) => Number(r.count || 0) > 0)
                          .map((r, i) => (
                            <div key={i} className="flex items-center justify-between text-[10px]">
                              <div className="flex items-center gap-2">
                                <div className="w-1.5 h-1.5 rounded-full flex-shrink-0 bg-[#ff3f6c]" style={{ opacity: Math.max(0.2, 1 - i * 0.15) }} />
                                <span className="text-[#535766]">{r.label}</span>
                              </div>
                              <span className="font-black text-[#ff3f6c]">{r.pct}%</span>
                            </div>
                          ))
                      ) : (
                        <p className="text-[10px] text-[#94969f]">Loading intent breakdown...</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Real quotes ── */}
              <div className="bg-white border border-[#e9e9eb] rounded-xl overflow-hidden">
                <div className="px-5 py-4 border-b border-[#e9e9eb] flex items-center justify-between">
                  <div>
                    <p className="text-[13px] font-bold text-[#282C3F]">Sample filtered public conversations</p>
                    <p className="text-[10px] text-[#94969f] mt-0.5">Live verbatims — platform-attributed, PII sanitised, only where the theme is supported by the evidence</p>
                  </div>
                  <button
                    onClick={() => setShowAllQuotes(!showAllQuotes)}
                    className="text-[10px] font-bold text-[#ff3f6c] bg-[#fff0f3] hover:bg-[#ffe4e9] px-3 py-1.5 rounded-lg transition-colors border border-[#ffcdd7]"
                  >
                    {showAllQuotes ? 'Hide all comments' : `Show all ${quotes.length} comments`}
                  </button>
                </div>
                <div className={`p-5 transition-all duration-300 ${showAllQuotes ? 'max-h-[500px] overflow-y-auto' : ''}`}>
                  <div className="grid grid-cols-3 gap-3">
                    {loadingQuotes ? (
                      <div className="col-span-3 text-center py-10 text-[11px] text-[#94969f]">Loading live verbatims from Supabase...</div>
                    ) : (showAllQuotes ? quotes : quotes.slice(0, 6)).map((q, i) => (
                      <div key={i} className="rounded-xl p-3.5 border border-[#e9e9eb] bg-[#fafafa] hover:border-[#ffcdd7] transition-colors flex flex-col">
                        <p className="text-[11px] italic text-[#282C3F] leading-relaxed mb-3">"{q.text}"</p>
                        <div className="flex items-center justify-between mt-auto">
                          <PBadge platform={q.platform} />
                          <span className="text-[9px] text-[#94969f]">{q.theme}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="px-5 py-3 border-t border-[#e9e9eb]">
                  <p className="text-[10px] text-[#94969f]">
                    ⚠️ Source mix is uneven (96% Play Store); findings reflect the available public conversation corpus and should be validated through primary user research.
                  </p>
                </div>
              </div>

              {/* ── OPPORTUNITIES ── */}
              <div className="bg-white border border-[#e9e9eb] rounded-xl overflow-hidden mt-5">
                <div className="px-5 py-4 border-b border-[#e9e9eb]">
                  <p className="text-[13px] font-bold text-[#282C3F]">Potential opportunity areas</p>
                  <p className="text-[10px] text-[#94969f] mt-0.5">Discovery-stage themes only — not final product recommendations</p>
                </div>
                <div className="divide-y divide-[#e9e9eb]">
                  {OPPORTUNITIES.map((opp, i) => {
                    const themeData = themes.find((t) => t.theme === opp.theme || t.id === opp.id) || { pct: 0, count: 0 };
                    const hasEvidence = (themeData.count || 0) > 0 || (themeData.mention_count || 0) > 0;
                    return (
                      <div key={opp.id} className="p-5 hover:bg-[#fafafa] transition-colors flex gap-5">
                        <div className="w-8 h-8 rounded-full bg-[#282C3F] text-white flex-shrink-0 flex items-center justify-center font-black text-[12px]">
                          {i + 1}
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            <h3 className="text-[12px] font-bold text-[#282C3F]">{opp.label}</h3>
                            <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${hasEvidence ? 'bg-[#fff0f3] text-[#ff3f6c]' : 'bg-[#f5f5f6] text-[#94969f]'}`}>
                              {hasEvidence ? `Evidence-backed · ${themeData.pct}%` : 'Exploratory · 0% evidence'}
                            </span>
                            <span className="px-2 py-0.5 rounded-full text-[9px] font-bold bg-[#f5f5f6] text-[#535766]">
                              {opp.impact}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <p className="text-[9px] font-black uppercase tracking-wider text-[#94969f] mb-1">Discovery signal</p>
                              <p className="text-[10px] text-[#535766] leading-relaxed">{opp.what}</p>
                            </div>
                            <div>
                              <p className="text-[9px] font-black uppercase tracking-wider text-[#94969f] mb-1">Why this matters</p>
                              <p className="text-[10px] text-[#535766] leading-relaxed">{opp.why}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

            </div>
          )}

          {/* ══════════════════════════════════════════
              AI COPILOT
          ══════════════════════════════════════════ */}
          {tab === 'copilot' && (
            <div className="max-w-[880px] mx-auto flex gap-5" style={{ height: 'calc(100vh - 130px)' }}>

              <div className="flex-1 bg-white border border-[#e9e9eb] rounded-xl flex flex-col overflow-hidden">
                <div className="px-5 py-3.5 border-b border-[#e9e9eb] bg-[#fafafa] flex items-center gap-2">
                  <Bot className="w-4 h-4 text-[#ff3f6c]" />
                  <div>
                    <p className="text-[12px] font-bold text-[#282C3F]">Myntra AI Discovery Copilot</p>
                    <p className="text-[9px] text-[#94969f]">Grounded in {totalAnalyzed ? totalAnalyzed.toLocaleString() : 'live'} verbatims · Live database</p>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-[#fafafa]">
                  {messages.map((m, i) => (
                    <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div
                        className="max-w-[80%] p-3.5 text-[11px] leading-relaxed"
                        style={{
                          background: m.role === 'user' ? '#282C3F' : '#ffffff',
                          color: m.role === 'user' ? '#ffffff' : '#282C3F',
                          border: m.role === 'user' ? 'none' : '1px solid #e9e9eb',
                          borderRadius: m.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                        }}
                      >
                        {m.role === 'assistant' && (
                          <div className="flex items-center gap-1.5 mb-2 pb-1.5 border-b border-[#f0f0f0]">
                            <Bot className="w-3 h-3 text-[#ff3f6c]" />
                            <span className="text-[9px] font-black text-[#94969f] uppercase tracking-wider">Myntra AI</span>
                          </div>
                        )}
                        <div className="markdown-body">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                              ul: ({node, ...props}) => <ul className="list-disc pl-4 mb-2" {...props} />,
                              ol: ({node, ...props}) => <ol className="list-decimal pl-4 mb-2" {...props} />,
                              li: ({node, ...props}) => <li className="mb-1" {...props} />,
                              strong: ({node, ...props}) => <strong className="font-bold" {...props} />
                            }}
                          >
                            {m.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  ))}
                  {generating && (
                    <div className="flex justify-start">
                      <div className="flex items-center gap-2 px-4 py-3 rounded-2xl bg-white border border-[#e9e9eb]">
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-[#ff3f6c]" />
                        <span className="text-[10px] font-bold text-[#94969f]">Generating insight...</span>
                      </div>
                    </div>
                  )}
                  <div ref={chatEnd} />
                </div>

                <div className="p-4 border-t border-[#e9e9eb] bg-white">
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && sendMsg()}
                      placeholder="Ask about a discovery theme, evidence strength, or source comparison..."
                      className="flex-1 rounded-xl py-2.5 px-3.5 text-[11px] bg-[#f5f5f6] border border-[#e9e9eb] text-[#282C3F] placeholder-[#94969f] focus:outline-none focus:border-[#ff3f6c] focus:bg-white transition-colors"
                      disabled={generating}
                    />
                    <button
                      onClick={() => sendMsg()}
                      disabled={generating || !input.trim()}
                      className="p-2.5 bg-[#ff3f6c] hover:bg-[#e33660] rounded-xl text-white flex-shrink-0 transition-colors disabled:opacity-40"
                    >
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>

              {/* Suggestions */}
              <div className="w-52 flex flex-col gap-3">
                <div className="bg-white border border-[#e9e9eb] rounded-xl overflow-hidden">
                  <div className="px-4 py-3 border-b border-[#e9e9eb] bg-[#fafafa]">
                    <p className="text-[11px] font-bold text-[#282C3F]">Try asking</p>
                    <p className="text-[9px] text-[#94969f]">Click to send</p>
                  </div>
                  <div className="p-3 space-y-2">
                    {SUGGESTED_QUERIES.map((q, i) => (
                      <button
                        key={i}
                        onClick={() => !generating && sendMsg(q)}
                        disabled={generating}
                        className="w-full text-left p-2.5 rounded-lg text-[10px] text-[#535766] bg-[#fafafa] border border-[#e9e9eb] hover:border-[#ff3f6c] hover:bg-[#fff8f9] transition-colors leading-relaxed"
                      >
                        "{q}"
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
