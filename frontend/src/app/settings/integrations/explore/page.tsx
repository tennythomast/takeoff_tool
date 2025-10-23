"use client"

import React from 'react';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Search, Filter, ArrowLeft } from "lucide-react";
import { useRouter } from 'next/navigation';

export default function ExploreIntegrationsPage() {
  const router = useRouter();
  
  // Sample integration categories for the marketplace
  const categories = [
    { id: 'productivity', name: 'Productivity', count: 24 },
    { id: 'ai', name: 'AI & ML', count: 18 },
    { id: 'development', name: 'Development', count: 32 },
    { id: 'crm', name: 'CRM & Sales', count: 15 },
    { id: 'database', name: 'Databases', count: 12 },
    { id: 'finance', name: 'Finance', count: 8 },
    { id: 'media', name: 'Media', count: 10 },
    { id: 'web', name: 'Web Services', count: 22 },
  ];
  
  return (
    <div className="container mx-auto py-8 px-4">
      <Button 
        variant="ghost" 
        className="mb-6"
        onClick={() => router.push('/settings/integrations')}
      >
        <ArrowLeft size={16} className="mr-2" /> Back to Integrations
      </Button>
      
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Integration Marketplace</h1>
        <p className="text-gray-600 mt-2 text-lg">
          Discover and connect to a wide range of services and tools
        </p>
      </div>
      
      {/* Search and Filter */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-8">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={18} />
          <Input
            placeholder="Search marketplace..."
            className="pl-10"
          />
        </div>
        
        <Button variant="outline">
          <Filter size={16} className="mr-2" /> Filter
        </Button>
      </div>
      
      {/* Categories */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
        {categories.map((category) => (
          <Card key={category.id} className="hover:shadow-md transition-shadow cursor-pointer">
            <CardContent className="p-6">
              <h3 className="text-lg font-semibold mb-2">{category.name}</h3>
              <p className="text-gray-500 mb-4">{category.count} integrations</p>
              <Badge variant="outline">View All</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
      
      <div className="text-center mt-12 mb-8">
        <h2 className="text-2xl font-bold mb-2">Don't see what you're looking for?</h2>
        <p className="text-gray-600 mb-6">
          Request a new integration or build your own custom connector
        </p>
        <div className="flex justify-center gap-4">
          <Button variant="outline">Request Integration</Button>
          <Button>Build Custom Connector</Button>
        </div>
      </div>
    </div>
  );
}
