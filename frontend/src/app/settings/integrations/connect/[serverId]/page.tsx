"use client"

import { useParams } from "next/navigation";
import ConnectionForm from "@/components/integrations/ConnectionForm";

export default function ConnectServerPage() {
  const params = useParams();
  const serverId = params.serverId as string;
  
  return <ConnectionForm serverId={serverId} />;
}
