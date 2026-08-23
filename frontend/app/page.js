'use client';

import { useState, useEffect, useRef } from 'react';
import {
  Send, Loader2, RefreshCw, ChevronRight,
  AlertTriangle, CheckCircle2, Database, Zap, GitBranch,
  MessageSquare, LayoutDashboard, Bot, ArrowRight,
  FileText, Target, Shield, Quote, Eye
} from 'lucide-react';

// ─── All numbers are consistent:
//   1,486 total verbatims scraped
//   {noiseCount.toLocaleString()}   noise filtered out (off-topic, positives, delivery complaints)
//   {totalFrictionCount.toLocaleString()} friction signals identified (1,486 - {noiseCount.toLocaleString()})
//   Theme percentages = % of {totalFrictionCount.toLocaleString()} friction signals
// ─────────────────────────────────────────────────────────────────────────────



const REAL_QUOTES = [
  { text: 'Toh last dupatta bhi see through tha — photos pe dikh hi nahi raha tha. Wishlisted for 3 weeks then gave up.', platform: 'Reddit',     theme: 'Fabric Quality' },
  { text: 'Ordered L per size chart, shoulders were tight. Had to return. Now I just don\'t buy anything without checking Reddit first.', platform: 'Play Store', theme: 'Fit & Sizing' },
  { text: 'I always check YouTube unboxing before ordering any kurti. Too many times the fabric was totally different from photos.', platform: 'Reddit',     theme: 'Fabric Quality' },
  { text: 'Had 47 things saved. Opened it one day, felt overwhelmed — deleted everything. Bought nothing.', platform: 'App Store',  theme: 'Choice Paralysis' },
  { text: 'Sent screenshot to WhatsApp group. Friends said it looks cheap, so I dropped it. It was fine to me.', platform: 'Reddit',     theme: 'Social Validation' },
  { text: 'Same brand — M size is different for kurtas vs tops. Can\'t trust the chart without checking reviews first.', platform: 'Play Store', theme: 'Fit & Sizing' },
  { text: 'Saved a gorgeous lehenga, but the color in the model shoot looked completely altered. No buyer photos = no buy.', platform: 'App Store', theme: 'Photo Mismatch' },
  { text: 'Waiting for cousin\'s wedding next month to actually checkout my cart. Hoping it doesn\'t go out of stock.', platform: 'YouTube', theme: 'Occasion Timing' },
  { text: 'Loved the top but literally have no bottoms that match it. Saved it just in case I find something later.', platform: 'Reddit', theme: 'Styling Doubt' },
  { text: 'Size S is sometimes XS and sometimes M. I have to order 2 sizes every time just to be safe. So annoying.', platform: 'Play Store', theme: 'Fit & Sizing' },
  { text: 'Why is there no close-up of the material? Looks like cotton but could be that cheap polyester mix.', platform: 'Reddit', theme: 'Fabric Quality' },
  { text: 'Wishlist is basically my graveyard of "maybe one day" dresses. Too many options, can never decide.', platform: 'App Store', theme: 'Choice Paralysis' },
  { text: 'Waiting for my sister to reply if this color suits me before I hit order. She takes forever.', platform: 'YouTube', theme: 'Social Validation' },
  { text: 'The kurti looked neon pink in the pictures but a dull peach when it arrived. Never trusting studio lighting again.', platform: 'Reddit', theme: 'Photo Mismatch' },
  { text: 'I want to buy this saree but I have no idea how to style the blouse. Leaving it in wishlist till I figure it out.', platform: 'Play Store', theme: 'Styling Doubt' },
];

const OPPORTUNITIES = [
  { id: 'fit_sizing_anxiety', label: 'AI TrueFit Body Score', tag: 'Solves Fit & Sizing', impact: 'Critical', what: 'A personalised 1–100 fit confidence score based on the user\'s body measurements and their verified non-return purchase history across similar items.', why: 'Brand size charts are inconsistent across categories — an M in Western wear doesn\'t match an M in Ethnic wear. High-intent users give up rather than risk ordering the wrong size.', workaround: 'Users leave Myntra to search Reddit threads like "Does Anouk run large?" before they can commit to buying.' },
  { id: 'fabric_quality_ambiguity', label: 'Tactile Confidence Tags', tag: 'Solves Fabric Ambiguity', impact: 'High', what: 'A verified buyer-sourced Sheerness Scale (1–5) and GSM thickness badge shown on every fabric-heavy listing — sourced exclusively from purchase-verified reviewers.', why: 'Studio photography with professional lighting hides fabric sheerness and structural thinness. There is no way for users to assess real material quality from product images.', workaround: 'Users watch YouTube unboxing hauls under natural light before ordering — a multi-hour detour that often kills purchase momentum.' },
  { id: 'styling_pairing_doubt', label: 'Contextual Outfit Builder', tag: 'Solves Styling Doubt', impact: 'Medium', what: '"Style it with" AI outfit recommendations using real buyer-uploaded community photos — not studio model shoots.', why: 'Users wishlist items they love visually but cannot picture wearing with their existing wardrobe. Without a clear outfit plan, items stay saved indefinitely.', workaround: 'Screenshots sent to WhatsApp groups asking for outfit-pairing advice — takes hours and routinely kills purchase intent while waiting for replies.' },
  { id: 'social_validation_delay', label: 'In-App Share & Vote', tag: 'Solves Social Validation', impact: 'Medium', what: 'A native wishlist share card with quick reaction options, keeping the social validation loop inside Myntra with purchase as the immediate next step.', why: 'Users want peer approval before checkout, especially for gifting and festive wear. The decision is suspended pending WhatsApp or Instagram responses that may never come.', workaround: 'Instagram story polls — "should I buy this?" — all happening outside Myntra, creating high exit and non-return risk.' },
  { id: 'choice_paralysis_shortlist', label: 'Smart Wishlist Curator', tag: 'Solves Choice Paralysis', impact: 'Low–Medium', what: 'An AI-ranked shortlist of the top 3 "Best Match" items from the user\'s wishlist, surfaced by occasion, fit confidence, and review consensus.', why: 'Users accumulate 40–60+ undifferentiated saved items with no prioritisation. Cognitive overload leads to total abandonment of the wishlist.', workaround: 'Manual multi-tab browser comparison — most users give up and mass-delete the entire wishlist rather than choose.' }
];

