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
  ["AR", "0.300", "1.000"],
  ["AR-Text", "0.100", "0.900"],
  ["EVAR-Hard", "0.100", "0.900"],
  ["EVAR-Hard + repair*", "0.000", "1.000"],
];

const guardrails = [
  "Ground-truth labels never enter agent prompts.",
  "The verifier sees receipts and repository evidence—not expected answers.",
  "Failed runs remain in the result set instead of disappearing.",
  "Model configuration, prompts, budgets, and seeds are recorded.",
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
            <p className="eyebrow light">Current diagnostic signal</p>
            <p>External PR 20 · EVAR-Hard with receipt repair</p>
          </div>
          <div className="metric">
            <strong>0.000</strong>
            <span>False consensus rate</span>
          </div>
          <div className="metric">
            <strong>1.000</strong>
            <span>Supported claim retention</span>
          </div>
          <p className="caveat">
            Development result on an inspected 20-case benchmark—not a claim of
            real-world performance.
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
          <p className="sectionKicker">External PR 20</p>
          <h2 id="results-heading">A harder, commit-grounded stress test.</h2>
          <p>
            Twenty supported and unsupported claims drawn from pinned public repository
            commits. Lower FCR is better; higher SCR is better.
          </p>
        </div>
        <div className="resultsTable" role="table" aria-label="External PR 20 benchmark results">
          <div className="resultRow resultHead" role="row">
            <span role="columnheader">Protocol</span>
            <span role="columnheader">FCR ↓</span>
            <span role="columnheader">SCR ↑</span>
          </div>
          {results.map(([protocol, fcr, scr], index) => (
            <div className={index === 3 ? "resultRow diagnostic" : "resultRow"} role="row" key={protocol}>
              <strong role="cell">{protocol}</strong>
              <span role="cell">{fcr}</span>
              <span role="cell">{scr}</span>
            </div>
          ))}
          <p className="tableNote">
            *Diagnostic result after tuning on this inspected benchmark. It is development
            evidence, not a fresh held-out result.
          </p>
        </div>
      </section>

      <section className="limits sectionPad" id="limits" aria-labelledby="limits-heading">
        <div className="shell limitsGrid">
          <div>
            <p className="sectionKicker inverse">Scientific guardrails</p>
            <h2 id="limits-heading">Built to expose failure, not hide it.</h2>
            <p className="limitsLead">
              EVAR is a research harness, not a production code-review product. The current
              evidence is promising—and deliberately bounded.
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
          <pre><code><span>$</span> python -m evar.run \
  --protocol evar \
  --cases cases.jsonl

<span>$</span> python -m evar.eval_table \
  --results results/*.jsonl \
  --by-family --costs</code></pre>
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
          </div>
        </div>
      </footer>
    </main>
  );
}
