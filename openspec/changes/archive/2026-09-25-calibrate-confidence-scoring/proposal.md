# Proposal

## Why

The current merge confidence scoring reports misleadingly low confidence (e.g. 27% on a routine 1-line Renovate update that is 100% safe to merge). This occurs because the scorer reads Laya's normalized Shannon entropy rather than decision probability, and the context builder penalizes bot updates and configuration-only changes for lacking unit tests and human reviews.

## What Changes

- Update context distillation to detect automated bots (Renovate, Dependabot, ImgBot) and label them appropriately.
- Update context distillation to detect non-code/configuration changes (yaml, json, markdown, config files) and set test requirements to "NOT APPLICABLE" rather than "NO".
- Refine Laya decision criteria to explicitly consider automated routine dependency patch updates and configuration changes as safe when CI checks pass.
- Calibrate the confidence calculation using decision probability mass and margin over runner-up choices instead of Shannon entropy.

## Capabilities

### New Capabilities
<!-- None -->

### Modified Capabilities
- `pr-scoring`: Calibrate confidence calculation from Laya output and enrich context distillation for bot PRs and non-code configuration files.

## Impact

- Affected modules: `gh_agent_pr.distill`, `gh_agent_pr.scorer`, and corresponding tests.
- Observable behavior: Safe PRs (e.g. routine Renovate patches with green CI) will receive appropriately high confidence scores (85%-98%) rather than 20%-40%.
