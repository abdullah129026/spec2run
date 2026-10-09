"use client";

import SwaggerUI from "swagger-ui-react";
import "swagger-ui-react/swagger-ui.css";
import { useSpec2RunStore } from "@/lib/store";

export default function SwaggerTab() {
  const spec = useSpec2RunStore((s) => s.spec);
  if (!spec) return null;

  return (
    <div className="spec2run-swagger h-full overflow-y-auto bg-[#09090b]">
      <SwaggerUI spec={spec} docExpansion="list" defaultModelsExpandDepth={1} />
    </div>
  );
}
