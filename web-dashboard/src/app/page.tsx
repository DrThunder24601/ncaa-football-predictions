'use client';

import { useState, useEffect } from 'react';

interface Prediction {
  Matchup: string;
  Favorite: string;
  Underdog: string;
  'Predicted Difference': string;
  Line: string;
  Edge: string;
}

interface CoverAnalysis {
  Game: string;
  'Our Bet': string;
  Result: string;
}

interface DashboardData {
  predictions: Prediction[];
  coverAnalysis: CoverAnalysis[];
  lastUpdated: string;
}

type Theme = 'dark' | 'light' | 'neon' | 'minimal';

export default function BettingDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [minEdge, setMinEdge] = useState(2.0);
  const [theme, setTheme] = useState<Theme>('dark');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/predictions');
      const result = await response.json();
      setData(result);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-white text-xl">Loading betting data...</div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-red-400 text-xl">Failed to load data</div>
      </div>
    );
  }

  // Filter for betting opportunities
  const bettingOpps = data.predictions
    .filter(pred => pred.Line && pred.Line !== 'N/A' && pred.Line !== 'No Line Available')
    .map(pred => {
      const edge = parseFloat(pred.Edge) || 0;
      const predDiff = parseFloat(pred['Predicted Difference']) || 0;
      const vegasLine = parseFloat(pred.Line) || 0;
      
      let betRec = '';
      let betType = '';
      
      if (edge >= minEdge) {
        if (predDiff > vegasLine) {
          betRec = `Take ${pred.Favorite} -${vegasLine}`;
          betType = 'Favorite';
        } else {
          betRec = `Take ${pred.Underdog} +${vegasLine}`;
          betType = 'Underdog';
        }
      }
      
      // Edge band classification with historical performance
      let confidence, edgeBand, bandEmoji;
      if (edge < 2) {
        edgeBand = "0-2"; bandEmoji = "🔴"; confidence = "Avoid (40%)";
      } else if (edge < 5) {
        edgeBand = "2-5"; bandEmoji = "🟡"; confidence = "Weak (37%)";
      } else if (edge < 7) {
        edgeBand = "5-7"; bandEmoji = "🟢"; confidence = "Good (75%)";
      } else if (edge < 9) {
        edgeBand = "7-9"; bandEmoji = "🔥"; confidence = "Excellent (100%)";
      } else if (edge < 12) {
        edgeBand = "9-12"; bandEmoji = "💎"; confidence = "Strong (60%)";
      } else {
        edgeBand = "12+"; bandEmoji = "👑"; confidence = "Elite (64%)";
      }
      
      return {
        ...pred,
        betRec,
        betType,
        edge,
        confidence,
        vegasLine,
        edgeBand,
        bandEmoji
      };
    })
    .filter(bet => bet.edge >= minEdge)
    .sort((a, b) => b.edge - a.edge);

  // Calculate performance metrics
  const validCoverGames = data.coverAnalysis.filter(game => 
    game.Result === 'WIN' || game.Result === 'LOSS'
  );
  const totalBets = validCoverGames.length;
  const wins = validCoverGames.filter(game => game.Result === 'WIN').length;
  const winRate = totalBets > 0 ? (wins / totalBets) * 100 : 0;

  // Theme configurations
  const themes = {
    dark: {
      bg: 'bg-gray-900',
      cardBg: 'bg-gray-800',
      headerBg: 'bg-gray-800',
      border: 'border-gray-700',
      text: 'text-white',
      textSecondary: 'text-gray-300',
      textMuted: 'text-gray-400',
      accent: 'text-orange-400'
    },
    light: {
      bg: 'bg-white',
      cardBg: 'bg-gray-50',
      headerBg: 'bg-blue-600',
      border: 'border-gray-200',
      text: 'text-gray-900',
      textSecondary: 'text-gray-700',
      textMuted: 'text-gray-500',
      accent: 'text-white'
    },
    neon: {
      bg: 'bg-black',
      cardBg: 'bg-gray-900',
      headerBg: 'bg-purple-900',
      border: 'border-purple-500',
      text: 'text-green-400',
      textSecondary: 'text-cyan-300',
      textMuted: 'text-purple-300',
      accent: 'text-pink-400'
    },
    minimal: {
      bg: 'bg-slate-50',
      cardBg: 'bg-white',
      headerBg: 'bg-slate-800',
      border: 'border-slate-200',
      text: 'text-slate-900',
      textSecondary: 'text-slate-600',
      textMuted: 'text-slate-400',
      accent: 'text-white'
    }
  };

  const currentTheme = themes[theme];

  return (
    <div className={`min-h-screen ${currentTheme.bg} ${currentTheme.text}`}>
      {/* Header */}
      <div className={`${currentTheme.headerBg} border-b ${currentTheme.border} p-8`}>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-4 mb-2">
              <h1 className="text-5xl font-black tracking-tight bg-gradient-to-r from-orange-400 via-red-500 to-yellow-500 bg-clip-text text-transparent">
                CV BETS
              </h1>
              <div className="text-2xl">🏈</div>
            </div>
            <p className={`text-lg ${currentTheme.textSecondary} font-light`}>
              CV Bets: Your Winning Resume Starts Here 📈
            </p>
            <div className="flex items-center gap-4 mt-3">
              <span className={`px-3 py-1 rounded-full text-xs font-bold bg-green-600 text-white`}>
                {winRate.toFixed(1)}% WIN RATE
              </span>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-gradient-to-r from-orange-500 to-yellow-500 text-white">
                LIVE TRACKING
              </span>
            </div>
          </div>
          
          <div className={`text-right ${currentTheme.textMuted}`}>
            <div className="text-sm font-medium">SEASON 2025</div>
            <div className="text-xs">Week {Math.ceil(new Date().getDate() / 7)}</div>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className={`${currentTheme.headerBg} border-b ${currentTheme.border} p-4`}>
        <div className="flex items-center gap-4 flex-wrap">
          <button 
            onClick={fetchData}
            className="bg-gradient-to-r from-orange-500 to-red-500 hover:from-orange-600 hover:to-red-600 px-4 py-2 rounded-lg font-medium text-white shadow-lg"
          >
            🔄 Refresh Data
          </button>
          
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Theme:</label>
            <select 
              value={theme}
              onChange={(e) => setTheme(e.target.value as Theme)}
              className="px-3 py-1 rounded bg-gray-700 text-white border border-gray-600"
            >
              <option value="dark">🌙 Dark</option>
              <option value="light">☀️ Light</option>
              <option value="neon">⚡ Neon</option>
              <option value="minimal">📄 Minimal</option>
            </select>
          </div>
          
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">Minimum Edge:</label>
            <input
              type="range"
              min="0"
              max="10"
              step="0.5"
              value={minEdge}
              onChange={(e) => setMinEdge(parseFloat(e.target.value))}
              className="w-32"
            />
            <span className={`text-sm ${currentTheme.textSecondary}`}>{minEdge}</span>
          </div>
          
          <div className={`ml-auto text-sm ${currentTheme.textMuted}`}>
            Last updated: {new Date(data.lastUpdated).toLocaleTimeString()}
          </div>
        </div>
      </div>

      <div className="p-6">
        {/* Performance Summary */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className={`${currentTheme.cardBg} p-4 rounded-lg border ${currentTheme.border}`}>
            <div className="text-2xl font-bold text-orange-400">{totalBets}</div>
            <div className={`text-sm ${currentTheme.textSecondary}`}>Total Bets</div>
          </div>
          
          <div className={`${currentTheme.cardBg} p-4 rounded-lg border ${currentTheme.border}`}>
            <div className="text-2xl font-bold text-green-400">{wins}</div>
            <div className={`text-sm ${currentTheme.textSecondary}`}>Wins</div>
          </div>
          
          <div className={`${currentTheme.cardBg} p-4 rounded-lg border ${currentTheme.border}`}>
            <div className="text-2xl font-bold text-yellow-400">{winRate.toFixed(1)}%</div>
            <div className={`text-sm ${currentTheme.textSecondary}`}>Win Rate</div>
          </div>
          
          <div className={`${currentTheme.cardBg} p-4 rounded-lg border ${currentTheme.border}`}>
            <div className="text-2xl font-bold text-purple-400">{bettingOpps.length}</div>
            <div className={`text-sm ${currentTheme.textSecondary}`}>Current Opportunities</div>
          </div>
        </div>

        {/* Betting Opportunities */}
        <h2 className="text-2xl font-bold mb-6">🎯 Betting Opportunities (Edge ≥ {minEdge})</h2>
        
        {bettingOpps.length === 0 ? (
          <div className={`${currentTheme.cardBg} p-8 rounded-lg border ${currentTheme.border} text-center`}>
            <div className={currentTheme.textMuted}>No betting opportunities found with edge ≥ {minEdge}</div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {bettingOpps.map((bet, index) => {
              // Determine card styling based on edge band
              let borderColor, bgColor;
              if (bet.edgeBand === '12+') {
                borderColor = 'border-purple-500';
                bgColor = theme === 'neon' ? 'bg-purple-500/10' : 'bg-purple-900/20';
              } else if (bet.edgeBand === '9-12') {
                borderColor = 'border-blue-500';
                bgColor = theme === 'neon' ? 'bg-blue-500/10' : 'bg-blue-900/20';
              } else if (bet.edgeBand === '7-9') {
                borderColor = 'border-red-500';
                bgColor = theme === 'neon' ? 'bg-red-500/10' : 'bg-red-900/20';
              } else if (bet.edgeBand === '5-7') {
                borderColor = 'border-green-500';
                bgColor = theme === 'neon' ? 'bg-green-500/10' : 'bg-green-900/20';
              } else {
                borderColor = 'border-yellow-500';
                bgColor = theme === 'neon' ? 'bg-yellow-500/10' : 'bg-yellow-900/20';
              }
              
              return (
                <div key={index} className={`${currentTheme.cardBg} ${bgColor} ${borderColor} border-2 rounded-xl p-6`}>
                  <h3 className={`text-xl font-bold mb-2 flex items-center gap-2 ${currentTheme.text}`}>
                    <span>{bet.bandEmoji}</span>
                    <span>{bet.betRec}</span>
                  </h3>
                  
                  <p className={`${currentTheme.textSecondary} mb-4`}>{bet.Matchup}</p>
                  
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className={`font-semibold ${currentTheme.textSecondary}`}>Edge</div>
                      <div className={`text-xl font-bold ${currentTheme.text}`}>{bet.edge.toFixed(1)}</div>
                    </div>
                    
                    <div>
                      <div className={`font-semibold ${currentTheme.textSecondary}`}>Band</div>
                      <div className={currentTheme.text}>{bet.edgeBand}</div>
                    </div>
                    
                    <div>
                      <div className={`font-semibold ${currentTheme.textSecondary}`}>Type</div>
                      <div className={currentTheme.text}>{bet.betType}</div>
                    </div>
                    
                    <div>
                      <div className={`font-semibold ${currentTheme.textSecondary}`}>Confidence</div>
                      <div className={currentTheme.text}>{bet.confidence}</div>
                    </div>
                  </div>
                  
                  <div className={`mt-4 pt-4 border-t ${currentTheme.border} text-xs ${currentTheme.textMuted}`}>
                    Our Prediction: {bet.Favorite} -{bet['Predicted Difference']} | Vegas: {bet.vegasLine}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Edge Band Performance Section */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-6">📊 Edge Band Historical Performance</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {[
              { band: "0-2", emoji: "🔴", record: "2-3", pct: "40%", desc: "Avoid" },
              { band: "2-5", emoji: "🟡", record: "3-5", pct: "37%", desc: "Weak" },
              { band: "5-7", emoji: "🟢", record: "3-1", pct: "75%", desc: "Good" },
              { band: "7-9", emoji: "🔥", record: "2-0", pct: "100%", desc: "Excellent" },
              { band: "9-12", emoji: "💎", record: "3-2", pct: "60%", desc: "Strong" },
              { band: "12+", emoji: "👑", record: "9-5", pct: "64%", desc: "Elite" }
            ].map((band, index) => (
              <div key={index} className={`${currentTheme.cardBg} p-4 rounded-lg border ${currentTheme.border} text-center`}>
                <div className="text-2xl mb-2">{band.emoji}</div>
                <div className={`font-bold ${currentTheme.text}`}>{band.band} pts</div>
                <div className={`text-sm ${currentTheme.textSecondary}`}>{band.record}</div>
                <div className={`font-bold ${band.pct === '100%' ? 'text-green-400' : band.pct.startsWith('7') || band.pct.startsWith('6') ? 'text-yellow-400' : 'text-red-400'}`}>
                  {band.pct}
                </div>
                <div className={`text-xs ${currentTheme.textMuted}`}>{band.desc}</div>
              </div>
            ))}
          </div>
          
          <div className={`mt-6 p-4 rounded-lg ${currentTheme.cardBg} border ${currentTheme.border} text-center`}>
            <div className={`text-lg font-bold ${currentTheme.text}`}>
              🏆 Overall Record: 22-16 (57.9%)
            </div>
            <div className={`text-sm ${currentTheme.textMuted} mt-2`}>
              Strategy: Target 5+ point edges • Avoid under 5 points
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}