"use client"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import Link from "next/link"
import { useState } from "react"
import { useRouter } from "next/navigation"
import { signup } from "@/lib/auth/auth-service"

export function SignupForm({
  className,
  ...props
}: React.ComponentProps<"form">) {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [error, setError] = useState("");

  const checkPasswordStrength = (password: string) => {
    let strength = 0;
    if (password.length >= 8) strength += 1;
    if (/[A-Z]/.test(password)) strength += 1;
    if (/[0-9]/.test(password)) strength += 1;
    if (/[^A-Za-z0-9]/.test(password)) strength += 1;
    setPasswordStrength(strength);
  };

  const handlePasswordChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newPassword = e.target.value;
    setPassword(newPassword);
    checkPasswordStrength(newPassword);
  };

  const validateForm = () => {
    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return false;
    }

    if (passwordStrength < 2) {
      setError("Password is too weak. Please create a stronger password.");
      return false;
    }

    if (!termsAccepted) {
      setError("You must accept the terms of service and privacy policy.");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      await signup({
        firstName,
        lastName,
        email,
        password,
      });
      
      // Show success message and redirect to login page
      setError("");
      alert("Account created successfully! Please log in with your new credentials.");
      router.push("/login");
    } catch (err: Error | unknown) {
      console.error("Signup error:", err);
      const errorMessage = err instanceof Error ? err.message : "Failed to create account. Please try again.";
      setError(errorMessage);
      // Display error message to user
      alert("Signup failed: " + errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <form className={cn("flex flex-col gap-6", className)} onSubmit={handleSubmit} {...props}>
      <div className="flex flex-col items-center gap-2 text-center">
        <h1 className="text-2xl font-bold">Create an account</h1>
        <p className="text-muted-foreground text-sm text-balance">
          Enter your information below to create your account
        </p>
      </div>
      {error && (
        <div className="bg-destructive/15 text-destructive text-sm p-3 rounded-md">
          {error}
        </div>
      )}
      <div className="grid gap-6">
        <div className="grid grid-cols-2 gap-4">
          <div className="grid gap-2">
            <Label htmlFor="firstName">First name</Label>
            <Input 
              id="firstName" 
              type="text" 
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              required 
              disabled={isLoading}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="lastName">Last name</Label>
            <Input 
              id="lastName" 
              type="text" 
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              required 
              disabled={isLoading}
            />
          </div>
        </div>
        <div className="grid gap-2">
          <Label htmlFor="email">Email</Label>
          <Input 
            id="email" 
            type="email" 
            placeholder="m@example.com" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required 
            disabled={isLoading}
          />
        </div>
        <div className="grid gap-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={handlePasswordChange}
            required
            disabled={isLoading}
          />
          {password && (
            <div className="mt-1">
              <div className="text-xs mb-1">
                Password strength:{" "}
                {passwordStrength === 0
                  ? "Very weak"
                  : passwordStrength === 1
                  ? "Weak"
                  : passwordStrength === 2
                  ? "Medium"
                  : passwordStrength === 3
                  ? "Strong"
                  : "Very strong"}
              </div>
              <div className="flex gap-1 h-1">
                <div
                  className={`flex-1 rounded-full ${passwordStrength >= 1 ? "bg-red-500" : "bg-gray-200"}`}
                ></div>
                <div
                  className={`flex-1 rounded-full ${passwordStrength >= 2 ? "bg-yellow-500" : "bg-gray-200"}`}
                ></div>
                <div
                  className={`flex-1 rounded-full ${passwordStrength >= 3 ? "bg-green-500" : "bg-gray-200"}`}
                ></div>
                <div
                  className={`flex-1 rounded-full ${passwordStrength >= 4 ? "bg-green-700" : "bg-gray-200"}`}
                ></div>
              </div>
            </div>
          )}
        </div>
        <div className="grid gap-2">
          <Label htmlFor="confirmPassword">Confirm Password</Label>
          <Input 
            id="confirmPassword" 
            type="password" 
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required 
            disabled={isLoading}
          />
        </div>
        <div className="flex items-center space-x-2">
          <input
            type="checkbox"
            id="terms"
            className="h-4 w-4 rounded border-gray-300 text-[#A76052] focus:ring-[#A76052]"
            checked={termsAccepted}
            onChange={(e) => setTermsAccepted(e.target.checked)}
            required
            disabled={isLoading}
          />
          <Label
            htmlFor="terms"
            className="text-sm font-normal leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
          >
            I agree to the{" "}
            <a href="#" className="text-[#A76052] hover:underline underline-offset-4">
              terms of service
            </a>{" "}
            and{" "}
            <a href="#" className="text-[#A76052] hover:underline underline-offset-4">
              privacy policy
            </a>
          </Label>
        </div>
        <Button 
          type="submit" 
          className="w-full bg-[#A76052] hover:bg-[#A76052]/90 text-white"
          disabled={isLoading}
        >
          {isLoading ? "Creating account..." : "Create account"}
        </Button>
      </div>
      <div className="text-center text-sm">
        Already have an account?{" "}
        <Link href="/login" className="text-[#A76052] hover:underline underline-offset-4">
          Login
        </Link>
      </div>
    </form>
  )
}
