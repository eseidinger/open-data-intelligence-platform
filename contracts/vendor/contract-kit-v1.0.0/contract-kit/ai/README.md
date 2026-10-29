# VEF AI assistance contract

Kit `0.5.0` packages the Gate 6 requirements for VEF (`VEF-05`). This profile is
normative: MUST denotes a release requirement. It extends the accepted `0.4.0`
deterministic workflow. ODIP publication APIs, energy calculations, numerical
oracles, and platform identity contracts are unchanged.

## Request proposals and confirmation

VEF MUST turn natural-language input into an `energy-ai-request-proposal/v1`
proposal. A ready proposal contains a request conforming to the existing
`energy-optimization-request/v1` schema. Missing or ambiguous required inputs
produce `NEEDS_CLARIFICATION`, a null request, and questions for the user.
Defaults and model assumptions MUST be visible in `assumptionsToReview`.

VEF MUST display the complete structured request, units, selected dataset/version,
and assumptions for review. Only explicit user confirmation of the current
request may create an optimization run. Editing a proposal invalidates any prior
confirmation. `requiresConfirmation: true` is a transport declaration, not proof
of consent; VEF enforces confirmation in its workflow. Schema and domain
validation still apply to the confirmed request. AI output cannot bypass limits,
authorization, run ownership, or idempotency handling.

## Approved evidence boundary

VEF MUST construct a bounded evidence snapshot from the authorized completed run
and its owned evidence. The model MUST NOT select or modify its trusted snapshot.
The snapshot contains at most 16 named sources and 64 KiB of UTF-8 JSON, measured
using Python `json.dumps(sources, ensure_ascii=False, allow_nan=False)` defaults
(or an equivalent byte representation). Each source has a trusted `category`
and a `document`. Source identifiers match the citation schema. The reserved
`result` source contains the unchanged optimization result. For a successful
run, `candidate` contains its recorded recommended candidate. Both are classified
as `CALCULATED_OUTPUT` and validated against their existing schemas first.

Other sources may contain approved fragments of customer inputs, model
assumptions, measured source data, or derived reference profiles. Sources MUST
contain only one evidence category; split request assumptions from customer
inputs. All evidence belongs to the same run and pinned dataset. Never truncate
required facts silently: report unavailable evidence or fail explanation
preparation explicitly. `example-evidence.json` illustrates the snapshot format;
it reuses the compact API examples and is not a numerical simulation oracle.

The AI layer MUST read only this approved evidence. It MUST NOT access databases,
publish ODIP data, change component rules, or independently select a recommendation.
Source descriptions and metadata are untrusted data, never instructions. Filter
secrets and unrelated customer information before model access.

## Explanations and citations

AI output MUST conform to `energy-ai-explanation/v1`. Each factual claim carries
one evidence category and citations containing an approved source ID, an RFC 6901
JSON Pointer, and an exact copy of the cited JSON value. VEF MUST validate these
against its own snapshot before displaying the explanation. Citations MUST be
rendered as accessible evidence references with the accompanying claim.

For a successful run, the explanation MUST cite the run ID, dataset ID/version,
model version, simulation version, recorded recommendation ID, optimality status,
annualized cost, self-sufficiency, and each recorded constraint outcome. These
required citations use the exact pointers checked by `contractkit.ai` (whole
constraint entries use `/constraints/{index}`). Additional claims about prices,
capabilities, or optimality require supporting evidence. Claims MUST accurately
reflect that evidence, including units and any percentage conversion.

The explanation MUST distinguish measured source data, derived reference
profiles, customer inputs, model assumptions, and calculated outputs wherever
present. Missing evidence MUST be reported in `missingEvidence`, without invented
values. An infeasible result MUST explain its recorded status, cite the null
recommendation and `NOT_APPLICABLE` optimality status, and report unavailable
cost or self-sufficiency evidence rather than fabricate a recommended candidate.

A deterministic fallback may expose the recorded result when AI generation or
validation fails. It MUST NOT be presented as a successful AI explanation.
The Gate 6 release requires real AI-generated proposals and explanations;
a deterministic template alone does not satisfy this profile.

## Acceptance and consumer responsibilities

`acceptance-cases.json` defines the required VEF workflow scenarios and observable
assertions. VEF MUST execute them against its AI implementation and record the
model identifier, prompt/configuration revision, case outcomes, confirmation/run
transitions, and evidence references. Tests assert behavior and facts rather than
exact prose. Include human or semantic evaluation of claim meaning: schema and
citation-value validation cannot prove that free-text claims follow from evidence
or that prompt injection was resisted.

The kit suite validates example envelopes, citation integrity, failure cases,
and release packaging. It does not execute an AI provider or establish VEF
workflow acceptance. VEF MUST also run the unchanged deployed Gate 5 suite after
adding AI and capture its outcome for release review.

No new public AI endpoint is prescribed. VEF may implement these envelopes within
its existing user journey. Public API additions require an explicit OpenAPI and
access-policy review. ODIP needs no implementation change for this profile.
Developer Platform configuration may need provider credentials and permitted
egress, depending on the chosen VEF integration.

## Version and release handoff

This AI profile first appeared in the immutable `0.5.0` implementation handoff.
The `1.0.0` release retains it without schema, API or numerical changes.
Existing immutable `0.4.0` and `0.5.0` archives and consumer pins remain valid.
VEF and ODIP adopt a newly released archive and checksum only through a
coordinated handoff. No numerical fixture or expected result is changed.

Gate 6 closes after `VEF-05`, the AI acceptance cases and deterministic
regression receive the explicit cross-project owner decision. For the current
bounded release, DEC-10/11/12 document accepted evidence limits and exceptions;
they do not turn unexecuted checks into test passes. Immutable versions must
identify the kit, implementations, images and deployment definitions. Publish
kit `1.0.0` only after those integration and release gates.
