"use client"

import React from 'react';
import WorkspaceListingPage from '@/components/workspaces/WorkspaceListingPage';
import { AuthGuard } from '@/components/auth/auth-guard';

export default function RecentWorkspacesPage() {
  return (
    <AuthGuard>
      <WorkspaceListingPage status="recent" pathname="/workspaces/recent" />
    </AuthGuard>
  );
}
