import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Brain,
  Lightbulb,
  TrendingUp,
  AlertTriangle,
  Package,
  Users as UsersIcon,
  ShoppingBag,
  MapPin,
  Calendar
} from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

import Card from '../components/ui/Card';

const Insights: React.FC = () => {
  const [showInsights, setShowInsights] = useState(false);
  const [loading, setLoading] = useState(false);

  // Form inputs
  const [promoName, setPromoName] = useState('');
  const [promoStartDate, setPromoStartDate] = useState('2025-09-28');
  const [promoEndDate, setPromoEndDate] = useState('2025-10-02');
  const [festivalName, setFestivalName] = useState('Dussehra');
  const [festivalDate, setFestivalDate] = useState('2025-10-02');

  const handleGenerate = () => {
    setLoading(true);
    // Simulate processing
    setTimeout(() => {
      setShowInsights(true);
      setLoading(false);
    }, 800);
  };

  // Hardcoded chart data
  const giftsData = [
    { date: 'Sep 28', interactions: 10 },
    { date: 'Sep 29', interactions: 11 },
    { date: 'Sep 30', interactions: 12 },
    { date: 'Oct 1', interactions: 13 },
    { date: 'Oct 2', interactions: 22 }
  ];

  const footfallData = [
    { date: 'Sep 28', footfall: 36 },
    { date: 'Sep 29', footfall: 39 },
    { date: 'Sep 30', footfall: 41 },
    { date: 'Oct 1', footfall: 44 },
    { date: 'Oct 2', footfall: 58 },
    { date: 'Oct 3', footfall: 47 }
  ];

  return (
    <div className="h-full bg-bg-subtle overflow-auto">
      {/* Header */}
      <div className="gradient-header px-6 py-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-text mb-2">AI Insights</h1>
            <p className="text-muted">Actionable recommendations powered by data analysis</p>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="btn-primary flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Generating...
              </>
            ) : (
              <>
                <Brain className="h-4 w-4" />
                Generate Insights
              </>
            )}
          </button>
        </div>
      </div>

      <div className="px-6 pb-6 pt-6">
        {!showInsights ? (
          <div className="space-y-6">
            {/* Input Form */}
            <Card>
              <div className="p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-6">Configure Analysis Parameters</h2>

                <div className="space-y-6">
                  {/* Festival Section */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      Festival Information
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Festival Name
                        </label>
                        <input
                          type="text"
                          value={festivalName}
                          onChange={(e) => setFestivalName(e.target.value)}
                          className="input w-full"
                          placeholder="e.g., Dussehra, Diwali"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Festival Date
                        </label>
                        <input
                          type="date"
                          value={festivalDate}
                          onChange={(e) => setFestivalDate(e.target.value)}
                          className="input w-full"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Promo Section */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <TrendingUp className="h-4 w-4" />
                      Promotion Period (Optional)
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Promotion Name
                        </label>
                        <input
                          type="text"
                          value={promoName}
                          onChange={(e) => setPromoName(e.target.value)}
                          className="input w-full"
                          placeholder="e.g., Flash Sale, Clearance"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          Start Date
                        </label>
                        <input
                          type="date"
                          value={promoStartDate}
                          onChange={(e) => setPromoStartDate(e.target.value)}
                          className="input w-full"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          End Date
                        </label>
                        <input
                          type="date"
                          value={promoEndDate}
                          onChange={(e) => setPromoEndDate(e.target.value)}
                          className="input w-full"
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-800">
                    <strong>Tip:</strong> Add festival dates and promotion periods to get more accurate insights about sales spikes and customer behavior patterns.
                  </p>
                </div>
              </div>
            </Card>

            {/* Preview Card */}
            <div className="bg-white rounded-2xl shadow-lg p-12 text-center">
              <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-6">
                <Lightbulb className="h-10 w-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-3">Ready to Generate Insights</h2>
              <p className="text-gray-600 mb-8">
                Click "Generate Insights" to analyze your store data and receive actionable recommendations.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Insights Cards */}
            <Card
              title="Actionable Insights"
              subtitle="6 recommendations based on your data"
            >
              <div className="space-y-4">
                {/* Insight 1: Festival */}
                <div className="p-4 bg-gray-50 rounded-lg hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                      <AlertTriangle className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">{festivalName} Festival Impact</h3>
                        <span className="px-2 py-1 rounded-full text-xs font-medium border bg-red-100 text-red-700 border-red-200">
                          HIGH
                        </span>
                      </div>
                      <p className="text-gray-600 leading-relaxed">
                        Gifts shelf interactions spiked by 69% on {new Date(festivalDate).toLocaleDateString()} ({festivalName}).
                        Average interactions increased from 12 to 22 during the festival period.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Insight 2: Aisle */}
                <div className="p-4 bg-gray-50 rounded-lg hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                      <MapPin className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">Aisle 2 Footfall Optimization</h3>
                        <span className="px-2 py-1 rounded-full text-xs font-medium border bg-red-100 text-red-700 border-red-200">
                          HIGH
                        </span>
                      </div>
                      <p className="text-gray-600 leading-relaxed">
                        Aisle 2 has seen a 50% increase in footfall (from 30 to 45 visitors). Consider relocating high-margin products
                        or promotional end-caps to this high-traffic area to maximize conversion opportunities.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Insight 3: Inventory */}
                <div className="p-4 bg-gray-50 rounded-lg hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                      <Package className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">Festival Inventory Planning</h3>
                        <span className="px-2 py-1 rounded-full text-xs font-medium border bg-yellow-100 text-yellow-700 border-yellow-200">
                          MEDIUM
                        </span>
                      </div>
                      <p className="text-gray-600 leading-relaxed">
                        Stock Gifts shelf with 2-3x normal inventory levels 3-5 days before upcoming festivals.
                        Current data shows 22 interactions on festival days vs 12 on regular days.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Insight 4: Staffing */}
                <div className="p-4 bg-gray-50 rounded-lg hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                      <UsersIcon className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">Peak Day Staffing</h3>
                        <span className="px-2 py-1 rounded-full text-xs font-medium border bg-yellow-100 text-yellow-700 border-yellow-200">
                          MEDIUM
                        </span>
                      </div>
                      <p className="text-gray-600 leading-relaxed">
                        Deploy +2 staff members near checkout and Gifts area on festival days. Peak footfall (58 people)
                        is 36% above average (43 people).
                      </p>
                    </div>
                  </div>
                </div>

                {/* Insight 5: Cross-sell */}
                <div className="p-4 bg-gray-50 rounded-lg hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                      <ShoppingBag className="h-5 w-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">Cross-Sell Opportunity</h3>
                        <span className="px-2 py-1 rounded-full text-xs font-medium border bg-yellow-100 text-yellow-700 border-yellow-200">
                          MEDIUM
                        </span>
                      </div>
                      <p className="text-gray-600 leading-relaxed">
                        Place Books and Board Games adjacent to or as impulse buys near Gifts shelf. Customers browsing gifts
                        are likely shopping for occasions where complementary products drive higher basket values.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Insight 6: Promo effectiveness */}
                {promoName && (
                  <div className="p-4 bg-gray-50 rounded-lg hover:shadow-md transition-shadow">
                    <div className="flex items-start gap-4">
                      <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg flex items-center justify-center">
                        <TrendingUp className="h-5 w-5 text-white" />
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">{promoName} Promotion Analysis</h3>
                          <span className="px-2 py-1 rounded-full text-xs font-medium border bg-blue-100 text-blue-700 border-blue-200">
                            LOW
                          </span>
                        </div>
                        <p className="text-gray-600 leading-relaxed">
                          The {promoName} promotion from {new Date(promoStartDate).toLocaleDateString()} to {new Date(promoEndDate).toLocaleDateString()}
                          showed moderate effectiveness. Consider extending similar promotions during festival periods for maximum impact.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Gifts Chart */}
              <Card
                title="Festival Impact"
                subtitle="Gifts shelf interaction history"
              >
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={giftsData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="date" stroke="#6b7280" style={{ fontSize: '12px' }} />
                      <YAxis stroke="#6b7280" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e7eb',
                          borderRadius: '0.5rem'
                        }}
                      />
                      <Bar dataKey="interactions" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>

              {/* Footfall Chart */}
              <Card
                title="Footfall Trend"
                subtitle="Daily visitor pattern"
              >
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={footfallData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="date" stroke="#6b7280" style={{ fontSize: '12px' }} />
                      <YAxis stroke="#6b7280" />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#fff',
                          border: '1px solid #e5e7eb',
                          borderRadius: '0.5rem'
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="footfall"
                        stroke="#10b981"
                        strokeWidth={2}
                        dot={{ r: 4, fill: '#10b981' }}
                        activeDot={{ r: 6 }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
            </div>

            {/* Quick Actions */}
            <Card
              title="Quick Actions"
              subtitle="Prioritized next steps"
            >
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 bg-gradient-to-br from-red-50 to-orange-50 rounded-lg border border-red-200">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                    <span className="text-sm font-semibold text-red-900">{festivalName} Festival Impact</span>
                  </div>
                  <p className="text-xs text-red-700 line-clamp-2">
                    Gifts shelf interactions spiked by 69% on {new Date(festivalDate).toLocaleDateString()}.
                  </p>
                </div>
                <div className="p-4 bg-gradient-to-br from-red-50 to-orange-50 rounded-lg border border-red-200">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                    <span className="text-sm font-semibold text-red-900">Aisle 2 Footfall Optimization</span>
                  </div>
                  <p className="text-xs text-red-700 line-clamp-2">
                    Aisle 2 has seen a 50% increase in footfall (from 30 to 45 visitors).
                  </p>
                </div>
                <div className="p-4 bg-gradient-to-br from-red-50 to-orange-50 rounded-lg border border-red-200">
                  <div className="flex items-center gap-2 mb-2">
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                    <span className="text-sm font-semibold text-red-900">Festival Inventory Planning</span>
                  </div>
                  <p className="text-xs text-red-700 line-clamp-2">
                    Stock Gifts shelf with 2-3x normal inventory levels before festivals.
                  </p>
                </div>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Insights;
