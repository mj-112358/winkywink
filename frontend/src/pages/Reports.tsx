import React from 'react';
import { motion } from 'framer-motion';
import Card from '../components/ui/Card';

const Reports: React.FC = () => {
  return (
    <div className="min-h-full bg-bg-subtle">
      <div className="gradient-header px-6 py-8">
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold text-text mb-2">Reports</h1>
          <p className="text-muted">Analytics reports</p>
        </motion.div>
      </div>
      <div className="px-6 pb-6 -mt-4">
        <Card title="Reports">
          <div className="p-8 text-center text-gray-500">
            Reports feature coming soon...
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Reports;
