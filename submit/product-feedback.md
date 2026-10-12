# Product feedback — fleet-voice-ops (Alexa+ track)

Devpost提出フォームの「Product feedback」欄用。使用した各ツール/SDKごとに
「何に使ったか・良かった点・要改善点・オンボーディング所感・また使うか」を書く。

## MCP (modelcontextprotocol.io docs + `mcp` Python SDK 2.x)

- **Used for**: the whole product — a self-hosted MCP server over Streamable
  HTTP exposing 4 tools.
- **What worked**: the spec is readable and the Python SDK got us from zero to
  a serving endpoint in under an hour. Tool registration is declarative.
- **What needs work**: pinning the right SDK surface took trial and error —
  the docs describe the spec version (2025-11-25) but the mapping from spec
  features to SDK classes (Streamable HTTP server helpers vs. legacy FastMCP)
  isn't documented in one place. A "which SDK version implements spec X"
  table would have saved real time.
- **Onboarding**: fast for "hello world", slower for transport details.
- **Would I build again**: yes — the standard itself is the right call.

## Alexa+ add-on developer docs (developer.amazon.com)

- **Used for**: understanding what a self-hosted MCP server must look like to
  be Alexa+-compatible (auth surface, error responses, discovery).
- **What worked**: quickstart guides are concrete and code-forward.
- **What needs work**:
  1. The preview gating is inconsistent across pages — the add-on docs home
     notes tools are partner-only, but individual setup-guide pages sometimes
     omit it. We planned against CLI/Web Simulator access before finding it
     isn't available to hackathon entrants. State the gating on every guide.
  2. Error-semantics diverge from the published MCP expectation: a 401
     returned **without** `WWW-Authenticate` is intentional per your docs, but
     that's non-obvious versus RFC conventions — a one-line "intentional,
     here's why" callout would prevent misreads.
  3. `@alexa-ai/addon-local-inspector` is great but discoverable only from
     inside specific guides — surface it in the main Alexa+ hackathon page.
- **Onboarding**: good once you know which parts are gated.
- **Would I build again**: yes; the preview gating just needs louder signage.

## Feedback on the hackathon mechanics

- Product feedback being a required submission field is excellent — it makes
  friction-logging part of the artifact. Keep it.
- The "simulated experience is allowed" option is what made this submission
  feasible without partner access; state it at the top of the Alexa+ page,
  not only in the rules.
