// src/app/layout.tsx
import "./globals.css"
import localFont from "next/font/local"
import { SidebarProvider } from "@/context/sidebar-context"
import { ChatSidebarProvider } from "@/context/chat-sidebar-context"
import { SonnerToastProvider } from "@/components/ui/sonner-toast-provider"


// Load Inter font locally instead of from Google Fonts
const inter = localFont({
  src: [
    {
      path: "../fonts/Inter/Inter_18pt-Regular.ttf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../fonts/Inter/Inter_18pt-Medium.ttf",
      weight: "500",
      style: "normal",
    },
    {
      path: "../fonts/Inter/Inter_18pt-Bold.ttf",
      weight: "700",
      style: "normal",
    },
    {
      path: "../fonts/Inter/Inter_18pt-Italic.ttf",
      weight: "400",
      style: "italic",
    },
  ],
  variable: "--font-inter",
  display: "swap",
})

// Load Magnetik font locally
const magnetik = localFont({
  src: [
    {
      path: "../fonts/magnetik/Magnetik-Regular.otf",
      weight: "400",
      style: "normal",
    },
    {
      path: "../fonts/magnetik/Magnetik-Medium.otf",
      weight: "500",
      style: "normal",
    },
    {
      path: "../fonts/magnetik/Magnetik-Bold.otf",
      weight: "700",
      style: "normal",
    },
    {
      path: "../fonts/magnetik/Magnetik-RegularItalic.otf",
      weight: "400",
      style: "italic",
    },
  ],
  variable: "--font-magnetik",
  display: "swap",
})

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <head>
      </head>
      <body className={`bg-[#E0E1E1] text-[#192026] ${magnetik.variable} ${inter.variable} font-sans`}>
        <SidebarProvider>
          <ChatSidebarProvider>
            {children}
            <SonnerToastProvider />
          </ChatSidebarProvider>
        </SidebarProvider>
      </body>
    </html>
  )
}