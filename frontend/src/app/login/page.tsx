import { LoginForm } from "@/components/login-form"
import Image from "next/image"

export default function LoginPage() {
  return (
    <div className="flex min-h-svh flex-col md:flex-row">
      {/* Left side - Background with logo */}
      <div className="flex w-full items-center justify-center md:w-1/2 bg-muted p-8">
        <div className="relative z-10 w-full max-w-md">
          <Image 
            src="/assets/brand/logos/dataelan-logo-primary-light.svg" 
            alt="Dataelan" 
            width={180}
            height={48}
            className="h-12 w-auto mb-8"
          />
          <div className="space-y-2">
            <h1 className="text-3xl font-bold">Welcome back</h1>
            <p className="text-muted-foreground">Enter your credentials to access your account</p>
          </div>
        </div>
      </div>
      
      {/* Right side - Login Form */}
      <div className="flex w-full items-center justify-center p-8 md:w-1/2">
        <div className="mx-auto w-full max-w-sm">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}