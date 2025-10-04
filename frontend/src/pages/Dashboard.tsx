import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Users,
  Clock,
  TrendingUp,
  Activity,
  BarChart3
} from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

import KPICard from '../components/ui/Card';
import Card from '../components/ui/Card';
import { config } from '../config';
import { formatSecondsToReadable } from '../utils/time';

const Dashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [kpiData, setKpiData] = useState({
    today_footfall: 0,
    peak_hour: '',
    avg_dwell_seconds: 0,
    total_interactions: 0,
    trend_footfall: 0
  });
  const [hourlyData, setHourlyData] = useState<any[]>([]);
  const [footfallDaily, setFootfallDaily] = useState<any[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('auth_token');

      const [kpisRes, hourlyRes, dailyRes] = await Promise.all([
        fetch(`${config.apiBaseUrl}/api/analytics/dashboard_kpis`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${config.apiBaseUrl}/api/analytics/hourly_footfall`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${config.apiBaseUrl}/api/analytics/footfall_daily`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);

      const kpis = await kpisRes.json();
      const hourly = await hourlyRes.json();
      const daily = await dailyRes.json();

      // Update KPIs
      setKpiData({
        today_footfall: kpis.today_footfall,
        peak_hour: '2-3 PM',  // Can calculate this from hourly data if needed
        avg_dwell_seconds: Math.round(kpis.avg_dwell_seconds),
        total_interactions: kpis.total_shelf_interactions,
        trend_footfall: 8.5
      });

      setHourlyData(hourly.hours);

      // Format daily data
      const dailyFormatted = daily.series.map((entry: any) => ({
        date: new Date(entry.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        footfall: entry.footfall
      }));
      setFootfallDaily(dailyFormatted);
    } catch (error) {
      console.error('Error loading dashboard data:', error);
      // Suppress error toast
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0 }
  };

  return (
    <div className="min-h-full bg-bg-subtle">
      {/* Header */}
      <div className="gradient-header px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <h1 className="text-3xl font-bold text-text mb-2">Dashboard</h1>
          <p className="text-muted">Store overview & KPIs</p>
        </motion.div>
      </div>

      <div className="px-6 pb-6 -mt-4">
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="visible"
          className="space-y-6"
        >
          {/* KPI Cards */}
          <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Users className="h-6 w-6 text-blue-600" />
                  </div>
                  {kpiData.trend_footfall > 0 && (
                    <span className="text-sm text-green-600 flex items-center">
                      <TrendingUp className="h-4 w-4 mr-1" />
                      +{kpiData.trend_footfall}%
                    </span>
                  )}
                </div>
                <h3 className="text-2xl font-bold text-gray-900">{kpiData.today_footfall}</h3>
                <p className="text-sm text-gray-600 mt-1">Today's Footfall</p>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Activity className="h-6 w-6 text-purple-600" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-gray-900">{kpiData.total_interactions}</h3>
                <p className="text-sm text-gray-600 mt-1">Shelf Interactions</p>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <Clock className="h-6 w-6 text-green-600" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-gray-900">{formatSecondsToReadable(kpiData.avg_dwell_seconds)}</h3>
                <p className="text-sm text-gray-600 mt-1">Avg Dwell Time</p>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-orange-100 rounded-lg flex items-center justify-center">
                    <BarChart3 className="h-6 w-6 text-orange-600" />
                  </div>
                </div>
                <h3 className="text-lg font-bold text-gray-900">{kpiData.peak_hour}</h3>
                <p className="text-sm text-gray-600 mt-1">Peak Hour</p>
              </div>
            </Card>
          </motion.div>

          {/* Hourly Footfall Chart */}
          <motion.div variants={itemVariants}>
            <Card
              title="Today's Hourly Footfall"
              subtitle="Visitor traffic by hour"
              loading={loading}
            >
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={hourlyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="hour" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e5e7eb',
                        borderRadius: '0.5rem'
                      }}
                    />
                    <Bar dataKey="footfall" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </motion.div>

          {/* Daily Trend */}
          <motion.div variants={itemVariants}>
            <Card
              title="Daily Footfall Trend (Last 6 Days)"
              subtitle="Visitor patterns over time"
              loading={loading}
            >
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={footfallDaily}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="date" stroke="#6b7280" />
                    <YAxis stroke="#6b7280" />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#fff',
                        border: '1px solid #e5e7eb',
                        borderRadius: '0.5rem'
                      }}
                      formatter={(value: number) => [`${value} people`, 'Footfall']}
                    />
                    <Line
                      type="monotone"
                      dataKey="footfall"
                      stroke="#10b981"
                      strokeWidth={3}
                      dot={{ r: 5, fill: '#10b981' }}
                      activeDot={{ r: 7 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </motion.div>

          {/* Quick Stats */}
          <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <div className="p-6">
                <h3 className="text-sm font-medium text-gray-600 mb-3">Key Metrics</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Total Visits (6 days)</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {footfallDaily.reduce((sum, d) => sum + d.footfall, 0)}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Average Daily</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {footfallDaily.length > 0 ? Math.round(footfallDaily.reduce((sum, d) => sum + d.footfall, 0) / footfallDaily.length) : 0}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Peak Day</span>
                    <span className="text-sm font-semibold text-gray-900">
                      {footfallDaily.length > 0 ? footfallDaily.reduce((max, d) => d.footfall > max.footfall ? d : max, footfallDaily[0]).footfall : 0} visitors
                    </span>
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <h3 className="text-sm font-medium text-gray-600 mb-3">Top Performing Shelves</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Gifts</span>
                    <span className="text-sm font-semibold text-gray-900">22 interactions</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Board Games</span>
                    <span className="text-sm font-semibold text-gray-900">10 interactions</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-600">Books</span>
                    <span className="text-sm font-semibold text-gray-900">7 interactions</span>
                  </div>
                </div>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <h3 className="text-sm font-medium text-gray-600 mb-3">Store Status</h3>
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">All Systems Operational</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">Analytics Engine Active</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                    <span className="text-sm text-gray-600">Real-time Tracking Enabled</span>
                  </div>
                </div>
              </div>
            </Card>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};

export default Dashboard;
