"use client"

import { useParams } from "next/navigation";
import ConnectionForm from "@/components/integrations/ConnectionForm";

export default function EditConnectionPage() {
  const params = useParams();
  const connectionId = params.connectionId as string;
  
  return <ConnectionForm connectionId={connectionId} isEdit={true} />;
}
