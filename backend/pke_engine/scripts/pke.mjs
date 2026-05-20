#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import http from "node:http";
import os from "node:os";
import { spawnSync } from "node:child_process";

const VAULT = process.env.PKE_VAULT || path.join(os.homedir(), "MyKnowledge");
const DEFAULT_VAULT = VAULT;
const DEFAULT_COLLECTION = "myknowledge";
const DEFAULT_STATE = path.join(VAULT, ".pke", "state.json");
const QMD_PATH = process.env.PKE_QMD_PATH || "/opt/homebrew/bin";
const QMD_ENV = { ...process.env, PATH: QMD_PATH ? `${QMD_PATH}:${process.env.PATH || ""}` : (process.env.PATH || "") };

const args = process.argv.slice(2);
const command = args.shift() || "help";
const opts = parseOptions(args);
const vault = opts.vault || DEFAULT_VAULT;
const collection = opts.collection || DEFAULT_COLLECTION;
const statePath = opts.state || DEFAULT_STATE;
const pkeDir = path.dirname(statePath);
const monitorStatePath = opts.monitorState || path.join(pkeDir, "monitor-state.json");
const eventsPath = opts.events || path.join(pkeDir, "events.jsonl");
const reportsDir = opts.reports || path.join(pkeDir, "reports");
const proposalsDir = opts.proposals || path.join(pkeDir, "proposals");
const appliedDir = opts.applied || path.join(pkeDir, "applied");
const rejectedDir = opts.rejected || path.join(pkeDir, "rejected");
const backupsDir = opts.backups || path.join(pkeDir, "backups");

const wikiDir = path.join(vault, "wiki");
const rawDir = path.join(vault, "raw");
const KNOWLEDGE_SECTIONS = [
  "Current Understanding",
  "Key Principles",
  "Evidence",
  "Conflicts / Evolution",
  "Stale Or Risky Claims",
  "Open Questions",
  "Related Pages",
];

main().catch((err) => {
  console.error(`pke: ${err.message}`);
  process.exitCode = 1;
});

async function main() {
  switch (command) {
    case "help":
    case "--help":
    case "-h":
      return help();
    case "status":
      return status();
    case "use":
      return useCommand(args.join(" ").trim());
    case "changed":
      return changedCommand({ save: opts.save || opts.baseline });
    case "daily":
      return dailyCommand();
    case "learn":
      return learnCommand(args[0], args[1]);
    case "capture":
      return captureCommand(args[0]);
    case "compile":
      return compileCommand(args.join(" ").trim());
    case "close-session":
      return closeSessionCommand(args[0]);
    case "stale":
      return staleCommand(args.join(" ").trim());
    case "monitor":
      return monitorCommand();
    case "events":
      return eventsCommand();
    case "report":
      return reportCommand(args[0] || "latest");
    case "dashboard":
      return dashboardCommand();
    case "candidates":
      return candidatesCommand();
    case "propose":
      return proposeCommand();
    case "proposals":
      return proposalsCommand();
    case "proposal":
      return proposalCommand(args[0]);
    case "apply":
      return applyCommand(args[0]);
    case "reject":
      return rejectCommand(args[0]);
    case "improve":
      return improveCommand();
    default:
      throw new Error(`unknown command "${command}". Run: pke help`);
  }
}

function help() {
  console.log(`Personal Knowledge Engine CLI

Usage:
  pke status
  pke use "question"
  pke changed [--save]
  pke daily [--save]
  pke learn draft.md final.md
  pke capture path/to/source.md [--write]
  pke compile "topic or page"
  pke close-session transcript.md
  pke stale "topic or page" [--sensitivity <low|medium|high>]
  pke monitor [--path vault-relative-path] [--watch]
  pke events [--limit 20]
  pke report latest|today|usage [--json]
  pke dashboard [--port 8787] [--path raw/] [--auto-scan]
  pke candidates              (confidence-adjusted, sorted by acceptance history)
  pke improve [--json] [--apply]
  pke propose --path raw/note.md [--target wiki/page.md]
  pke propose --event event-id [--target wiki/page.md]
  pke proposals
  pke proposal proposal-id
  pke apply proposal-id       (use --batch-safe for safe batch approval)
  pke reject proposal-id

Options:
  --vault <path>        Vault path (default: ${DEFAULT_VAULT})
  --collection <name>   qmd collection (default: ${DEFAULT_COLLECTION})
  --state <path>        State file (default: ${DEFAULT_STATE})
  --path <path>         Scope monitor/watch to a vault-relative path
  --json                Output JSON where supported
  --save                Save changed-file baseline
  --usage               Generate usage pattern report (alias: pke report usage)
  --write               Allow commands that write evidence files
  --watch               Watch a required --path in realtime
  --port <number>       Dashboard port (default: 8787)
  --auto-scan           Dashboard scans the configured --path on refresh
  --target <path>       Target wiki page for a proposal
  --apply               Write self-improvement proposals (for improve command)

Environment:
  PKE_VAULT      Knowledge vault root (default: ~/MyKnowledge)
  PKE_QMD_PATH   Directory containing qmd binary (default: /opt/homebrew/bin)

Principles:
  Use is automatic. Compile requires a definite update clue.
  Raw files are evidence and are rarely edited.
  Wiki writes are not performed by this MVP unless explicitly implemented/approved.

Limits:
  Max file size:       10 MB (larger files skipped)
  Event retention:     100,000 events (older archived)
  Pending proposals:   200 max (warning if exceeded)
  Candidates:          100 max, 30-day expiry
  Daily proposals:     5 max (rate-limited by priority)
  Report retention:    90 days (older archived)
`);
}

function status() {
  const qmdStatus = runQmd(["status"], { allowFailure: true });
  const coverage = templateCoverage();
  const state = readState();
  const result = {
    vault,
    wikiDir,
    rawDir,
    statePath,
    baselineAt: state.baselineAt || null,
    trackedFiles: state.files ? Object.keys(state.files).length : 0,
    templateCoverage: coverage,
    qmdStatus: qmdStatus.stdout.trim(),
    qmdError: qmdStatus.stderr.trim(),
  };
  if (opts.json) return printJson(result);
  console.log(result.qmdStatus || result.qmdError);
  console.log("");
  console.log("PKE");
  console.log(`  Vault:        ${vault}`);
  console.log(`  State:        ${statePath}`);
  console.log(`  Baseline:     ${result.baselineAt || "none"}`);
  console.log(`  Tracked:      ${result.trackedFiles} files`);
  console.log(`  Wiki pages:   ${coverage.total}`);
  console.log(`  Template:     ${coverage.compliant}/${coverage.total} compliant`);
  if (coverage.missing.length) {
    console.log(`  Missing:      ${coverage.missing.length} page(s)`);
  }
}

function useCommand(query) {
  if (!query) throw new Error("usage: pke use \"question\"");
  const res = runQmd(["query", query, "-c", collection, "-n", String(opts.n || 8)], { allowFailure: false });
  process.stdout.write(res.stdout);
  if (res.stderr.trim()) process.stderr.write(res.stderr);
}

function changedCommand({ save = false } = {}) {
  const current = scanVault();
  const state = readState();
  const previous = state.files || {};
  const changes = diffSnapshots(previous, current.files);
  const result = {
    vault,
    baselineAt: state.baselineAt || null,
    checkedAt: new Date().toISOString(),
    counts: {
      added: changes.added.length,
      modified: changes.modified.length,
      removed: changes.removed.length,
      totalChanged: changes.added.length + changes.modified.length + changes.removed.length,
    },
    changes,
  };
  if (save) {
    writeState({ baselineAt: result.checkedAt, files: current.files });
    result.saved = true;
  }
  if (opts.json) return printJson(result);
  printChanges(result);
}

function dailyCommand() {
  const current = scanVault();
  const state = readState();
  const previous = state.files || {};
  const changes = diffSnapshots(previous, current.files);
  const MAX_DAILY_PROPOSALS = 5;
  const compiledCandidates = compileCandidates(changes);
  // P6-01: Merge self-improvement proposals before rate-limiting
  const selfImproveProposals = generateRetrievalTuningProposals();
  const allCandidates = [...compiledCandidates, ...selfImproveProposals];
  const candidates = allCandidates.length > MAX_DAILY_PROPOSALS
    ? filterProposalsByPriority(allCandidates, MAX_DAILY_PROPOSALS)
    : allCandidates;
  const result = {
    mode: "proposal-only",
    checkedAt: new Date().toISOString(),
    baselineAt: state.baselineAt || null,
    changed: changes,
    candidates,
    totalCandidates: allCandidates.length,
    recommendations: [
      "Review changed raw files as evidence only.",
      "Compile wiki only when you explicitly approve a proposed update.",
      "Run `pke changed --save` after reviewing to set a new baseline.",
      "Run `PATH=/opt/homebrew/bin:$PATH qmd update` and `qmd embed -c myknowledge` after approved wiki edits.",
    ],
  };
  if (opts.save) {
    writeState({ baselineAt: result.checkedAt, files: current.files });
    result.saved = true;
  }
  if (opts.json) return printJson(result);
  console.log("Daily Compilation Proposal");
  console.log(`  Mode:      ${result.mode}`);
  console.log(`  Baseline:  ${result.baselineAt || "none"}`);
  console.log(`  Checked:   ${result.checkedAt}`);
  console.log("");
  printChanges({ changes, counts: {
    added: changes.added.length,
    modified: changes.modified.length,
    removed: changes.removed.length,
    totalChanged: changes.added.length + changes.modified.length + changes.removed.length,
  } });
  console.log("");
  console.log("Compile Candidates");
  if (!candidates.length) {
    console.log("  none");
  } else {
    if (allCandidates.length > MAX_DAILY_PROPOSALS) {
      console.log(`  pke: showing top ${candidates.length} of ${allCandidates.length} candidates (${allCandidates.length - candidates.length} deferred)`);
    }
    for (const c of candidates) {
      if (c.proposal_type === "retrieval_tuning") {
        console.log(`  - [self-improve] ${c.target_page}`);
        console.log(`      ${c.reason}`);
      } else {
        console.log(`  - ${c.kind}: ${c.path}`);
        for (const hint of c.hints) console.log(`      ${hint}`);
      }
    }
  }
  console.log("");
  console.log("Recommendations");
  for (const r of result.recommendations) console.log(`  - ${r}`);
}

