// src/app/account/layout.tsx
import { MainLayout } from "@/components/layout/main-layout"

export default function AccountLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <MainLayout>
      {children}
    </MainLayout>
  )
}
