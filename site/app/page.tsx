const steps = [
  ["01", "Review", "A reviewer proposes a concrete code claim."],
  ["02", "Challenge", "A critic tests the claim’s reasoning."],
  ["03", "Verify", "A deterministic receipt checks the evidence."],
];

const protocols = [
  {
    name: "AR",
    label: "Textual consensus",
    copy: "A reviewer proposes findings and a critic challenges them. Agreement remains persuasive, not proven.",
  },
  {
    name: "AR-Text",
    label: "Evidence described",
    copy: "The reviewer adds textual support when challenged, but nothing independently executes or checks it.",
  },
  {
    name: "EVAR-Hard",
    label: "Evidence verified",
    copy: "A structured receipt must pass deterministic verification before a finding can become actionable.",
  },
];

const results = [
  ["GPT-4.1 · AR", "0.400", "0.700"],
  ["GPT-4.1 · AR-Text", "0.200", "0.700"],
  ["GPT-4.1 · EVAR-Hard", "0.300", "0.600"],
  ["GPT-4.1 mini · AR", "0.400", "0.900"],
  ["GPT-4.1 mini · AR-Text", "0.200", "0.700"],
  ["GPT-4.1 mini · EVAR-Hard", "0.200", "0.700"],
];

const guardrails = [
  "Ground-truth labels never enter agent prompts.",
  "Prompts, verifier code, configs, cases, and patches were frozen before model calls.",
  "Failed runs remain explicit; infrastructure-invalid attempts are preserved separately.",
  "All 720 canonical records and transcripts received judge-free audits.",
];