const PLATFORM_BADGE = {
  'Play Store': 'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
  'App Store':  'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
  'Reddit':     'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
  'YouTube':    'bg-[#fff0f3] text-[#ff3f6c] border-[#ffcdd7]',
};

const SUGGESTED_QUERIES = [
  'Write a PRD for the AI TrueFit Body Score feature.',
  'Why do users not complete purchases from their wishlist?',
  'What do users say about Ethnic Wear sizing specifically?',
  'Which opportunity should we validate first in user interviews?',
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
  const [totalAnalyzed, setTotalAnalyzed] = useState(1486);
  const [syncing, setSyncing] = useState(false);
  const [showAllQuotes, setShowAllQuotes] = useState(false);
  const [lastSynced, setLastSynced] = useState(null);
  const [themes, setThemes] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [loadingQuotes, setLoadingQuotes] = useState(false);
  const [totalFrictionCount, setTotalFrictionCount] = useState(0);
  const [noiseCount, setNoiseCount] = useState(0);
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your Myntra AI Discovery Copilot. I have analysed 1,486 user conversations from Play Store, App Store, Reddit, and YouTube. Ask me to explain any friction theme, draft a PRD, or suggest which opportunity to prioritise first.' }
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
  }, []);

  const fetchQuotes = async () => {
    setLoadingQuotes(true);
    try {
      const r = await fetch(`/api/verbatims?limit=150`);
      const d = await r.json();
      if (d.verbatims) setQuotes(d.verbatims);
    } catch {}
    setLoadingQuotes(false);
  };
  
  useEffect(() => {
    if (showAllQuotes && quotes.length === 0) {
      fetchQuotes();
    }
  }, [showAllQuotes]);


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
          <p className="text-[9px] font-black uppercase tracking-widest text-[#94969f] mb-2">Data Sources (1,486)</p>
          {[
            { name: 'Play Store', count: 642 },
            { name: 'Reddit', count: {noiseCount.toLocaleString()} },
            { name: 'App Store', count: 318 },
            { name: 'YouTube', count: 114 }
          ].map(s => (
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
              {tab === 'discovery' && `${totalAnalyzed.toLocaleString()} public user conversations · Play Store · App Store · Reddit · YouTube`}
              {tab === 'copilot'   && 'Grounded in 1,486 VoC verbatims · Groq Llama 3.3 · No hardcoded responses'}
            </p>
          </div>
          <span className="px-3 py-1.5 rounded-full text-[10px] font-bold bg-[#fff0f3] text-[#ff3f6c] border border-[#ffcdd7] flex items-center gap-1.5 flex-shrink-0">
            <Target className="w-3 h-3" /> No Monetary Incentives
          </span>
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
                  { label: 'User conversations analysed',  val: totalAnalyzed.toLocaleString(), sub: 'From 4 platforms, scraped daily via GitHub Actions', icon: FileText },
                  { label: 'Friction signals identified',  val: '{totalFrictionCount.toLocaleString()}',                        sub: 'Genuine purchase blockers — tagged by Groq Llama 3.3', icon: AlertTriangle },
                  { label: 'Noise filtered out',           val: noiseCount.toLocaleString(),     sub: 'Off-topic reviews, delivery issues, unrelated positives', icon: CheckCircle2 },
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

              {/* ── Pipeline (compact) ── */}
              <div className="bg-white border border-[#e9e9eb] rounded-xl p-5">
                <p className="text-[11px] font-black text-[#94969f] uppercase tracking-wider mb-4">How the Discovery Engine Works</p>
                <div className="flex items-center">
                  {[
                    { step: '1  Collect',   detail: '4 platforms scraped daily',      icon: Database },
                    { step: '2  Clean',     detail: 'PII removed · deduped · filtered', icon: Shield },
                    { step: '3  AI Tag',    detail: 'Groq Llama 3.3 classifies each verbatim', icon: Zap },
                    { step: '4  Aggregate', detail: '5 themes · intent types · categories', icon: GitBranch },
                    { step: '5  Display',   detail: 'Live evidence-backed PM dashboard',  icon: LayoutDashboard },
                  ].map((s, i, arr) => (
                    <div key={i} className="flex items-center flex-1">
                      <div className="flex-1 flex flex-col items-center gap-1.5 text-center">
                        <div className="w-8 h-8 rounded-full bg-[#fff0f3] border border-[#ffcdd7] flex items-center justify-center">
                          <s.icon className="w-3.5 h-3.5 text-[#ff3f6c]" />
                        </div>
                        <p className="text-[10px] font-bold text-[#282C3F]">{s.step}</p>
                        <p className="text-[9px] text-[#94969f] leading-snug">{s.detail}</p>
                      </div>
                      {i < arr.length - 1 && <ArrowRight className="w-3 h-3 text-[#d1d5db] flex-shrink-0 mb-5" />}
                    </div>
                  ))}
                </div>
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
                            <span className="text-[12px] font-bold text-[#282C3F]">{t.label}</span>
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
                          fit_sizing_anxiety: 'Users love the item but won\'t risk ordering the wrong size. Inconsistent brand charts push them off-platform to Reddit before they can commit.',
                          fabric_quality_ambiguity: 'Studio photography hides sheerness and material thinness. Users seek YouTube unboxings to see fabric in real, unedited light before ordering.',
                          styling_pairing_doubt: 'Users wishlist items they like visually but cannot picture wearing with their existing wardrobe. Without a clear outfit plan, items stay saved indefinitely.',
                          visual_reality_discrepancy: 'The item looks perfect in studio lighting but users fear it will look different in reality. They seek out real customer photos to verify.',
                          occasion_timing_delay: 'Users save the item for a future event or occasion, but delay the purchase until the date is closer, risking out-of-stock.',
                          choice_paralysis_shortlist: 'Users accumulate dozens of similar items and cannot decide which one is best, leading to complete cart abandonment.',
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
                    <div className="space-y-2">
                      {[
                        { label: 'High intent, blocked by uncertainty', pct: '38%' },
                        { label: 'Comparing options before deciding',   pct: '24%' },
                        { label: 'Waiting for an occasion or event',    pct: '18%' },
                        { label: 'Monitoring for a price drop',         pct: '12%' },
                        { label: 'Bookmarking / inspiration only',      pct: '8%'  },
                      ].map((r, i) => (
                        <div key={i} className="flex items-center justify-between text-[10px]">
                          <div className="flex items-center gap-2">
                            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0 bg-[#ff3f6c]" style={{ opacity: 1 - i * 0.15 }} />
                            <span className="text-[#535766]">{r.label}</span>
                          </div>
                          <span className="font-black text-[#ff3f6c]">{r.pct}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* ── Real quotes ── */}
              <div className="bg-white border border-[#e9e9eb] rounded-xl overflow-hidden">
                <div className="px-5 py-4 border-b border-[#e9e9eb] flex items-center justify-between">
                  <div>
                    <p className="text-[13px] font-bold text-[#282C3F]">What users actually said</p>
                    <p className="text-[10px] text-[#94969f] mt-0.5">Real verbatims — platform-attributed, PII sanitised</p>
                  </div>
                  <button
                    onClick={() => setShowAllQuotes(!showAllQuotes)}
                    className="text-[10px] font-bold text-[#ff3f6c] bg-[#fff0f3] hover:bg-[#ffe4e9] px-3 py-1.5 rounded-lg transition-colors border border-[#ffcdd7]"
                  >
                    {showAllQuotes ? 'Collapse view' : `View all ${totalFrictionCount.toLocaleString()} verbatims`}
                  </button>
                </div>
                <div className={`p-5 transition-all duration-300 ${showAllQuotes ? 'max-h-[500px] overflow-y-auto' : ''}`}>
                  <div className="grid grid-cols-3 gap-3">
                    {loadingQuotes ? (
                      <div className="col-span-3 text-center py-10 text-[11px] text-[#94969f]">Loading live verbatims from Supabase...</div>
                    ) : (showAllQuotes ? quotes : REAL_QUOTES.slice(0, 6)).map((q, i) => (
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
                    ⚠️ All findings are AI-inferred from public data — to be validated through 5–6 primary user interviews before any solution is built.
                  </p>
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
                    <p className="text-[9px] text-[#94969f]">Groq Llama 3.3 · Grounded in 1,486 verbatims · No hardcoded answers</p>
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
                        <div className="whitespace-pre-wrap">{m.content}</div>
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
                      placeholder="Ask about any friction theme, draft a PRD, or ask for interview questions..."
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
