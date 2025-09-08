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

interface Results {
  [key: string]: string;
}

interface DashboardData {
  predictions: Prediction[];
  coverAnalysis: CoverAnalysis[];
  results: Results[];
  lastUpdated: string;
}

type Theme = 'dark' | 'light' | 'neon' | 'minimal';

export default function BettingDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const minEdge = 2.0; // Fixed threshold, no longer user-adjustable
  const [theme, setTheme] = useState<Theme>('dark');
  const [activeTab, setActiveTab] = useState<'predictions' | 'results' | 'cover-analysis'>('predictions');

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
        edgeBand = "0-2"; bandEmoji = "🔴"; confidence = "Fade (33.3%)";
      } else if (edge < 5) {
        edgeBand = "2-5"; bandEmoji = "🟡"; confidence = "Fade (33.3%)";
      } else if (edge < 7) {
        edgeBand = "5-7"; bandEmoji = "🟢"; confidence = "Good (66.7%)";
      } else if (edge < 9) {
        edgeBand = "7-9"; bandEmoji = "🔥"; confidence = "Strong (66.7%)";
      } else if (edge < 12) {
        edgeBand = "9-12"; bandEmoji = "💎"; confidence = "Strong (66.7%)";
      } else {
        edgeBand = "12+"; bandEmoji = "👑"; confidence = "Elite (71.4%)";
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
          
          
          <div className={`ml-auto text-sm ${currentTheme.textMuted}`}>
            Last updated: {new Date(data.lastUpdated).toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className={`${currentTheme.headerBg} border-b ${currentTheme.border} p-4`}>
        <div className="flex space-x-1">
          <button
            onClick={() => setActiveTab('predictions')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'predictions'
                ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white'
                : `${currentTheme.textSecondary} hover:${currentTheme.text}`
            }`}
          >
            🎯 Predictions
          </button>
          <button
            onClick={() => setActiveTab('results')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'results'
                ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white'
                : `${currentTheme.textSecondary} hover:${currentTheme.text}`
            }`}
          >
            📊 Results
          </button>
          <button
            onClick={() => setActiveTab('cover-analysis')}
            className={`px-6 py-3 rounded-lg font-medium transition-colors ${
              activeTab === 'cover-analysis'
                ? 'bg-gradient-to-r from-orange-500 to-red-500 text-white'
                : `${currentTheme.textSecondary} hover:${currentTheme.text}`
            }`}
          >
            🏈 Cover Analysis
          </button>
        </div>
      </div>

      {/* Tab Content */}
      {activeTab === 'predictions' && (
        <>
      {/* Edge Band Performance Indicators */}
      <div className={`${currentTheme.headerBg} border-b ${currentTheme.border} p-6`}>
        <h2 className="text-2xl font-bold mb-6 text-white">📊 Edge Band Performance Guide</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          {[
            { band: "0-2", emoji: "🔴", record: "9-18", pct: "33.3%", desc: "Fade" },
            { band: "2-5", emoji: "🟡", record: "9-18", pct: "33.3%", desc: "Fade" },
            { band: "5-7", emoji: "🟢", record: "6-3", pct: "66.7%", desc: "Good" },
            { band: "7-9", emoji: "🔥", record: "14-7", pct: "66.7%", desc: "Strong" },
            { band: "9-12", emoji: "💎", record: "4-2", pct: "66.7%", desc: "Strong" },
            { band: "12+", emoji: "👑", record: "5-2", pct: "71.4%", desc: "Elite" }
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
        
        <div className={`p-4 rounded-lg ${currentTheme.cardBg} border ${currentTheme.border} text-center`}>
          <div className={`text-lg font-bold ${currentTheme.text}`}>
            🏆 Overall Strategy: Target 5+ point edges (29-14 overall, 67.4%) | Fade 0-5 edges (18-9 fade, 66.7%)
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

        {/* Collapsible Prediction Bins by Edge Band */}
        <h2 className="text-2xl font-bold mb-6">🎯 Betting Predictions by Confidence</h2>
        
        {(() => {
          // Group predictions by edge band
          const bandGroups: { [key: string]: (Prediction & { edge: number; edgeBand: string; bandEmoji: string; betRec: string; confidence: string; vegasLine: number })[] } = {};
          const bandOrder = ['12+', '9-12', '7-9', '5-7', '2-5', '0-2'];
          
          bettingOpps.forEach(bet => {
            if (!bandGroups[bet.edgeBand]) {
              bandGroups[bet.edgeBand] = [];
            }
            bandGroups[bet.edgeBand].push(bet);
          });
          
          // Also include non-betting opportunities for completeness
          data.predictions
            .filter(pred => pred.Line && pred.Line !== 'N/A' && pred.Line !== 'No Line Available')
            .forEach(pred => {
              const edge = parseFloat(pred.Edge) || 0;
              const edgeBand = edge < 2 ? '0-2' : edge < 5 ? '2-5' : edge < 7 ? '5-7' : edge < 9 ? '7-9' : edge < 12 ? '9-12' : '12+';
              
              if (edge < minEdge) {
                if (!bandGroups[edgeBand]) {
                  bandGroups[edgeBand] = [];
                }
                
                const vegasLine = parseFloat(pred.Line) || 0;
                const bandEmoji = edgeBand === '0-2' ? '🔴' : edgeBand === '2-5' ? '🟡' : edgeBand === '5-7' ? '🟢' : edgeBand === '7-9' ? '🔥' : edgeBand === '9-12' ? '💎' : '👑';
                
                bandGroups[edgeBand].push({
                  ...pred,
                  edge,
                  edgeBand,
                  bandEmoji,
                  betRec: 'Below Threshold',
                  confidence: 'Low Edge',
                  vegasLine
                });
              }
            });
          
          return bandOrder.map(band => {
            if (!bandGroups[band] || bandGroups[band].length === 0) return null;
            
            const games = bandGroups[band].sort((a, b) => b.edge - a.edge);
            const bandInfo = {
              '12+': { emoji: '👑', name: 'Elite', pct: '71.4%', color: 'border-purple-500' },
              '9-12': { emoji: '💎', name: 'Strong', pct: '66.7%', color: 'border-blue-500' },
              '7-9': { emoji: '🔥', name: 'Strong', pct: '66.7%', color: 'border-red-500' },
              '5-7': { emoji: '🟢', name: 'Good', pct: '66.7%', color: 'border-green-500' },
              '2-5': { emoji: '🟡', name: 'Fade', pct: '33.3%', color: 'border-yellow-500' },
              '0-2': { emoji: '🔴', name: 'Fade', pct: '33.3%', color: 'border-red-500' }
            }[band];
            
            return (
              <details key={band} className="mb-4" open={['12+', '9-12', '7-9'].includes(band)}>
                <summary className={`${currentTheme.cardBg} p-4 rounded-lg border ${bandInfo?.color} cursor-pointer hover:opacity-80 transition-opacity`}>
                  <div className="flex items-center justify-between">
                    <span className="text-xl font-bold flex items-center gap-2">
                      {bandInfo?.emoji} {band} Point Edge - {bandInfo?.name} ({bandInfo?.pct})
                    </span>
                    <span className={`text-sm ${currentTheme.textMuted}`}>
                      {games.length} games
                    </span>
                  </div>
                </summary>
                
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {games.map((bet, index) => {
                    const isGoodBet = bet.edge >= minEdge;
                    
                    return (
                      <div key={index} className={`${currentTheme.cardBg} ${isGoodBet ? `${bandInfo?.color} border-2` : `border ${currentTheme.border}`} rounded-lg p-4 ${isGoodBet ? 'shadow-lg' : ''}`}>
                        <h4 className={`font-bold mb-2 flex items-center gap-2 ${currentTheme.text}`}>
                          <span>{bet.bandEmoji}</span>
                          <span>{bet.Matchup}</span>
                        </h4>
                        
                        {isGoodBet && (
                          <div className={`text-lg font-bold mb-2 ${currentTheme.accent}`}>
                            {bet.betRec}
                          </div>
                        )}
                        
                        <div className="grid grid-cols-3 gap-2 text-sm">
                          <div>
                            <div className={`font-semibold ${currentTheme.textSecondary}`}>Edge</div>
                            <div className={currentTheme.text}>{bet.edge.toFixed(1)}</div>
                          </div>
                          
                          <div>
                            <div className={`font-semibold ${currentTheme.textSecondary}`}>Model</div>
                            <div className={currentTheme.text}>{bet['Predicted Difference']}</div>
                          </div>
                          
                          <div>
                            <div className={`font-semibold ${currentTheme.textSecondary}`}>Vegas</div>
                            <div className={currentTheme.text}>{bet.Line}</div>
                          </div>
                        </div>
                        
                        {!isGoodBet && (
                          <div className={`mt-2 text-xs ${currentTheme.textMuted}`}>
                            Below {minEdge} threshold
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </details>
            );
          }).filter(Boolean);
        })()}

        {/* Games by Schedule Order */}
        <h2 className="text-2xl font-bold mb-6 mt-12">📅 Games by Schedule</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.predictions
            .filter(pred => pred.Line && pred.Line !== 'N/A' && pred.Line !== 'No Line Available')
            .map((pred, index) => {
              const edge = parseFloat(pred.Edge) || 0;
              const predDiff = parseFloat(pred['Predicted Difference']) || 0;
              const vegasLine = parseFloat(pred.Line) || 0;
              const edgeBand = edge < 2 ? '0-2' : edge < 5 ? '2-5' : edge < 7 ? '5-7' : edge < 9 ? '7-9' : edge < 12 ? '9-12' : '12+';
              const bandEmoji = edgeBand === '0-2' ? '🔴' : edgeBand === '2-5' ? '🟡' : edgeBand === '5-7' ? '🟢' : edgeBand === '7-9' ? '🔥' : edgeBand === '9-12' ? '💎' : '👑';
              
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
              } else {
                betRec = 'Below Threshold';
                betType = 'Low Edge';
              }
              
              const isGoodBet = edge >= minEdge;
              const bandInfo = {
                '12+': { color: 'border-purple-500' },
                '9-12': { color: 'border-blue-500' },
                '7-9': { color: 'border-red-500' },
                '5-7': { color: 'border-green-500' },
                '2-5': { color: 'border-yellow-500' },
                '0-2': { color: 'border-red-500' }
              }[edgeBand];
              
              return (
                <div key={index} className={`${currentTheme.cardBg} ${isGoodBet ? `${bandInfo?.color} border-2` : `border ${currentTheme.border}`} rounded-lg p-4 ${isGoodBet ? 'shadow-lg' : ''}`}>
                  <h4 className={`font-bold mb-2 flex items-center gap-2 ${currentTheme.text}`}>
                    <span>{bandEmoji}</span>
                    <span>{pred.Matchup}</span>
                  </h4>
                  
                  {isGoodBet && (
                    <div className={`text-lg font-bold mb-2 ${currentTheme.accent}`}>
                      {betRec}
                    </div>
                  )}
                  
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <div className={`font-semibold ${currentTheme.textSecondary}`}>Edge</div>
                      <div className={currentTheme.text}>{edge.toFixed(1)}</div>
                    </div>
                    
                    <div>
                      <div className={`font-semibold ${currentTheme.textSecondary}`}>Model</div>
                      <div className={currentTheme.text}>{pred['Predicted Difference']}</div>
                    </div>
                    
                    <div>
                      <div className={`font-semibold ${currentTheme.textSecondary}`}>Vegas</div>
                      <div className={currentTheme.text}>{pred.Line}</div>
                    </div>
                  </div>
                  
                  {!isGoodBet && (
                    <div className={`mt-2 text-xs ${currentTheme.textMuted}`}>
                      Below 2.0 threshold
                    </div>
                  )}
                </div>
              );
            })}
        </div>

      </div>
        </>
      )}

      {/* Results Tab */}
      {activeTab === 'results' && (
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6">📊 Results</h2>
          <div className={`${currentTheme.cardBg} p-4 rounded-lg border ${currentTheme.border} overflow-x-auto`}>
            <table className="w-full">
              <thead>
                <tr className={`border-b ${currentTheme.border}`}>
                  {data?.results?.[0] && Object.keys(data.results[0]).map((header) => (
                    <th key={header} className={`text-left p-2 ${currentTheme.text} font-semibold`}>
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data?.results?.map((row, index) => (
                  <tr key={index} className={`border-b ${currentTheme.border} hover:opacity-80 transition-opacity`}>
                    {Object.values(row).map((value, cellIndex) => (
                      <td key={cellIndex} className={`p-2 ${currentTheme.textSecondary}`}>
                        {value}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Cover Analysis Tab */}
      {activeTab === 'cover-analysis' && (
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-6">🏈 Cover Analysis (Table View)</h2>
          <div className={`${currentTheme.cardBg} p-4 rounded-lg border ${currentTheme.border} overflow-x-auto`}>
            <table className="w-full">
              <thead>
                <tr className={`border-b ${currentTheme.border}`}>
                  <th className={`text-left p-3 ${currentTheme.text} font-semibold`}>Date</th>
                  <th className={`text-left p-3 ${currentTheme.text} font-semibold`}>Game</th>
                  <th className={`text-left p-3 ${currentTheme.text} font-semibold`}>Our Bet</th>
                  <th className={`text-center p-3 ${currentTheme.text} font-semibold`}>Result</th>
                </tr>
              </thead>
              <tbody>
                {data?.coverAnalysis?.sort((a, b) => {
                  // Sort by date if available, otherwise by game name
                  const aRecord = a as unknown as Record<string, string>;
                  const bRecord = b as unknown as Record<string, string>;
                  const dateA = aRecord.Date || aRecord.date || aRecord.DATE || a.Game;
                  const dateB = bRecord.Date || bRecord.date || bRecord.DATE || b.Game;
                  return String(dateB).localeCompare(String(dateA));
                })?.map((game, index) => (
                  <tr key={index} className={`border-b ${currentTheme.border} hover:opacity-80 transition-opacity`}>
                    <td className={`p-3 ${currentTheme.textSecondary}`}>
                      {(() => {
                        const gameRecord = game as unknown as Record<string, string>;
                        return gameRecord.Date || gameRecord.date || gameRecord.DATE || 'TBD';
                      })()}
                    </td>
                    <td className={`p-3 ${currentTheme.text} font-medium`}>
                      {game.Game}
                    </td>
                    <td className={`p-3 ${currentTheme.textSecondary}`}>
                      {game['Our Bet']}
                    </td>
                    <td className="p-3 text-center">
                      <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                        game.Result === 'WIN' ? 'bg-green-600 text-white' : 
                        game.Result === 'LOSS' ? 'bg-red-600 text-white' : 
                        'bg-gray-600 text-white'
                      }`}>
                        {game.Result}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}