export default function Home() {
  return (
    <main>
      <nav className="nav shell" aria-label="Primary navigation">
        <a className="wordmark" href="#top" aria-label="EVAR home">
          EVAR<span>.</span>
        </a>
        <div className="navLinks">
          <a href="#method">Method</a>
          <a href="#evidence">Evidence</a>
          <a href="#limits">Limits</a>
          <a className="navCta" href="https://github.com/kishormorol/evar/blob/master/PAPER.md">
            Read the paper
          </a>
        </div>
      </nav>

      <section className="hero shell" id="top">
        <div className="heroCopy">
          <p className="eyebrow">
            <span /> Evidence-verified adversarial review
          </p>
          <h1>
            Agreement is not
            <br />
            <em>evidence.</em>
          </h1>
          <p className="lede">
            EVAR asks a sharper question of AI code review: can a finding survive
            a mechanical check, not merely convince another model?
          </p>
          <div className="heroActions">
            <a className="button primary" href="#method">
              See how EVAR works <span aria-hidden="true">→</span>
            </a>
            <a className="button secondary" href="https://github.com/kishormorol/evar">
              View repository
            </a>
          </div>
        </div>

        <div className="protocolCard" id="method" aria-label="EVAR protocol flow">
          <div className="cardHeader">
            <span>Protocol / EVAR-Hard</span>
            <span className="liveDot">Research harness</span>
          </div>
          <div className="steps">
            {steps.map(([number, title, copy], index) => (
              <div className="step" key={number}>
                <span className="stepNumber">{number}</span>
                <div>
                  <strong>{title}</strong>
                  <p>{copy}</p>
                </div>
                {index < steps.length - 1 && <span className="connector" />}
              </div>
            ))}
          </div>
          <div className="gate">
            <span className="gateMark">✓</span>
            <div>
              <strong>Actionable only when verified</strong>
              <p>Unsupported receipts stop at the gate.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="signal" id="evidence" aria-label="Current benchmark signal">
        <div className="shell signalGrid">
          <div className="signalIntro">
            <p className="eyebrow light">Untouched final holdout</p>
            <p>Human PR 20 · GPT-4.1 mini · one frozen run</p>
          </div>
          <div className="metric">
            <strong>0.200</strong>
            <span>False consensus rate</span>
          </div>
          <div className="metric">
            <strong>0.700</strong>
            <span>Supported claim retention</span>
          </div>
          <p className="caveat">
            EVAR ties AR-Text on the mini model and trails it on GPT-4.1.
            Verification is auditable—not a free performance win.
          </p>
        </div>
      </section>

      <section className="thesis shell sectionPad">
        <div className="sectionKicker">The research problem</div>
        <div className="thesisGrid">
          <h2>Two models can agree—and still be wrong.</h2>
          <div className="thesisCopy">
            <p>
              Reviewer–critic systems can converge on plausible findings because both
              agents operate inside the same textual frame. EVAR adds an external gate:
              a claim must point to evidence that can be mechanically checked.
            </p>
            <p>
              The experiment measures the tradeoff between rejecting unsupported claims
              and retaining supported ones, under equal model and interaction budgets.
            </p>
          </div>
        </div>
      </section>

      <section className="protocols sectionPad" aria-labelledby="protocol-heading">
        <div className="shell">
          <div className="sectionHeading">
            <div>
              <p className="sectionKicker">Three protocols, one question</p>
              <h2 id="protocol-heading">Where should trust enter the loop?</h2>
            </div>
            <p>Same task. Same budgets. Different standards of evidence.</p>
          </div>
          <div className="protocolGrid">
            {protocols.map((protocol, index) => (
              <article className={index === 2 ? "protocolTile featured" : "protocolTile"} key={protocol.name}>
                <span className="tileIndex">0{index + 1}</span>
                <h3>{protocol.name}</h3>
                <strong>{protocol.label}</strong>
                <p>{protocol.copy}</p>
                <span className="tileRule" />
                <small>{index === 2 ? "Mechanical acceptance gate" : "Model-mediated acceptance"}</small>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="results shell sectionPad" aria-labelledby="results-heading">
        <div className="resultsIntro">
          <p className="sectionKicker">Human PR 20 · untouched evaluation</p>
          <h2 id="results-heading">A useful negative result.</h2>
          <p>
            Ten real human review comments become 20 temporal cases across Black, pytest,
            Rich, Pydantic, and Poetry. The reviewed commit supports each claim; the merge
            commit no longer does. Lower FCR is better; higher SCR is better.
          </p>
          <p>
            The v2 evidence format verifies 18 of 20 receipts for each model. That solves
            much of the mechanical retention problem, but it does not outperform the
            simpler AR-Text baseline on final decisions.
          </p>
        </div>
        <div className="resultsTable" role="table" aria-label="Human PR 20 frozen holdout results">
          <div className="resultRow resultHead" role="row">
            <span role="columnheader">Protocol</span>
            <span role="columnheader">FCR ↓</span>
            <span role="columnheader">SCR ↑</span>
          </div>
          {results.map(([protocol, fcr, scr], index) => (
            <div className={index === 2 || index === 5 ? "resultRow evar" : "resultRow"} role="row" key={protocol}>
              <strong role="cell">{protocol}</strong>
              <span role="cell">{fcr}</span>
              <span role="cell">{scr}</span>
            </div>
          ))}
          <p className="tableNote">
            Every condition has ten cases per label, so intervals are wide. Paired deltas,
            tokens, latency, source links, and the complete audit are in the artifact.
          </p>
        </div>
      </section>

      <section className="limits sectionPad" id="limits" aria-labelledby="limits-heading">
        <div className="shell limitsGrid">
          <div>
            <p className="sectionKicker inverse">Scientific guardrails</p>
            <h2 id="limits-heading">Built to expose failure, not hide it.</h2>
            <p className="limitsLead">
              EVAR is a research harness, not a production code-review product. The public
              evidence includes the mixed result and remains deliberately bounded.
            </p>
          </div>
          <ol className="guardrailList">
            {guardrails.map((guardrail, index) => (
              <li key={guardrail}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{guardrail}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="run shell sectionPad" aria-labelledby="run-heading">
        <div className="runCopy">
          <p className="sectionKicker">Run the harness</p>
          <h2 id="run-heading">Reproduce the comparison.</h2>
          <p>Python 3.11+ · deterministic smoke tests · optional OpenAI-backed experiments.</p>
          <a className="textLink" href="https://github.com/kishormorol/evar/blob/master/README.md">
            Read the full setup guide <span aria-hidden="true">↗</span>
          </a>
        </div>
        <div className="terminal" aria-label="EVAR command example">
          <div className="terminalBar"><span /><span /><span /><small>evar / experiment</small></div>
          <pre><code><span>$</span> python -m evar.freeze verify \
  --manifest benchmarks/human_pr_20/freeze_manifest.json

<span>$</span> PYTHONPATH=. python \
  scripts/report_human_pr_20.py</code></pre>
        </div>
      </section>

      <footer>
        <div className="shell footerGrid">
          <div>
            <a className="wordmark footerMark" href="#top">EVAR<span>.</span></a>
            <p>Evidence-Verified Adversarial Review</p>
          </div>
          <p className="footerStatement">Make agreement earn its confidence.</p>
          <div className="footerLinks">
            <a href="https://github.com/kishormorol/evar">Repository ↗</a>
            <a href="https://github.com/kishormorol/evar/blob/master/PAPER.md">Paper ↗</a>
            <a href="https://github.com/kishormorol/evar/tree/master/benchmarks/human_pr_20">Artifact ↗</a>
            <a href="https://github.com/kishormorol/evar/blob/master/review/INDEPENDENT_REVIEW.md">Review ↗</a>
          </div>
        </div>
      </footer>
    </main>
  );
}
