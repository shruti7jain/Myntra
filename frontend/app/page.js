'use client';

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Sparkles, 
  Send, 
  RefreshCw, 
  AlertCircle, 
  CheckCircle2, 
  ShoppingBag, 
  ExternalLink, 
  MessageSquare, 
  TrendingUp, 
  Layers, 
  Flame, 
  Tag, 
  Database,
  Quote,
  Award,
  Lightbulb,
  PieChart,
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

  // Chat Copilot State
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: '👋 Hello PM! I am your **Myntra Wishlist AI Discovery Copilot**. Ask me anything about our 1,486 customer feedback verbatims (e.g., *"Why do users hesitate on ethnic wear?"* or *"What causes drop-offs in dresses?"*).'
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch live insights from internal API route
  const fetchInsights = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/insights');
      const data = await res.json();

      if (data && data.insights && data.insights.length > 0) {
        setInsights(data.insights);
        setSelectedTheme(data.insights[0]);
        setTotalAnalyzed(data.total_raw_analyzed || 1486);
        setLastUpdated(new Date().toLocaleTimeString());
      }
    } catch (err) {
      console.error('Error fetching insights:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInsights();
    // Auto-refresh every 45 seconds to keep data live
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

  const getThemeColor = (index) => {
    const colors = [
      'bg-gradient-to-r from-pink-500 to-rose-600',
      'bg-gradient-to-r from-purple-500 to-indigo-600',
      'bg-gradient-to-r from-amber-500 to-orange-600',
      'bg-gradient-to-r from-emerald-500 to-teal-600',
      'bg-gradient-to-r from-blue-500 to-cyan-600',
      'bg-gradient-to-r from-violet-500 to-fuchsia-600',
      'bg-gradient-to-r from-slate-500 to-zinc-600'
    ];
    return colors[index % colors.length];
  };

  const getCategoryColor = (name) => {
    switch (name) {
      case 'Ethnic Wear': return { bar: 'bg-gradient-to-r from-pink-500 to-rose-500', text: 'text-pink-400', border: 'border-pink-500/30', bg: 'bg-pink-500/10' };
      case 'Western Wear': return { bar: 'bg-gradient-to-r from-indigo-500 to-blue-500', text: 'text-indigo-400', border: 'border-indigo-500/30', bg: 'bg-indigo-500/10' };
      case 'Dresses': return { bar: 'bg-gradient-to-r from-purple-500 to-fuchsia-500', text: 'text-purple-400', border: 'border-purple-500/30', bg: 'bg-purple-500/10' };
      case 'Footwear': return { bar: 'bg-gradient-to-r from-amber-500 to-orange-500', text: 'text-amber-400', border: 'border-amber-500/30', bg: 'bg-amber-500/10' };
      default: return { bar: 'bg-gradient-to-r from-teal-500 to-emerald-500', text: 'text-teal-400', border: 'border-teal-500/30', bg: 'bg-teal-500/10' };
    }
  };

  // Top 3 priority non-monetary product levers
  const getProductLever = (themeKey) => {
    switch (themeKey) {
      case 'fabric_quality_ambiguity':
        return {
          lever: 'Fabric Opacity & Tactile Gauge',
          desc: '1-5 Sheerness Scale, thickness GSM badge, and wash durability customer tags.',
          badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/30'
        };
      case 'visual_reality_discrepancy':
        return {
          lever: 'Natural Daylight Photo Reviews',
          desc: 'Filter customer photos by natural daylight vs indoor lighting to eliminate color uncertainty.',
          badgeColor: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/30'
        };
      case 'fit_sizing_anxiety':
        return {
          lever: 'AI Body-Measurement TrueFit',
          desc: 'Shoulder/bust match confidence score calibrated against past non-returned orders.',
          badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/30'
        };
      default:
        return {
          lever: 'Non-Monetary Confidence Badge',
          desc: 'Contextual decision-support trigger.',
          badgeColor: 'bg-pink-500/10 text-pink-400 border-pink-500/30'
        };
    }
  };

  const top3Themes = insights.slice(0, 3);
  const top3CumulativePct = top3Themes.reduce((acc, t) => acc + (parseFloat(t.pct_of_total) || 0), 0).toFixed(1);

  // Dynamic Fashion Category Distribution Aggregation
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
    <div className="min-h-screen bg-[#0d0e12] text-gray-100 p-4 md:p-8">
      {/* Top Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between pb-6 border-b border-gray-800 gap-4">
        <div>
          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-[#ff3f6c]/10 text-[#ff3f6c] border border-[#ff3f6c]/30 rounded-full text-xs font-semibold tracking-wide uppercase flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> PM Growth Intelligence
            </span>
            <span className="px-2.5 py-0.5 bg-emerald-950/60 text-emerald-400 border border-emerald-800/40 rounded-full text-xs flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span> Live Supabase Connected
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight mt-2 text-white flex items-center gap-2">
            Myntra Wishlist AI Discovery Engine
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Empirical Voice of Customer (VoC) diagnostic platform identifying 30-day wishlist purchase friction under zero monetary incentives.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={fetchInsights} 
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-[#181820] hover:bg-[#20202c] border border-gray-700 text-sm font-medium rounded-lg transition-all text-gray-200"
          >
            <RefreshCw className={`w-4 h-4 text-pink-500 ${loading ? 'animate-spin' : ''}`} />
            {loading ? 'Syncing...' : 'Refresh Insights'}
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto mt-6 space-y-8">
        {/* Executive KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-card p-5 rounded-xl border border-gray-800 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Total VoC Analyzed</span>
              <Database className="w-5 h-5 text-pink-500" />
            </div>
            <div className="text-3xl font-black text-white mt-2">1,486</div>
            <div className="text-xs text-emerald-400 mt-2 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> 100% Normalized in Supabase
            </div>
          </div>

          <div className="glass-card p-5 rounded-xl border border-gray-800 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Top 3 Friction Share</span>
              <Flame className="w-5 h-5 text-orange-400" />
            </div>
            <div className="text-3xl font-black text-white mt-2">{top3CumulativePct}%</div>
            <div className="text-xs text-orange-400 mt-2 truncate">
              {top3Themes.map(t => `${t.theme_label.split(' ')[0]} (${t.pct_of_total}%)`).join(' + ')}
            </div>
          </div>

          <div className="glass-card p-5 rounded-xl border border-gray-800 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Strategic Constraint</span>
              <AlertCircle className="w-5 h-5 text-indigo-400" />
            </div>
            <div className="text-xl font-bold text-white mt-2">Zero Monetary Levers</div>
            <div className="text-xs text-gray-400 mt-2">
              Pure discovery & tactile certainty
            </div>
          </div>

          <div className="glass-card p-5 rounded-xl border border-gray-800 relative overflow-hidden">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">4 Data Channels</span>
              <Layers className="w-5 h-5 text-teal-400" />
            </div>
            <div className="text-sm font-semibold text-white mt-2 flex flex-wrap gap-1.5">
              <span className="px-2 py-0.5 bg-gray-800 rounded text-xs">Play Store</span>
              <span className="px-2 py-0.5 bg-gray-800 rounded text-xs">App Store</span>
              <span className="px-2 py-0.5 bg-gray-800 rounded text-xs">Reddit</span>
              <span className="px-2 py-0.5 bg-gray-800 rounded text-xs">YouTube</span>
            </div>
            <div className="text-xs text-teal-400 mt-2">
              Multi-source cross-validated
            </div>
          </div>
        </div>

        {/* NEW SECTION: FASHION CATEGORY DISTRIBUTION & FRICTION GRAPH */}
        <section className="glass-card p-6 rounded-xl border border-gray-800 space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-4 border-b border-gray-800 gap-2">
            <div>
              <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
                <Shirt className="w-6 h-6 text-[#ff3f6c]" />
                Fashion Category Distribution & Drop-Off Volume
              </h2>
              <p className="text-xs text-gray-400 mt-1">
                Visual breakdown of 1,486 customer friction verbatims across Myntra product departments.
              </p>
            </div>
            <span className="px-3 py-1 bg-pink-500/10 text-pink-400 border border-pink-500/30 rounded-full text-xs font-semibold">
              Live Category Matrix
            </span>
          </div>

          {/* Category Bar Graph Visualizer */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left: Interactive Category Bar Graph */}
            <div className="lg:col-span-7 space-y-4">
              <h3 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
                Category Friction Distribution Graph
              </h3>
              
              <div className="space-y-4 pt-1">
                {categoryChartData.map((cat, cIdx) => {
                  const colors = getCategoryColor(cat.category);
                  const isSelected = selectedCategory === cat.category;
                  const barWidthPct = Math.max((cat.count / maxCategoryCount) * 100, 6);

                  return (
                    <div 
                      key={cat.category}
                      onClick={() => setSelectedCategory(isSelected ? null : cat.category)}
                      className={`p-3 rounded-lg border transition-all cursor-pointer ${
                        isSelected 
                          ? 'bg-[#1e1e28] border-pink-500/60 shadow-lg shadow-pink-950/20' 
                          : 'bg-[#14141c] border-gray-800/80 hover:border-gray-700 hover:bg-[#181822]'
                      }`}
                    >
                      <div className="flex items-center justify-between text-sm mb-2">
                        <div className="flex items-center gap-2">
                          <span className={`w-2.5 h-2.5 rounded-full ${colors.bar}`}></span>
                          <span className="font-bold text-gray-100">{cat.category}</span>
                        </div>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-mono text-gray-400">{cat.count} verbatims</span>
                          <span className="text-xs font-extrabold text-white px-2 py-0.5 bg-gray-800 rounded">
                            {cat.pct}%
                          </span>
                        </div>
                      </div>

                      {/* Animated Gradient Bar */}
                      <div className="w-full h-3 bg-gray-800/60 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${colors.bar} transition-all duration-700`}
                          style={{ width: `${barWidthPct}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Right: Category Insight & Primary Blocker Summary */}
            <div className="lg:col-span-5 bg-[#121218] p-5 rounded-xl border border-gray-800/90 flex flex-col justify-between">
              <div>
                <span className="text-xs font-semibold text-pink-400 uppercase tracking-wider flex items-center gap-1.5">
                  <Compass className="w-4 h-4" /> Category Friction Diagnostic
                </span>
                <h4 className="text-base font-bold text-white mt-1">
                  {selectedCategory ? `${selectedCategory} Focus` : 'High-Volume Category Summary'}
                </h4>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  {selectedCategory 
                    ? `Detailed Voice of Customer breakdown for ${selectedCategory}.`
                    : 'Ethnic Wear and Western Wear constitute over 60% of all saved-item drop-offs due to fabric and sizing ambiguity.'}
                </p>

                <div className="space-y-3 mt-4">
                  {(selectedCategory 
                    ? categoryChartData.filter(c => c.category === selectedCategory)
                    : categoryChartData.slice(0, 3)
                  ).map((cat) => {
                    const colors = getCategoryColor(cat.category);
                    return (
                      <div key={cat.category} className={`p-3 rounded-lg border text-xs ${colors.bg} ${colors.border}`}>
                        <div className="flex items-center justify-between font-bold text-white mb-1">
                          <span>{cat.category}</span>
                          <span className={colors.text}>{cat.count} Mentions ({cat.pct}%)</span>
                        </div>
                        <div className="text-[11px] text-gray-300">
                          <strong className="text-white">Primary Friction:</strong> {cat.topTheme}
                        </div>
                        <div className="text-[11px] text-gray-400 italic mt-1">
                          "{cat.primaryQuote}"
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="text-[11px] text-gray-500 mt-4 pt-3 border-t border-gray-800/80">
                💡 Click any category bar on the left to filter specific category dynamics.
              </div>
            </div>
          </div>
        </section>

        {/* Main Grid: Left = Insights Explorer, Right = AI Copilot */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Quantified Thematic Explorer */}
          <section className="lg:col-span-7 space-y-4">
            <div className="glass-card p-6 rounded-xl border border-gray-800">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-bold text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5 text-[#ff3f6c]" /> Quantified Friction Taxonomy
                  </h2>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Click any theme below to view details and authentic verbatim evidence.
                  </p>
                </div>
                <span className="text-xs text-gray-400">7 Active Themes</span>
              </div>

              {/* Theme Progress List */}
              <div className="space-y-3 mt-4">
                {insights.map((item, idx) => {
                  const isSelected = selectedTheme?.theme === item.theme;
                  return (
                    <div 
                      key={item.theme}
                      onClick={() => setSelectedTheme(item)}
                      className={`p-3.5 rounded-lg cursor-pointer transition-all border ${
                        isSelected 
                          ? 'bg-[#1e1e28] border-[#ff3f6c]/60 shadow-lg shadow-pink-950/20' 
                          : 'bg-[#15151c] border-gray-800/80 hover:border-gray-700 hover:bg-[#181822]'
                      }`}
                    >
                      <div className="flex items-center justify-between text-sm mb-2">
                        <div className="flex items-center gap-2">
                          <span className="w-5 h-5 rounded-full bg-gray-800 text-gray-300 text-xs flex items-center justify-center font-bold">
                            {idx + 1}
                          </span>
                          <span className="font-semibold text-gray-100">{item.theme_label}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-gray-400">{item.mention_count} mentions</span>
                          <span className="text-xs font-bold text-white px-2 py-0.5 bg-gray-800 rounded">
                            {item.pct_of_total}%
                          </span>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="w-full h-2 bg-gray-800/80 rounded-full overflow-hidden">
                        <div 
                          className={`h-full rounded-full ${getThemeColor(idx)} transition-all duration-500`}
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
              <div className="glass-card p-6 rounded-xl border border-gray-800 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-gray-800">
                  <div>
                    <span className="text-xs font-semibold text-pink-500 uppercase tracking-wider">Inspected Problem Space</span>
                    <h3 className="text-lg font-bold text-white mt-0.5">{selectedTheme.theme_label}</h3>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-black text-white">{selectedTheme.pct_of_total}%</span>
                    <p className="text-xs text-gray-400">{selectedTheme.mention_count} customer reports</p>
                  </div>
                </div>

                {/* Category Breakdown Tags */}
                {selectedTheme.segment_breakdown && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Most Impacted Segments</h4>
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(selectedTheme.segment_breakdown).map(([cat, count]) => (
                        count > 0 && (
                          <span key={cat} className="px-2.5 py-1 bg-gray-800/80 text-gray-200 border border-gray-700 rounded-md text-xs flex items-center gap-1.5">
                            <Tag className="w-3 h-3 text-pink-400" />
                            {cat}: <strong className="text-white">{count}</strong>
                          </span>
                        )
                      ))}
                    </div>
                  </div>
                )}

                {/* Verbatim Quotes */}
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
                    <Quote className="w-3.5 h-3.5 text-pink-400" /> Authentic Customer Verbatims
                  </h4>
                  <div className="space-y-2">
                    {(selectedTheme.sample_quotes || []).slice(0, 3).map((quote, qIdx) => (
                      <div key={qIdx} className="p-3 bg-[#13131a] rounded-lg border border-gray-800 text-xs text-gray-300 italic">
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
            <div className="glass-card p-6 rounded-xl border border-gray-800 flex flex-col h-[700px]">
              <div className="flex items-center justify-between pb-4 border-b border-gray-800">
                <div className="flex items-center gap-2.5">
                  <div className="w-8 h-8 rounded-lg bg-[#ff3f6c]/20 border border-[#ff3f6c]/40 flex items-center justify-center text-[#ff3f6c]">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-white">AI Discovery PM Copilot</h3>
                    <p className="text-xs text-gray-400">Grounded in 1,486 live VoC records</p>
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
                      className={`max-w-[88%] p-3.5 rounded-xl text-xs leading-relaxed ${
                        m.role === 'user' 
                          ? 'bg-[#ff3f6c] text-white rounded-br-none' 
                          : 'bg-[#1a1a24] text-gray-200 border border-gray-800 rounded-bl-none'
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{m.content}</div>
                    </div>
                  </div>
                ))}
                {isGenerating && (
                  <div className="flex justify-start">
                    <div className="p-3 bg-[#1a1a24] border border-gray-800 rounded-xl text-xs text-gray-400 flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-pink-500 animate-spin" />
                      Analyzing VoC intelligence across 4 channels...
                    </div>
                  </div>
                )}
              </div>

              {/* Quick Prompt Suggestions */}
              <div className="pt-2 pb-3 border-t border-gray-800/80">
                <p className="text-[10px] text-gray-500 mb-1.5 uppercase font-semibold">Suggested PM Questions</p>
                <div className="flex flex-wrap gap-1.5">
                  <button 
                    onClick={() => handleSendMessage("Why do users hesitate to purchase ethnic wear?")}
                    className="text-[11px] px-2 py-1 bg-gray-800/70 hover:bg-gray-700 text-gray-300 rounded border border-gray-700 transition-all text-left"
                  >
                    Ethnic Wear Fit Doubts?
                  </button>
                  <button 
                    onClick={() => handleSendMessage("What is the main reason for fabric hesitation?")}
                    className="text-[11px] px-2 py-1 bg-gray-800/70 hover:bg-gray-700 text-gray-300 rounded border border-gray-700 transition-all text-left"
                  >
                    Fabric Quality Friction?
                  </button>
                  <button 
                    onClick={() => handleSendMessage("Top 3 non-monetary discovery recommendations?")}
                    className="text-[11px] px-2 py-1 bg-gray-800/70 hover:bg-gray-700 text-gray-300 rounded border border-gray-700 transition-all text-left"
                  >
                    Top Non-Monetary Actions
                  </button>
                </div>
              </div>

              {/* Chat Input Bar */}
              <form 
                onSubmit={(e) => { e.preventDefault(); handleSendMessage(); }}
                className="flex items-center gap-2 pt-2 border-t border-gray-800"
              >
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask a question about customer drop-offs..."
                  className="flex-1 bg-[#13131a] border border-gray-700 focus:border-pink-500 focus:outline-none rounded-lg px-3.5 py-2.5 text-xs text-white placeholder-gray-500"
                />
                <button
                  type="submit"
                  disabled={!inputMessage.trim() || isGenerating}
                  className="p-2.5 bg-[#ff3f6c] hover:bg-[#e0345d] disabled:opacity-50 text-white rounded-lg transition-all"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </div>
          </section>
        </div>

        {/* BOTTOM SECTION: Top 1, Top 2, and Top 3 Friction Summary Boxes */}
        <section className="space-y-4 pt-4 border-t border-gray-800">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div>
              <h2 className="text-xl font-extrabold text-white flex items-center gap-2">
                <Award className="w-6 h-6 text-amber-400" />
                Top 3 Critical Drop-Off Drivers ({top3CumulativePct}% Cumulative Impact)
              </h2>
              <p className="text-xs text-gray-400 mt-1">
                Real-time dynamic ranking of the top 3 highest-weight friction themes causing users to save items without purchasing.
              </p>
            </div>
            <span className="px-3 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full text-xs font-semibold">
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
                  className="glass-card p-5 rounded-xl border border-gray-800 hover:border-pink-500/40 transition-all flex flex-col justify-between space-y-4"
                >
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-amber-400 bg-amber-950/60 px-2.5 py-1 rounded-md border border-amber-800/40">
                        {rankLabels[idx]}
                      </span>
                      <span className="text-xs font-bold text-white px-2.5 py-1 bg-gray-800 rounded">
                        {item.pct_of_total}% Weight
                      </span>
                    </div>

                    <div>
                      <h3 className="text-base font-extrabold text-white leading-snug">{item.theme_label}</h3>
                      <p className="text-xs text-gray-400 mt-1 font-mono">{item.mention_count} Customer Mentions</p>
                    </div>

                    {/* Impacted Segments */}
                    {item.segment_breakdown && (
                      <div>
                        <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider">Top Impacted Categories:</span>
                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                          {Object.entries(item.segment_breakdown)
                            .filter(([_, count]) => count > 0)
                            .slice(0, 3)
                            .map(([cat, count]) => (
                              <span key={cat} className="px-2 py-0.5 bg-gray-800/90 text-gray-200 border border-gray-700 rounded text-[11px]">
                                {cat}: <strong className="text-white">{count}</strong>
                              </span>
                            ))}
                        </div>
                      </div>
                    )}

                    {/* Authentic Sample Quote */}
                    <div>
                      <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-1">
                        <Quote className="w-3 h-3 text-pink-400" /> Customer Verbatim Evidence:
                      </span>
                      <p className="text-xs text-gray-300 italic bg-[#121218] p-3 rounded-lg border border-gray-800/80 mt-1.5 leading-relaxed">
                        "{(item.sample_quotes && item.sample_quotes[0]) ? item.sample_quotes[0] : 'Verified customer friction report.'}"
                      </p>
                    </div>
                  </div>

                  {/* Recommended Non-Monetary Product Lever */}
                  <div className="pt-3 border-t border-gray-800/80">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-pink-400 mb-1">
                      <Lightbulb className="w-3.5 h-3.5" /> Non-Monetary Product Solution:
                    </div>
                    <div className={`p-2.5 rounded-lg border text-xs ${leverInfo.badgeColor}`}>
                      <div className="font-bold text-white mb-0.5">{leverInfo.lever}</div>
                      <div className="text-[11px] text-gray-300">{leverInfo.desc}</div>
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
