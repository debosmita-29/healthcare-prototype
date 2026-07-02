import { CheckCircle2, Circle, LoaderCircle, ShieldCheck, TestTube2 } from "lucide-react";

const NODE_LABELS = [
  ["input_guardrails", "Guardrails"],
  ["planner", "Planner"],
  ["async_retrieval_fanout", "Async Retrieval"],
  ["sync_join", "Join"],
  ["rag_select", "RAG"],
  ["synthesize", "Synthesis"],
  ["supervisor", "Supervisor"],
  ["evaluate", "Eval"],
  ["cost_performance", "Cost"]
];

export function StatusRail({ events, status }) {
  const completedNodes = new Set(events.map((event) => event.node));
  return (
    <aside className="status-rail" aria-label="Graph status">
      <div className="rail-heading">
        <ShieldCheck size={18} />
        <span>Graph Control Plane</span>
      </div>
      <div className="node-list">
        {NODE_LABELS.map(([node, label]) => {
          const done = completedNodes.has(node);
          const active = !done && status === "running";
          const Icon = done ? CheckCircle2 : active ? LoaderCircle : Circle;
          return (
            <div className={`node-row ${done ? "done" : ""}`} key={node}>
              <Icon size={17} className={active ? "spin" : ""} />
              <span>{label}</span>
            </div>
          );
        })}
      </div>
      <div className="rail-footer">
        <TestTube2 size={16} />
        <span>{status || "idle"}</span>
      </div>
    </aside>
  );
}