function learnCommand(draftFile, finalFile) {
  if (!draftFile || !finalFile) throw new Error("usage: pke learn draft.md final.md");
  const draftPath = path.resolve(draftFile);
  const finalPath = path.resolve(finalFile);
  const draft = readTextFile(draftPath);
  const final = readTextFile(finalPath);
  const diff = lineDiff(draft, final);
  const classified = classifyDiff(diff);
  const result = {
    draft: draftPath,
    final: finalPath,
    summary: {
      addedLines: diff.added.length,
      removedLines: diff.removed.length,
      unchangedLines: diff.unchanged,
    },
    classifications: classified,
    proposedCompile: buildLearnProposal(classified),
    updateRule: "proposal-only; wiki update requires explicit approval",
  };
  if (opts.json) return printJson(result);
  console.log("Draft-Final Learning Proposal");
  console.log(`  Draft: ${draftPath}`);
  console.log(`  Final: ${finalPath}`);
  console.log(`  Added lines:   ${result.summary.addedLines}`);
  console.log(`  Removed lines: ${result.summary.removedLines}`);
  console.log("");
  for (const group of classified) {
    console.log(`${group.label}`);
    if (!group.items.length) {
      console.log("  none");
      continue;
    }
    for (const item of group.items.slice(0, 12)) console.log(`  - ${trimLine(item)}`);
  }
  console.log("");
  console.log("Proposed Compile");
  for (const p of result.proposedCompile) console.log(`  - ${p}`);
  console.log("");
  console.log("No wiki files were changed.");
}

function captureCommand(sourceFile) {
  if (!sourceFile) throw new Error("usage: pke capture path/to/source.md [--write]");
  const sourcePath = path.resolve(sourceFile);
  if (!fs.existsSync(sourcePath)) throw new Error(`source not found: ${sourcePath}`);
  const targetDir = path.join(rawDir, "_captures");
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const base = path.basename(sourcePath);
  const target = path.join(targetDir, `${timestamp}-${base}`);
  const result = {
    source: sourcePath,
    target,
    write: Boolean(opts.write),
    rule: "capture stores evidence, not conclusions",
  };
  if (opts.write) {
    fs.mkdirSync(targetDir, { recursive: true });
    fs.copyFileSync(sourcePath, target);
  }
  if (opts.json) return printJson(result);
  console.log("Capture");
  console.log(`  Source: ${sourcePath}`);
  console.log(`  Target: ${target}`);
  console.log(`  Write:  ${opts.write ? "yes" : "no, preview only"}`);
  console.log("  Wiki:   not updated");
}

function compileCommand(topic) {
  if (!topic) throw new Error("usage: pke compile \"topic or page\"");
  const before = scanVault();
  const state = readState();
  const baselineChanges = diffSnapshots(state.files || {}, before.files);
  const res = runQmd(["query", topic, "-c", collection, "-n", "8"], { allowFailure: true });
  const after = scanVault();
  const commandChanges = diffSnapshots(before.files, after.files);
  const changeReport = {
    mode: "proposal-only",
    changedByThisCommand: commandChanges,
    changedSinceBaseline: baselineChanges,
    knowledgeWrites: [],
    evidenceWrites: [],
    unresolvedItems: [
      "No approved wiki patch was applied in this MVP compile run.",
      "Review the target page and approve an exact update before writing knowledge.",
    ],
  };
  if (opts.json) {
    return printJson({
      topic,
      collection,
      relevantContext: res.stdout || res.stderr,
      changeReport,
      nextStep: "Review the target page and approve an exact wiki update before writing.",
    });
  }
  console.log("Compile Plan");
  console.log(`  Topic: ${topic}`);
  console.log("  Mode:  proposal-only");
  console.log("");
  console.log("Relevant Context");
  process.stdout.write(res.stdout || res.stderr);
  console.log("");
  printCompileChangeReport(changeReport);
  console.log("");
  console.log("Next Step");
  console.log("  Review the target page and approve an exact wiki update before writing.");
}

function closeSessionCommand(transcriptFile) {
  if (!transcriptFile) throw new Error("usage: pke close-session transcript.md");
  const transcriptPath = path.resolve(transcriptFile);
  const text = readTextFile(transcriptPath);
  const lines = text.split(/\n/).map((l) => l.trim()).filter(Boolean);
  const signal = lines.filter((l) => /decid|conclusion|therefore|update|should|must|结论|决定|应该|更新/.test(l.toLowerCase()));
  const result = {
    transcript: transcriptPath,
    lineCount: lines.length,
    possibleDurableSignals: signal.slice(0, 30),
    rule: "proposal-only; wiki update requires explicit approval",
  };
  if (opts.json) return printJson(result);
  console.log("Session Compile Proposal");
  console.log(`  Transcript: ${transcriptPath}`);
  console.log(`  Lines:      ${lines.length}`);
  console.log("");
  console.log("Possible Durable Signals");
  if (!signal.length) console.log("  none detected by simple local scan");
  for (const s of signal.slice(0, 20)) console.log(`  - ${trimLine(s)}`);
  console.log("");
  console.log("No wiki files were changed.");
}

function staleCommand(topic) {
  if (!topic) throw new Error("usage: pke stale \"topic or page\"");
  const sensitivity = opts.sensitivity || "medium";
  let keywords;
  if (sensitivity === "low") {
    keywords = "stale risky";
  } else if (sensitivity === "high") {
    keywords = "stale risky claims assumptions outdated deprecated superseded";
  } else {
    keywords = "stale risky claims assumptions";
  }
  const res = runQmd(["query", `${topic} ${keywords}`, "-c", collection, "-n", "8"], { allowFailure: true });
  console.log("Staleness Review Context");
  console.log(`  Topic:       ${topic}`);
  console.log(`  Sensitivity: ${sensitivity}`);
  console.log("  Mode:        proposal-only");
  console.log("");
  process.stdout.write(res.stdout || res.stderr);
}

function monitorCommand() {
  const scope = opts.path ? resolveVaultScope(opts.path) : null;
  if (opts.watch) return watchMonitor(scope);
  const report = runMonitor({ scope, source: "monitor" });
  if (opts.json) return printJson(report);
  printMonitorReport(report);
}

function eventsCommand() {
  const limit = Number(opts.limit || 20);
  const events = readEvents().slice(-limit);
  if (opts.json) return printJson(events);
  console.log("Knowledge Events");
  if (!events.length) {
    console.log("  none");
    return;
  }
  for (const event of events) {
    console.log(`- ${event.time} ${event.event_type} ${event.path || ""}`);
    if (event.summary) console.log(`    ${trimLine(event.summary)}`);
  }
}

function reportCommand(which) {
  if (which === "usage" || opts.usage) {
    const report = generateUsageReport();
    if (opts.json) return printJson(report);
    console.log(`Usage Pattern Report (last ${report.timeWindow} days)`);
    console.log("====================================");
    console.log(`Total events: ${report.totalEvents}`);
    console.log(`Total proposals: ${report.totalProposals}`);
    console.log(`Approval rate: ${report.approvalRate !== null ? report.approvalRate.toFixed(1) + "%" : "N/A"}`);
    console.log(`Compile velocity: ${report.compileVelocity.toFixed(1)} proposals/week`);
    console.log("");
    console.log("Top Topics by Activity:");
    if (!report.topTopics.length) {
      console.log("  none");
    } else {
      report.topTopics.forEach((t, i) => {
        const acceptance = (t.approvals + t.rejections) > 0
          ? ((t.approvals / (t.approvals + t.rejections)) * 100).toFixed(0) + "%"
          : "N/A";
        console.log(`  ${String(i + 1).padStart(2)}. ${t.topic.padEnd(20)} events: ${t.events}  proposals: ${t.proposals}  acceptance: ${acceptance}`);
      });
    }
    return;
  }
  const reports = listReports();
  let selected = [];
  if (which === "latest") selected = reports.slice(-1);
  else if (which === "today") {
    const today = new Date().toISOString().slice(0, 10);
    selected = reports.filter((file) => path.basename(file).startsWith(today));
  } else {
    throw new Error("usage: pke report latest|today");
  }
  if (opts.json) return printJson(selected.map((file) => ({ path: file, text: fs.readFileSync(file, "utf8") })));
  if (!selected.length) {
    console.log("Knowledge Monitor Report");
    console.log("  none");
    return;
  }
  for (const file of selected) {
    console.log(fs.readFileSync(file, "utf8").trimEnd());
    console.log("");
  }
}

function candidatesCommand() {
  const MAX_CANDIDATES = 100;
  const EXPIRY_DAYS = 30;
  const cutoff = new Date(Date.now() - EXPIRY_DAYS * 24 * 60 * 60 * 1000).toISOString();
  const events = readEvents()
    .filter(isCompileTriggerEvent)
    .filter((e) => e.time >= cutoff)
    .slice(-MAX_CANDIDATES)
    .reverse();
  const candidates = events.map(eventToCandidate);

  // P6-02: Adjust confidence by acceptance history
  const rates = analyzeAcceptanceRates();
  const hasHistory = rates.totalApplied + rates.totalRejected > 0;
  for (const candidate of candidates) {
    const baseConf = candidate.confidence || "medium";
    candidate.adjustedConfidence = hasHistory
      ? adjustConfidenceByHistory(baseConf, candidate.event_type, rates)
      : baseConf;
  }
  // Sort by adjusted confidence (highest first)
  const confOrder = { high: 3, medium: 2, low: 1 };
  candidates.sort((a, b) => (confOrder[b.adjustedConfidence] || 0) - (confOrder[a.adjustedConfidence] || 0));

  if (opts.json) return printJson(candidates);
  console.log("Compile Candidates");
  if (hasHistory) {
    console.log(`  (confidence adjusted by acceptance history: ${(rates.overallRate * 100).toFixed(0)}% overall rate)`);
  }
  if (!candidates.length) {
    console.log("  none");
    return;
  }
  for (const candidate of candidates) {
    console.log(`- ${candidate.event_type}: ${candidate.source_file}`);
    console.log(`    reason: ${candidate.reason}`);
    console.log(`    confidence: ${candidate.adjustedConfidence}`);
    console.log(`    suggested target: ${candidate.suggested_target || "needs selection"}`);
  }
}

function proposeCommand() {
  const eventId = opts.event;
  const sourcePath = opts.path;
  if (!eventId && !sourcePath) throw new Error("usage: pke propose --path raw/note.md [--target wiki/page.md] OR pke propose --event event-id");
  const kind = fileKind(sourcePath || "");
  const event = eventId ? findEvent(eventId) : makeEvent(`${kind}_modified`, sourcePath, kind, "manual", `Manual proposal for ${sourcePath}`);
  if (!event) throw new Error(`event not found: ${eventId}`);
  const proposal = createProposalFromEvent(event, opts.target);
  writeProposal(proposal);
  if (opts.json) return printJson(proposal);
  printProposal(proposal);
}

function proposalsCommand() {
  const proposals = listProposals().filter((proposal) => !opts.status || proposal.status === opts.status);
  if (opts.json) return printJson(proposals);
  console.log("Compile Proposals");
  if (!proposals.length) {
    console.log("  none");
    return;
  }
  for (const proposal of proposals) {
    console.log(`- ${proposal.id} [${proposal.status}]`);
    console.log(`    source: ${proposal.source_files.join(", ")}`);
    console.log(`    target: ${proposal.target_page || "needs selection"}`);
    console.log(`    reason: ${proposal.reason}`);
  }
}

