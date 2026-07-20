import { useEffect, useMemo, useState } from "react";

const PIPELINE = ["fetching", "parsing", "tracing", "profiling", "classifying", "reasoning"];
const LABELS = { fetching: "Fetching", parsing: "Parsing", tracing: "Tracing", profiling: "Building Behavior Profile", classifying: "Classifying", reasoning: "Reasoning" };
const FOLLOW_UP_STATES = [
  "Reviewing the established evidence…",
  "Following the traced data flow…",
  "Checking the documented claims…",
  "Preparing a grounded answer…",
];

function normaliseUrl(value) {
  return value.startsWith("http") ? value : `https://${value}`;
}

function trustMeta(level) {
  return {
    verified: ["verified", "VERIFIED"],
    review: ["review", "REVIEW"],
    high_risk: ["high-risk", "HIGH RISK"],
  }[level] ?? ["active", "Analyzing"];
}

function profileRows(profile) {
  if (!profile) return [];
  const fields = [["Network Access", "network"], ["Filesystem Access", "filesystem"], ["Shell Execution", "shell"], ["Environment Secrets", "secrets"]];
  const rows = fields.map(([label, key]) => {
    const item = profile[key] ?? { detected: false, evidence: [] };
    const count = item.evidence?.length ?? 0;
    return { label, tone: item.detected ? "detected" : "none", value: item.detected ? `${count} finding${count === 1 ? "" : "s"} detected` : "none found" };
  });
  const domains = profile.network?.external_domains ?? [];
  rows.push({ label: "External Domains", tone: domains.length ? "flagged" : "none", value: domains.length ? domains.join(", ") : "none found" });
  return rows;
}

function observedText(finding) {
  const source = finding.source ? `${finding.source.file}:${finding.source.line} ${finding.source.description}` : "direct operation";
  const sink = finding.sink ? `${finding.sink.file}:${finding.sink.line} ${finding.sink.description}` : "sink location unavailable";
  return `${source} → ${sink}${finding.external_domain ? ` (${finding.external_domain})` : ""}`;
}

function findingLocation(finding) {
  const location = finding.sink ?? finding.source;
  return location ? `${location.file} · line ${location.line}` : "source location unavailable";
}

async function copyText(value) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return;
    }
  } catch {
    // Local HTTP and restrictive browser permissions can reject Clipboard API.
  }
  const area = document.createElement("textarea");
  area.value = value;
  area.style.position = "fixed";
  area.style.opacity = "0";
  document.body.append(area);
  area.select();
  const didCopy = document.execCommand("copy");
  area.remove();
  if (!didCopy) throw new Error("Clipboard access was denied");
}

