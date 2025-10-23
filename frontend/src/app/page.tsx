"use client"

import Link from "next/link"
import Image from "next/image"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { ArrowRight, Bot, DollarSign, Shield, Zap, CheckCircle, TrendingDown, Users, Clock, Beaker, BarChart3, Calculator, Mail } from "lucide-react"
import { useState, useEffect, useCallback, useRef } from "react"

export default function Home() {
  const [currentWordIndex, setCurrentWordIndex] = useState(0)
  const [isVisible, setIsVisible] = useState(true)
  const [activeFeature, setActiveFeature] = useState('optimization')
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  const words = ["Intelligent Cost Optimization", "Governance"]
  
  const animateTextChange = useCallback(() => {
    // Fade out current text
    setIsVisible(false)
    
    // After fade out completes, change text and fade in
    timeoutRef.current = setTimeout(() => {
      setCurrentWordIndex((prev) => (prev + 1) % words.length)
      setIsVisible(true)
    }, 300) // Wait for fade out to complete
  }, [words.length])
  
  useEffect(() => {
    // Check for reduced motion preference
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    
    if (prefersReducedMotion) {
      return
    }
    
    // Start the animation cycle
    const startAnimation = () => {
      timeoutRef.current = setTimeout(() => {
        animateTextChange()
        // Set up recurring animation
        const interval = setInterval(animateTextChange, 3000) // Change every 3 seconds
        return () => clearInterval(interval)
      }, 2000) // Initial delay
    }
    
    startAnimation()
    
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [animateTextChange])
  
  return (
    <div 
      className="min-h-screen relative overflow-hidden"
      style={{
        background: [
          'radial-gradient(ellipse 60% 80% at 80% 35%, #3D5B81 0%, transparent 50%)',
          'radial-gradient(ellipse 100% 60% at 40% 80%, #98C0D9 0%, transparent 50%)',
          'radial-gradient(ellipse 120% 80% at 90% 100%, #B8D4E8 0%, transparent 60%)',
          'linear-gradient(180deg, #192026 0%, #192026 20%, #2A3441 40%, #3D5B81 65%, #6B8DB5 85%, #98C0D9 100%)'
        ].join(', ')
      }}
    >
      {/* Animated gradient overlay for subtle movement */}
      <div 
        className="absolute inset-0 opacity-30"
        style={{
          background: `
            radial-gradient(circle 800px at 60% 200px, #3D5B81 0%, transparent 50%),
            radial-gradient(circle 600px at 20% 300px, #98C0D9 0%, transparent 50%),
            radial-gradient(circle 400px at 80% 100px, #192026 0%, transparent 50%)
          `,
          animation: 'gradientShift 20s ease-in-out infinite alternate'
        }}
      />
      
      <style jsx>{`
        @keyframes gradientShift {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          100% {
            transform: translate(30px, -20px) scale(1.05);
          }
        }
      `}</style>
      {/* Navigation */}
      <nav className="" style={{backgroundColor: '#192026'}}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Link href="/" className="flex items-center space-x-2">
                <Image
                  src="/assets/brand/logos/dataelan-logo-primary-dark.svg"
                  alt="Dataelan"
                  width={120}
                  height={40}
                  className="h-8 w-auto"
                />
              </Link>
            </div>
            <div className="flex items-center space-x-4">
              <Link href="/login">
                <Button variant="ghost" className="text-white hover:text-clay-signal hover:bg-white/10">Login</Button>
              </Link>
              <Link href="/signup">
                <Button className="bg-clay-signal hover:bg-clay-signal/90 text-white">Join Beta</Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="px-6 lg:px-8 py-20 lg:py-32 relative">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-4xl lg:text-6xl font-bold text-white mb-12 leading-tight">
            Enterprise AI Platform with<br/>
            <span className="text-clay-signal">
              Intelligent Cost Optimization
            </span>
          </h1>
          
          <p className="text-xl lg:text-2xl text-white/95 mb-16 max-w-4xl mx-auto leading-relaxed font-medium">
            Built-in governance and workspace isolation for teams that need control
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <Button size="lg" className="bg-clay-signal hover:bg-clay-signal/90 text-white text-lg px-8 py-4 rounded-lg shadow-lg">
              Join Beta Program
            </Button>
            <Button 
              size="lg" 
              variant="outline" 
              className="border-2 border-clay-signal text-clay-signal hover:bg-clay-signal/10 hover:border-clay-signal/80 hover:text-clay-signal text-lg px-8 py-4 rounded-lg backdrop-blur-md shadow-lg"
            >
              Request Demo
            </Button>
          </div>
          
          <div className="flex items-center justify-center gap-8 text-sm text-white/90">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-clay-signal" />
              <span>Enterprise Ready</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-clay-signal" />
              <span>Smart Routing</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-4 w-4 text-clay-signal" />
              <span>Data Isolation</span>
            </div>
          </div>
        </div>
      </section>

      {/* Enterprise AI Challenge Section */}
      <section className="py-20 px-6 lg:px-8 relative">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-white mb-6">
              The Enterprise AI Challenge
            </h2>
            <p className="text-xl text-white/90 max-w-3xl mx-auto leading-relaxed">
              Organizations struggle with AI governance and cost control while trying to scale intelligent solutions across teams.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-8 mb-16">
            {/* Governance & Security Card */}
            <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 hover:bg-[#E0E1E1] transition-all duration-300 hover:shadow-xl hover:border-white/30">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-clay-signal/20 flex items-center justify-center">
                  <svg className="w-8 h-8 text-clay-signal" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
                    <path d="M10 17l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-slate-800 mb-4">Governance & Security Gaps</h3>
                <div className="space-y-3 max-w-sm mx-auto">
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                    <span className="text-slate-700 text-left leading-relaxed">Data isolation challenges across teams</span>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                    <span className="text-slate-700 text-left leading-relaxed">Compliance and audit trail gaps</span>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                    <span className="text-slate-700 text-left leading-relaxed">Inconsistent security policies</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Cost & Efficiency Card */}
            <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 hover:bg-[#E0E1E1] transition-all duration-300 hover:shadow-xl hover:border-white/30">
              <CardContent className="p-8 text-center">
                <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-clay-signal/20 flex items-center justify-center">
                  <svg className="w-8 h-8 text-clay-signal" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M7 14l5-5 5 5z"/>
                    <path d="M12 6V2m0 4l-3 3m3-3l3 3m-3-3v4"/>
                  </svg>
                </div>
                <h3 className="text-2xl font-bold text-slate-800 mb-4">Cost & Efficiency Issues</h3>
                <div className="space-y-3 max-w-sm mx-auto">
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                    <span className="text-slate-700 text-left leading-relaxed">Unpredictable AI spending patterns</span>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                    <span className="text-slate-700 text-left leading-relaxed">Inefficient model selection</span>
                  </div>
                  <div className="flex items-start space-x-3">
                    <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                    <span className="text-slate-700 text-left leading-relaxed">Lack of usage optimization</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="py-20 px-6 lg:px-8 relative">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-white mb-6">
              Complete AI Platform for Enterprise Teams
            </h2>
            <p className="text-xl text-white/90 max-w-3xl mx-auto leading-relaxed">
              Professional AI agent platform with built-in cost optimization and enterprise governance
            </p>
          </div>
          
          {/* Interactive Feature Showcase */}
          <div className="relative">
            {/* Feature Navigation Tabs */}
            <div className="flex flex-wrap justify-center gap-4 mb-12">
              <button 
                onClick={() => setActiveFeature('optimization')}
                className={`px-6 py-3 rounded-lg font-semibold transition-all duration-300 ${
                  activeFeature === 'optimization' 
                    ? 'bg-clay-signal text-white shadow-lg scale-105' 
                    : 'bg-white/10 text-white/80 hover:bg-white/20 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                  Cost Optimization
                </div>
              </button>
              
              <button 
                onClick={() => setActiveFeature('governance')}
                className={`px-6 py-3 rounded-lg font-semibold transition-all duration-300 ${
                  activeFeature === 'governance' 
                    ? 'bg-clay-signal text-white shadow-lg scale-105' 
                    : 'bg-white/10 text-white/80 hover:bg-white/20 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
                  </svg>
                  Data Governance
                </div>
              </button>
              
              <button 
                onClick={() => setActiveFeature('collaboration')}
                className={`px-6 py-3 rounded-lg font-semibold transition-all duration-300 ${
                  activeFeature === 'collaboration' 
                    ? 'bg-clay-signal text-white shadow-lg scale-105' 
                    : 'bg-white/10 text-white/80 hover:bg-white/20 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zM4 18v-4h3v4h2v-7.5c0-1.1-.9-2-2-2s-2 .9-2 2V18H4zm9-10c-1.1 0-2 .9-2 2v7.5h2V14h3v4h2v-6.5c0-1.1-.9-2-2-2H13z"/>
                  </svg>
                  Team Collaboration
                </div>
              </button>
              
              <button 
                onClick={() => setActiveFeature('builder')}
                className={`px-6 py-3 rounded-lg font-semibold transition-all duration-300 ${
                  activeFeature === 'builder' 
                    ? 'bg-clay-signal text-white shadow-lg scale-105' 
                    : 'bg-white/10 text-white/80 hover:bg-white/20 hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                  </svg>
                  Visual Builder
                </div>
              </button>
            </div>

            {/* Feature Content Display */}
            <div className="relative min-h-[500px]">
              {/* Data Governance */}
              <div className={`absolute inset-0 transition-all duration-500 ${
                activeFeature === 'governance' 
                  ? 'opacity-100 translate-x-0' 
                  : 'opacity-0 translate-x-8 pointer-events-none'
              }`}>
                <div className="grid lg:grid-cols-2 gap-12 items-center">
                  <div className="space-y-6">
                    <div className="inline-flex items-center gap-3 px-4 py-2 bg-clay-signal/20 rounded-full">
                      <svg className="w-6 h-6 text-clay-signal" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4z"/>
                      </svg>
                      <span className="text-clay-signal font-semibold">Enterprise Security</span>
                    </div>
                    
                    <h3 className="text-3xl lg:text-4xl font-bold text-white mb-4">
                      Complete Data Governance
                    </h3>
                    
                    <p className="text-xl text-white/80 leading-relaxed mb-8">
                      Enterprise-grade security with complete workspace isolation and compliance controls for sensitive data.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Multi-tenant Architecture</h4>
                            <p className="text-sm text-white/70">Isolated environments for each team</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Role-based Access</h4>
                            <p className="text-sm text-white/70">Granular permission controls</p>
                          </div>
                        </div>
                      </div>
                      
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Activity Monitoring</h4>
                            <p className="text-sm text-white/70">Complete audit trails</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Hosted Open Source Models</h4>
                            <p className="text-sm text-white/70">Self-hosted model options</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="relative">
                    <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 p-8 transform hover:scale-105 transition-transform duration-300">
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-slate-800">Security Dashboard</h4>
                          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                        </div>
                        
                        <div className="space-y-4">
                          <div className="flex items-center justify-between p-3 bg-white/50 rounded-lg">
                            <span className="text-sm text-slate-700">Active Workspaces</span>
                            <span className="font-semibold text-slate-800">12</span>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 bg-white/50 rounded-lg">
                            <span className="text-sm text-slate-700">User Permissions</span>
                            <span className="font-semibold text-clay-signal">Configured</span>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 bg-white/50 rounded-lg">
                            <span className="text-sm text-slate-700">Audit Logs</span>
                            <span className="font-semibold text-green-600">Active</span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </div>

              {/* Cost Optimization */}
              <div className={`absolute inset-0 transition-all duration-500 ${
                activeFeature === 'optimization' 
                  ? 'opacity-100 translate-x-0' 
                  : 'opacity-0 translate-x-8 pointer-events-none'
              }`}>
                <div className="grid lg:grid-cols-2 gap-12 items-center">
                  <div className="space-y-6">
                    <div className="inline-flex items-center gap-3 px-4 py-2 bg-clay-signal/20 rounded-full">
                      <svg className="w-6 h-6 text-clay-signal" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                      </svg>
                      <span className="text-clay-signal font-semibold">Smart Routing</span>
                    </div>
                    
                    <h3 className="text-3xl lg:text-4xl font-bold text-white mb-4">
                      Intelligent Cost Optimization
                    </h3>
                    
                    <p className="text-xl text-white/80 leading-relaxed mb-8">
                      Smart model routing with real-time cost tracking that automatically optimizes for performance and budget efficiency.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Auto Model Selection</h4>
                            <p className="text-sm text-white/70">Optimal model for each task</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Real-time Tracking</h4>
                            <p className="text-sm text-white/70">Live cost monitoring</p>
                          </div>
                        </div>
                      </div>
                      
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Budget Optimization</h4>
                            <p className="text-sm text-white/70">Automatic cost controls</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">ROI Analytics</h4>
                            <p className="text-sm text-white/70">Performance insights</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="relative">
                    <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 p-8 transform hover:scale-105 transition-transform duration-300">
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-slate-800">Cost Analytics</h4>
                          <div className="text-2xl font-bold text-green-600">-67%</div>
                        </div>
                        
                        <div className="space-y-4">
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="text-slate-700">Monthly Savings</span>
                              <span className="font-semibold text-slate-800">$12,450</span>
                            </div>
                            <div className="w-full bg-slate-200 rounded-full h-2">
                              <div className="bg-clay-signal h-2 rounded-full w-3/4 animate-pulse"></div>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-4">
                            <div className="p-3 bg-white/50 rounded-lg text-center">
                              <div className="text-lg font-bold text-slate-800">GPT-4</div>
                              <div className="text-xs text-slate-600">Complex Tasks</div>
                            </div>
                            <div className="p-3 bg-white/50 rounded-lg text-center">
                              <div className="text-lg font-bold text-slate-800">GPT-3.5</div>
                              <div className="text-xs text-slate-600">Simple Tasks</div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </div>

              {/* Team Collaboration */}
              <div className={`absolute inset-0 transition-all duration-500 ${
                activeFeature === 'collaboration' 
                  ? 'opacity-100 translate-x-0' 
                  : 'opacity-0 translate-x-8 pointer-events-none'
              }`}>
                <div className="grid lg:grid-cols-2 gap-12 items-center">
                  <div className="space-y-6">
                    <div className="inline-flex items-center gap-3 px-4 py-2 bg-clay-signal/20 rounded-full">
                      <svg className="w-6 h-6 text-clay-signal" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zM4 18v-4h3v4h2v-7.5c0-1.1-.9-2-2-2s-2 .9-2 2V18H4zm9-10c-1.1 0-2 .9-2 2v7.5h2V14h3v4h2v-6.5c0-1.1-.9-2-2-2H13z"/>
                      </svg>
                      <span className="text-clay-signal font-semibold">Team Workspace</span>
                    </div>
                    
                    <h3 className="text-3xl lg:text-4xl font-bold text-white mb-4">
                      Team Collaboration
                    </h3>
                    
                    <p className="text-xl text-white/80 leading-relaxed mb-8">
                      Department-level isolation with shared templates and centralized management for seamless teamwork.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Department Isolation</h4>
                            <p className="text-sm text-white/70">Secure team boundaries</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Shared Templates</h4>
                            <p className="text-sm text-white/70">Reusable workflows</p>
                          </div>
                        </div>
                      </div>
                      
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Centralized Management</h4>
                            <p className="text-sm text-white/70">Admin oversight</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Team Analytics</h4>
                            <p className="text-sm text-white/70">Usage insights</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="relative">
                    <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 p-8 transform hover:scale-105 transition-transform duration-300">
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-slate-800">Team Dashboard</h4>
                          <div className="flex items-center gap-2">
                            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                            <span className="text-sm text-slate-600">5 Active</span>
                          </div>
                        </div>
                        
                        <div className="space-y-4">
                          <div className="flex items-center justify-between p-3 bg-white/50 rounded-lg">
                            <span className="text-sm text-slate-700">Engineering</span>
                            <span className="font-semibold text-slate-800">12 members</span>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 bg-white/50 rounded-lg">
                            <span className="text-sm text-slate-700">Marketing</span>
                            <span className="font-semibold text-slate-800">8 members</span>
                          </div>
                          
                          <div className="flex items-center justify-between p-3 bg-white/50 rounded-lg">
                            <span className="text-sm text-slate-700">Sales</span>
                            <span className="font-semibold text-slate-800">6 members</span>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </div>

              {/* Visual Builder */}
              <div className={`absolute inset-0 transition-all duration-500 ${
                activeFeature === 'builder' 
                  ? 'opacity-100 translate-x-0' 
                  : 'opacity-0 translate-x-8 pointer-events-none'
              }`}>
                <div className="grid lg:grid-cols-2 gap-12 items-center">
                  <div className="space-y-6">
                    <div className="inline-flex items-center gap-3 px-4 py-2 bg-clay-signal/20 rounded-full">
                      <svg className="w-6 h-6 text-clay-signal" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
                      </svg>
                      <span className="text-clay-signal font-semibold">No-Code Builder</span>
                    </div>
                    
                    <h3 className="text-3xl lg:text-4xl font-bold text-white mb-4">
                      Visual Builder
                    </h3>
                    
                    <p className="text-xl text-white/80 leading-relaxed mb-8">
                      Drag-and-drop interface for building custom AI agents with pre-built templates and workflows.
                    </p>
                    
                    <div className="grid grid-cols-2 gap-6">
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Drag & Drop</h4>
                            <p className="text-sm text-white/70">Visual workflow builder</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Pre-built Templates</h4>
                            <p className="text-sm text-white/70">Ready-to-use agents</p>
                          </div>
                        </div>
                      </div>
                      
                      <div className="space-y-4">
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">One-click Deploy</h4>
                            <p className="text-sm text-white/70">Instant activation</p>
                          </div>
                        </div>
                        
                        <div className="flex items-start gap-3">
                          <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0"></div>
                          <div>
                            <h4 className="font-semibold text-white mb-1">Custom Integrations</h4>
                            <p className="text-sm text-white/70">Connect your tools</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="relative">
                    <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 p-8 transform hover:scale-105 transition-transform duration-300">
                      <div className="space-y-6">
                        <div className="flex items-center justify-between">
                          <h4 className="font-bold text-slate-800">Agent Builder</h4>
                          <div className="px-2 py-1 bg-clay-signal/20 text-clay-signal text-xs rounded-full">Live</div>
                        </div>
                        
                        <div className="space-y-4">
                          <div className="p-4 bg-white/50 rounded-lg border-2 border-dashed border-clay-signal/30">
                            <div className="text-center text-slate-600">
                              <svg className="w-8 h-8 mx-auto mb-2 text-clay-signal" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                              </svg>
                              <div className="text-sm font-medium">Customer Support Agent</div>
                              <div className="text-xs text-slate-500">Drag to deploy</div>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-2">
                            <div className="p-2 bg-white/30 rounded text-center text-xs text-slate-600">Templates</div>
                            <div className="p-2 bg-white/30 rounded text-center text-xs text-slate-600">Integrations</div>
                          </div>
                        </div>
                      </div>
                    </Card>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>



      {/* Beta Program Section */}
      <section className="py-20 px-6 lg:px-8 relative bg-slate-900/20 backdrop-blur-md">
        <div className="max-w-4xl mx-auto text-center">
          <div className="mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-white mb-6">
              Join Our Enterprise Beta
            </h2>
            <p className="text-xl text-white/90 max-w-3xl mx-auto leading-relaxed">
              Limited to 50 organizations - priority given to companies with enterprise AI needs
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-12 max-w-4xl mx-auto">
            <div>
              <h3 className="text-2xl font-semibold mb-6 text-white">What's Included:</h3>
              <div className="space-y-4">
                <div className="flex items-start space-x-3">
                  <CheckCircle className="h-5 w-5 text-clay-signal mt-0.5 flex-shrink-0" />
                  <span className="text-white/90">Full platform access during beta</span>
                </div>
                <div className="flex items-start space-x-3">
                  <CheckCircle className="h-5 w-5 text-clay-signal mt-0.5 flex-shrink-0" />
                  <span className="text-white/90">White-glove setup and training</span>
                </div>
                <div className="flex items-start space-x-3">
                  <CheckCircle className="h-5 w-5 text-clay-signal mt-0.5 flex-shrink-0" />
                  <span className="text-white/90">Direct access to our engineering team</span>
                </div>
                <div className="flex items-start space-x-3">
                  <CheckCircle className="h-5 w-5 text-clay-signal mt-0.5 flex-shrink-0" />
                  <span className="text-white/90">Custom workspace configuration</span>
                </div>
                <div className="flex items-start space-x-3">
                  <CheckCircle className="h-5 w-5 text-clay-signal mt-0.5 flex-shrink-0" />
                  <span className="text-white/90">Priority feature development</span>
                </div>
              </div>
            </div>
            
            <div>
              <h3 className="text-2xl font-semibold mb-6 text-white">Beta Requirements:</h3>
              <div className="space-y-4 mb-8">
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0" />
                  <span className="text-white/90">50+ employees or $500+/month AI spend</span>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0" />
                  <span className="text-white/90">Need for data isolation/governance</span>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0" />
                  <span className="text-white/90">Technical point person for integration</span>
                </div>
                <div className="flex items-start space-x-3">
                  <div className="w-2 h-2 bg-clay-signal rounded-full mt-2 flex-shrink-0" />
                  <span className="text-white/90">Commitment to provide detailed feedback</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>



      {/* Competitive Differentiation Section */}
      <section className="py-20 px-6 lg:px-8 relative bg-slate-900/20 backdrop-blur-md">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-white mb-6">
              The Only Enterprise-First AI Platform with Cost Optimization
            </h2>
          </div>
          
          <div className="grid md:grid-cols-2 gap-12">
            <div>
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-semibold mb-2 text-white">Enterprise Platforms:</h3>
                  <p className="text-white/80">Focus on features, ignore costs</p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2 text-white">Developer Tools:</h3>
                  <p className="text-white/80">Great for individuals, can't scale to organizations</p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-2 text-white">Cost Tools:</h3>
                  <p className="text-white/80">Save money but lack enterprise governance</p>
                </div>
              </div>
            </div>
            
            <div>
              <div className="bg-slate-900/90 backdrop-blur-md rounded-lg p-6 border border-white/30">
                <h3 className="text-2xl font-semibold mb-4 text-white">Dataelan:</h3>
                <div className="space-y-3 text-white/90">
                  <p>✅ Enterprise governance</p>
                  <p>✅ Intelligent cost optimization</p>
                  <p>✅ Professional interface</p>
                  <p>✅ Complete solution</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Enterprise Beta Program Section */}
      <section className="py-20 px-6 lg:px-8 relative">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl lg:text-5xl font-bold text-white mb-4">
              Choose Your Plan
            </h2>
            <p className="text-xl text-white/90 max-w-2xl mx-auto">
              Start with our free beta program or learn about enterprise pricing
            </p>
          </div>
          
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            {/* Beta Access Card */}
            <div className="relative h-full">
              <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 hover:border-clay-signal/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 relative overflow-hidden h-full">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-clay-signal to-clay-signal/60"></div>
                <CardContent className="p-8 text-center h-full flex flex-col">
                  <div className="mb-6">
                    <h3 className="text-2xl font-bold text-slate-800 mb-2">Beta Access</h3>
                    <p className="text-slate-600 text-sm h-10 flex items-center justify-center">Perfect for enterprises ready to innovate with AI</p>
                  </div>
                  
                  <div className="mb-8">
                    <div className="flex items-baseline justify-center mb-2 h-16">
                      <span className="text-5xl font-bold text-clay-signal leading-none">Free</span>
                    </div>
                    <p className="text-slate-600 text-sm">Full platform access during beta</p>
                  </div>
                  
                  <div className="space-y-4 mb-8 text-left flex-grow">
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-clay-signal/20 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-clay-signal" />
                      </div>
                      <span className="text-slate-700 text-sm">Complete workspace setup & configuration</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-clay-signal/20 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-clay-signal" />
                      </div>
                      <span className="text-slate-700 text-sm">White-glove onboarding & training</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-clay-signal/20 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-clay-signal" />
                      </div>
                      <span className="text-slate-700 text-sm">Direct access to engineering team</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-clay-signal/20 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-clay-signal" />
                      </div>
                      <span className="text-slate-700 text-sm">Priority feature development input</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-clay-signal/20 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-clay-signal" />
                      </div>
                      <span className="text-slate-700 text-sm">Founding member benefits</span>
                    </div>
                  </div>
                  
                  <div className="mt-auto">
                    <Button className="w-full bg-clay-signal hover:bg-clay-signal/90 text-white py-3 text-base font-semibold rounded-lg shadow-lg hover:shadow-xl transition-all duration-300">
                      Apply for Beta Access
                    </Button>
                    
                    <p className="text-xs text-slate-500 mt-4">
                      Limited to 50 organizations
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
            
            {/* Enterprise Pricing Card */}
            <div className="relative h-full">
              <Card className="bg-[#E0E1E1]/95 backdrop-blur-md border-white/20 hover:border-clay-signal/50 transition-all duration-300 hover:shadow-2xl hover:scale-105 relative overflow-hidden h-full">
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-slate-600 to-slate-400"></div>
                <CardContent className="p-8 text-center h-full flex flex-col">
                  <div className="mb-6">
                    <h3 className="text-2xl font-bold text-slate-800 mb-2">Enterprise</h3>
                    <p className="text-slate-600 text-sm h-10 flex items-center justify-center">Custom solutions for large organizations</p>
                  </div>
                  
                  <div className="mb-8">
                    <div className="flex items-baseline justify-center mb-2 h-16">
                      <span className="text-5xl font-bold text-slate-700 leading-none">On Request</span>
                    </div>
                    <p className="text-slate-600 text-sm">Tailored enterprise pricing</p>
                  </div>
                  
                  <div className="space-y-4 mb-8 text-left flex-grow">
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-slate-600" />
                      </div>
                      <span className="text-slate-700 text-sm">Everything in Beta Access</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-slate-600" />
                      </div>
                      <span className="text-slate-700 text-sm">Advanced analytics & reporting</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-slate-600" />
                      </div>
                      <span className="text-slate-700 text-sm">Dedicated customer success manager</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-slate-600" />
                      </div>
                      <span className="text-slate-700 text-sm">Custom integrations & workflows</span>
                    </div>
                    <div className="flex items-start gap-3">
                      <div className="w-5 h-5 rounded-full bg-slate-200 flex items-center justify-center mt-0.5 flex-shrink-0">
                        <CheckCircle className="h-3 w-3 text-slate-600" />
                      </div>
                      <span className="text-slate-700 text-sm">SLA guarantees & premium support</span>
                    </div>
                  </div>
                  
                  <div className="mt-auto">
                    <Button variant="outline" className="w-full border-2 border-slate-600 text-slate-700 hover:bg-slate-600 hover:text-white py-3 text-base font-semibold rounded-lg transition-all duration-300">
                      Contact Sales
                    </Button>
                    
                    <p className="text-xs text-slate-500 mt-4">
                      Custom pricing based on scale
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
          
          <div className="text-center mt-12">
            <p className="text-white/70 text-sm">
              Questions about pricing? <a href="#" className="text-clay-signal hover:text-clay-signal/80 underline">Contact our team</a>
            </p>
          </div>
        </div>
      </section>

      {/* Footer CTA Section */}
      <section className="py-20 px-6 lg:px-8 relative bg-slate-900/20 backdrop-blur-md">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl lg:text-5xl font-bold text-white mb-6">
            Ready to Scale AI Across Your Organization?
          </h2>
          <p className="text-xl text-white/90 mb-8">
            Transform how your enterprise builds, deploys, and manages AI agents
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-8">
            <Button size="lg" className="bg-clay-signal hover:bg-clay-signal/90 text-white text-lg px-8 py-4">
              Apply for Enterprise Beta
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
            <Button size="lg" className="bg-white text-slate-800 hover:bg-white/90 border border-white/20 text-lg px-8 py-4">
              Schedule Platform Demo
            </Button>
          </div>
          
          <div className="text-sm text-white/80">
            <p>For enterprise inquiries: <a href="mailto:hello@dataelan.com" className="underline hover:text-clay-signal">enterprise@dataelan.com</a></p>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 lg:px-8 relative">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between mb-8">
            <div className="flex items-center space-x-2 mb-4 md:mb-0">
              <Image
                src="/assets/brand/logos/dataelan-logo-primary-light.svg"
                alt="Dataelan"
                width={140}
                height={40}
                className="h-10 w-auto"
              />
            </div>
            
            <div className="flex items-center space-x-4">
              <Link href="#" className="text-slate-600 hover:text-clay-signal transition-colors">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M24 4.557c-.883.392-1.832.656-2.828.775 1.017-.609 1.798-1.574 2.165-2.724-.951.564-2.005.974-3.127 1.195-.897-.957-2.178-1.555-3.594-1.555-3.179 0-5.515 2.966-4.797 6.045-4.091-.205-7.719-2.165-10.148-5.144-1.29 2.213-.669 5.108 1.523 6.574-.806-.026-1.566-.247-2.229-.616-.054 2.281 1.581 4.415 3.949 4.89-.693.188-1.452.232-2.224.084.626 1.956 2.444 3.379 4.6 3.419-2.07 1.623-4.678 2.348-7.29 2.04 2.179 1.397 4.768 2.212 7.548 2.212 9.142 0 14.307-7.721 13.995-14.646.962-.695 1.797-1.562 2.457-2.549z"/>
                </svg>
                <span className="sr-only">Twitter</span>
              </Link>
              <Link href="#" className="text-slate-600 hover:text-clay-signal transition-colors">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="sr-only">Facebook</span>
              </Link>
              <Link href="#" className="text-slate-600 hover:text-clay-signal transition-colors">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
                </svg>
                <span className="sr-only">LinkedIn</span>
              </Link>
              <Link href="#" className="text-slate-600 hover:text-clay-signal transition-colors">
                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M23.498 6c-.77.35-1.6.58-2.46.69.88-.53 1.56-1.37 1.88-2.38-.83.5-1.75.85-2.72 1.05C18.37 4.5 17.26 4 16 4c-2.35 0-4.27 1.92-4.27 4.29 0 .34.04.67.11.98C8.28 9.09 5.11 7.38 3 4.79c-.37.63-.58 1.37-.58 2.15 0 1.49.75 2.81 1.91 3.56-.71 0-1.37-.2-1.95-.5v.03c0 2.08 1.48 3.82 3.44 4.21a4.22 4.22 0 0 1-1.93.07 4.28 4.28 0 0 0 4 2.98 8.521 8.521 0 0 1-5.33 1.84c-.34 0-.68-.02-1.02-.06C3.44 20.29 5.7 21 8.12 21 16 21 20.33 14.46 20.33 8.79c0-.19 0-.37-.01-.56.84-.6 1.56-1.36 2.14-2.23z"/>
                </svg>
                <span className="sr-only">YouTube</span>
              </Link>
            </div>
          </div>
          
          <hr className="border-slate-300 mb-8" />
          
          <div className="flex flex-col md:flex-row items-center justify-between text-sm text-slate-600">
            <div className="mb-4 md:mb-0">
              &copy; 2024 Dataelan. All rights reserved.
            </div>
            <div className="flex items-center space-x-6">
              <Link href="#" className="hover:text-slate-800 transition-colors underline">
                Privacy Policy
              </Link>
              <Link href="#" className="hover:text-slate-800 transition-colors underline">
                Terms of Service
              </Link>
              <Link href="#" className="hover:text-slate-800 transition-colors underline">
                Cookies Settings
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}