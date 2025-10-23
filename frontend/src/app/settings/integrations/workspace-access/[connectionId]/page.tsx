"use client"

import { useParams } from "next/navigation";
import WorkspaceAccessPage from "@/components/integrations/WorkspaceAccessPage";

export default function WorkspaceAccessRoute() {
  const params = useParams();
  const connectionId = params.connectionId as string;
  
  return <WorkspaceAccessPage connectionId={connectionId} />;
}
