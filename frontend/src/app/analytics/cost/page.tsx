"use client";

export default function CostAnalytics() {
  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Cost Analytics</h1>
        <p className="text-gray-600 mt-2">Track your AI cost optimization savings</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white p-6 rounded-lg shadow border">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Total Savings</h3>
          <p className="text-3xl font-bold text-green-600">67%</p>
          <p className="text-sm text-gray-500">vs direct API costs</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow border">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Monthly Spend</h3>
          <p className="text-3xl font-bold text-blue-600">$1,247</p>
          <p className="text-sm text-gray-500">optimized routing</p>
        </div>
        
        <div className="bg-white p-6 rounded-lg shadow border">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Active Agents</h3>
          <p className="text-3xl font-bold text-purple-600">12</p>
          <p className="text-sm text-gray-500">cost optimized</p>
        </div>
      </div>
      
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">
          📊 <strong>Coming Soon:</strong> Detailed cost analytics dashboard with real-time savings tracking.
        </p>
      </div>
    </div>
  );
}