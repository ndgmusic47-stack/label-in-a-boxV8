import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { api } from '../utils/api';

export default function AnalyticsDashboard({ sessionId, voice, onClose }) {
  const [viewMode, setViewMode] = useState('project'); // 'project' or 'dashboard'
  const [loading, setLoading] = useState(false);
  const [projectAnalytics, setProjectAnalytics] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);
  const [insights, setInsights] = useState([]);

  useEffect(() => {
    if (viewMode === 'project' && sessionId) {
      loadProjectAnalytics();
    } else if (viewMode === 'dashboard') {
      loadDashboardAnalytics();
    }
  }, [viewMode, sessionId]);

  const loadProjectAnalytics = async () => {
    setLoading(true);
    try {
      // Phase 2.2: handleResponse extracts data automatically
      const result = await api.getProjectAnalytics(sessionId);
      setProjectAnalytics(result.analytics);
      setInsights(result.insights || []);
      voice.speak('Your project analytics are ready.');
    } catch (err) {
      console.error('Failed to load analytics:', err);
      voice.speak('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const loadDashboardAnalytics = async () => {
    setLoading(true);
    try {
      // Phase 2.2: handleResponse extracts data automatically
      const result = await api.getDashboardAnalytics();
      setDashboardData(result.dashboard);
      setInsights(result.insights || []);
      voice.speak('Your dashboard analytics are ready.');
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      voice.speak('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const renderProjectView = () => {
    if (!projectAnalytics) return null;

    const { streams, revenue, saves, shares, platform_breakdown, engagement_rate } = projectAnalytics;

    return (
      <div className="space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon="📊" label="Total Streams" value={streams?.toLocaleString() || '0'} />
          <StatCard icon="💰" label="Revenue" value={`$${revenue?.toFixed(2) || '0.00'}`} />
          <StatCard icon="💾" label="Saves" value={saves?.toLocaleString() || '0'} />
          <StatCard icon="🔄" label="Shares" value={shares?.toLocaleString() || '0'} />
        </div>

        {/* Engagement Rate */}
        {engagement_rate !== undefined && (
          <div className="bg-gradient-to-r from-blue-900/20 to-purple-900/20 border border-studio-white/10 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-montserrat text-studio-white/60 mb-1">Engagement Rate</p>
                <p className="text-3xl font-bold text-studio-white">{engagement_rate.toFixed(2)}%</p>
              </div>
              <div className="text-5xl">🔥</div>
            </div>
          </div>
        )}

        {/* Platform Breakdown */}
        {platform_breakdown && Object.keys(platform_breakdown).length > 0 && (
          <div className="bg-studio-gray/30 border border-studio-white/10 rounded-lg p-6">
            <h3 className="font-montserrat text-lg text-studio-white mb-4 flex items-center gap-2">
              <span>📱</span> Platform Breakdown
            </h3>
            <div className="space-y-3">
              {Object.entries(platform_breakdown).map(([platform, count]) => {
                const percentage = streams > 0 ? (count / streams) * 100 : 0;
                return (
                  <div key={platform}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="font-poppins text-studio-white/70">{platform}</span>
                      <span className="font-poppins text-studio-white">{count.toLocaleString()} ({percentage.toFixed(1)}%)</span>
                    </div>
                    <div className="w-full bg-studio-gray/50 rounded-full h-2">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${percentage}%` }}
                        className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full"
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderDashboardView = () => {
    if (!dashboardData) return null;

    const { total_streams, total_revenue, total_saves, total_shares, top_tracks, platform_breakdown, total_projects } = dashboardData;

    return (
      <div className="space-y-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard icon="🌟" label="Total Streams" value={total_streams?.toLocaleString() || '0'} color="blue" />
          <StatCard icon="💎" label="Total Revenue" value={`$${total_revenue?.toFixed(2) || '0.00'}`} color="green" />
          <StatCard icon="🎵" label="Total Tracks" value={total_projects?.toString() || '0'} color="purple" />
          <StatCard icon="💾" label="Total Saves" value={total_saves?.toLocaleString() || '0'} color="pink" />
        </div>

        {/* Top Tracks */}
        {top_tracks && top_tracks.length > 0 && (
          <div className="bg-studio-gray/30 border border-studio-white/10 rounded-lg p-6">
            <h3 className="font-montserrat text-lg text-studio-white mb-4 flex items-center gap-2">
              <span>🏆</span> Top Tracks
            </h3>
            <div className="space-y-3">
              {top_tracks.slice(0, 5).map((track, index) => (
                <div key={track.session_id || index} className="flex items-center justify-between bg-studio-gray/20 rounded-lg p-3">
                  <div className="flex items-center gap-3">
                    <div className="text-2xl font-bold text-studio-white/40">#{index + 1}</div>
                    <div>
                      <p className="font-montserrat text-studio-white">{track.title}</p>
                      <p className="font-poppins text-xs text-studio-white/60">{track.streams.toLocaleString()} streams</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-poppins text-sm text-green-400">${track.revenue.toFixed(2)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Platform Distribution */}
        {platform_breakdown && Object.keys(platform_breakdown).length > 0 && (
          <div className="bg-studio-gray/30 border border-studio-white/10 rounded-lg p-6">
            <h3 className="font-montserrat text-lg text-studio-white mb-4 flex items-center gap-2">
              <span>🌐</span> Platform Distribution
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {Object.entries(platform_breakdown).map(([platform, count]) => (
                <div key={platform} className="bg-studio-gray/20 rounded-lg p-4 text-center">
                  <p className="font-poppins text-sm text-studio-white/60 mb-1">{platform}</p>
                  <p className="font-montserrat text-2xl text-studio-white">{count.toLocaleString()}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-studio-dark/95 backdrop-blur-sm z-50 overflow-y-auto"
    >
      <div className="min-h-screen p-8">
        {/* Header */}
        <div className="max-w-6xl mx-auto mb-8">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h1 className="text-4xl font-montserrat text-studio-white mb-2 flex items-center gap-3">
                <span>📊</span> Analytics Dashboard
              </h1>
              <p className="font-poppins text-studio-white/60">Track your performance with Pulse AI</p>
            </div>
            <button
              onClick={onClose}
              className="text-studio-white/60 hover:text-studio-white text-3xl transition-colors"
            >
              ×
            </button>
          </div>

          {/* View Toggle */}
          <div className="flex gap-4 mb-6">
            <button
              onClick={() => setViewMode('project')}
              className={`px-6 py-3 rounded-lg font-montserrat transition-all ${
                viewMode === 'project'
                  ? 'bg-blue-600 text-white'
                  : 'bg-studio-gray/50 text-studio-white/60 hover:bg-studio-gray'
              }`}
            >
              📈 Current Project
            </button>
            <button
              onClick={() => setViewMode('dashboard')}
              className={`px-6 py-3 rounded-lg font-montserrat transition-all ${
                viewMode === 'dashboard'
                  ? 'bg-purple-600 text-white'
                  : 'bg-studio-gray/50 text-studio-white/60 hover:bg-studio-gray'
              }`}
            >
              🌟 All Projects
            </button>
          </div>

          {/* AI Insights */}
          {insights && insights.length > 0 && (
            <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border border-purple-500/30 rounded-lg p-6 mb-6">
              <h3 className="font-montserrat text-lg text-studio-white mb-3 flex items-center gap-2">
                <span>🤖</span> Pulse AI Insights
              </h3>
              <div className="space-y-2">
                {insights.map((insight, index) => (
                  <p key={index} className="font-poppins text-studio-white/80">
                    {insight}
                  </p>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="max-w-6xl mx-auto">
          {loading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin text-6xl mb-4">📊</div>
              <p className="font-montserrat text-studio-white/60">Loading analytics...</p>
            </div>
          ) : (
            viewMode === 'project' ? renderProjectView() : renderDashboardView()
          )}
        </div>
      </div>
    </motion.div>
  );
}

function StatCard({ icon, label, value, color = 'blue' }) {
  const colorMap = {
    blue: 'from-blue-900/20 to-blue-700/20 border-blue-500/30',
    green: 'from-green-900/20 to-green-700/20 border-green-500/30',
    purple: 'from-purple-900/20 to-purple-700/20 border-purple-500/30',
    pink: 'from-pink-900/20 to-pink-700/20 border-pink-500/30',
  };

  return (
    <motion.div
      initial={{ scale: 0.9, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={`bg-gradient-to-br ${colorMap[color]} border rounded-lg p-6`}
    >
      <div className="text-4xl mb-2">{icon}</div>
      <p className="text-sm font-montserrat text-studio-white/60 mb-1">{label}</p>
      <p className="text-2xl font-bold text-studio-white">{value}</p>
    </motion.div>
  );
}
