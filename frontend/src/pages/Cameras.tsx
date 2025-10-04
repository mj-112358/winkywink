import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Camera as CameraIcon, Wifi, WifiOff, CheckCircle, AlertCircle } from 'lucide-react';
import Card from '../components/ui/Card';
import { config } from '../config';

interface Camera {
  camera_id: string;
  name: string;
  is_entrance: boolean;
  is_active: boolean;
  capabilities: string[];
}

const Cameras: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [cameras, setCameras] = useState<Camera[]>([]);

  useEffect(() => {
    loadCameras();
  }, []);

  const loadCameras = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('auth_token');
      const res = await fetch(`${config.apiBaseUrl}/api/cameras/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setCameras(data);
    } catch (error) {
      console.error('Error loading cameras:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-full bg-bg-subtle">
      <div className="gradient-header px-6 py-8">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold text-text mb-2">Cameras</h1>
          <p className="text-muted">Manage store cameras</p>
        </motion.div>
      </div>

      <div className="px-6 pb-6 -mt-4">
        <Card title="Camera Overview" subtitle={`${cameras.length} cameras`}>
          {loading ? (
            <div className="p-8 text-center">Loading...</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {cameras.map((cam) => (
                <div key={cam.camera_id} className="p-6 border rounded-lg">
                  <div className="flex items-center gap-3 mb-4">
                    <CameraIcon className="h-8 w-8 text-blue-600" />
                    <div>
                      <h3 className="font-semibold">{cam.name}</h3>
                      <p className="text-sm text-gray-500">{cam.camera_id}</p>
                    </div>
                  </div>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Type:</span>
                      <span>{cam.is_entrance ? 'Entrance' : 'Interior'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status:</span>
                      <span className={cam.is_active ? 'text-green-600' : 'text-gray-400'}>
                        {cam.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};

export default Cameras;
