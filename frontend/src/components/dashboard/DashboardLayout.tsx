import React from 'react';

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">
            Cost Optimization Dashboard
          </h1>
          <p className="text-lg text-slate-600">
            Monitor your AI cost savings and optimization performance in real-time
          </p>
        </div>
        
        <div className="space-y-8">
          {children}
        </div>
      </div>
    </div>
  );
}
