# Friction Log — fleet-voice-ops (Alexa+ track)

Format per the submission form: task attempted, steps taken, expected vs.
actual result, severity, workaround used, actionable suggestion.

## Entry 1 — MCP spec version ↔ SDK surface mapping

- **Task attempted**: pin the `mcp` Python SDK surface that implements
  Streamable HTTP transport at spec 2025-11-25.
- **Steps taken**: read modelcontextprotocol.io spec pages, then searched the
  Python SDK for the matching server helpers (Streamable HTTP vs. legacy
  FastMCP/SSE).
- **Expected**: a documented mapping "spec version X → SDK version/classes Y".
- **Actual**: the spec pages name the spec version, but the spec→SDK mapping
  is not documented in one place; resolved by trial and error plus source
  reading.
- **Severity**: Medium (cost ~1 hour, no correctness risk once resolved).
- **Workaround**: pinned `mcp==2.3.0` and verified transport behavior
  end-to-end through an ngrok tunnel from a generic MCP client.
- **Actionable suggestion**: publish a "which SDK version implements spec X"
  table on the spec site and in the SDK README.

## Entry 2 — Alexa+ add-on preview gating is inconsistent across pages

- **Task attempted**: determine whether hackathon entrants can access the
  Alexa+ add-on CLI / Web Simulator to test a self-hosted MCP server.
- **Steps taken**: read the add-on docs home (notes tools are partner-only),
  then followed individual setup-guide pages.
- **Expected**: gating stated consistently on every page that describes
  partner-only tooling.
- **Actual**: some setup guides omit the partner-only note, so we planned
  against CLI/Simulator access before discovering it is not available to
  hackathon entrants.
- **Severity**: High for planning (changed the demo strategy: we ship a
  simulated voice loop instead of a device walkthrough).
- **Workaround**: used the rules-allowed "simulated Alexa+ experience" path
  and documented verified-vs-unverified behavior in the submission.
- **Actionable suggestion**: state the gating banner on every guide page, not
  only the docs home.

## Entry 3 — 401 without `WWW-Authenticate` on the add-on surface

- **Task attempted**: probe the add-on endpoint's error semantics to mirror
  Alexa+-compatible auth behavior in our MCP server.
- **Steps taken**: sent unauthenticated requests and inspected status +
  headers.
- **Expected** (RFC convention): a 401 carries a `WWW-Authenticate` challenge
  header.
- **Actual**: 401 returned without `WWW-Authenticate` — apparently
  intentional per the docs, but non-obvious versus RFC conventions and easy
  to misread as a broken endpoint.
- **Severity**: Low-Medium (a one-line doc callout prevents the misread).
- **Workaround**: noted the behavior and chose conventional Bearer auth for
  the self-hosted server instead of copying the surface verbatim.
- **Actionable suggestion**: add a one-line "intentional, here's why" note to
  the auth/error reference.

## Entry 4 — `@alexa-ai/addon-local-inspector` discoverability

- **Task attempted**: find the recommended local testing tool for Alexa+
  add-ons before a device is available.
- **Steps taken**: navigated from the main Alexa+ hackathon/developer pages.
- **Expected**: the local inspector linked from the main hackathon/Alexa+
  landing page.
- **Actual**: the tool is documented only inside specific setup guides;
  found late in the build cycle.
- **Severity**: Medium.
- **Workaround**: validated the MCP server with a generic MCP client +
  ngrok, documented in the repo's evidence files.
- **Actionable suggestion**: surface the local inspector on the main Alexa+
  hackathon page.
