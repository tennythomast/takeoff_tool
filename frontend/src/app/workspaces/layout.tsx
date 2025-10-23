"use client"

import React from 'react';
import { MainLayout } from '@/components/layout/main-layout';

export default function WorkspacesLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <MainLayout>{children}</MainLayout>;
}