function proposalCommand(id) {
  if (!id) throw new Error("usage: pke proposal proposal-id");
  const proposal = readProposal(id);
  if (opts.json) return printJson(proposal);
  printProposal(proposal);
}

function applyCommand(id) {
  if (opts.batchSafe) return applyBatchSafe(id);
  if (!id) throw new Error("usage: pke apply proposal-id");
  const proposal = readProposal(id);
  const result = applyProposal(proposal);
  if (opts.json) return printJson(result);
  console.log("Applied Proposal");
  console.log(`  Proposal: ${proposal.id}`);
  console.log(`  Target:   ${proposal.target_page}`);
  console.log(`  Backup:   ${result.backupPath}`);
  console.log(`  Changed:  ${result.changed ? "yes" : "no"}`);
  if (result.qmdRefresh) {
    console.log(`  qmd update: ${result.qmdRefresh.update.status === 0 ? "ok" : "failed"}`);
    console.log(`  qmd embed:  ${result.qmdRefresh.embed.status === 0 ? "ok" : "failed"}`);
  }
}

function isSafeAppendOnlyProposal(proposal) {
  if (!proposal || !proposal.patch || !proposal.patch.operations) return false;
  if (proposal.confidence !== "high") return false;
  const safeSections = ["Evidence", "Open Questions", "Related Pages"];
  return proposal.patch.operations.every(op =>
    safeSections.includes(op.section) &&
    (op.type === "append_to_section" || op.type === "create_page")
  );
}

function applyBatchSafe(id) {
  if (id) {
    // Specific proposal ID provided with --batch-safe
    const proposal = readProposal(id);
    if (!isSafeAppendOnlyProposal(proposal)) {
      console.log(`Proposal ${id} is not eligible for fast-path (requires manual review)`);
      return;
    }
    const result = applyProposal(proposal);
    appendEvents([{ type: "proposal_applied", id: proposal.id, target: proposal.target_page, method: "batch-safe", ts: new Date().toISOString() }]);
    if (opts.json) return printJson(result);
    console.log("Applied Proposal (fast-path)");
    console.log(`  Proposal: ${proposal.id}`);
    console.log(`  Target:   ${proposal.target_page}`);
    console.log(`  Backup:   ${result.backupPath}`);
    console.log(`  Changed:  ${result.changed ? "yes" : "no"}`);
    return;
  }

  // No ID: batch apply all safe pending proposals
  const allProposals = listProposals();
  const pending = allProposals.filter(p => p.status === "pending");
  const safe = pending.filter(p => isSafeAppendOnlyProposal(p));

  if (!safe.length) {
    console.log("No safe proposals eligible for batch approval.");
    return;
  }

  console.log(`Found ${safe.length} safe proposal${safe.length === 1 ? "" : "s"} eligible for batch approval`);

  let applied = 0;
  const results = [];
  for (const proposal of safe) {
    try {
      const result = applyProposal(proposal);
      appendEvents([{ type: "proposal_applied", id: proposal.id, target: proposal.target_page, method: "batch-safe", ts: new Date().toISOString() }]);
      applied++;
      results.push({ id: proposal.id, target: proposal.target_page, changed: result.changed, error: null });
      console.log(`  Applied: ${proposal.id} -> ${proposal.target_page}`);
    } catch (err) {
      results.push({ id: proposal.id, target: proposal.target_page, changed: false, error: err.message });
      console.log(`  Failed:  ${proposal.id} - ${err.message}`);
    }
  }

  console.log(`\nApplied ${applied}/${safe.length} safe proposals`);
  if (opts.json) printJson(results);
}

function rejectCommand(id) {
  if (!id) throw new Error("usage: pke reject proposal-id");
  const proposal = readProposal(id);
  proposal.status = "rejected";
  proposal.rejectedAt = new Date().toISOString();
  writeProposal(proposal);
  fs.mkdirSync(rejectedDir, { recursive: true });
  fs.copyFileSync(proposalPath(proposal.id), path.join(rejectedDir, `${proposal.id}.json`));
  if (opts.json) return printJson(proposal);
  console.log(`Rejected proposal: ${proposal.id}`);
}

function dashboardCommand() {
  const port = Number(opts.port || 8787);
  const host = opts.host || "127.0.0.1";
  const scope = opts.path ? resolveVaultScope(opts.path) : null;
  const server = http.createServer((req, res) => {
    const url = new URL(req.url || "/", `http://${host}:${port}`);
    if (url.pathname === "/api/dashboard") {
      if (opts.autoScan) runMonitor({ scope, source: "dashboard", writeEmptyReport: false });
      return sendJson(res, dashboardData(scope));
    }
    if (url.pathname === "/api/scan") {
      const report = runMonitor({ scope, source: "dashboard", writeEmptyReport: true });
      return sendJson(res, { report, dashboard: dashboardData(scope) });
    }
    if (url.pathname === "/api/propose") {
      const eventId = url.searchParams.get("event");
      const target = url.searchParams.get("target") || undefined;
      const event = eventId ? findEvent(eventId) : null;
      if (!event) return sendJson(res, { error: "event not found" }, 404);
      const proposal = createProposalFromEvent(event, target);
      writeProposal(proposal);
      return sendJson(res, { proposal, dashboard: dashboardData(scope) });
    }
    if (url.pathname === "/api/apply") {
      const id = url.searchParams.get("id");
      if (!id) return sendJson(res, { error: "missing id" }, 400);
      try {
        const result = applyProposal(readProposal(id));
        return sendJson(res, { result, dashboard: dashboardData(scope) });
      } catch (err) {
        return sendJson(res, { error: err.message }, 400);
      }
    }
    if (url.pathname === "/api/reject") {
      const id = url.searchParams.get("id");
      if (!id) return sendJson(res, { error: "missing id" }, 400);
      try {
        const proposal = readProposal(id);
        proposal.status = "rejected";
        proposal.rejectedAt = new Date().toISOString();
        writeProposal(proposal);
        fs.mkdirSync(rejectedDir, { recursive: true });
        fs.copyFileSync(proposalPath(proposal.id), path.join(rejectedDir, `${proposal.id}.json`));
        return sendJson(res, { proposal, dashboard: dashboardData(scope) });
      } catch (err) {
        return sendJson(res, { error: err.message }, 400);
      }
    }
    if (url.pathname === "/") return sendHtml(res, renderDashboardHtml());
    res.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    res.end("Not found");
  });
  server.listen(port, host, () => {
    console.log("PKE Dashboard");
    console.log(`  URL:     http://${host}:${port}`);
    console.log(`  Vault:   ${vault}`);
    console.log(`  Scope:   ${scope?.rel || "events only"}`);
    console.log(`  Scan:    ${opts.autoScan ? "auto on refresh" : "manual"}`);
    console.log(`  Events:  ${eventsPath}`);
    console.log(`  Reports: ${reportsDir}`);
    console.log("  Press Ctrl-C to stop.");
  });
}

function runMonitor({ scope = null, source = "monitor", writeEmptyReport = true } = {}) {
  const previous = readJsonFile(monitorStatePath, { files: {}, wikiSections: {} });
  const reviewState = readState();
  const monitorFiles = scope ? filterSnapshotByScope(previous.files || {}, scope.rel) : previous.files || {};
  const reviewFiles = scope ? filterSnapshotByScope(reviewState.files || {}, scope.rel) : reviewState.files || {};
  const previousFiles = applyRemovalTombstones({ ...reviewFiles, ...monitorFiles }, previous.removedFiles || {}, scope?.rel);
  const previousSections = scope ? filterSnapshotByScope(previous.wikiSections || {}, scope.rel) : previous.wikiSections || {};
  const current = scanVault(scope);
  const changes = diffSnapshots(previousFiles, current.files);
  const wikiSections = collectWikiSections(current.files);
  const fileEvents = buildFileEvents(changes, source);
  const knowledgeEvents = buildKnowledgeEvents(changes, previousSections, wikiSections, source);
  const events = [...fileEvents, ...knowledgeEvents];
  const checkedAt = new Date().toISOString();
  const summary = summarizeMonitorEvents(events, changes);
  const nextFiles = scope ? mergeScopedSnapshot(previous.files || {}, current.files, scope.rel) : current.files;
  const nextWikiSections = scope ? mergeScopedSnapshot(previous.wikiSections || {}, wikiSections, scope.rel) : wikiSections;
  const nextRemovedFiles = updateRemovalTombstones(previous.removedFiles || {}, changes, current.files, scope?.rel);
  const report = {
    checkedAt,
    scope: scope?.rel || "vault",
    monitorStatePath,
    eventsPath,
    reportsDir,
    counts: {
      filesAdded: changes.added.length,
      filesModified: changes.modified.length,
      filesRemoved: changes.removed.length,
      events: events.length,
    },
    changes,
    summary,
    events,
  };
  if (events.length) appendEvents(events);
  const reportPath = events.length || writeEmptyReport ? writeMonitorReport(report) : null;
  report.reportPath = reportPath;
  writeJsonFile(monitorStatePath, {
    checkedAt,
    scope: report.scope,
    files: nextFiles,
    wikiSections: nextWikiSections,
    removedFiles: nextRemovedFiles,
    latestReport: serializeMonitorReportForState(report),
    latestActivityReport: events.length ? serializeMonitorReportForState(report) : previous.latestActivityReport || null,
  });
  return report;
}

function watchMonitor(scope) {
  if (!scope) {
    throw new Error("realtime watch requires --path. Example: pke monitor --watch --path wiki/");
  }
  if (!fs.existsSync(scope.abs)) throw new Error(`watch path not found: ${scope.rel}`);
  console.log("Knowledge Monitor Watch");
  console.log(`  Vault: ${vault}`);
  console.log(`  Path:  ${scope.rel}`);
  console.log(`  Mode:  scoped polling every ${Number(opts.interval || opts.debounce || 2000)}ms`);
  console.log("  Press Ctrl-C to stop.");
  console.log("");
  const run = () => {
    const report = runMonitor({ scope, source: "watch", writeEmptyReport: false });
    if (report.counts.events || opts.verbose) printWatchSummary(report);
  };
  run();
  const interval = setInterval(run, Number(opts.interval || opts.debounce || 2000));
  process.on("SIGINT", () => {
    clearInterval(interval);
    console.log("");
    console.log("Knowledge Monitor Watch stopped.");
    process.exit(0);
  });
}

