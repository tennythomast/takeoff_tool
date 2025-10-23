"use client"

import { useParams } from "next/navigation";
import ConnectionManagePage from "@/components/integrations/ConnectionManagePage";

export default function ManageConnectionPage() {
  const params = useParams();
  const connectionId = params.connectionId as string;
  
  return <ConnectionManagePage connectionId={connectionId} />;
}
