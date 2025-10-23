import * as React from 'react'
import { MainLayout } from "@/components/layout/main-layout"

export default function AgentsLayout({
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
