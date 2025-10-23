import Link from "next/link"
import { Logo } from "@/components/ui/logo"
import { Facebook, Instagram, Twitter, Linkedin, Youtube } from "lucide-react"

export function Footer() {
  return (
    <footer className="bg-slate-800 text-white">
      <div className="max-w-6xl mx-auto px-6 lg:px-8 py-12">
        {/* Main footer content */}
        <div className="flex flex-col md:flex-row items-center justify-between mb-8">
          <div className="flex items-center space-x-2 mb-6 md:mb-0">
            <Logo variant="light" size="md" />
          </div>
          
          <div className="flex items-center space-x-8 mb-6 md:mb-0">
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              Link One
            </Link>
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              Link Two
            </Link>
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              Link Three
            </Link>
          </div>
          
          <div className="flex items-center space-x-4">
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              <Facebook className="h-5 w-5" />
              <span className="sr-only">Facebook</span>
            </Link>
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              <Instagram className="h-5 w-5" />
              <span className="sr-only">Instagram</span>
            </Link>
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              <Twitter className="h-5 w-5" />
              <span className="sr-only">Twitter</span>
            </Link>
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              <Linkedin className="h-5 w-5" />
              <span className="sr-only">LinkedIn</span>
            </Link>
            <Link href="#" className="text-white hover:text-clay-signal transition-colors">
              <Youtube className="h-5 w-5" />
              <span className="sr-only">YouTube</span>
            </Link>
          </div>
        </div>
        
        {/* Divider line */}
        <div className="border-t border-clay-signal/30 mb-6"></div>
        
        {/* Bottom footer */}
        <div className="flex flex-col md:flex-row items-center justify-between text-sm text-white/70">
          <div className="mb-4 md:mb-0">
            © 2024 Relume. All rights reserved.
          </div>
          <div className="flex items-center space-x-6">
            <Link href="#" className="hover:text-white transition-colors underline">
              Privacy Policy
            </Link>
            <Link href="#" className="hover:text-white transition-colors underline">
              Terms of Service
            </Link>
            <Link href="#" className="hover:text-white transition-colors underline">
              Cookies Settings
            </Link>
          </div>
        </div>
      </div>
    </footer>
  )
}
