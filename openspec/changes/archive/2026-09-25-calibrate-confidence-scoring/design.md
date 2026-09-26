# Design

## Context

See proposal.md - Why.
In zero-shot inference, Laya's temperature-scaled softmax on 3-choice questions operates within an effective range of ~0.33 (random baseline) to ~0.70 (strong dominance). Reading Shannon entropy or unscaled probability produces artificially depressed confidence percentages.

## Goals / Non-Goals

**Goals:**
- Provide realistic, human-intuitive confidence percentages (e.g. 85-98% for routine safe updates with green CI).
- Avoid penalizing bot maintenance PRs and configuration-only updates for missing tests or missing human reviews.
- Retain Laya System-1 inference as the core decision maker.

**Non-Goals:**
- Retraining or fine-tuning the base Laya model weights.

## Decisions

### 1. Confidence Calibration Formula
- **Decision**: Calibrate the raw softmax probability distribution $(p_{\text{top}}, p_{\text{runner-up}})$ using min-max scaling over Laya's active range $[0.33, 0.68]$ combined with decision margin:
  $$p_{\text{norm}} = \operatorname{clip}\left(\frac{p_{\text{top}} - 0.33}{0.68 - 0.33}, 0.0, 1.0\right)$$
  $$\text{margin} = p_{\text{top}} - p_{\text{runner-up}}$$
  $$\text{Confidence} = \operatorname{clip}(0.50 + 0.50 \cdot (0.6 \cdot p_{\text{norm}} + 0.4 \cdot \operatorname{clip}(\text{margin} \times 2.5, 0.0, 1.0)), 0.10, 0.99)$$
- **Rationale**: An answer with $P=0.65$ and margin $0.35$ maps to ~90-95% confidence, perfectly reflecting dominant certainty in zero-shot classification.

### 2. Context Distillation Heuristics
- **Decision**:
  - Detect bot authors (e.g. `app/renovate`, `dependabot`, `imgbot`, `*bot*`).
  - Classify modified files as code vs non-code (documentation, configuration, schema, assets).
  - When all modified files are non-code, mark `Test Requirement: NOT APPLICABLE (Configuration / Documentation)` instead of `Includes Tests: NO`.
- **Rationale**: Prevents Laya from penalizing PRs that by definition do not require unit tests.

### 3. Prompt Criteria Tuning
- **Decision**: Explicitly include routine automated dependency patches and minor configuration updates with green CI in the `merge_ready` criteria definition.

## Risks / Trade-offs

- **[Risk] Overconfidence on complex PRs** → Mitigation: When $p_{\text{top}}$ is close to $p_{\text{runner-up}}$ (small margin), the calibration formula dampens confidence down toward 50-60%.