function runQmd(qmdArgs, { allowFailure = false } = {}) {
  const res = spawnSync("qmd", qmdArgs, {
    encoding: "utf8",
    env: QMD_ENV,
    maxBuffer: 20 * 1024 * 1024,
  });
  if (!allowFailure && res.status !== 0) {
    throw new Error(`qmd ${qmdArgs.join(" ")} failed:\n${res.stderr || res.stdout}`);
  }
  return { status: res.status, stdout: res.stdout || "", stderr: res.stderr || "" };
}

function scanVault() {
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
  const scope = arguments[0] || null;
  if (scope) {
    const files = {};
    const targets = fs.existsSync(scope.abs)
      ? fs.statSync(scope.abs).isDirectory()
        ? walk(scope.abs)
        : [scope.abs]
      : [];
    for (const file of targets) {
      if (!isSupportedFile(file)) continue;
      const rel = path.relative(vault, file);
      const stat = fs.statSync(file);
      if (stat.size > MAX_FILE_SIZE) {
        console.warn(`pke: skipping oversized file (${(stat.size / 1024 / 1024).toFixed(1)} MB): ${rel}`);
        continue;
      }
      files[rel] = {
        kind: fileKind(rel),
        size: stat.size,
        mtimeMs: Math.round(stat.mtimeMs),
        sha256: sha256(file),
      };
    }
    return { files };
  }
  const roots = [
    { root: rawDir, kind: "raw" },
    { root: wikiDir, kind: "wiki" },
  ];
  const files = {};
  for (const { root, kind } of roots) {
    if (!fs.existsSync(root)) continue;
    for (const file of walk(root)) {
      if (!isSupportedFile(file)) continue;
      const rel = path.relative(vault, file);
      const stat = fs.statSync(file);
      if (stat.size > MAX_FILE_SIZE) {
        console.warn(`pke: skipping oversized file (${(stat.size / 1024 / 1024).toFixed(1)} MB): ${rel}`);
        continue;
      }
      files[rel] = {
        kind,
        size: stat.size,
        mtimeMs: Math.round(stat.mtimeMs),
        sha256: sha256(file),
      };
    }
  }
  return { files };
}

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith(".") && entry.name !== ".pke") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(full));
    else if (entry.isFile()) out.push(full);
  }
  return out;
}

function isSupportedFile(file) {
  return /\.(md|txt|markdown)$/i.test(file);
}

function fileKind(rel) {
  if (rel === "raw" || rel.startsWith("raw/")) return "raw";
  if (rel === "wiki" || rel.startsWith("wiki/")) return "wiki";
  return "other";
}

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function diffSnapshots(previous, current) {
  const added = [];
  const modified = [];
  const removed = [];
  for (const [file, meta] of Object.entries(current)) {
    if (!previous[file]) added.push({ path: file, ...meta });
    else if (previous[file].sha256 !== meta.sha256) modified.push({ path: file, before: previous[file], after: meta });
  }
  for (const [file, meta] of Object.entries(previous)) {
    if (!current[file]) removed.push({ path: file, ...meta });
  }
  return {
    added: sortChanges(added),
    modified: sortChanges(modified),
    removed: sortChanges(removed),
  };
}

function sortChanges(items) {
  return items.sort((a, b) => a.path.localeCompare(b.path));
}

// --- P6-02: Compile Strategy Refinement ---

/**
 * Analyze acceptance rates of proposals by trigger/event type.
 * Returns structured rates for confidence adjustment.
 */
function analyzeAcceptanceRates() {
  const proposals = listProposals();
  let totalApplied = 0;
  let totalRejected = 0;
  let totalPending = 0;
  const byType = {}; // { eventType: { applied, rejected } }

  for (const p of proposals) {
    const eventType = p.event_type || p.trigger || "unknown";
    if (!byType[eventType]) byType[eventType] = { applied: 0, rejected: 0 };
    if (p.status === "applied") {
      totalApplied++;
      byType[eventType].applied++;
    } else if (p.status === "rejected") {
      totalRejected++;
      byType[eventType].rejected++;
    } else {
      totalPending++;
    }
  }

  const decided = totalApplied + totalRejected;
  const overallRate = decided > 0 ? totalApplied / decided : 0.5;
  const ratesByType = {};
  for (const [type, counts] of Object.entries(byType)) {
    const d = counts.applied + counts.rejected;
    ratesByType[type] = d > 0 ? counts.applied / d : overallRate;
  }

  return {
    overallRate,
    ratesByType,
    totalApplied,
    totalRejected,
    totalPending,
    calculatedAt: new Date().toISOString(),
  };
}

/**
 * Adjust confidence level based on historical acceptance rate for the given event type.
 * Applies multiplicative adjustment in the 80-120% range.
 */
function adjustConfidenceByHistory(baseConfidence, eventType, rates) {
  const rate = rates.ratesByType[eventType] ?? rates.overallRate ?? 0.5;
  const confValues = { high: 0.9, medium: 0.6, low: 0.3 };
  const base = confValues[baseConfidence] || 0.5;
  const adjusted = base * (0.8 + rate * 0.4); // 80-120% range
  return adjusted > 0.75 ? "high" : adjusted > 0.45 ? "medium" : "low";
}

// --- P6-01: Retrieval Tuning Proposals ---

/**
 * Generate self-improvement proposals for retrieval tuning.
 * Identifies topics with frequent events but missing/low-quality wiki pages.
 */
