"use client"

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { AuthGuard } from "@/components/auth/auth-guard";
import { Upload, ZoomIn, ZoomOut, RotateCw, Download, MessageCircle, Ruler, Pencil, Move, Eraser } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { FloatingChat } from "@/components/workspace-chat/floating-chat";

type PageParams = { id: string };

export default function WorkspacePage({ params }: { params: PageParams }) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [zoomLevel, setZoomLevel] = useState(100);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeTool, setActiveTool] = useState<'select' | 'measure' | 'draw' | 'erase'>('select');
  const [measurements, setMeasurements] = useState<{id: string, type: string, value: string, points: {x: number, y: number}[]}[]>([]);
  const [showMeasurements, setShowMeasurements] = useState(true);
  const [scale, setScale] = useState<string>('1:100');

  // Handle file upload
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      
      // Create a URL for the file
      const fileUrl = URL.createObjectURL(file);
      setPdfUrl(fileUrl);
    }
  };

  // Handle zoom in
  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 10, 200));
  };

  // Handle zoom out
  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 10, 50));
  };

  // Toggle chat
  const toggleChat = () => {
    setIsChatOpen(prev => !prev);
  };

  return (
    <AuthGuard>
      <div className="flex flex-col h-screen bg-gray-100">
        {/* Header */}
        <header className="bg-white border-b border-gray-200 p-4">
          <div className="flex justify-between items-center">
            <h1 className="text-xl font-bold">Engineering Drawing Workspace</h1>
            <div className="flex items-center space-x-2">
              <label htmlFor="file-upload" className="cursor-pointer">
                <div className="flex items-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md">
                  <Upload size={16} />
                  <span>Upload PDF</span>
                </div>
                <Input 
                  id="file-upload" 
                  type="file" 
                  accept=".pdf" 
                  className="hidden" 
                  onChange={handleFileChange} 
                />
              </label>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-hidden">
          {pdfUrl ? (
            <div className="relative h-full">
              {/* Toolbar */}
              <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10 bg-white rounded-lg shadow-md flex items-center p-2 space-x-2">
                <Button variant="outline" size="icon" onClick={handleZoomIn}>
                  <ZoomIn size={16} />
                </Button>
                <span className="text-sm font-medium">{zoomLevel}%</span>
                <Button variant="outline" size="icon" onClick={handleZoomOut}>
                  <ZoomOut size={16} />
                </Button>
                <Separator orientation="vertical" className="h-6" />
                
                {/* Scale selector */}
                <div className="flex items-center space-x-1">
                  <span className="text-xs font-medium">Scale:</span>
                  <select 
                    className="text-xs border rounded px-1 py-0.5"
                    value={scale}
                    onChange={(e) => setScale(e.target.value)}
                  >
                    <option value="1:50">1:50</option>
                    <option value="1:100">1:100</option>
                    <option value="1:200">1:200</option>
                    <option value="1:500">1:500</option>
                    <option value="custom">Custom</option>
                  </select>
                </div>
                
                <Separator orientation="vertical" className="h-6" />
                
                {/* Measurement toggle */}
                <Button 
                  variant={showMeasurements ? "default" : "outline"} 
                  size="sm"
                  className="text-xs"
                  onClick={() => setShowMeasurements(!showMeasurements)}
                  disabled={measurements.length === 0}
                >
                  <Ruler size={14} className="mr-1" />
                  {measurements.length > 0 ? measurements.length : 'No'} measurements
                </Button>
                
                <Separator orientation="vertical" className="h-6" />
                
                <Button variant="outline" size="icon">
                  <RotateCw size={16} />
                </Button>
                <Button variant="outline" size="icon">
                  <Download size={16} />
                </Button>
              </div>

              {/* PDF Viewer */}
              <div className="h-full overflow-auto p-4 flex justify-center">
                <div className="relative" style={{ transform: `scale(${zoomLevel / 100})`, transformOrigin: 'center top' }}>
                  <iframe 
                    src={`${pdfUrl}#toolbar=0&navpanes=0`} 
                    className="border-0 shadow-lg" 
                    width="800" 
                    height="1100"
                  />
                  
                  {/* Measurement overlays will be added dynamically when users create them */}
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full flex flex-col items-center justify-center">
              <Card className="w-full max-w-md">
                <CardContent className="pt-6">
                  <div className="text-center space-y-4">
                    <Upload className="mx-auto h-12 w-12 text-gray-400" />
                    <h3 className="text-lg font-medium">Upload Engineering Drawing</h3>
                    <p className="text-sm text-gray-500">
                      Upload a PDF file of your engineering drawing to get started.
                      You can zoom, pan, and annotate the drawing once uploaded.
                    </p>
                    <label htmlFor="file-upload-main" className="cursor-pointer">
                      <div className="flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md mx-auto w-fit">
                        <Upload size={16} />
                        <span>Select PDF</span>
                      </div>
                      <Input 
                        id="file-upload-main" 
                        type="file" 
                        accept=".pdf" 
                        className="hidden" 
                        onChange={handleFileChange} 
                      />
                    </label>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </main>

        {/* Drawing tools sidebar */}
        {pdfUrl && (
          <div className="fixed left-4 top-1/2 transform -translate-y-1/2 bg-white rounded-lg shadow-lg p-2 flex flex-col space-y-3">
            <Button 
              variant={activeTool === 'select' ? "default" : "ghost"} 
              size="icon" 
              title="Select & Move"
              onClick={() => setActiveTool('select')}
            >
              <Move size={18} />
            </Button>
            <Button 
              variant={activeTool === 'measure' ? "default" : "ghost"} 
              size="icon" 
              title="Measure"
              onClick={() => setActiveTool('measure')}
            >
              <Ruler size={18} />
            </Button>
            <Button 
              variant={activeTool === 'draw' ? "default" : "ghost"} 
              size="icon" 
              title="Draw"
              onClick={() => setActiveTool('draw')}
            >
              <Pencil size={18} />
            </Button>
            <Button 
              variant={activeTool === 'erase' ? "default" : "ghost"} 
              size="icon" 
              title="Erase"
              onClick={() => setActiveTool('erase')}
            >
              <Eraser size={18} />
            </Button>
            <Separator className="my-1" />
            <Button 
              variant={isChatOpen ? "default" : "ghost"} 
              size="icon" 
              title="Chat Assistant" 
              onClick={toggleChat}
            >
              <MessageCircle size={18} />
            </Button>
          </div>
        )}
        
        {/* Floating chat button (only shown when no PDF is loaded) */}
        {!pdfUrl && (
          <Button 
            className="fixed bottom-6 right-6 rounded-full w-12 h-12 shadow-lg" 
            onClick={toggleChat}
          >
            <MessageCircle size={20} />
          </Button>
        )}
        
        {/* Floating chat component */}
        <FloatingChat 
          isOpen={isChatOpen} 
          onClose={() => setIsChatOpen(false)} 
          workspaceId={params.id} 
        />
      </div>
    </AuthGuard>
  );
}
