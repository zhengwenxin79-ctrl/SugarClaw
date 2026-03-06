#!/usr/bin/env bash
# SugarClaw Environment Setup Script
# Idempotent — safe to re-run at any time.
set -e

# ── Colors ────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()    { printf "${BLUE}[INFO]${NC}  %s\n" "$*"; }
ok()      { printf "${GREEN}[OK]${NC}    %s\n" "$*"; }
warn()    { printf "${YELLOW}[WARN]${NC}  %s\n" "$*"; }
err()     { printf "${RED}[ERR]${NC}   %s\n" "$*"; }
step()    { printf "\n${BOLD}${CYAN}==> %s${NC}\n" "$*"; }

# ── Paths ─────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/.." && pwd)"

FOOD_GI_DIR="$WORKSPACE/skills/food-gi-rag"
KALMAN_DIR="$WORKSPACE/skills/kalman-filter-engine"
VENV_DIR="$FOOD_GI_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
VENV_PIP="$VENV_DIR/bin/pip"

SEED_DATA="$FOOD_GI_DIR/data/foods_500.json"
BUILD_SCRIPT="$FOOD_GI_DIR/scripts/build_vectordb.py"
QUERY_SCRIPT="$FOOD_GI_DIR/scripts/query_food.py"
KALMAN_SCRIPT="$KALMAN_DIR/scripts/kalman_engine.py"

# ── 1. Check Python 3.8+ ─────────────────────────────────────────
step "Checking Python version"

PYTHON3=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON3="$candidate"
        break
    fi
done

if [ -z "$PYTHON3" ]; then
    err "Python 3 not found. Please install Python 3.8+ and re-run."
    exit 1
fi

PY_VERSION=$("$PYTHON3" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$("$PYTHON3" -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$("$PYTHON3" -c 'import sys; print(sys.version_info.minor)')

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    err "Python 3.8+ required, found $PY_VERSION"
    exit 1
fi

ok "Python $PY_VERSION found at $(command -v "$PYTHON3")"

# ── 2. Create virtual environment ────────────────────────────────
step "Setting up virtual environment at $VENV_DIR"

if [ -f "$VENV_PYTHON" ]; then
    info "Virtual environment already exists — reusing it."
else
    info "Creating virtual environment..."
    "$PYTHON3" -m venv "$VENV_DIR"
    ok "Virtual environment created."
fi

# Upgrade pip quietly
"$VENV_PYTHON" -m pip install --upgrade pip --quiet

# ── 3. Install dependencies ──────────────────────────────────────
step "Installing Python dependencies"

PACKAGES=(
    numpy
    chromadb
    openpyxl
    sentence-transformers
)

# Install all packages; pip will skip already-satisfied ones.
"$VENV_PIP" install --quiet "${PACKAGES[@]}"

ok "Installed: ${PACKAGES[*]}"

# ── 4. Build ChromaDB vector database ────────────────────────────
step "Building ChromaDB vector database from foods_500.json"

if [ ! -f "$SEED_DATA" ]; then
    err "Seed data not found at $SEED_DATA"
    exit 1
fi

if [ ! -f "$BUILD_SCRIPT" ]; then
    err "Build script not found at $BUILD_SCRIPT"
    exit 1
fi

info "Running build_vectordb.py --seed $SEED_DATA ..."
"$VENV_PYTHON" "$BUILD_SCRIPT" --seed "$SEED_DATA"
ok "Vector database built successfully."

# ── 5. Verify installation ───────────────────────────────────────
step "Verifying installation"

# 5a. Test food query
info "Running test food query..."
if [ -f "$QUERY_SCRIPT" ]; then
    QUERY_OUTPUT=$("$VENV_PYTHON" "$QUERY_SCRIPT" "米饭" --max 1 2>&1) && true
    if [ $? -eq 0 ]; then
        ok "Food GI query test passed."
        info "Sample output (first 3 lines):"
        echo "$QUERY_OUTPUT" | head -3 | sed 's/^/     /'
    else
        warn "Food GI query returned non-zero exit code. Output:"
        echo "$QUERY_OUTPUT" | head -5 | sed 's/^/     /'
    fi
else
    warn "query_food.py not found — skipping query test."
fi

echo ""

# 5b. Test Kalman prediction
info "Running test Kalman prediction..."
if [ -f "$KALMAN_SCRIPT" ]; then
    KALMAN_OUTPUT=$("$VENV_PYTHON" "$KALMAN_SCRIPT" --readings "6.2 6.5 6.8 7.3 7.9 8.5" 2>&1) && true
    if [ $? -eq 0 ]; then
        ok "Kalman filter prediction test passed."
        info "Sample output (first 3 lines):"
        echo "$KALMAN_OUTPUT" | head -3 | sed 's/^/     /'
    else
        warn "Kalman engine returned non-zero exit code. Output:"
        echo "$KALMAN_OUTPUT" | head -5 | sed 's/^/     /'
    fi
else
    warn "kalman_engine.py not found — skipping Kalman test."
fi

# ── 6. Success ────────────────────────────────────────────────────
step "Setup complete!"

cat <<EOF

${GREEN}${BOLD}SugarClaw environment is ready.${NC}

${BOLD}Quick reference:${NC}

  ${CYAN}VENV=${NC}$VENV_PYTHON

  ${BOLD}Food GI/GL query:${NC}
    \$VENV scripts/query_food.py "热干面"
    \$VENV scripts/query_food.py --counter "肠粉"
    \$VENV scripts/query_food.py --high-gi --max 10

  ${BOLD}Kalman blood glucose prediction:${NC}
    \$VENV scripts/kalman_engine.py --readings "6.2 6.5 6.8 7.3 7.9 8.5"
    \$VENV scripts/kalman_engine.py --readings "6.2 6.5 6.8" --event meal --gi 82

  ${BOLD}Database management:${NC}
    \$VENV scripts/build_vectordb.py --stats
    \$VENV scripts/build_vectordb.py --append data/extra_foods.json

EOF
