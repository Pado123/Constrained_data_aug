#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "============================================================"
echo "Pipeline launcher"
echo "============================================================"
: "${N_SIM:=5}"
: "${OUTPUT_DIR:=$ROOT_DIR/five_case_results}"
: "${DATA_DIR:=$ROOT_DIR/data}"
: "${DEFAULT_K:=3}"
: "${CASES:=}"
: "${RANKING_MODE:=support_confidence}"
: "${RANDOM_SEED:=1618}"
: "${DECLARE_INTERSECTION_DEVICE:=gpu}"
: "${DECLARE_PROFILE_INTERSECTIONS:=0}"
: "${DECLARE_MAX_PRODUCT_STATES:=5000000}"
: "${DECLARE_USE_FORM_RULES_TABLE:=1}"
: "${DECLARE_ALIGN_PERCENTAGE_DECLARE:=1}"
: "${USE_TRAIN_TEST_SPLIT_50:=0}"
: "${TRAIN_TEST_SPLIT_RATIO:=0.5}"
: "${FILTER_REFERENCE_BY_CONSTRAINTS:=1}"
export DECLARE_INTERSECTION_DEVICE DECLARE_PROFILE_INTERSECTIONS DECLARE_MAX_PRODUCT_STATES RANDOM_SEED DECLARE_USE_FORM_RULES_TABLE DECLARE_ALIGN_PERCENTAGE_DECLARE USE_TRAIN_TEST_SPLIT_50 TRAIN_TEST_SPLIT_RATIO FILTER_REFERENCE_BY_CONSTRAINTS

echo "This run will:"
echo "  1) Load cached constraints or mine them from full logs"
echo "  2) Discover logs recursively from: ${DATA_DIR}"
echo "  3) Optional selected cases: ${CASES:-<all discovered>}"
echo "  4) Default k for new cases: ${DEFAULT_K}"
echo "  5) Rank constraints with mode: ${RANKING_MODE}"
echo "  6) Random seed: ${RANDOM_SEED:-<disabled>}"
echo "  7) Constraint discovery: form_rules_table=${DECLARE_USE_FORM_RULES_TABLE} (matches percentage_declare_traces)"
echo "  8) Scenario C: align_pct=${DECLARE_ALIGN_PERCENTAGE_DECLARE} (TS ∩ top-k constraints, per-trace check)"
echo "  8b) Train/test: USE_TRAIN_TEST_SPLIT_50=${USE_TRAIN_TEST_SPLIT_50} (0=whole log, 1=split), RATIO=${TRAIN_TEST_SPLIT_RATIO}"
echo "  8c) 2-gram reference: FILTER_REFERENCE_BY_CONSTRAINTS=${FILTER_REFERENCE_BY_CONSTRAINTS} (0=unfiltered, 1=constraint-filtered)"
echo "  9) Run ${N_SIM} simulations for scenarios A, B, C"
echo " 10) Repeat the full pipeline for constraint samples"
echo " 11) Compute 2-gram distance and entropy metrics + mean/std summaries per set"
echo " 12) Profile intersection bottlenecks and guard product-state explosion"
echo "Intersection backend request: ${DECLARE_INTERSECTION_DEVICE} (auto-fallback to CPU if unsupported)"
echo "============================================================"

CMD=(
  python "$ROOT_DIR/five_case_pipeline.py"
  --n-sim "$N_SIM"
  --output-dir "$OUTPUT_DIR"
  --data-dir "$DATA_DIR"
  --default-k "$DEFAULT_K"
  --ranking-mode "$RANKING_MODE"
)

if [[ -n "${CASES}" ]]; then
  # Space-separated case names, e.g. CASES="Production lending cvs"
  # shellcheck disable=SC2206
  CASE_ARRAY=($CASES)
  CMD+=(--cases "${CASE_ARRAY[@]}")
fi

if [[ -n "${RANDOM_SEED}" ]]; then
  CMD+=(--seed "${RANDOM_SEED}")
fi

if [[ -n "${TRAIN_TEST_SPLIT_RATIO}" ]]; then
  CMD+=(--train-split-ratio "${TRAIN_TEST_SPLIT_RATIO}")
fi

if [[ -n "${USE_TRAIN_TEST_SPLIT_50}" ]]; then
  CMD+=(--use-train-test-split "${USE_TRAIN_TEST_SPLIT_50}")
fi

if [[ -n "${FILTER_REFERENCE_BY_CONSTRAINTS}" ]]; then
  CMD+=(--filter-reference-by-constraints "${FILTER_REFERENCE_BY_CONSTRAINTS}")
fi

"${CMD[@]}"
echo "============================================================"
echo "Completed. Results available in: $OUTPUT_DIR"
echo "============================================================"
