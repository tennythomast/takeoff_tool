import * as React from 'react'
import { MainLayout } from '@/components/layout/main-layout'

export default function SettingsLayout({
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