function generateRetrievalTuningProposals() {
  const allEvents = readEvents();
  const events = allEvents.slice(-1000); // last 1000 events
  if (!events.length) return [];

  // Group events by topic
  const topicMap = {}; // { topic: { count, paths, conflicts } }
  for (const e of events) {
    const topic = extractTopicFromPath(e.path);
    if (topic === "unknown") continue;
    if (!topicMap[topic]) topicMap[topic] = { count: 0, paths: [], conflicts: 0 };
    topicMap[topic].count++;
    if (topicMap[topic].paths.length < 10) topicMap[topic].paths.push(e.path);
    if (e.event_type === "conflict_detected") topicMap[topic].conflicts++;
  }

  // Top 10 by frequency
  const sortedTopics = Object.entries(topicMap)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 10);

  // De-duplicate against existing proposals
  const existingProposals = listProposals();
  const existingTopics = new Set(
    existingProposals
      .filter((p) => p.proposal_type === "retrieval_tuning")
      .map((p) => p.target_page)
  );

  const proposals = [];
  for (const [topic, data] of sortedTopics) {
    const targetPage = `wiki/${topic}.md`;
    if (existingTopics.has(targetPage)) continue; // already proposed

    const wikiPagePath = path.join(wikiDir, `${topic}.md`);
    const pageExists = fs.existsSync(wikiPagePath);

    let reason, coverageGap;
    if (!pageExists) {
      reason = `Topic "${topic}" has ${data.count} events but no wiki page — creating one would improve retrieval`;
      coverageGap = "missing_page";
    } else if (data.conflicts > 0) {
      reason = `Topic "${topic}" has ${data.count} events with ${data.conflicts} conflicts — page may need improvement`;
      coverageGap = "low_confidence";
    } else {
      continue; // page exists and no conflicts, skip
    }

    proposals.push({
      id: `self-improve-retrieval-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      createdAt: new Date().toISOString(),
      status: "pending",
      proposal_type: "retrieval_tuning",
      confidence: "medium",
      reason,
      target_page: targetPage,
      source_files: data.paths,
      detected_signals: {
        event_frequency: data.count,
        coverage_gap: coverageGap,
      },
      patch: {
        operations: [{
          type: "create_page",
          target: targetPage,
          template: "knowledge_page",
        }],
      },
    });
  }

  return proposals;
}

/**
 * Command: pke improve — show self-improvement proposals for retrieval tuning
 */
function improveCommand() {
  const proposals = generateRetrievalTuningProposals();

  if (opts.apply) {
    for (const p of proposals) {
      writeProposal(p);
    }
    if (!opts.json) {
      console.log(`Wrote ${proposals.length} self-improvement proposal(s) to proposals directory.`);
    }
  }

  if (opts.json) return printJson(proposals);

  console.log("Self-Improvement Proposals (Retrieval Tuning)");
  if (!proposals.length) {
    console.log("  none — all frequent topics already have wiki coverage or proposals");
    return;
  }
  for (const p of proposals) {
    console.log(`  [self-improve] ${p.target_page}`);
    console.log(`    reason: ${p.reason}`);
    console.log(`    signals: freq=${p.detected_signals.event_frequency}, gap=${p.detected_signals.coverage_gap}`);
  }
  if (!opts.apply) {
    console.log("");
    console.log("  Run with --apply to write these proposals.");
  }
}

function extractTopicFromPath(filePath) {
  if (!filePath) return "unknown";
  const base = path.basename(filePath, path.extname(filePath));
  return base.trim().replace(/\s+/g, "-");
}

function generateUsageReport(timeWindow = 30) {
  const cutoff = new Date(Date.now() - timeWindow * 24 * 60 * 60 * 1000);
  const allEvents = readEvents();
  const allProposals = listProposals();
  const events = allEvents.filter((e) => new Date(e.time || 0) >= cutoff);
  const proposals = allProposals.filter((p) => new Date(p.createdAt || p.time || 0) >= cutoff);
  const topicMap = {};
  for (const e of events) {
    const topic = extractTopicFromPath(e.path);
    if (!topicMap[topic]) topicMap[topic] = { topic, events: 0, proposals: 0, approvals: 0, rejections: 0, conflicts: 0 };
    topicMap[topic].events++;
    if (e.event_type === "conflict_detected") topicMap[topic].conflicts++;
  }
  for (const p of proposals) {
    const topic = extractTopicFromPath(p.source_files?.[0] || p.target_page);
    if (!topicMap[topic]) topicMap[topic] = { topic, events: 0, proposals: 0, approvals: 0, rejections: 0, conflicts: 0 };
    topicMap[topic].proposals++;
    if (p.status === "applied") topicMap[topic].approvals++;
    if (p.status === "rejected") topicMap[topic].rejections++;
  }
  const topTopics = Object.values(topicMap)
    .sort((a, b) => b.events - a.events)
    .slice(0, 10);
  const totalApprovals = proposals.filter((p) => p.status === "applied").length;
  const totalRejections = proposals.filter((p) => p.status === "rejected").length;
  const decided = totalApprovals + totalRejections;
  const approvalRate = decided > 0 ? (totalApprovals / decided) * 100 : null;
  const weeks = timeWindow / 7;
  const compileVelocity = weeks > 0 ? proposals.length / weeks : 0;
  return {
    timeWindow,
    reportedAt: new Date().toISOString(),
    totalEvents: events.length,
    totalProposals: proposals.length,
    approvalRate,
    topTopics,
    compileVelocity,
  };
}

function filterProposalsByPriority(candidates, maxCount = 5) {
  const confOrder = { high: 3, medium: 2, low: 1 };
  const sorted = [...candidates].sort((a, b) => {
    const confDiff = (confOrder[b.confidence] || 0) - (confOrder[a.confidence] || 0);
    if (confDiff !== 0) return confDiff;
    const evA = a.detected_signals?.evidence_count || 0;
    const evB = b.detected_signals?.evidence_count || 0;
    if (evB !== evA) return evB - evA;
    return new Date(b.time || b.createdAt || 0) - new Date(a.time || a.createdAt || 0);
  });
  return sorted.slice(0, maxCount);
}

function compileCandidates(changes) {
  const items = [];
  for (const c of [...changes.added, ...changes.modified]) {
    const kind = c.kind || c.after?.kind || "unknown";
    const hints = [];
    if (kind === "raw") {
      hints.push("changed evidence; review before compiling any wiki update");
      hints.push("search related wiki pages before proposing changes");
    } else if (kind === "wiki") {
      hints.push("wiki changed; verify template, embeddings, and links");
    }
    if (/qoder|qoderwork|商业|strategy|prd|product/i.test(c.path)) hints.push("active product/strategy topic");
    items.push({ path: c.path, kind, hints });
  }
  return items;
}

function templateCoverage() {
  const sections = [
    "Current Understanding",
    "Key Principles",
    "Evidence",
    "Conflicts / Evolution",
    "Stale Or Risky Claims",
    "Open Questions",
    "Related Pages",
  ];
  const files = fs.existsSync(wikiDir) ? fs.readdirSync(wikiDir).filter((f) => f.endsWith(".md")) : [];
  const missing = [];
  for (const file of files) {
    const text = fs.readFileSync(path.join(wikiDir, file), "utf8");
    const absent = sections.filter((s) => !new RegExp(`^##\\s+${escapeRegex(s)}\\s*$`, "m").test(text));
    if (absent.length) missing.push({ file, absent });
  }
  return { total: files.length, compliant: files.length - missing.length, missing };
}

function readState() {
  return readJsonFile(statePath, {});
}

function writeState(state) {
  fs.mkdirSync(path.dirname(statePath), { recursive: true });
  fs.writeFileSync(statePath, JSON.stringify(state, null, 2), "utf8");
}

function parseOptions(argv) {
  const out = {};
  for (let i = argv.length - 1; i >= 0; i--) {
    const a = argv[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2).replace(/-([a-z])/g, (_, ch) => ch.toUpperCase());
    if (["json", "save", "baseline", "write", "watch", "autoScan", "verbose", "usage", "batchSafe", "apply"].includes(key)) {
      out[key] = true;
      argv.splice(i, 1);
    } else {
      out[key] = argv[i + 1];
      argv.splice(i, 2);
    }
  }
  return out;
}

function printJson(value) {
  console.log(JSON.stringify(value, null, 2));
}

function printChanges(result) {
  const { changes, counts } = result;
  console.log("Changed Files");
  console.log(`  Added:     ${counts.added}`);
  console.log(`  Modified:  ${counts.modified}`);
  console.log(`  Removed:   ${counts.removed}`);
  console.log(`  Total:     ${counts.totalChanged}`);
  for (const [label, list] of [["Added", changes.added], ["Modified", changes.modified], ["Removed", changes.removed]]) {
    if (!list.length) continue;
    console.log("");
    console.log(label);
    for (const item of list.slice(0, 50)) console.log(`  - ${item.path}`);
    if (list.length > 50) console.log(`  ... ${list.length - 50} more`);
  }
}

function printCompileChangeReport(report) {
  console.log("Change Report");
  console.log(`  Mode:             ${report.mode}`);
  console.log(`  Knowledge writes: ${report.knowledgeWrites.length}`);
  console.log(`  Evidence writes:  ${report.evidenceWrites.length}`);
  console.log(`  Unresolved items: ${report.unresolvedItems.length}`);
  console.log("");
  console.log("Changed By This Compile Command");
  printChanges({
    changes: report.changedByThisCommand,
    counts: countChanges(report.changedByThisCommand),
  });
  console.log("");
  console.log("Changed Since Saved Baseline");
  printChanges({
    changes: report.changedSinceBaseline,
    counts: countChanges(report.changedSinceBaseline),
  });
  console.log("");
  console.log("Unresolved Items");
  for (const item of report.unresolvedItems) console.log(`  - ${item}`);
}

function countChanges(changes) {
  return {
    added: changes.added.length,
    modified: changes.modified.length,
    removed: changes.removed.length,
    totalChanged: changes.added.length + changes.modified.length + changes.removed.length,
  };
}

function resolveVaultScope(input) {
  const abs = path.resolve(vault, input);
  const rel = path.relative(vault, abs);
  if (rel.startsWith("..") || path.isAbsolute(rel)) {
    throw new Error(`monitor path must be inside vault: ${input}`);
  }
  return { abs, rel: rel || "." };
}

function collectWikiSections(files) {
  const out = {};
  for (const [rel, meta] of Object.entries(files)) {
    if (meta.kind !== "wiki") continue;
    const full = path.join(vault, rel);
    if (!fs.existsSync(full)) continue;
    out[rel] = parseMarkdownSections(readTextFile(full));
  }
  return out;
}

function parseMarkdownSections(text) {
  const sections = {};
  let current = "_preamble";
  let inFence = false;
  sections[current] = [];
  for (const line of text.split(/\r?\n/)) {
    if (line.trim().startsWith("```")) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    const match = line.match(/^##\s+(.+?)\s*$/);
    if (match) {
      current = match[1];
      sections[current] = [];
    } else {
      sections[current].push(line);
    }
  }
  for (const key of Object.keys(sections)) {
    sections[key] = sections[key].map((line) => line.trim()).filter(Boolean);
  }
  return sections;
}

function buildFileEvents(changes, source) {
  const events = [];
  for (const item of changes.added) events.push(makeEvent(`${item.kind}_added`, item.path, item.kind, source, `Added ${item.kind} file.`));
  for (const item of changes.modified) {
    const kind = item.after?.kind || item.kind || fileKind(item.path);
    events.push(makeEvent(`${kind}_modified`, item.path, kind, source, `Modified ${kind} file.`));
  }
  for (const item of changes.removed) events.push(makeEvent(`${item.kind}_removed`, item.path, item.kind, source, `Removed ${item.kind} file.`));
  return events;
}

function buildKnowledgeEvents(changes, previousSections, currentSections, source) {
  const events = [];
  const changedWiki = [...changes.added, ...changes.modified].filter((item) => (item.kind || item.after?.kind) === "wiki");
  for (const item of changedWiki) {
    const rel = item.path;
    const prev = previousSections[rel] || {};
    const cur = currentSections[rel] || {};
    for (const section of KNOWLEDGE_SECTIONS) {
      const addedLines = diffLines(prev[section] || [], cur[section] || []);
      const removedLines = diffLines(cur[section] || [], prev[section] || []);
      for (const line of addedLines.slice(0, 20)) {
        const eventType = sectionEventType(section, line);
        events.push(makeEvent(eventType, rel, "wiki", source, trimLine(line), { section, line }));
      }
      if (section === "Current Understanding" && addedLines.length && removedLines.length) {
        events.push(makeEvent("conclusion_changed", rel, "wiki", source, "Current Understanding changed.", {
          section,
          added: addedLines.slice(0, 10),
          removed: removedLines.slice(0, 10),
        }));
      }
    }
  }
  return events;
}

function diffLines(before, after) {
  const beforeSet = new Set(before);
  return after.filter((line) => !beforeSet.has(line));
}

function sectionEventType(section, line) {
  if (section === "Current Understanding" || section === "Key Principles") return "conclusion_added";
  if (section === "Conflicts / Evolution") return "conflict_detected";
  if (section === "Stale Or Risky Claims") return "stale_claim_detected";
  if (section === "Open Questions") return "open_question_added";
  if (section === "Evidence") return line.includes("[[") ? "evidence_link_added" : "evidence_added";
  return "knowledge_section_updated";
}

function makeEvent(eventType, rel, kind, source, summary, extra = {}) {
  const time = new Date().toISOString();
  return {
    id: `${time}-${crypto.randomBytes(4).toString("hex")}`,
    time,
    event_type: eventType,
    path: rel,
    kind,
    source,
    summary,
    approval_status: eventType.includes("proposed") ? "pending" : "observed",
    ...extra,
  };
}

function summarizeMonitorEvents(events, changes) {
  return {
    filesChanged: changes.added.length + changes.modified.length + changes.removed.length,
    newConclusions: events.filter((e) => e.event_type === "conclusion_added").map((e) => e.summary),
    conflicts: events.filter((e) => e.event_type === "conflict_detected").map((e) => e.summary),
    staleClaims: events.filter((e) => e.event_type === "stale_claim_detected").map((e) => e.summary),
    openQuestions: events.filter((e) => e.event_type === "open_question_added").map((e) => e.summary),
    approvalNeeded: events.filter((e) => ["conflict_detected", "stale_claim_detected", "conclusion_changed"].includes(e.event_type)),
  };
}

function appendEvents(events) {
  fs.mkdirSync(path.dirname(eventsPath), { recursive: true });
  fs.appendFileSync(eventsPath, `${events.map((event) => JSON.stringify(event)).join("\n")}\n`, "utf8");
  rotateEventLogIfNeeded();
}

function rotateEventLogIfNeeded() {
  const MAX_EVENTS = 100_000;
  if (!fs.existsSync(eventsPath)) return;
  const lines = fs.readFileSync(eventsPath, "utf8").split(/\n/).filter(Boolean);
  if (lines.length <= MAX_EVENTS) return;
  const archiveDir = path.join(pkeDir, "events-archive");
  fs.mkdirSync(archiveDir, { recursive: true });
  const archiveDate = new Date().toISOString().replace(/[:.]/g, "-");
  const archivePath = path.join(archiveDir, `${archiveDate}-archived.jsonl`);
  const toArchive = lines.slice(0, lines.length - MAX_EVENTS);
  fs.writeFileSync(archivePath, toArchive.join("\n") + "\n", "utf8");
  const kept = lines.slice(lines.length - MAX_EVENTS);
  fs.writeFileSync(eventsPath, kept.join("\n") + "\n", "utf8");
  console.warn(`pke: rotated ${toArchive.length} events to ${path.basename(archivePath)}`);
}

function readEvents() {
  if (!fs.existsSync(eventsPath)) return [];
  return fs.readFileSync(eventsPath, "utf8").split(/\n/).filter(Boolean).map((line) => JSON.parse(line));
}

function findEvent(id) {
  return readEvents().find((event) => event.id === id);
}

function isCompileTriggerEvent(event) {
  return [
    "raw_added",
    "raw_modified",
    "wiki_modified",
    "conflict_detected",
    "stale_claim_detected",
    "open_question_added",
    "conclusion_added",
    "conclusion_changed",
  ].includes(event.event_type);
}

function eventToCandidate(event) {
  return {
    event_id: event.id,
    event_type: event.event_type,
    source_file: event.path,
    suggested_target: suggestTargetPage(event.path),
    reason: candidateReason(event),
  };
}

function candidateReason(event) {
  if (event.event_type === "raw_added") return "new raw evidence needs review before promotion";
  if (event.event_type === "raw_modified") return "raw evidence changed since the saved review baseline";
  if (event.event_type === "conflict_detected") return "conflict section changed and may need an approved knowledge update";
  if (event.event_type === "stale_claim_detected") return "stale/risky claim needs review";
  if (event.event_type === "open_question_added") return "open question may need tracking or resolution";
  if (event.event_type === "conclusion_added" || event.event_type === "conclusion_changed") return "knowledge conclusion changed";
  return "knowledge event may deserve compile review";
}

function createProposalFromEvent(event, targetOverride) {
  const source = event.path;
  const target = normalizeTargetPage(targetOverride || suggestTargetPage(source));
  const id = `proposal-${new Date().toISOString().replace(/[:.]/g, "-")}-${crypto.randomBytes(3).toString("hex")}`;
  const operations = target ? buildSafePatchOperations(event, source, target) : [];
  return {
    id,
    createdAt: new Date().toISOString(),
    status: "pending",
    trigger: event.event_type,
    source_event_ids: event.id ? [event.id] : [],
    source_files: source ? [source] : [],
    target_page: target,
    reason: candidateReason(event),
    confidence: target ? "medium" : "low",
    requires_user_approval: true,
    detected_signals: {
      new_conclusions: event.event_type.includes("conclusion") ? [event.summary].filter(Boolean) : [],
      conflicts: event.event_type === "conflict_detected" ? [event.summary].filter(Boolean) : [],
      stale_claims: event.event_type === "stale_claim_detected" ? [event.summary].filter(Boolean) : [],
      open_questions: event.event_type === "open_question_added" ? [event.summary].filter(Boolean) : [],
    },
    patch: {
      target_page: target,
      operations,
    },
  };
}

function buildSafePatchOperations(event, source, target) {
  const sourceLink = sourceToWikiLink(source);
  const today = new Date().toISOString().slice(0, 10);
  const operations = [];
  if (event.event_type.startsWith("raw_")) {
    operations.push({
      type: "append_to_section",
      section: "Evidence",
      content: `- [[${sourceLink}]]: raw evidence ${event.event_type === "raw_modified" ? "updated" : "added"} on ${today}.`,
    });
    operations.push({
      type: "append_to_section",
      section: "Open Questions",
      content: `- Which claims from [[${sourceLink}]] should be promoted into current understanding?`,
    });
  } else if (event.event_type === "conflict_detected") {
    operations.push({
      type: "append_to_section",
      section: "Conflicts / Evolution",
      content: `- ${event.summary}`,
    });
  } else if (event.event_type === "stale_claim_detected") {
    operations.push({
      type: "append_to_section",
      section: "Stale Or Risky Claims",
      content: `- ${event.summary}`,
    });
  } else if (event.event_type === "open_question_added") {
    operations.push({
      type: "append_to_section",
      section: "Open Questions",
      content: `- ${event.summary}`,
    });
  } else if (event.event_type.includes("conclusion")) {
    operations.push({
      type: "append_to_section",
      section: "Current Understanding",
      content: `${event.summary}`,
    });
  }
  return operations;
}

function suggestTargetPage(source) {
  if (!source) return null;
  if (source.startsWith("wiki/")) return source;
  const base = path.basename(source, path.extname(source));
  const direct = path.join("wiki", `${base}.md`);
  if (fs.existsSync(path.join(vault, direct))) return direct;
  const sourceText = fs.existsSync(path.join(vault, source)) ? fs.readFileSync(path.join(vault, source), "utf8") : "";
  const link = sourceText.match(/\[\[([^\]]+)\]\]/);
  if (link) {
    const linked = path.join("wiki", `${link[1].replace(/\.md$/i, "")}.md`);
    if (fs.existsSync(path.join(vault, linked))) return linked;
  }
  if (/chatgpt|llm|ai|openai|karpathy/i.test(source)) {
    const ai = "wiki/ai-llm-research.md";
    if (fs.existsSync(path.join(vault, ai))) return ai;
  }
  return null;
}

function normalizeTargetPage(target) {
  if (!target) return null;
  const rel = target.startsWith("wiki/") ? target : path.join("wiki", target);
  return rel.endsWith(".md") ? rel : `${rel}.md`;
}

function sourceToWikiLink(source) {
  return path.basename(source || "", path.extname(source || ""));
}

function proposalPath(id) {
  return path.join(proposalsDir, `${id}.json`);
}

function writeProposal(proposal) {
  const PROPOSAL_CAP = 200;
  fs.mkdirSync(proposalsDir, { recursive: true });
  fs.writeFileSync(proposalPath(proposal.id), JSON.stringify(proposal, null, 2), "utf8");
  const pendingCount = listProposals().filter((p) => p.status === "pending").length;
  if (pendingCount > PROPOSAL_CAP) {
    console.warn(`pke: warning - pending proposals (${pendingCount}) exceeds limit (200). Consider reviewing older proposals.`);
  }
}

function readProposal(id) {
  const file = proposalPath(id);
  if (!fs.existsSync(file)) throw new Error(`proposal not found: ${id}`);
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function listProposals() {
  if (!fs.existsSync(proposalsDir)) return [];
  return fs.readdirSync(proposalsDir)
    .filter((file) => file.endsWith(".json"))
    .sort()
    .map((file) => JSON.parse(fs.readFileSync(path.join(proposalsDir, file), "utf8")));
}

function printProposal(proposal) {
  console.log(`Proposal ${proposal.id}`);
  console.log(`  Status: ${proposal.status}`);
  console.log(`  Trigger: ${proposal.trigger}`);
  console.log(`  Source: ${proposal.source_files.join(", ") || "none"}`);
  console.log(`  Target: ${proposal.target_page || "needs selection"}`);
  console.log(`  Reason: ${proposal.reason}`);
  console.log(`  Confidence: ${proposal.confidence}`);
  console.log("");
  console.log("Patch");
  if (!proposal.patch.operations.length) {
    console.log("  no patch; choose --target and recreate proposal");
    return;
  }
  for (const op of proposal.patch.operations) {
    console.log(`  - ${op.type} -> ${op.section}`);
    console.log(`    ${op.content}`);
  }
}

function applyProposal(proposal) {
  if (proposal.status !== "pending") throw new Error(`proposal is not pending: ${proposal.status}`);
  if (!proposal.target_page) throw new Error("proposal has no target_page; recreate with --target");
  if (!proposal.patch.operations.length) throw new Error("proposal has no patch operations");
  const targetPath = path.join(vault, proposal.target_page);
  if (!fs.existsSync(targetPath)) throw new Error(`target page not found: ${proposal.target_page}`);
  const before = fs.readFileSync(targetPath, "utf8");
  const backupPath = backupTargetPage(targetPath, proposal.id);
  let after = before;
  for (const operation of proposal.patch.operations) {
    after = applyPatchOperation(after, operation);
  }
  const changed = after !== before;
  if (changed) fs.writeFileSync(targetPath, after, "utf8");
  const qmdRefresh = changed ? refreshQmdAfterApply() : null;
  proposal.status = "applied";
  proposal.appliedAt = new Date().toISOString();
  proposal.backupPath = backupPath;
  proposal.changeReport = {
    target: proposal.target_page,
    changed,
    beforeSha256: crypto.createHash("sha256").update(before).digest("hex"),
    afterSha256: crypto.createHash("sha256").update(after).digest("hex"),
    operations: proposal.patch.operations.length,
    qmdRefresh,
  };
  writeProposal(proposal);
  fs.mkdirSync(appliedDir, { recursive: true });
  fs.copyFileSync(proposalPath(proposal.id), path.join(appliedDir, `${proposal.id}.json`));
  return { proposal, backupPath, changed, qmdRefresh };
}

function backupTargetPage(targetPath, proposalId) {
  const rel = path.relative(vault, targetPath).replace(/[\/\\]/g, "__");
  fs.mkdirSync(backupsDir, { recursive: true });
  const backupPath = path.join(backupsDir, `${proposalId}-${rel}`);
  fs.copyFileSync(targetPath, backupPath);
  return backupPath;
}

function applyPatchOperation(text, operation) {
  if (operation.type !== "append_to_section") throw new Error(`unsupported patch operation: ${operation.type}`);
  if (text.includes(operation.content)) return text;
  const sectionPattern = new RegExp(`(^##\\s+${escapeRegex(operation.section)}\\s*$)`, "m");
  const match = text.match(sectionPattern);
  if (!match || match.index === undefined) {
    const suffix = text.endsWith("\n") ? "" : "\n";
    return `${text}${suffix}\n## ${operation.section}\n\n${operation.content}\n`;
  }
  const start = match.index + match[0].length;
  const next = text.slice(start).search(/^##\s+/m);
  const insertAt = next === -1 ? text.length : start + next;
  const before = text.slice(0, insertAt).replace(/\s*$/, "\n\n");
  const after = text.slice(insertAt).replace(/^\s*/, "\n");
  return `${before}${operation.content}\n${after}`;
}

function refreshQmdAfterApply() {
  return {
    update: runQmd(["update"], { allowFailure: true }),
    embed: runQmd(["embed", "-c", collection], { allowFailure: true }),
  };
}

function dashboardData(scope = null) {
  const events = readEvents().slice(-200).reverse();
  const reports = listReports().slice(-20).reverse().map((file) => ({
    path: file,
    name: path.basename(file),
    mtimeMs: fs.statSync(file).mtimeMs,
  }));
  const state = readJsonFile(monitorStatePath, {});
  const latestReport = state.latestReport || readLatestMonitorReport();
  const latestActivityReport = state.latestActivityReport || (latestReport?.events?.length ? latestReport : null) || readLatestActivityReport();
  const latestEvents = latestReport?.events || [];
  const activityEvents = latestEvents.length ? latestEvents : latestActivityReport?.events || [];
  const byType = {};
  for (const event of events) byType[event.event_type] = (byType[event.event_type] || 0) + 1;
  const proposals = listProposals().slice(-100).reverse();
  return {
    generatedAt: new Date().toISOString(),
    vault,
    eventsPath,
    reportsDir,
    monitorStatePath,
    scope: scope?.rel || null,
    autoScan: Boolean(opts.autoScan),
    lastMonitorAt: state.checkedAt || null,
    totals: {
      events: events.length,
      newConclusions: events.filter((event) => event.event_type === "conclusion_added").length,
      conflicts: events.filter((event) => event.event_type === "conflict_detected").length,
      staleClaims: events.filter((event) => event.event_type === "stale_claim_detected").length,
      openQuestions: events.filter((event) => event.event_type === "open_question_added").length,
    },
    latestScan: latestReport ? {
      checkedAt: latestReport.checkedAt,
      scope: latestReport.scope,
      counts: latestReport.counts,
      summary: latestReport.summary,
      events: latestEvents,
    } : null,
    latestScanEvents: latestEvents,
    latestActivity: latestActivityReport ? {
      checkedAt: latestActivityReport.checkedAt,
      scope: latestActivityReport.scope,
      counts: latestActivityReport.counts,
      summary: latestActivityReport.summary,
      events: latestActivityReport.events || [],
    } : null,
    activityEvents,
    latestTotals: {
      events: latestEvents.length,
      added: latestReport?.counts?.filesAdded || 0,
      modified: latestReport?.counts?.filesModified || 0,
      removed: latestReport?.counts?.filesRemoved || 0,
      filesChanged: latestReport?.summary?.filesChanged || 0,
    },
    activityTotals: {
      events: latestActivityReport?.events?.length || 0,
      added: latestActivityReport?.counts?.filesAdded || 0,
      modified: latestActivityReport?.counts?.filesModified || 0,
      removed: latestActivityReport?.counts?.filesRemoved || 0,
      filesChanged: latestActivityReport?.summary?.filesChanged || 0,
    },
    byType,
    events,
    reports,
    proposals,
  };
}

function renderDashboardHtml() {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PKE Dashboard</title>
  <style>
    :root {
      --bg: #f7f8fb;
      --panel: #ffffff;
      --ink: #17202a;
      --muted: #627084;
      --line: #d9dee8;
      --accent: #146c94;
      --warn: #9d5c00;
      --risk: #b42318;
      --good: #18794e;
    }
    * { box-sizing: border-box; }
    body { margin: 0; background: var(--bg); color: var(--ink); font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    header { border-bottom: 1px solid var(--line); background: #fff; padding: 18px 28px; position: sticky; top: 0; z-index: 1; }
    h1 { margin: 0; font-size: 20px; letter-spacing: 0; }
    header p { margin: 4px 0 0; color: var(--muted); }
    main { padding: 22px 28px 36px; max-width: 1320px; margin: 0 auto; }
    .grid { display: grid; gap: 14px; }
    .metrics { grid-template-columns: repeat(5, minmax(140px, 1fr)); }
    .two { grid-template-columns: minmax(0, 2fr) minmax(320px, 1fr); margin-top: 16px; }
    section, .metric { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; }
    .metric { padding: 14px 16px; min-height: 86px; }
    .metric span { display: block; color: var(--muted); font-size: 12px; }
    .metric strong { display: block; font-size: 28px; margin-top: 6px; }
    section { overflow: hidden; }
    section h2 { margin: 0; padding: 13px 16px; border-bottom: 1px solid var(--line); font-size: 15px; background: #fbfcff; }
    .toolbar { display: flex; gap: 8px; align-items: center; margin: 0 0 14px; flex-wrap: wrap; }
    button { border: 1px solid var(--line); background: #fff; border-radius: 6px; padding: 7px 10px; cursor: pointer; color: var(--ink); }
    button.active { border-color: var(--accent); color: var(--accent); }
    .list { list-style: none; margin: 0; padding: 0; max-height: 620px; overflow: auto; }
    .item { padding: 12px 16px; border-bottom: 1px solid var(--line); }
    .item:last-child { border-bottom: 0; }
    .meta { color: var(--muted); font-size: 12px; display: flex; gap: 8px; flex-wrap: wrap; }
    .summary { margin-top: 5px; }
    .tag { border-radius: 999px; padding: 2px 7px; background: #edf2f7; color: #415166; }
    .conflict { color: var(--risk); }
    .stale { color: var(--warn); }
    .conclusion { color: var(--good); }
    .empty { padding: 24px 16px; color: var(--muted); }
    .reports .item { display: flex; justify-content: space-between; gap: 10px; }
    .actions { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
    .patch { margin-top: 8px; color: var(--muted); }
    code { color: var(--muted); word-break: break-all; }
    @media (max-width: 900px) {
      .metrics, .two { grid-template-columns: 1fr; }
      main, header { padding-left: 16px; padding-right: 16px; }
    }
  </style>
</head>
<body>
  <header>
    <h1>Personal Knowledge Engine Dashboard</h1>
    <p id="subtitle">Loading knowledge monitor state...</p>
  </header>
  <main>
    <div class="toolbar">
      <button data-filter="all" class="active">All</button>
      <button data-filter="conclusion_added">Conclusions</button>
      <button data-filter="conflict_detected">Conflicts</button>
      <button data-filter="stale_claim_detected">Stale</button>
      <button data-filter="open_question_added">Questions</button>
      <button id="scan">Scan Now</button>
      <button id="refresh">Refresh</button>
    </div>
    <div class="grid metrics" id="metrics"></div>
    <div class="grid two">
      <section>
        <h2>Latest Scan Events</h2>
        <ul class="list" id="events"></ul>
      </section>
      <section>
        <h2>Pending Compile Proposals</h2>
        <ul class="list" id="proposals"></ul>
      </section>
    </div>
    <div class="grid two">
      <section class="reports">
        <h2>Reports</h2>
        <ul class="list" id="reports"></ul>
      </section>
      <section>
        <h2>Self-Improvement Rules</h2>
        <div class="item">
          <div class="summary">Monitor observes. Proposal drafts. Apply writes only after approval.</div>
          <div class="meta"><code>append-only wiki patches</code><code>raw files stay evidence</code></div>
        </div>
      </section>
    </div>
  </main>
  <script>
    let data = null;
    let filter = "all";
    const typeClass = { conclusion_added: "conclusion", conclusion_changed: "conclusion", conflict_detected: "conflict", stale_claim_detected: "stale" };
    const labels = { events: "Events", added: "Added", modified: "Modified", removed: "Removed", filesChanged: "Files Changed", newConclusions: "New Conclusions", conflicts: "Conflicts", staleClaims: "Stale Claims", openQuestions: "Open Questions" };
    async function load() {
      const res = await fetch("/api/dashboard", { cache: "no-store" });
      data = await res.json();
      render();
    }
    function render() {
      document.getElementById("subtitle").textContent = "Vault: " + data.vault + " · Scope: " + (data.scope || "events only") + " · Scan: " + (data.autoScan ? "auto" : "manual") + " · Last monitor: " + (data.lastMonitorAt || "none") + " · Updated: " + data.generatedAt;
      const metrics = [
        ["Current Scan Events", data.latestTotals.events],
        ["Current Scan Modified", data.latestTotals.modified],
        ["Current Scan Removed", data.latestTotals.removed],
        ["Last Activity Events", data.activityTotals.events],
        ["History Events", data.totals.events],
      ];
      document.getElementById("metrics").innerHTML = metrics.map(([label, value]) => '<div class="metric"><span>' + label + '</span><strong>' + value + '</strong></div>').join("");
      const activeEvents = data.activityEvents || data.latestScanEvents || [];
      const sourceEvents = filter === "all" ? activeEvents : activeEvents.filter((event) => event.event_type === filter);
      const events = sourceEvents.length ? sourceEvents : (filter === "all" ? data.events : data.events.filter((event) => event.event_type === filter));
      document.getElementById("events").innerHTML = events.length ? events.map(renderEvent).join("") : '<li class="empty">No events.</li>';
      document.getElementById("reports").innerHTML = data.reports.length ? data.reports.map(renderReport).join("") : '<li class="empty">No reports.</li>';
      const pending = data.proposals.filter((proposal) => proposal.status === "pending");
      document.getElementById("proposals").innerHTML = pending.length ? pending.map(renderProposal).join("") : '<li class="empty">No pending proposals.</li>';
    }
    function renderEvent(event) {
      const cls = typeClass[event.event_type] || "";
      const canPropose = ["raw_added","raw_modified","conflict_detected","stale_claim_detected","open_question_added","conclusion_added","conclusion_changed"].includes(event.event_type);
      return '<li class="item"><div class="meta"><span class="tag ' + cls + '">' + event.event_type + '</span><span>' + event.time + '</span></div><div class="summary">' + escapeHtml(event.summary || "") + '</div><div class="meta"><code>' + escapeHtml(event.path || "") + '</code></div>' +
        (canPropose ? '<div class="actions"><button onclick="createProposal(\\'' + event.id + '\\')">Create Proposal</button></div>' : '') +
      '</li>';
    }
    function renderProposal(proposal) {
      const patch = proposal.patch.operations.map((op) => op.section + ': ' + op.content).join(' | ');
      const canApply = proposal.target_page && proposal.patch.operations.length;
      return '<li class="item"><div class="meta"><span class="tag">' + proposal.status + '</span><span>' + proposal.id + '</span></div>' +
        '<div class="summary">' + escapeHtml(proposal.reason || '') + '</div>' +
        '<div class="meta"><code>source: ' + escapeHtml((proposal.source_files || []).join(', ')) + '</code></div>' +
        '<div class="meta"><code>target: ' + escapeHtml(proposal.target_page || 'needs selection') + '</code></div>' +
        '<div class="patch">' + escapeHtml(patch || 'no patch') + '</div>' +
        '<div class="actions">' + (canApply ? '<button onclick="applyProposal(\\'' + proposal.id + '\\')">Approve & Apply</button>' : '') + '<button onclick="rejectProposal(\\'' + proposal.id + '\\')">Reject</button></div>' +
      '</li>';
    }
    function renderReport(report) {
      return '<li class="item"><span>' + escapeHtml(report.name) + '</span><code>' + Math.round(report.mtimeMs) + '</code></li>';
    }
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }
    document.querySelectorAll("[data-filter]").forEach((btn) => {
      btn.addEventListener("click", () => {
        filter = btn.dataset.filter;
        document.querySelectorAll("[data-filter]").forEach((b) => b.classList.toggle("active", b === btn));
        render();
      });
    });
    document.getElementById("refresh").addEventListener("click", load);
    document.getElementById("scan").addEventListener("click", async () => {
      await fetch("/api/scan", { cache: "no-store" });
      await load();
    });
    async function createProposal(id) {
      await fetch("/api/propose?event=" + encodeURIComponent(id), { cache: "no-store" });
      await load();
    }
    async function applyProposal(id) {
      const res = await fetch("/api/apply?id=" + encodeURIComponent(id), { cache: "no-store" });
      const body = await res.json();
      if (body.error) alert(body.error);
      await load();
    }
    async function rejectProposal(id) {
      await fetch("/api/reject?id=" + encodeURIComponent(id), { cache: "no-store" });
      await load();
    }
    window.createProposal = createProposal;
    window.applyProposal = applyProposal;
    window.rejectProposal = rejectProposal;
    load();
    setInterval(load, 5000);
  </script>
</body>
</html>`;
}

function sendJson(res, data, status = 200) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
  res.end(JSON.stringify(data));
}

function sendHtml(res, html) {
  res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
  res.end(html);
}

function writeMonitorReport(report) {
  fs.mkdirSync(reportsDir, { recursive: true });
  const stamp = report.checkedAt.replace(/[:.]/g, "-");
  const file = path.join(reportsDir, `${stamp}-monitor.md`);
  fs.writeFileSync(file, renderMonitorReport(report), "utf8");
  return file;
}

function listReports() {
  if (!fs.existsSync(reportsDir)) return [];
  enforceReportRetention();
  return fs.readdirSync(reportsDir)
    .filter((file) => file.endsWith(".md"))
    .sort()
    .map((file) => path.join(reportsDir, file));
}

function enforceReportRetention() {
  const RETENTION_DAYS = 90;
  const cutoffMs = Date.now() - RETENTION_DAYS * 24 * 60 * 60 * 1000;
  const archiveDir = path.join(pkeDir, "reports-archive");
  const files = fs.readdirSync(reportsDir).filter((f) => f.endsWith(".md"));
  for (const file of files) {
    const full = path.join(reportsDir, file);
    const stat = fs.statSync(full);
    if (stat.mtimeMs < cutoffMs) {
      fs.mkdirSync(archiveDir, { recursive: true });
      fs.renameSync(full, path.join(archiveDir, file));
      console.warn(`pke: archived report older than 90 days: ${file}`);
    }
  }
}

function readLatestMonitorReport() {
  const latest = listReports().slice(-1)[0];
  if (!latest) return null;
  return parseMonitorReportFile(latest);
}

function readLatestActivityReport() {
  const reports = listReports().slice().reverse();
  for (const file of reports) {
    const report = parseMonitorReportFile(file);
    if (report.events.length || report.counts.events) return report;
  }
  return null;
}

function parseMonitorReportFile(file) {
  const text = fs.readFileSync(file, "utf8");
  const eventLines = [];
  let inEvents = false;
  for (const line of text.split(/\n/)) {
    if (line.trim() === "## Events") {
      inEvents = true;
      continue;
    }
    if (inEvents && line.startsWith("## ")) break;
    if (inEvents && line.startsWith("- ") && line !== "- none") eventLines.push(line.slice(2));
  }
  const state = readJsonFile(monitorStatePath, {});
  const events = eventLines.map((line) => {
    const match = line.match(/^([^:]+):\s+(.+?)\s+-\s+(.+)$/);
    return match ? {
      id: `latest-${crypto.createHash("sha1").update(line).digest("hex").slice(0, 8)}`,
      time: state.checkedAt || "",
      event_type: match[1],
      path: match[2],
      summary: match[3],
      source: "latest_report",
    } : null;
  }).filter(Boolean);
  const counts = {
    events: Number((text.match(/- Events:\s+(\d+)/) || [])[1] || 0),
    filesAdded: Number((text.match(/- Added:\s+(\d+)/) || [])[1] || 0),
    filesModified: Number((text.match(/- Modified:\s+(\d+)/) || [])[1] || 0),
    filesRemoved: Number((text.match(/- Removed:\s+(\d+)/) || [])[1] || 0),
  };
  return {
    checkedAt: (text.match(/- Checked:\s+(.+)/) || [])[1] || null,
    scope: (text.match(/- Scope:\s+(.+)/) || [])[1] || null,
    counts,
    summary: {
      filesChanged: Number((text.match(/- Files changed:\s+(\d+)/) || [])[1] || 0),
    },
    events,
  };
}

function renderMonitorReport(report) {
  const lines = [];
  lines.push("# Knowledge Monitor Report");
  lines.push("");
  lines.push(`- Checked: ${report.checkedAt}`);
  lines.push(`- Scope: ${report.scope}`);
  lines.push(`- Events: ${report.counts.events}`);
  lines.push(`- Files changed: ${report.summary.filesChanged}`);
  lines.push("");
  lines.push("## File Changes");
  lines.push("");
  lines.push(`- Added: ${report.counts.filesAdded}`);
  lines.push(`- Modified: ${report.counts.filesModified}`);
  lines.push(`- Removed: ${report.counts.filesRemoved}`);
  lines.push("");
  renderList(lines, "## New Conclusions", report.summary.newConclusions);
  renderList(lines, "## Conflicts Detected", report.summary.conflicts);
  renderList(lines, "## Stale Claims", report.summary.staleClaims);
  renderList(lines, "## Open Questions", report.summary.openQuestions);
  renderList(lines, "## Approval Needed", report.summary.approvalNeeded.map((event) => `${event.event_type}: ${event.path} - ${event.summary}`));
  lines.push("## Events");
  lines.push("");
  if (!report.events.length) lines.push("- none");
  for (const event of report.events) lines.push(`- ${event.event_type}: ${event.path} - ${event.summary}`);
  lines.push("");
  return lines.join("\n");
}

function serializeMonitorReportForState(report) {
  return {
    checkedAt: report.checkedAt,
    scope: report.scope,
    counts: report.counts,
    changes: report.changes,
    summary: report.summary,
    events: report.events,
    reportPath: report.reportPath || null,
  };
}

function renderList(lines, title, items) {
  lines.push(title);
  lines.push("");
  if (!items.length) lines.push("- none");
  for (const item of items) lines.push(`- ${item}`);
  lines.push("");
}

function printMonitorReport(report) {
  console.log(renderMonitorReport(report).trimEnd());
  console.log("");
  console.log(`Report: ${report.reportPath || "none"}`);
  console.log(`Events: ${eventsPath}`);
}

function printWatchSummary(report) {
  console.log(`[${new Date().toLocaleTimeString()}] ${report.counts.events} event(s), ${report.summary.filesChanged} file change(s)`);
  for (const event of report.events.slice(0, 8)) {
    console.log(`  - ${event.event_type}: ${event.path} - ${trimLine(event.summary)}`);
  }
  if (report.events.length > 8) console.log(`  ... ${report.events.length - 8} more`);
}

function readJsonFile(file, fallback) {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8"));
  } catch {
    return fallback;
  }
}

function writeJsonFile(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, JSON.stringify(value, null, 2), "utf8");
}

function readTextFile(file) {
  if (!fs.existsSync(file)) throw new Error(`file not found: ${file}`);
  return fs.readFileSync(file, "utf8");
}

function lineDiff(a, b) {
  const aLines = a.split(/\r?\n/);
  const bLines = b.split(/\r?\n/);
  const aSet = new Map();
  for (const line of aLines) aSet.set(line, (aSet.get(line) || 0) + 1);
  const bSet = new Map();
  for (const line of bLines) bSet.set(line, (bSet.get(line) || 0) + 1);
  const added = [];
  const removed = [];
  let unchanged = 0;
  for (const line of bLines) {
    if ((aSet.get(line) || 0) > 0) {
      aSet.set(line, aSet.get(line) - 1);
      unchanged++;
    } else if (line.trim()) added.push(line);
  }
  for (const line of aLines) {
    if ((bSet.get(line) || 0) > 0) {
      bSet.set(line, bSet.get(line) - 1);
    } else if (line.trim()) removed.push(line);
  }
  return { added, removed, unchanged };
}

function classifyDiff(diff) {
  const groups = [
    { label: "Product Judgment / Scope Changes", test: /(should|must|priority|scope|requirement|decision|risk|assumption|用户|需求|应该|必须|风险|假设|优先|范围)/i, items: [] },
    { label: "Factual Corrections", test: /(correct|wrong|data|number|date|fact|because|evidence|事实|数据|日期|证据|错误)/i, items: [] },
    { label: "Style Preferences", test: /(tone|wording|rewrite|clear|concise|style|表达|措辞|语气|简洁|改写)/i, items: [] },
    { label: "Other Added Final Text", test: /[\s\S]/, items: [] },
  ];
  for (const line of diff.added) {
    const target = groups.find((g) => g.test.test(line));
    target.items.push(line);
  }
  return groups;
}

function buildLearnProposal(classified) {
  const proposals = [];
  const judgment = classified.find((g) => g.label.startsWith("Product"))?.items || [];
  const facts = classified.find((g) => g.label.startsWith("Factual"))?.items || [];
  const style = classified.find((g) => g.label.startsWith("Style"))?.items || [];
  if (judgment.length) proposals.push("Review product judgment changes for possible wiki compile.");
  if (facts.length) proposals.push("Verify factual corrections before compiling them as knowledge.");
  if (style.length) proposals.push("Consider capturing repeated style preferences in a writing-style page.");
  if (!proposals.length) proposals.push("No strong durable-knowledge signal detected by local diff.");
  return proposals;
}

function trimLine(line) {
  const s = line.replace(/^\s*[-*]\s+/, "").replace(/\s+/g, " ").trim();
  return s.length > 180 ? `${s.slice(0, 177)}...` : s;
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function filterSnapshotByScope(snapshot, scopeRel) {
  if (!scopeRel || scopeRel === ".") return snapshot;
  const out = {};
  for (const [rel, value] of Object.entries(snapshot)) {
    if (rel === scopeRel || rel.startsWith(`${scopeRel.replace(/\/$/, "")}/`)) out[rel] = value;
  }
  return out;
}

function mergeScopedSnapshot(previous, currentScoped, scopeRel) {
  if (!scopeRel || scopeRel === ".") return currentScoped;
  const out = {};
  const prefix = `${scopeRel.replace(/\/$/, "")}/`;
  for (const [rel, value] of Object.entries(previous)) {
    if (rel !== scopeRel && !rel.startsWith(prefix)) out[rel] = value;
  }
  return { ...out, ...currentScoped };
}

function applyRemovalTombstones(files, tombstones, scopeRel = null) {
  const out = { ...files };
  for (const rel of Object.keys(tombstones || {})) {
    if (scopeRel && !pathMatchesScope(rel, scopeRel)) continue;
    delete out[rel];
  }
  return out;
}

function updateRemovalTombstones(previousTombstones, changes, currentFiles, scopeRel = null) {
  const next = { ...previousTombstones };
  const checkedAt = new Date().toISOString();
  for (const item of changes.removed) {
    next[item.path] = {
      removedAt: checkedAt,
      kind: item.kind || fileKind(item.path),
      sha256: item.sha256 || item.before?.sha256 || null,
    };
  }
  for (const rel of Object.keys(currentFiles)) {
    if (scopeRel && !pathMatchesScope(rel, scopeRel)) continue;
    delete next[rel];
  }
  return next;
}

function pathMatchesScope(rel, scopeRel) {
  if (!scopeRel || scopeRel === ".") return true;
  const prefix = `${scopeRel.replace(/\/$/, "")}/`;
  return rel === scopeRel || rel.startsWith(prefix);
}
