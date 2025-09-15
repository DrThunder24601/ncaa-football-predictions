'use client';

import { useState, useEffect } from 'react';

interface BettingOpportunity {
  matchup: string;
  favorite: string;
  underdog: string;
  ourLine: number;
  vegasLine: number;
  edge: number;
  betRecommendation: string;
  confidence: string;
  edgeBand: string;
}

interface PerformanceMetrics {
  totalBets: number;
  wins: number;
  losses: number;
  winRate: number;
  currentWeekOpportunities: number;
}

export default function BettingDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [opportunities, setOpportunities] = useState<BettingOpportunity[]>([]);
  const [performance, setPerformance] = useState<PerformanceMetrics>({
    totalBets: 0,
    wins: 0,
    losses: 0,
    winRate: 0,
    currentWeekOpportunities: 0
  });
  const [showPerformance, setShowPerformance] = useState(false);

  useEffect(() => {
    fetchBettingData();
  }, []);

  const fetchBettingData = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/predictions');
      if (!response.ok) {
        throw new Error('Failed to fetch betting data');
      }
      
      const data = await response.json();
      
      // Process predictions into betting opportunities
      const bettingOpps = processPredictions(data.predictions);
      setOpportunities(bettingOpps);
      
      // Calculate performance metrics
      const metrics = calculatePerformance(data.coverAnalysis, bettingOpps.length);
      setPerformance(metrics);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const processPredictions = (predictions: any[]): BettingOpportunity[] => {
    if (!predictions || predictions.length === 0) return [];

    return predictions
      .filter(pred => {
        // Only include games with valid Vegas lines and edges
        return pred.Line && 
               pred.Line !== 'N/A' && 
               pred.Line !== 'No Line Available' &&
               pred.Edge && 
               !isNaN(parseFloat(pred.Edge));
      })
      .map(pred => {
        const edge = parseFloat(pred.Edge) || 0;
        const ourLine = parseFloat(pred['Predicted Difference']) || 0;
        const vegasLine = parseFloat(pred.Line) || 0;

        // Determine bet recommendation
        let betRec = '';
        if (edge >= 2.0) {
          if (ourLine > vegasLine) {
            betRec = `Take ${pred.Favorite} -${vegasLine}`;
          } else {
            betRec = `Take ${pred.Underdog} +${vegasLine}`;
          }
        } else {
          betRec = 'Below threshold';
        }

        // Edge band classification with actual win rates
        let confidence = '';
        let edgeBand = '';
        if (edge >= 12) {
          confidence = 'Elite (58.5%)';
          edgeBand = '12+';
        } else if (edge >= 9) {
          confidence = 'Strong (70.6%)';
          edgeBand = '9-12';
        } else if (edge >= 7) {
          confidence = 'Good (66.7%)';
          edgeBand = '7-9';
        } else if (edge >= 5) {
          confidence = 'Weak (46.2%)';
          edgeBand = '5-7';
        } else if (edge >= 2) {
          confidence = 'Fade (35.7%)';
          edgeBand = '2-5';
        } else {
          confidence = 'Fade (46.7%)';
          edgeBand = '0-2';
        }

        return {
          matchup: pred.Matchup || '',
          favorite: pred.Favorite || '',
          underdog: pred.Underdog || '',
          ourLine,
          vegasLine,
          edge,
          betRecommendation: betRec,
          confidence,
          edgeBand
        };
      })
      .sort((a, b) => b.edge - a.edge); // Sort by edge desc
  };

  const calculatePerformance = (coverAnalysis: any[], currentOpps: number): PerformanceMetrics => {
    if (!coverAnalysis || coverAnalysis.length === 0) {
      return {
        totalBets: 0,
        wins: 0,
        losses: 0,
        winRate: 0,
        currentWeekOpportunities: currentOpps
      };
    }

    const validBets = coverAnalysis.filter(bet => 
      bet.Result === 'WIN' || bet.Result === 'LOSS'
    );

    const wins = validBets.filter(bet => bet.Result === 'WIN').length;
    const losses = validBets.filter(bet => bet.Result === 'LOSS').length;
    const winRate = validBets.length > 0 ? (wins / validBets.length) * 100 : 0;

    return {
      totalBets: validBets.length,
      wins,
      losses,
      winRate,
      currentWeekOpportunities: currentOpps
    };
  };

  const getEdgeBandStyle = (edgeBand: string) => {
    switch (edgeBand) {
      case '12+': return 'bg-purple-100 border-purple-500 text-purple-800';
      case '9-12': return 'bg-blue-100 border-blue-500 text-blue-800';
      case '7-9': return 'bg-red-100 border-red-500 text-red-800';
      case '5-7': return 'bg-green-100 border-green-500 text-green-800';
      case '2-5': return 'bg-yellow-100 border-yellow-500 text-yellow-800';
      default: return 'bg-gray-100 border-gray-500 text-gray-800';
    }
  };

  const getEdgeBandEmoji = (edgeBand: string) => {
    switch (edgeBand) {
      case '12+': return '👑';
      case '9-12': return '💎';
      case '7-9': return '🟢';
      case '5-7': return '🟡';
      case '2-5': return '🔴';
      case '0-2': return '🔴';
      default: return '⚫';
    }
  };

  const getEdgeBandPerformance = (edgeBand: string) => {
    // Updated with actual Cover Analysis data
    const performances = {
      '12+': { record: '24-17', percentage: 58.5 },
      '9-12': { record: '12-5', percentage: 70.6 },
      '7-9': { record: '4-2', percentage: 66.7 },
      '5-7': { record: '6-7', percentage: 46.2 },
      '2-5': { record: '10-18', percentage: 35.7 },
      '0-2': { record: '7-8', percentage: 46.7 }
    };
    return performances[edgeBand] || { record: '0-0', percentage: 0 };
  };

  // Group opportunities by edge band
  const groupedOpportunities = {
    '12+': opportunities.filter(opp => opp.edgeBand === '12+'),
    '9-12': opportunities.filter(opp => opp.edgeBand === '9-12'),
    '7-9': opportunities.filter(opp => opp.edgeBand === '7-9'),
    '5-7': opportunities.filter(opp => opp.edgeBand === '5-7'),
    '2-5': opportunities.filter(opp => opp.edgeBand === '2-5'),
    '0-2': opportunities.filter(opp => opp.edgeBand === '0-2')
  };

  const [expandedBands, setExpandedBands] = useState<{[key: string]: boolean}>({
    '12+': true,
    '9-12': true,
    '7-9': true,
    '5-7': false,
    '2-5': false,
    '0-2': false
  });

  const toggleBand = (band: string) => {
    setExpandedBands(prev => ({
      ...prev,
      [band]: !prev[band]
    }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-500 mx-auto mb-4"></div>
          <div className="text-gray-600 text-lg">Loading betting opportunities...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-xl mb-2">Failed to Load Data</div>
          <div className="text-gray-600 mb-4">{error}</div>
          <button 
            onClick={fetchBettingData}
            className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const highEdgeOpps = opportunities.filter(opp => opp.edge >= 5);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">CV Bets</h1>
              <p className="text-gray-600">Profitable NCAA Football Betting</p>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-right">
                <div className="text-2xl font-bold text-green-600">{performance.winRate.toFixed(1)}%</div>
                <div className="text-sm text-gray-500">Win Rate</div>
              </div>
              <button
                onClick={() => setShowPerformance(!showPerformance)}
                className="bg-gray-100 hover:bg-gray-200 px-3 py-2 rounded text-sm"
              >
                {showPerformance ? 'Hide' : 'Show'} Performance
              </button>
              <button
                onClick={fetchBettingData}
                className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded"
              >
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Performance Section (Collapsible) */}
        {showPerformance && (
          <div className="bg-white rounded-lg shadow mb-8 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Performance Summary</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{performance.totalBets}</div>
                <div className="text-sm text-gray-500">Total Bets</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{performance.wins}</div>
                <div className="text-sm text-gray-500">Wins</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{performance.losses}</div>
                <div className="text-sm text-gray-500">Losses</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{performance.winRate.toFixed(1)}%</div>
                <div className="text-sm text-gray-500">Win Rate</div>
              </div>
            </div>
          </div>
        )}

        {/* Edge Band Organization */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">
              📊 Predictions by Edge Band ({opportunities.length})
            </h2>
            <p className="text-gray-600">Organized by edge size with live win rates</p>
          </div>
          <div className="p-6 space-y-4">
            {opportunities.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No betting opportunities available
              </div>
            ) : (
              <>
                {(['12+', '9-12', '7-9', '5-7', '2-5', '0-2'] as const).map(band => {
                  const bandOpps = groupedOpportunities[band];
                  if (bandOpps.length === 0) return null;

                  const performance = getEdgeBandPerformance(band);
                  const valueBets = bandOpps.filter(opp => opp.edge >= 2.5).length;
                  const isExpanded = expandedBands[band];

                  return (
                    <div key={band} className="border border-gray-200 rounded-lg">
                      {/* Collapsible Header */}
                      <button
                        onClick={() => toggleBand(band)}
                        className="w-full px-4 py-3 flex justify-between items-center hover:bg-gray-50 rounded-t-lg"
                      >
                        <div className="flex items-center space-x-3">
                          <span className="text-2xl">{getEdgeBandEmoji(band)}</span>
                          <div className="text-left">
                            <div className="font-semibold text-gray-900">
                              {band} Point Edge ({performance.record}, {performance.percentage}%)
                            </div>
                            <div className="text-sm text-gray-600">
                              {bandOpps.length} games
                              {valueBets > 0 && (
                                <span className="ml-2 px-2 py-1 bg-green-100 text-green-800 rounded text-xs">
                                  {valueBets} VALUE BETS
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className={`px-3 py-1 rounded text-sm font-medium ${getEdgeBandStyle(band)}`}>
                            {performance.percentage}% Win Rate
                          </div>
                          <div className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
                            ↓
                          </div>
                        </div>
                      </button>

                      {/* Collapsible Content */}
                      {isExpanded && (
                        <div className="border-t border-gray-200 p-4 space-y-3">
                          {bandOpps.map((opp, index) => (
                            <div key={index} className="border border-gray-100 rounded-lg p-3 hover:bg-gray-50">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <div className="font-semibold text-gray-900 mb-1">
                                    {opp.matchup}
                                  </div>
                                  {opp.edge >= 2.5 ? (
                                    <div className="text-green-700 font-medium">
                                      🎯 {opp.betRecommendation}
                                    </div>
                                  ) : (
                                    <div className="text-gray-500">
                                      No betting value (edge too small)
                                    </div>
                                  )}
                                  <div className="text-xs text-gray-500 mt-1">
                                    Model: {opp.ourLine.toFixed(1)} | Vegas: {opp.vegasLine.toFixed(1)}
                                  </div>
                                </div>
                                <div className="text-right ml-4">
                                  <div className="text-xl font-bold text-gray-900">
                                    {opp.edge.toFixed(1)}
                                  </div>
                                  <div className="text-xs text-gray-500">Edge</div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </div>

        {/* Performance Summary */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4 mt-6">
          {(['12+', '9-12', '7-9', '5-7', '2-5', '0-2'] as const).map(band => {
            const performance = getEdgeBandPerformance(band);
            const bandOpps = groupedOpportunities[band];
            
            return (
              <div key={band} className={`p-3 rounded-lg text-center ${getEdgeBandStyle(band)}`}>
                <div className="text-lg font-bold">
                  {getEdgeBandEmoji(band)} {band}
                </div>
                <div className="text-sm mt-1">
                  {performance.record}
                </div>
                <div className="text-sm font-semibold">
                  {performance.percentage}%
                </div>
                <div className="text-xs mt-1">
                  {bandOpps.length} current
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}