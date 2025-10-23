"use client"

import React from 'react';
import WorkspaceListingPage from '@/components/workspaces/WorkspaceListingPage';
import { AuthGuard } from '@/components/auth/auth-guard';

export default function ActiveWorkspacesPage() {
  return (
    <AuthGuard>
      <WorkspaceListingPage status="active" pathname="/workspaces/active" />
    </AuthGuard>
  );
}