export function AnalysisPage() {
  const githubUrl = useMemo(() => new URLSearchParams(window.location.search).get("github_url") ?? "", []);
  const [active, setActive] = useState(null);
  const [completed, setCompleted] = useState([]);
  const [profile, setProfile] = useState(null);
  const [findings, setFindings] = useState([]);
  const [classifications, setClassifications] = useState([]);
  const [verdict, setVerdict] = useState(null);
  const [error, setError] = useState("");
  const [errorCode, setErrorCode] = useState("");
  const [copied, setCopied] = useState("");
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState([]);
  const [pendingQuestion, setPendingQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [followUpError, setFollowUpError] = useState("");
  const [followUpState, setFollowUpState] = useState(0);

  useEffect(() => {
    if (!githubUrl) { setError("A public GitHub repository URL is required."); return; }
    const controller = new AbortController();
    let buffer = "";
    const started = performance.now();

    async function run() {
      try {
        const response = await fetch("/analyze", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ github_url: normaliseUrl(githubUrl) }), signal: controller.signal });
        if (!response.ok || !response.body) throw new Error("Unable to start repository analysis.");
        const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += value;
          const packets = buffer.split("\n\n");
          buffer = packets.pop() ?? "";
          packets.forEach(handlePacket);
        }
      } catch (cause) {
        if (cause.name !== "AbortError") setError(cause.message || "Unable to analyze this repository.");
      }
    }

    function handlePacket(packet) {
      const eventName = packet.match(/^event:\s*(.+)$/m)?.[1];
      const raw = packet.match(/^data:\s*(.+)$/m)?.[1];
      if (!eventName || !raw) return;
      const event = JSON.parse(raw);
      if (eventName === "progress") {
        const stage = event.stage;
        setActive(stage);
        setCompleted(PIPELINE.slice(0, PIPELINE.indexOf(stage)));
        if (stage === "tracing") setFindings(event.data.findings ?? []);
        if (stage === "classifying") setClassifications(event.data.classifications ?? []);
      }
      if (eventName === "profile") setProfile(event.behavior_profile);
      if (eventName === "verdict") { setVerdict(event.verdict); setActive(null); setCompleted(PIPELINE); }
      if (eventName === "error") { setError(event.message); setErrorCode(event.code ?? "analysis_error"); setActive(null); }
    }
    run();
    return () => controller.abort();
  }, [githubUrl]);

  useEffect(() => {
    if (active !== "reasoning" || verdict || error) return undefined;
    const timer = window.setTimeout(() => {
      setError("Reasoning is taking longer than expected. Check that Codex CLI is logged in, then try again.");
    }, 130000);
    return () => window.clearTimeout(timer);
  }, [active, verdict, error]);

  useEffect(() => {
    if (!asking) {
      setFollowUpState(0);
      return undefined;
    }
    const timer = window.setInterval(() => {
      setFollowUpState((current) => (current + 1) % FOLLOW_UP_STATES.length);
    }, 4000);
    return () => window.clearInterval(timer);
  }, [asking]);

  const [tone, verdictLabel] = trustMeta(verdict?.trust_level);
  const finalFindings = verdict?.evidence ?? findings;
  const finalProfile = verdict?.behavior_profile ?? profile;
  const finalClassifications = verdict?.classifications ?? classifications;
  const claim = finalClassifications.find((item) => item.claim_excerpt);
  const isHighRisk = verdict?.trust_level === "high_risk";
  const isReview = verdict?.trust_level === "review";

  if (errorCode === "repository_not_found") {
    return <main className="not-found-page"><section className="not-found-card"><div className="not-found-code">404</div><p className="eyebrow">Public repository required</p><h1>Repository not found.</h1><p>We could not find <code>{githubUrl.replace(/^https?:\/\//, "")}</code> on GitHub. It may be private, renamed, deleted, or the URL may be incomplete.</p><p className="not-found-note">Skill Passport can analyze public GitHub repositories only. It never requests access to private repositories.</p><div className="app-error-actions"><a className="btn-ghost" href="/">Try another repository</a><a className="btn-primary not-found-github" href="https://github.com" target="_blank" rel="noreferrer">Open GitHub</a></div></section></main>;
  }

  async function copy(value, key) {
    try {
      await copyText(value);
      setCopied(key);
      window.setTimeout(() => setCopied(""), 1500);
    } catch {
      setCopied("failed");
    }
  }

  async function askFollowUp(event) {
    event.preventDefault();
    if (!question.trim() || !verdict?.thread_id) return;
    const askedQuestion = question.trim();
    setAsking(true);
    setPendingQuestion(askedQuestion);
    setQuestion("");
    setFollowUpError("");
    try {
      const response = await fetch("/follow-up", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ thread_id: verdict.thread_id, question: askedQuestion }) });
      const body = await response.text();
      let payload = {};
      try { payload = body ? JSON.parse(body) : {}; } catch { throw new Error("The follow-up service returned an invalid response. Restart the frontend and backend, then try again."); }
      if (!response.ok) throw new Error(payload.detail || "Unable to answer the follow-up question.");
      if (!payload.answer) throw new Error("The follow-up service returned no answer. Please try again.");
      setConversation((items) => [...items, { question: askedQuestion, answer: payload.answer }]);
      setPendingQuestion("");
    } catch (cause) {
      setFollowUpError(cause.message || "Unable to answer the follow-up question.");
      setQuestion(askedQuestion);
      setPendingQuestion("");
    } finally {
      setAsking(false);
    }
  }

  return <>
    <header className="analysis-header"><div className="back"><a className="chev" href="/" aria-label="Back to homepage">←</a><span className="repo-name">{githubUrl.replace(/^https?:\/\//, "") || "repository analysis"}</span></div><div className={`status-chip ${verdict ? tone : error ? "high-risk" : "active"}`}><span className="dot" /><span>{verdict ? verdictLabel : error ? "Analysis stopped" : "Analyzing"}</span></div></header>
    <div className="layout"><aside className="rail"><div className="rail-title">Analysis pipeline</div><div className="pipeline"><div className="pipeline-fill" style={{ height: `${Math.max(completed.length - 0.5, 0) / PIPELINE.length * 100}%` }} />
      {PIPELINE.map((stage) => <div className={`stage ${active === stage ? "active" : completed.includes(stage) ? "complete" : "pending"}`} key={stage}><div className="dot">{completed.includes(stage) && active !== stage ? "✓" : ""}</div><div><div className="stage-label">{LABELS[stage]}</div><div className="stage-time">{completed.includes(stage) ? "complete" : active === stage ? "in progress" : "waiting"}</div></div></div>)}
    </div></aside>
      <main className="analysis-main">
        {error && <div className="error-card"><strong>Analysis stopped.</strong><span>{error}</span></div>}
        {!finalProfile && !error && <section className="card show skeleton-card"><div className="card-head"><h3>Behavior Profile</h3></div>{Array.from({ length: 5 }, (_, index) => <div className="profile-row" key={index}><span className="skeleton skeleton-label" /><span className="skeleton skeleton-tag" /></div>)}</section>}
        {finalProfile && <section className="card show"><div className="card-head"><h3>Behavior Profile</h3></div>{profileRows(finalProfile).map((row) => <div className="profile-row" key={row.label}><span className="profile-label">◔ {row.label}</span><span className={`tag ${row.tone}`}>{row.value}</span></div>)}</section>}
        {!verdict && !error && <><div className="section-title">Preparing analysis</div><section className="card show skeleton-card"><div className="skeleton skeleton-verdict" /><div className="skeleton skeleton-copy" /><div className="skeleton skeleton-copy short" /></section></>}
        {verdict && <><section className="verdict-card show"><div className={`seal-stamp ${tone}`}><span>{verdictLabel.replace(" ", "\n")}</span></div><p className="verdict-reason">{verdict.reasoning.judgment}</p><div className={`verdict-reco ${tone}`}>Recommendation: {verdict.recommendation}</div></section>
          <div className="section-title">Evidence</div><section className="card show">{finalFindings.length ? finalFindings.map((finding, index) => <article className="evidence-item" key={`${finding.category}-${index}`}><div className="ev-file"><span>{findingLocation(finding)}</span><span>{finding.category}</span></div><div className="ev-code">{observedText(finding)}</div><div className="ev-chain">{(finding.assignment_chain ?? []).map((step, stepIndex, chain) => <span key={`${step}-${stepIndex}`} className="chain-wrap"><span className={`chain-step ${stepIndex === chain.length - 1 ? "sink" : ""}`}>{step}</span>{stepIndex < chain.length - 1 && <span className="chain-arrow">→</span>}</span>)}{finding.external_domain && <span className="chain-step sink">{finding.external_domain}</span>}</div></article>) : <div className="empty-state">No sensitive behavior was found in the traced source files.</div>}</section>
          <div className="section-title">Claims vs. behavior</div><section className="card show"><div className="claims-grid"><div className="claim-col"><p className="claim-quote">{claim ? `“${claim.claim_excerpt}”` : "No contradictory repository claim was found."}</p><div className="claim-source">{claim ? "— repository documentation" : "— claim comparison"}</div></div><div className={`contradiction-icon ${tone}`}>{isHighRisk ? "×" : isReview ? "!" : "✓"}</div><div className="claim-col"><div className="observed-label">Observed behavior</div><div className="observed-text">{verdict.reasoning.translation}</div></div></div></section>
          <section className="card show"><div className="card-head"><h3>Follow-up Q&A</h3></div>{conversation.map((item, index) => <div className="qa-item" key={`${item.question}-${index}`}><div className="qa-question"><span>Question</span><p>{item.question}</p></div><div className="qa-answer"><span>Grounded answer</span><p>{item.answer}</p></div></div>)}{asking && <div className="qa-item"><div className="qa-question"><span>Question</span><p>{pendingQuestion}</p></div><div className="qa-answer answer-loading"><span>Grounded answer</span><p><i /><b className="loading-copy" key={followUpState}>{FOLLOW_UP_STATES[followUpState]}</b></p></div></div>}{!asking && <form className="followup" onSubmit={askFollowUp}><span className="prompt">›</span><input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={conversation.length ? "Ask another question about this analysis" : "Ask about this analysis — e.g. “could this be legitimate telemetry?”"} /><button className="followup-submit" disabled={!question.trim()}>Ask</button></form>}{followUpError && <div className="followup-error">{followUpError}</div>}</section>
          <div className="section-title">Installation</div><section className="card show install-card">{isHighRisk ? <div className="install-hidden"><span>⛔</span><span>Installation command hidden — repository classified <strong>HIGH RISK</strong>.</span></div> : <><div className="install-note">{isReview ? "Note: this repository discloses behavior that needs review before installing." : "This repository appears consistent with its published claims."}</div><div className="install-code"><code>{verdict.install_command}</code><button className="copy-btn" onClick={() => copy(verdict.install_command, "install")}>{copied === "install" ? "copied" : "copy"}</button></div><p className="install-disclaimer">Copied manually by you. Skill Passport never executes installations automatically.</p></>}</section>
        </>}
      </main>
    </div>
  </>;
}
