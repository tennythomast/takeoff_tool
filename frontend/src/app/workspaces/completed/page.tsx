"use client"

import React from 'react';
import WorkspaceListingPage from '@/components/workspaces/WorkspaceListingPage';
import { AuthGuard } from '@/components/auth/auth-guard';

export default function CompletedWorkspacesPage() {
  return (
    <AuthGuard>
      <WorkspaceListingPage status="completed" pathname="/workspaces/completed" />
    </AuthGuard>
  );
}
