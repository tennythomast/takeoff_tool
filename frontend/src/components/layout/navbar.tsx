import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Logo } from "@/components/ui/logo"

export function Navbar() {
  return (
    <nav className="flex items-center justify-between p-6 lg:px-8 bg-slate-800">
      <div className="flex items-center space-x-2">
        <Logo variant="light" size="md" />
      </div>
      
      <div className="hidden md:flex items-center space-x-8">
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
      
      <div className="flex items-center">
        <Button className="bg-clay-signal hover:bg-clay-signal/90 text-white px-6 py-2 rounded-lg">
          Button
        </Button>
      </div>
    </nav>
  )
}
