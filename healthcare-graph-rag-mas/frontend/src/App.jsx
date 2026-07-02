import { useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  Building2,
  FileSearch,
  FlaskConical,
  Play,
  ShieldCheck,
  Stethoscope,
  TimerReset
} from "lucide-react";
import { createBriefing, getBriefing, openEventStream } from "./lib/api.js";
import { Metric } from "./components/Metric.jsx";
import { StatusRail } from "./components/StatusRail.jsx";

const DEFAULT_FORM = {
  condition: "atopic dermatitis",
  audience: "health system strategy team",
  include_companies: true,
  include_trials: true,
  max_wait_seconds: 90
};

export function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [briefing, setBriefing] = useState(null);
  const [events, setEvents] = useState([]);
  const [error, setError] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const streamRef = useRef(null);

  const status = briefing?.status || (isRunning ? "running" : "idle");
  const evidenceById = useMemo(() => {
    const map = new Map();
    briefing?.evidence?.forEach((item) => map.set(item.id, item));
    return map;
  }, [briefing]);

  useEffect(() => {
    return () => streamRef.current?.close();
  }, []);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBriefing(null);
    setEvents([]);
    setIsRunning(true);
    streamRef.current?.close();

    try {
      const pending = await createBriefing(form);
      setBriefing(pending);
      streamRef.current = openEventStream(pending.run_id, async (message) => {
        setEvents((current) => [...current, message]);
        if (message.event === "complete") {
          const final = await getBriefing(pending.run_id);
          setBriefing(final);
          setEvents(final.audit_events.map((auditEvent) => ({ event: "audit", ...auditEvent })));
          setIsRunning(false);
          streamRef.current?.close();
        }
      });
    } catch (requestError) {
      setError(requestError.message);
      setIsRunning(false);
    }
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  return (
    <main className="app-shell">
      <section className="workspace">
        <StatusRail events={events} status={status} />

        <div className="main-panel">
          <header className="topbar">
            <div>
              <p className="eyebrow">Healthcare Strategy Intelligence</p>
              <h1>Graph RAG briefing workbench</h1>
            </div>
            <div className={`status-pill ${status}`}>
              <Activity size={16} />
              <span>{status}</span>
            </div>
          </header>

          <form className="briefing-form" onSubmit={submit}>
            <label className="field">
              <span>Medical condition</span>
              <input
                value={form.condition}
                onChange={(event) => updateField("condition", event.target.value)}
                placeholder="e.g. atopic dermatitis"
              />
            </label>
            <label className="field">
              <span>Audience</span>
              <input
                value={form.audience}
                onChange={(event) => updateField("audience", event.target.value)}
              />
            </label>
            <div className="toggle-row" role="group" aria-label="Retrieval options">
              <label>
                <input
                  type="checkbox"
                  checked={form.include_trials}
                  onChange={(event) => updateField("include_trials", event.target.checked)}
                />
                <FlaskConical size={16} />
                Trials
              </label>
              <label>
                <input
                  type="checkbox"
                  checked={form.include_companies}
                  onChange={(event) => updateField("include_companies", event.target.checked)}
                />
                <Building2 size={16} />
                Companies
              </label>
            </div>
            <button className="primary-button" disabled={isRunning || !form.condition.trim()}>
              <Play size={17} />
              Generate
            </button>
          </form>

          {error ? <div className="error-bar">{error}</div> : null}

          <section className="summary-strip" aria-label="Performance metrics">
            <Metric label="Retrieval" value={`${briefing?.performance?.async_retrieval_ms ?? 0} ms`} />
            <Metric label="RAG" value={`${briefing?.performance?.rag_ms ?? 0} ms`} />
            <Metric label="LLM" value={`${briefing?.performance?.llm_ms ?? 0} ms`} />
            <Metric label="Eval" value={`${briefing?.performance?.eval_ms ?? 0} ms`} />
          </section>

          <section className="briefing-layout">
            <article className="briefing-output">
              <div className="section-title">
                <Stethoscope size={18} />
                <h2>Structured Briefing</h2>
              </div>
              {briefing?.executive_summary ? (
                <p className="executive-summary">{briefing.executive_summary}</p>
              ) : (
                <p className="empty-state">Submit a condition to run the graph and generate the briefing.</p>
              )}

              {briefing?.sections?.map((section) => (
                <section className="brief-section" key={section.title}>
                  <h3>{section.title}</h3>
                  <ul>
                    {section.bullets.map((bullet) => (
                      <li key={bullet}>{bullet}</li>
                    ))}
                  </ul>
                  <div className="citation-row">
                    {section.evidence_ids.slice(0, 6).map((id) => {
                      const evidence = evidenceById.get(id);
                      return (
                        <a
                          className="citation-chip"
                          key={id}
                          href={evidence?.url || "#"}
                          target="_blank"
                          rel="noreferrer"
                          title={evidence?.title || id}
                        >
                          {evidence?.source_type || "evidence"}
                        </a>
                      );
                    })}
                  </div>
                </section>
              ))}
            </article>

            <aside className="side-stack">
              <section className="panel">
                <div className="section-title">
                  <ShieldCheck size={18} />
                  <h2>Governance</h2>
                </div>
                <p className={briefing?.governance?.approved ? "approved" : "pending"}>
                  {briefing?.governance?.approved ? "Approved" : "Pending"}
                </p>
                <ul className="compact-list">
                  {(briefing?.governance?.reasons || briefing?.governance?.required_revisions || []).map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>

              <section className="panel">
                <div className="section-title">
                  <TimerReset size={18} />
                  <h2>RAGAS Eval</h2>
                </div>
                <div className="score-grid">
                  <Metric label="Faithful" value={briefing?.evaluation?.faithfulness?.toFixed?.(2) ?? "0.00"} />
                  <Metric label="Relevant" value={briefing?.evaluation?.answer_relevancy?.toFixed?.(2) ?? "0.00"} />
                  <Metric label="Context" value={briefing?.evaluation?.context_precision?.toFixed?.(2) ?? "0.00"} />
                  <Metric label="Safety" value={briefing?.evaluation?.safety?.toFixed?.(2) ?? "0.00"} />
                </div>
              </section>

              <section className="panel">
                <div className="section-title">
                  <FileSearch size={18} />
                  <h2>Evidence</h2>
                </div>
                <div className="evidence-list">
                  {(briefing?.evidence || []).map((item) => (
                    <a href={item.url || "#"} target="_blank" rel="noreferrer" key={item.id}>
                      <strong>{item.title}</strong>
                      <span>{item.source_type} · {item.trust_tier}</span>
                    </a>
                  ))}
                </div>
              </section>
            </aside>
          </section>
        </div>
      </section>
    </main>
  );
}
