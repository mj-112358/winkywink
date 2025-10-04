import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart3, Clock, Users, RefreshCw, Camera as CameraIcon } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import Card from '../components/ui/Card';
import { config } from '../config';

const Live: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [cameras, setCameras] = useState<any[]>([]);
  const [todayFootfall, setTodayFootfall] = useState(0);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('auth_token');

      // Load cameras
      const camerasRes = await fetch(`${config.apiBaseUrl}/api/cameras/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const camerasData = await camerasRes.json();
      setCameras(camerasData);

      // Load today's footfall
      const kpisRes = await fetch(`${config.apiBaseUrl}/api/analytics/dashboard_kpis`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const kpis = await kpisRes.json();
      setTodayFootfall(kpis.today_footfall);
    } catch (error) {
      console.error('Error loading live data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-full bg-bg-subtle">
      <div className="gradient-header px-6 py-8">
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-text mb-2">Live Analytics</h1>
              <p className="text-muted">Real-time store monitoring</p>
            </div>
            <button
              onClick={loadData}
              className="px-4 py-2 bg-white text-primary rounded-lg hover:bg-gray-50 flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </motion.div>
      </div>

      <div className="px-6 pb-6 -mt-4">
        <div className="space-y-6">
          {/* KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <Users className="h-6 w-6 text-blue-600" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-gray-900">{todayFootfall}</h3>
                <p className="text-sm text-gray-600 mt-1">Live Footfall Today</p>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                    <CameraIcon className="h-6 w-6 text-green-600" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-gray-900">{cameras.filter(c => c.is_active).length}</h3>
                <p className="text-sm text-gray-600 mt-1">Active Cameras</p>
              </div>
            </Card>

            <Card>
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex-shrink-0 w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
                    <Clock className="h-6 w-6 text-purple-600" />
                  </div>
                </div>
                <h3 className="text-2xl font-bold text-gray-900">Live</h3>
                <p className="text-sm text-gray-600 mt-1">Real-time Tracking</p>
              </div>
            </Card>
          </div>

          {/* Cameras Status */}
          <Card title="Camera Status" subtitle="Live camera feeds">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cameras.map((camera) => (
                <div key={camera.camera_id} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-semibold">{camera.name}</h4>
                    <span className={`px-2 py-1 text-xs rounded ${camera.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {camera.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">
                    {camera.is_entrance ? 'Entrance Camera' : 'Interior Camera'}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Capabilities: {camera.capabilities?.join(', ') || 'N/A'}
                  </p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default Live;
