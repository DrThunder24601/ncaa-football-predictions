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

        // Edge band classification
        let confidence = '';
        let edgeBand = '';
        if (edge >= 12) {
          confidence = 'Elite (71.4%)';
          edgeBand = '12+';
        } else if (edge >= 9) {
          confidence = 'Strong (66.7%)';
          edgeBand = '9-12';
        } else if (edge >= 7) {
          confidence = 'Strong (66.7%)';
          edgeBand = '7-9';
        } else if (edge >= 5) {
          confidence = 'Good (66.7%)';
          edgeBand = '5-7';
        } else if (edge >= 2) {
          confidence = 'Fade (33.3%)';
          edgeBand = '2-5';
        } else {
          confidence = 'Fade (33.3%)';
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
      case '7-9': return '🔥';
      case '5-7': return '🟢';
      case '2-5': return '🟡';
      default: return '🔴';
    }
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

        {/* High-Edge Opportunities */}
        {highEdgeOpps.length > 0 && (
          <div className="bg-white rounded-lg shadow mb-8">
            <div className="px-6 py-4 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">
                🎯 High-Confidence Bets ({highEdgeOpps.length})
              </h2>
              <p className="text-gray-600">5+ point edges with 67%+ historical win rate</p>
            </div>
            <div className="p-6">
              <div className="grid gap-4">
                {highEdgeOpps.map((opp, index) => (
                  <div key={index} className={`border-2 rounded-lg p-4 ${getEdgeBandStyle(opp.edgeBand)}`}>
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-bold text-lg">{getEdgeBandEmoji(opp.edgeBand)} {opp.matchup}</div>
                        <div className="text-lg font-semibold mt-1">{opp.betRecommendation}</div>
                        <div className="text-sm mt-1">{opp.confidence}</div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold">{opp.edge.toFixed(1)}</div>
                        <div className="text-sm">Edge</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* All Betting Opportunities */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-bold text-gray-900">
              📊 All Opportunities ({opportunities.length})
            </h2>
            <p className="text-gray-600">Complete list sorted by edge value</p>
          </div>
          <div className="p-6">
            {opportunities.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                No betting opportunities available
              </div>
            ) : (
              <div className="grid gap-3">
                {opportunities.map((opp, index) => (
                  <div key={index} className="border border-gray-200 rounded-lg p-4 hover:bg-gray-50">
                    <div className="flex justify-between items-center">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <span className="text-lg">{getEdgeBandEmoji(opp.edgeBand)}</span>
                          <span className="font-semibold">{opp.matchup}</span>
                          <span className={`px-2 py-1 rounded text-xs ${getEdgeBandStyle(opp.edgeBand)}`}>
                            {opp.edgeBand}
                          </span>
                        </div>
                        <div className="text-sm text-gray-600 mt-1">
                          {opp.edge >= 2 ? opp.betRecommendation : 'Below betting threshold'}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold text-lg">{opp.edge.toFixed(1)}</div>
                        <div className="text-xs text-gray-500">Edge</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}