import React from 'react';
import AuthTest from '@/components/debug/AuthTest';

export default function DebugPage() {
  return (
    <div className="container mx-auto py-8">
      <h1 className="text-2xl font-bold mb-6">Debug Tools</h1>
      
      <div className="grid gap-6">
        <AuthTest />
      </div>
    </div>
  );
}
