import Image from "next/image"
import { cn } from "@/lib/utils"

interface LogoProps {
  variant?: "light" | "dark" | "white"
  size?: "sm" | "md" | "lg"
  className?: string
}

export function Logo({ variant = "light", size = "md", className }: LogoProps) {
  const sizeClasses = {
    sm: "h-6",
    md: "h-8", 
    lg: "h-12"
  }

  const logoSrc = {
    light: "/assets/brand/logos/dataelan-logo-primary-light.svg",
    dark: "/assets/brand/logos/dataelan-logo-primary-dark.svg", 
    white: "/assets/brand/logos/dataelan-logo-white.svg"
  }

  return (
    <Image
      src={logoSrc[variant]}
      alt="Dataelan"
      width={120}
      height={32}
      className={cn(sizeClasses[size], "w-auto", className)}
      priority
    />
  )
}
