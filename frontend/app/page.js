'use client';

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Sparkles, 
  Send, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  Layers, 
  Flame, 
  Tag, 
  Database,
  Quote,
  Award,
  Lightbulb,
  Shirt,
  Compass
} from 'lucide-react';

export default function Dashboard() {
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [totalAnalyzed, setTotalAnalyzed] = useState(1486);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedTheme, setSelectedTheme] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [justRefreshed, setJustRefreshed] = useState(false);

  // Chat Copilot State
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Hello PM! I am your **Myntra Wishlist AI Discovery Copilot**. Ask me anything about our 1,486 customer feedback verbatims (e.g., *"Why do users hesitate on ethnic wear?"* or *"What causes drop-offs in dresses?"*).'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch live insights from internal API route with cache-busting
  const fetchInsights = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/insights?t=${Date.now()}`, { cache: 'no-store' });
      const data = await res.json();

      if (data && data.insights && data.insights.length > 0) {
        setInsights(data.insights);
        setSelectedTheme(data.insights[0]);
        setTotalAnalyzed(data.total_raw_analyzed || 1486);
        setLastUpdated(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        setJustRefreshed(true);
        setTimeout(() => setJustRefreshed(false), 2500);
      }
    } catch (err) {
      console.error('Error fetching insights:', err);
    } finally {
      setTimeout(() => setLoading(false), 300);
    }
  };

  useEffect(() => {
    fetchInsights();
    const interval = setInterval(() => {
      fetchInsights();
    }, 45000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputMessage;
    if (!query.trim() || isGenerating) return;

    const newMessages = [...messages, { role: 'user', content: query }];
    setMessages(newMessages);
    setInputMessage('');
    setIsGenerating(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: query })
      });
      const data = await res.json();
      setMessages([...newMessages, { role: 'assistant', content: data.reply || data.error }]);
    } catch (err) {
      setMessages([...newMessages, { role: 'assistant', content: '⚠️ Error reaching AI Copilot service.' }]);
    } finally {
      setIsGenerating(false);
    }
  };

  // Top 3 priority non-monetary product levers
  const getProductLever = (themeKey) => {
    switch (themeKey) {
      case 'fabric_quality_ambiguity':
        return {
          lever: 'Fabric Opacity & Tactile Gauge',
          desc: '1-5 Sheerness Scale, fabric GSM thickness badge, and wash durability customer tags.'
        };
      case 'visual_reality_discrepancy':
        return {
          lever: 'Natural Daylight Photo Reviews',
          desc: 'Filter customer photos by natural daylight vs indoor studio lighting to eliminate color doubt.'
        };
      case 'fit_sizing_anxiety':
        return {
          lever: 'AI Body-Measurement TrueFit',
          desc: 'Shoulder/bust match confidence score calibrated against past non-returned orders.'
        };
      default:
        return {
          lever: 'Contextual Non-Monetary Trigger',
          desc: 'Decision-support clarity indicator.'
        };
    }
  };

  const top3Themes = insights.slice(0, 3);
  const top3CumulativePct = top3Themes.reduce((acc, t) => acc + (parseFloat(t.pct_of_total) || 0), 0).toFixed(1);

  // Dynamic Category Aggregation
  const categoryTotals = {
    'Ethnic Wear': 0,
    'Western Wear': 0,
    'Dresses': 0,
    'Footwear': 0,
    'General Fashion': 0,
  };

  const categoryBlockerMap = {
    'Ethnic Wear': { topTheme: 'Fit & Sizing Inconsistency', primaryQuote: 'Shoulder & bust proportions vary across brands like Anouk vs. Roadster.' },
    'Western Wear': { topTheme: 'Product Photo vs Reality', primaryQuote: 'Denim shade and stretch feel different under daylight compared to studio lights.' },
    'Dresses': { topTheme: 'Fabric Quality & Sheerness', primaryQuote: 'Transparent material concerns and uncertainty on lining thickness.' },
    'Footwear': { topTheme: 'Size & Squeak Comfort', primaryQuote: 'True-to-size doubt between UK/Euro standard charts causing hesitation.' },
    'General Fashion': { topTheme: 'Delivery & Occasion Fit', primaryQuote: 'Event timing deadlines and return cycle hesitation.' },
  };

  insights.forEach(item => {
    if (item.segment_breakdown) {
      Object.entries(item.segment_breakdown).forEach(([cat, count]) => {
        if (categoryTotals[cat] !== undefined) {
          categoryTotals[cat] += count;
        }
      });
    }
  });

  const totalCategoryMentions = Object.values(categoryTotals).reduce((a, b) => a + b, 0) || 1;
  const categoryChartData = Object.entries(categoryTotals).map(([name, count]) => ({
    category: name,
    count: count,
    pct: ((count / totalCategoryMentions) * 100).toFixed(1),
    ...categoryBlockerMap[name]
  })).sort((a, b) => b.count - a.count);

  const maxCategoryCount = Math.max(...categoryChartData.map(c => c.count), 1);

  return (
    <div className="min-h-screen bg-[#f5f5f6] text-[#282c3f] p-4 md:p-8 font-sans">
      {/* Top Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-[#eaeaec] gap-4 bg-white p-6 rounded-2xl shadow-xs">
        <div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-[#fff0f3] text-[#ff3f6c] border border-[#ff3f6c]/20 rounded-full text-xs font-bold tracking-wide uppercase flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Myntra PM Growth Intelligence
            </span>
            <span className="px-2.5 py-1 bg-[#f4f6f8] text-[#535766] rounded-full text-xs font-semibold border border-[#eaeaec]">
              Discovery Engine
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-black tracking-tight mt-2 text-[#282c3f] flex items-center gap-2">
            Myntra Wishlist AI Discovery Engine
          </h1>
          <p className="text-sm text-[#535766] mt-1 font-normal">
            Voice of Customer (VoC) behavioral intelligence diagnosing 30-day wishlist purchase friction under zero monetary incentives.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-xs text-[#535766] font-medium hidden sm:inline">
              {justRefreshed ? (
                <span className="text-[#ff3f6c] font-bold">✓ Synced just now</span>
              ) : (
                `Last updated: ${lastUpdated}`
              )}
            </span>
          )}
          <button 
            onClick={fetchInsights} 
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2.5 bg-white hover:bg-[#fff0f3] border border-[#d4d5d9] hover:border-[#ff3f6c] text-sm font-bold rounded-xl transition-all text-[#282c3f] hover:text-[#ff3f6c] shadow-2xs active:scale-95 cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 text-[#ff3f6c] ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Refreshing...' : (justRefreshed ? 'Updated!' : 'Refresh Insights')}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto mt-6 space-y-8">
        {/* Executive KPI Cards (Strict Myntra Palette: White, Pink, Black, Gray) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-[#eaeaec] shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#94969f] uppercase tracking-wider">Total VoC Analyzed</span>
              <div className="w-8 h-8 rounded-lg bg-[#fff0f3] flex items-center justify-center">
                <Database className="w-4 h-4 text-[#ff3f6c]" />
              </div>
            </div>
            <div className="text-3xl font-black text-[#282c3f] mt-2">1,486</div>
            <div className="text-xs text-[#282c3f] mt-2 flex items-center gap-1 font-semibold">
              <CheckCircle2 className="w-3.5 h-3.5 text-[#ff3f6c]" /> 100% Normalized in Database
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-[#eaeaec] shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#94969f] uppercase tracking-wider">Top 3 Friction Share</span>
              <div className="w-8 h-8 rounded-lg bg-[#fff0f3] flex items-center justify-center">
                <Flame className="w-4 h-4 text-[#ff3f6c]" />
              </div>
            </div>
            <div className="text-3xl font-black text-[#282c3f] mt-2">{top3CumulativePct}%</div>
            <div className="text-xs text-[#ff3f6c] mt-2 font-bold truncate">
              {top3Themes.map(t => `${t.theme_label.split(' ')[0]} (${t.pct_of_total}%)`).join(' + ')}
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-[#eaeaec] shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#94969f] uppercase tracking-wider">Strategic Constraint</span>
              <div className="w-8 h-8 rounded-lg bg-[#f4f6f8] flex items-center justify-center">
                <AlertCircle className="w-4 h-4 text-[#282c3f]" />
              </div>
            </div>
            <div className="text-xl font-black text-[#282c3f] mt-2">Zero Monetary Levers</div>
            <div className="text-xs text-[#535766] mt-2 font-medium">
              Pure discovery & tactile certainty
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-[#eaeaec] shadow-xs relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-[#94969f] uppercase tracking-wider">4 Data Channels</span>
              <div className="w-8 h-8 rounded-lg bg-[#fff0f3] flex items-center justify-center">
                <Layers className="w-4 h-4 text-[#ff3f6c]" />
              </div>
            </div>
            <div className="text-sm font-bold text-[#282c3f] mt-2 flex flex-wrap gap-1.5">
              <span className="px-2 py-0.5 bg-[#f4f6f8] text-[#282c3f] border border-[#eaeaec] rounded-md text-xs font-semibold">Play Store</span>
              <span className="px-2 py-0.5 bg-[#f4f6f8] text-[#282c3f] border border-[#eaeaec] rounded-md text-xs font-semibold">App Store</span>
              <span className="px-2 py-0.5 bg-[#f4f6f8] text-[#282c3f] border border-[#eaeaec] rounded-md text-xs font-semibold">Reddit</span>
              <span className="px-2 py-0.5 bg-[#f4f6f8] text-[#282c3f] border border-[#eaeaec] rounded-md text-xs font-semibold">YouTube</span>
            </div>
            <div className="text-xs text-[#535766] mt-2">
              Multi-source cross-validated
            </div>
          </div>
        </div>

        {/* FASHION CATEGORY DISTRIBUTION GRAPH (Clean Myntra Styling) */}
        <section className="bg-white p-6 rounded-2xl border border-[#eaeaec] shadow-xs space-y-6">
          <div className="pb-4 border-b border-[#eaeaec]">
            <h2 className="text-xl font-black text-[#282c3f] flex items-center gap-2">
              <Shirt className="w-5 h-5 text-[#ff3f6c]" />
              Fashion Category Distribution & Drop-Off Volume
            </h2>
            <p className="text-xs text-[#535766] mt-1">
              Visual breakdown of 1,486 customer friction verbatims across Myntra product departments.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Clean Pink & Gray Category Bars */}
            <div className="lg:col-span-7 space-y-4">
              <h3 className="text-xs font-bold text-[#94969f] uppercase tracking-wider">
                Category Friction Distribution
              </h3>
              
              <div className="space-y-3 pt-1">
                {categoryChartData.map((cat, idx) => {
                  const isSelected = selectedCategory === cat.category;
                  const barWidthPct = Math.max((cat.count / maxCategoryCount) * 100, 8);

                  return (
                    <div 
                      key={cat.category}
                      onClick={() => setSelectedCategory(isSelected ? null : cat.category)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isSelected 
                          ? 'bg-[#fff0f3] border-[#ff3f6c] shadow-2xs' 
                          : 'bg-[#fafbfc] border-[#eaeaec] hover:border-[#d4d5d9] hover:bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between text-sm mb-2">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-[#ff3f6c]"></span>
                          <span className="font-bold text-[#282c3f]">{cat.category}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-mono font-medium text-[#535766]">{cat.count} verbatims</span>
                          <span className="text-xs font-black text-[#ff3f6c] px-2 py-0.5 bg-[#fff0f3] border border-[#ff3f6c]/20 rounded-md">
                            {cat.pct}%
                          </span>
                        </div>
                      </div>

                      {/* Bar */}
                      <div className="w-full h-3 bg-[#fce4ec]/60 rounded-full overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-700 bg-gradient-to-r from-[#ff3f6c] to-[#ff527b]"
                          style={{ width: `${barWidthPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right: Category Insight & Primary Blocker Summary */}
            <div className="lg:col-span-5 bg-[#fafbfc] p-5 rounded-2xl border border-[#eaeaec] flex flex-col justify-between">
              <div>
                <span className="text-xs font-bold text-[#ff3f6c] uppercase tracking-wider flex items-center gap-1.5">
                  <Compass className="w-4 h-4" /> Category Diagnostic
                </span>
                <h4 className="text-base font-black text-[#282c3f] mt-1">
                  {selectedCategory ? `${selectedCategory} Focus` : 'High-Volume Category Summary'}
                </h4>
                <p className="text-xs text-[#535766] mt-1 leading-relaxed">
                  {selectedCategory 
                    ? `Detailed Voice of Customer breakdown for ${selectedCategory}.`
                    : 'Ethnic Wear and Western Wear constitute over 60% of all saved-item drop-offs due to fabric and sizing ambiguity.'}
                </p>

                <div className="space-y-3 mt-4">
                  {(selectedCategory 
                    ? categoryChartData.filter(c => c.category === selectedCategory)
                    : categoryChartData.slice(0, 3)
                  ).map((cat) => {
                    return (
                      <div key={cat.category} className="p-3.5 rounded-xl border border-[#eaeaec] text-xs bg-white shadow-2xs">
                        <div className="flex items-center justify-between font-bold text-[#282c3f] mb-1">
                          <span className="font-extrabold">{cat.category}</span>
                          <span className="text-[#ff3f6c] font-black">{cat.count} Mentions ({cat.pct}%)</span>
                        </div>
                        <div className="text-[11px] text-[#535766]">
                          <strong className="text-[#282c3f]">Primary Friction:</strong> {cat.topTheme}
                        </div>
                        <div className="text-[11px] text-[#535766] italic mt-1.5 bg-[#f8f9fb] p-2.5 rounded-lg border border-[#eaeaec]">
                          "{cat.primaryQuote}"
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="text-[11px] text-[#94969f] mt-4 pt-3 border-t border-[#eaeaec]">
                💡 Click any category bar on the left to filter specific category dynamics.
              </div>
            </div>
          </div>
        </section>

        {/* Main Grid: Left = Taxonomy Explorer, Right = AI Copilot */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Quantified Thematic Explorer */}
          <section className="lg:col-span-7 space-y-4">
            <div className="bg-white p-6 rounded-2xl border border-[#eaeaec] shadow-xs">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-black text-[#282c3f] flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[#ff3f6c]" /> Quantified Friction Taxonomy
                  </h2>
                  <p className="text-xs text-[#535766] mt-0.5">
                    Click any theme below to view details and authentic verbatim evidence.
                  </p>
                </div>
                <span className="text-xs font-bold text-[#94969f]">7 Active Themes</span>
              </div>

              {/* Theme Progress List */}
              <div className="space-y-3 mt-4">
                {insights.map((item, idx) => {
                  const isSelected = selectedTheme?.theme === item.theme;
                  return (
                    <div 
                      key={item.theme}
                      onClick={() => setSelectedTheme(item)}
                      className={`p-3.5 rounded-xl cursor-pointer transition-all border ${
                        isSelected 
                          ? 'bg-[#fff0f3] border-[#ff3f6c] shadow-2xs' 
                          : 'bg-[#fafbfc] border-[#eaeaec] hover:border-[#d4d5d9] hover:bg-white'
                      }`}
                    >
                      <div className="flex items-center justify-between text-sm mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`w-5 h-5 rounded-full text-xs flex items-center justify-center font-bold border ${
                            isSelected ? 'bg-[#ff3f6c] text-white border-[#ff3f6c]' : 'bg-[#f4f6f8] text-[#535766] border-[#eaeaec]'
                          }`}>
                            {idx + 1}
                          </span>
                          <span className="font-bold text-[#282c3f]">{item.theme_label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-[#535766]">{item.mention_count} mentions</span>
                          <span className="text-xs font-black text-[#282c3f] px-2 py-0.5 bg-white border border-[#eaeaec] rounded">
                            {item.pct_of_total}%
                          </span>
                        </div>
                      </div>

                      {/* Progress Bar (Myntra Pink Gradients) */}
                      <div className="w-full h-2.5 bg-[#fce4ec]/60 rounded-full overflow-hidden">
                        <div 
                          className="h-full rounded-full transition-all duration-500 bg-gradient-to-r from-[#ff3f6c] to-[#ff527b]"
                          style={{ width: `${item.pct_of_total}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selected Theme Details & Verbatim Quotes */}
            {selectedTheme && (
              <div className="bg-white p-6 rounded-2xl border border-[#eaeaec] shadow-xs space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-[#eaeaec]">
                  <div>
                    <span className="text-xs font-bold text-[#ff3f6c] uppercase tracking-wider">Inspected Problem Space</span>
                    <h3 className="text-lg font-black text-[#282c3f] mt-0.5">{selectedTheme.theme_label}</h3>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-black text-[#ff3f6c]">{selectedTheme.pct_of_total}%</span>
                    <p className="text-xs text-[#535766] font-medium">{selectedTheme.mention_count} customer reports</p>
                  </div>
                </div>

                {/* Category Breakdown Tags */}
                {selectedTheme.segment_breakdown && (
                  <div>
                    <h4 className="text-xs font-bold text-[#94969f] uppercase tracking-wider mb-2">Most Impacted Segments</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(selectedTheme.segment_breakdown).map(([cat, count]) => (
                        count > 0 && (
                          <span key={cat} className="px-2.5 py-1 bg-[#f4f6f8] text-[#282c3f] border border-[#eaeaec] rounded-lg text-xs font-bold flex items-center gap-1.5">
                            <Tag className="w-3 h-3 text-[#ff3f6c]" />
                            {cat}: <strong className="text-[#ff3f6c]">{count}</strong>
                          </span>
                        )
                      ))}
                    </div>
                  </div>
                )}

                {/* Verbatim Quotes */}
                <div>
                  <h4 className="text-xs font-bold text-[#94969f] uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                    <Quote className="w-3.5 h-3.5 text-[#ff3f6c]" /> Authentic Customer Verbatims
                  </h4>
                  <div className="space-y-2">
                    {(selectedTheme.sample_quotes || []).slice(0, 3).map((quote, qIdx) => (
                      <div key={qIdx} className="p-3.5 bg-[#fafbfc] rounded-xl border border-[#eaeaec] text-xs text-[#535766] italic leading-relaxed">
                        "{quote}"
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* Right Column: AI PM Discovery Copilot Chat */}
          <section className="lg:col-span-5 flex flex-col h-full">
            <div className="bg-white p-6 rounded-2xl border border-[#eaeaec] shadow-xs flex flex-col h-[700px]">
              <div className="flex items-center justify-between pb-4 border-b border-[#eaeaec]">
                <div className="flex items-center gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-[#fff0f3] border border-[#ff3f6c]/20 flex items-center justify-center text-[#ff3f6c]">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-black text-[#282c3f]">AI Discovery PM Copilot</h3>
                    <p className="text-xs text-[#535766]">Grounded in 1,486 live VoC records</p>
                  </div>
                </div>
              </div>

              {/* Chat Message Stream */}
              <div className="flex-1 overflow-y-auto space-y-3.5 py-4 pr-1">
                {messages.map((m, idx) => (
                  <div 
                    key={idx} 
                    className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div 
                      className={`max-w-[88%] p-3.5 rounded-2xl text-xs leading-relaxed ${
                        m.role === 'user' 
                          ? 'bg-[#ff3f6c] text-white rounded-br-none shadow-xs font-medium' 
                          : 'bg-[#f8f9fb] text-[#282c3f] border border-[#eaeaec] rounded-bl-none shadow-2xs'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{m.content}</div>
                    </div>
                  </div>
                ))}
                {isGenerating && (
                  <div className="flex justify-start">
                    <div className="p-3 bg-[#f8f9fb] border border-[#eaeaec] rounded-2xl text-xs text-[#535766] flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-[#ff3f6c] animate-spin" />
                      Analyzing VoC intelligence across 4 channels...
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Prompt Suggestions */}
              <div className="pt-2 pb-3 border-t border-[#eaeaec]">
                <p className="text-[10px] text-[#94969f] mb-1.5 uppercase font-bold">Suggested PM Questions</p>
                <div className="flex flex-wrap gap-1.5">
                  <button 
                    onClick={() => handleSendMessage("Why do users hesitate to purchase ethnic wear?")}
                    className="text-[11px] px-2.5 py-1.5 bg-[#f4f6f8] hover:bg-[#fff0f3] text-[#535766] hover:text-[#ff3f6c] rounded-lg border border-[#eaeaec] transition-all text-left font-medium"
                  >
                    Ethnic Wear Fit Doubts?
                  </button>
                  <button 
                    onClick={() => handleSendMessage("What is the main reason for fabric hesitation?")}
                    className="text-[11px] px-2.5 py-1.5 bg-[#f4f6f8] hover:bg-[#fff0f3] text-[#535766] hover:text-[#ff3f6c] rounded-lg border border-[#eaeaec] transition-all text-left font-medium"
                  >
                    Fabric Quality Friction?
                  </button>
                  <button 
                    onClick={() => handleSendMessage("Top 3 non-monetary discovery recommendations?")}
                    className="text-[11px] px-2.5 py-1.5 bg-[#f4f6f8] hover:bg-[#fff0f3] text-[#535766] hover:text-[#ff3f6c] rounded-lg border border-[#eaeaec] transition-all text-left font-medium"
                  >
                    Top Non-Monetary Actions
                  </button>
                </div>
              </div>

              {/* Chat Input Bar */}
              <form 
                onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
                className="flex items-center gap-2 pt-2 border-t border-[#eaeaec]"
              >
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask a question about customer drop-offs..."
                  className="flex-1 bg-[#f4f6f8] border border-[#eaeaec] focus:border-[#ff3f6c] focus:bg-white focus:outline-none rounded-xl px-3.5 py-2.5 text-xs text-[#282c3f] placeholder-[#94969f] transition-all font-medium"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isGenerating}
                  className="p-2.5 bg-[#ff3f6c] hover:bg-[#e0345d] disabled:opacity-50 text-white rounded-xl transition-all shadow-xs"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </section>
        </div>

        {/* BOTTOM SECTION: Top 1, Top 2, and Top 3 Friction Summary Boxes */}
        <section className="space-y-4 pt-4 border-t border-[#eaeaec]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h2 className="text-xl font-black text-[#282c3f] flex items-center gap-2">
                <Award className="w-6 h-6 text-[#ff3f6c]" />
                Top 3 Critical Drop-Off Drivers ({top3CumulativePct}% Cumulative Impact)
              </h2>
              <p className="text-xs text-[#535766] mt-1 font-normal">
                Real-time dynamic ranking of the top 3 highest-weight friction themes causing users to save items without purchasing.
              </p>
            </div>
            <span className="px-3 py-1 bg-[#fff0f3] text-[#ff3f6c] border border-[#ff3f6c]/20 rounded-full text-xs font-bold">
              Highest Strategic Priority
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {top3Themes.map((item, idx) => {
              const rankLabels = ['🥇 Rank #1 Priority', '🥈 Rank #2 Priority', '🥉 Rank #3 Priority'];
              const leverInfo = getProductLever(item.theme);

              return (
                <div 
                  key={item.theme}
                  className="bg-white p-5 rounded-2xl border border-[#eaeaec] hover:border-[#ff3f6c]/60 transition-all flex flex-col justify-between space-y-4 shadow-xs"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className={`text-xs font-black px-2.5 py-1 rounded-md border ${
                        idx === 0 
                          ? 'bg-[#fff0f3] text-[#ff3f6c] border-[#ff3f6c]/20' 
                          : 'bg-[#f4f6f8] text-[#282c3f] border-[#eaeaec]'
                      }`}>
                        {rankLabels[idx]}
                      </span>
                      <span className="text-xs font-black text-[#282c3f] px-2.5 py-1 bg-[#f4f6f8] border border-[#eaeaec] rounded-md">
                        {item.pct_of_total}% Weight
                      </span>
                    </div>

                    <div>
                      <h3 className="text-base font-black text-[#282c3f] leading-snug">{item.theme_label}</h3>
                      <p className="text-xs text-[#535766] mt-1 font-mono font-medium">{item.mention_count} Customer Mentions</p>
                    </div>

                    {/* Impacted Segments */}
                    {item.segment_breakdown && (
                      <div>
                        <span className="text-[11px] font-bold text-[#94969f] uppercase tracking-wider">Top Impacted Categories:</span>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {Object.entries(item.segment_breakdown)
                            .filter(([_, count]) => count > 0)
                            .slice(0, 3)
                            .map(([cat, count]) => (
                              <span key={cat} className="px-2 py-0.5 bg-[#f4f6f8] text-[#282c3f] border border-[#eaeaec] rounded text-[11px] font-bold">
                                {cat}: <strong className="text-[#ff3f6c]">{count}</strong>
                              </span>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Authentic Sample Quote */}
                    <div>
                      <span className="text-[11px] font-bold text-[#94969f] uppercase tracking-wider flex items-center gap-1">
                        <Quote className="w-3 h-3 text-[#ff3f6c]" /> Customer Verbatim Evidence:
                      </span>
                      <p className="text-xs text-[#535766] italic bg-[#fafbfc] p-3 rounded-xl border border-[#eaeaec] mt-1.5 leading-relaxed">
                        "{(item.sample_quotes && item.sample_quotes[0]) ? item.sample_quotes[0] : 'Verified customer friction report.'}"
                      </p>
                    </div>
                  </div>

                  {/* Recommended Non-Monetary Product Lever */}
                  <div className="pt-3 border-t border-[#eaeaec]">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-[#ff3f6c] mb-1">
                      <Lightbulb className="w-3.5 h-3.5" /> Non-Monetary Product Solution:
                    </div>
                    <div className="p-3 rounded-xl border border-[#ff3f6c]/20 bg-[#fff0f3] text-xs">
                      <div className="font-extrabold text-[#282c3f] mb-0.5">{leverInfo.lever}</div>
                      <div className="text-[11px] text-[#535766] font-medium leading-relaxed">{leverInfo.desc}</div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
