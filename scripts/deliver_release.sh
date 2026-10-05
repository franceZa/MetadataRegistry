#!/usr/bin/env bash
# T-39 · FR-L.2–L.11 · ADR-004 · the ONE delivery script (manual U2M and CI call the same file).
#
#   scripts/deliver_release.sh <release_id> [--from-dir DIR] [--no-activate]
#
# CD-1 download GitHub Release asset (or --from-dir)   CD-5 databricks bundle deploy
# CD-2 mdf verify-package --expect-release-id           CD-6 bundle run register job (REGISTERED)
# CD-3 copy to Volume; manifest.json LAST = sealed      CD-7 smoke query registry
# CD-4 copy back from Volume + verify again             CD-8 activate (ACTIVATED) + active_release_id
#
# Sealed rule (A-20): a Volume folder WITH manifest.json is immutable -> same hash = skip copy,
# different hash = fail. WITHOUT manifest.json = partial copy -> overwrite and finish.
# Never trusts `fs cp` exit code (it returns 0 when it skips); decisions come from manifest hashes.
#
# Env: DATABRICKS_CONFIG_PROFILE (manual) or DATABRICKS_AUTH_TYPE=github-oidc (CI) · MDF_CATALOG
# (dev_catalog) · MDF_TARGET (dev) · MDF_REPO (owner/repo) · MDF_WAREHOUSE_ID (auto) · MDF_ACTOR
# · MDF_PY (python with mdf installed; default `uv run --quiet python`) · MDF_POLL_SECONDS (5)
set -euo pipefail

cd "$(dirname "$0")/.."

die() { echo "❌ [$1] $2" >&2; exit 1; }
log() { echo "── $*"; }

RELEASE_ID="${1:-}"
shift || true
FROM_DIR=""
ACTIVATE=1
while [ $# -gt 0 ]; do
  case "$1" in
    --from-dir) FROM_DIR="${2:-}"; shift 2 ;;
    --no-activate) ACTIVATE=0; shift ;;
    *) die USAGE "unknown argument: $1" ;;
  esac
done

[[ "$RELEASE_ID" =~ ^mdf-[0-9a-f]{12}$ ]] || die USAGE "release_id must match mdf-<sha12> (got '${RELEASE_ID}')"
CATALOG="${MDF_CATALOG:-dev_catalog}"
[[ "$CATALOG" =~ ^[a-z_][a-z0-9_]*$ ]] || die USAGE "bad MDF_CATALOG '$CATALOG'"
TARGET="${MDF_TARGET:-dev}"
REPO="${MDF_REPO:-${GITHUB_REPOSITORY:-franceZa/MetadataRegistry}}"
POLL="${MDF_POLL_SECONDS:-5}"
if [ -n "${MDF_ACTOR:-}" ]; then ACTOR="$MDF_ACTOR"
elif [ "${GITHUB_ACTIONS:-}" = "true" ]; then ACTOR="github-oidc"
else ACTOR="manual"; fi
if [ -n "${MDF_PY:-}" ]; then PY=("$MDF_PY"); else PY=(uv run --quiet python); fi

DEST="dbfs:/Volumes/${CATALOG}/ops/files/releases/${RELEASE_ID}"
WORK="${MDF_WORK_DIR:-build/deliver}/${RELEASE_ID}"
rm -rf "$WORK"
mkdir -p "$WORK"
EVIDENCE="$WORK/evidence.md"

mask() {
  sed -E \
    -e 's#https://[^/ "]*databricks\.(com|net)#https://<host>#g' \
    -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/<user>/g'
}
ev() { printf '%s\n' "$*" | mask >> "$EVIDENCE"; }
sha() { sha256sum "$1" | cut -d' ' -f1; }
verify() { "${PY[@]}" -m mdf.cli verify-package "$1" --expect-release-id "$RELEASE_ID"; }
json_get() { "${PY[@]}" -c "import json,sys; d=json.load(sys.stdin); print($1)"; }

ev "# Delivery evidence — ${RELEASE_ID}"
ev ""
ev "- actor: ${ACTOR} · catalog: ${CATALOG} · target: ${TARGET} · started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
[ "$ACTOR" = "manual" ] && ev "- ⚠️ manual run (D-P5-6): automated CD (deploy-dev.yml) NOT proven by this run"

# ---------- preflight (FR-L.14 ค · T-45) ----------
# Stop BEFORE any step with a concrete next action when the tools or the login are missing.
next_manual="ขั้นต่อไป: ใช้ mode manual (ไม่ต้องมี CLI) → python scripts/next_steps.py manual ${RELEASE_ID} · ดู runbooks/release-delivery.md"
command -v databricks >/dev/null 2>&1 || { echo "❌ [PREFLIGHT] ไม่พบคำสั่ง databricks (Databricks CLI)" >&2; echo "ขั้นต่อไป: ติดตั้ง CLI https://docs.databricks.com/dev-tools/cli/install.html แล้วรันใหม่ — หรือ ${next_manual#ขั้นต่อไป: }" >&2; exit 1; }
[ -n "$FROM_DIR" ] || command -v gh >/dev/null 2>&1 || { echo "❌ [PREFLIGHT] ไม่พบคำสั่ง gh (GitHub CLI) สำหรับดาวน์โหลด release" >&2; echo "ขั้นต่อไป: ติดตั้ง gh หรือดาวน์โหลดไฟล์จากหน้า Release เองแล้วรันด้วย --from-dir <โฟลเดอร์> — หรือ ${next_manual#ขั้นต่อไป: }" >&2; exit 1; }
if ! AUTH_OUT="$(databricks current-user me --output json 2>&1)"; then
  echo "❌ [PREFLIGHT] login Databricks ไม่ผ่าน: $(printf '%s' "$AUTH_OUT" | head -1 | mask)" >&2
  if [ "$ACTOR" = "github-oidc" ]; then
    echo "ขั้นต่อไป: ตรวจ federation policy + repo variables DATABRICKS_HOST / DATABRICKS_CLIENT_ID (DEP-3) — หรือเปลี่ยน config/env/dev.yaml เป็น delivery_mode: u2m" >&2
  else
    echo "ขั้นต่อไป: databricks auth login --host https://<workspace-host> --profile ${DATABRICKS_CONFIG_PROFILE:-<profile>} แล้วรันคำสั่งเดิมอีกครั้ง" >&2
    echo "ถ้า login ไม่ได้จริง ๆ: ${next_manual#ขั้นต่อไป: }" >&2
  fi
  exit 1
fi

# ---------- CD-1 ----------
PKG="$WORK/pkg"
RELEASE_URL=""
if [ -n "$FROM_DIR" ]; then
  log "CD-1 using local package $FROM_DIR"
  [ -f "$FROM_DIR/manifest.json" ] || die CD-1 "no manifest.json in $FROM_DIR"
  cp -R "$FROM_DIR" "$PKG"
  ev "- CD-1: local package (--from-dir) · no GitHub Release URL"
else
  # T-52 · FR-L.3a: choose the download method from the REAL assets of the release —
  # never guess from manifest_version. New releases (rounds >= 5) have a single
  # "<release_id>.zip" asset; releases published before T-52 (v1 legacy) still have the
  # old flat multi-file assets and are downloaded the old way.
  ZIP_ASSET="${RELEASE_ID}.zip"
  # strip \r: python's stdout on Windows translates '\n' -> '\r\n' in text mode
  ASSET_NAMES="$(gh release view "$RELEASE_ID" -R "$REPO" --json assets -q '.assets[].name' 2>/dev/null | tr -d '\r' || true)"
  if printf '%s\n' "$ASSET_NAMES" | grep -qxF "$ZIP_ASSET"; then
    log "CD-1 gh release download $RELEASE_ID -R $REPO -p $ZIP_ASSET (zip)"
    ZIP_DIR="$WORK/zip-download"
    mkdir -p "$ZIP_DIR"
    gh release download "$RELEASE_ID" -R "$REPO" -D "$ZIP_DIR" -p "$ZIP_ASSET" || die CD-1 "cannot download GitHub Release asset $ZIP_ASSET"
    "${PY[@]}" scripts/safe_unzip.py "$ZIP_DIR/$ZIP_ASSET" "$PKG" || die CD-1 "zip-slip guard rejected $ZIP_ASSET — refusing to extract"
    RELEASE_URL="$(gh release view "$RELEASE_ID" -R "$REPO" --json url -q .url)"
    ev "- CD-1: ${RELEASE_URL} · downloaded ${ZIP_ASSET} · extracted via scripts/safe_unzip.py"
  else
    log "CD-1 gh release download $RELEASE_ID -R $REPO (v1 legacy flat assets)"
    gh release download "$RELEASE_ID" -R "$REPO" -D "$PKG" || die CD-1 "cannot download GitHub Release $RELEASE_ID"
    RELEASE_URL="$(gh release view "$RELEASE_ID" -R "$REPO" --json url -q .url)"
    ev "- CD-1: ${RELEASE_URL} · legacy flat assets (no ${ZIP_ASSET})"
  fi
fi

# ---------- CD-2 ----------
log "CD-2 verify-package (local)"
VERIFY_OUT="$(verify "$PKG")" || die CD-2 "package failed verification — nothing sent to the workspace"
printf '%s\n' "$VERIFY_OUT"
LOCAL_SHA="$(sha "$PKG/manifest.json")"
FILE_COUNT="$(json_get 'd["file_count"]' < "$PKG/manifest.json")"
ev "- CD-2: verify OK · manifest_sha256 \`${LOCAL_SHA}\` · file_count ${FILE_COUNT}"
CD2_WARN="$(printf '%s\n' "$VERIFY_OUT" | grep -F '[WARN]' | sed 's/^[[:space:]]*//' || true)"
[ -n "$CD2_WARN" ] && ev "- CD-2: ${CD2_WARN}"

# ---------- CD-3 ----------
# FR-L.4/L.4a/L.5 (T-50): file list comes from manifest.files[].path (v1 = bare name,
# v2 = "<source>/<file>"), NOT from `find`/`ls`, so stray files are never uploaded.
log "CD-3 sealed check $DEST"
COPIED=0
if LISTING="$(databricks fs ls "$DEST" --output json 2>/dev/null)"; then
  if printf '%s' "$LISTING" | grep -Eq '"name": *"manifest\.json"'; then
    databricks fs cp "$DEST/manifest.json" "$WORK/remote-manifest.json" >/dev/null
    REMOTE_SHA="$(sha "$WORK/remote-manifest.json")"
    if [ "$REMOTE_SHA" = "$LOCAL_SHA" ]; then
      log "CD-3 already sealed with identical manifest → skip copy"
      ev "- CD-3: already sealed (same manifest_sha256) → no copy"
    else
      die CD-3 "release $RELEASE_ID is sealed in the Volume with a DIFFERENT manifest (${REMOTE_SHA:0:12}… ≠ ${LOCAL_SHA:0:12}…) — immutable, refusing to overwrite"
    fi
  else
    log "CD-3 partial folder without manifest.json → resume (overwrite allowed)"
    ev "- CD-3: partial folder found (no manifest.json) → resumed"
  fi
fi
if [ ! -f "$WORK/remote-manifest.json" ]; then
  # single-file `fs cp` does not create parent folders on a UC Volume (observed T-41)
  databricks fs mkdir "$DEST" >/dev/null
  # strip \r: python's stdout on Windows translates '\n' -> '\r\n' in text mode
  MANIFEST_PATHS="$(json_get 'chr(10).join(sorted(e["path"] for e in d["files"]))' < "$PKG/manifest.json" | tr -d '\r')"
  MADE_DIRS=""
  N_FILES=0
  while IFS= read -r rel; do
    [ -z "$rel" ] && continue
    N_FILES=$((N_FILES + 1))
    dir="$(dirname "$rel")"
    if [ "$dir" != "." ]; then
      case " $MADE_DIRS " in
        *" $dir "*) : ;;
        *)
          databricks fs mkdir "$DEST/$dir" >/dev/null
          MADE_DIRS="$MADE_DIRS $dir"
          ;;
      esac
    fi
    databricks fs cp "$PKG/$rel" "$DEST/$rel" --overwrite >/dev/null
  done <<EOF
$MANIFEST_PATHS
EOF
  # validation-report.json always lives at the package root (FR-F.2)
  databricks fs cp "$PKG/validation-report.json" "$DEST/validation-report.json" --overwrite >/dev/null
  # manifest last (no --overwrite): its presence seals the folder
  databricks fs cp "$PKG/manifest.json" "$DEST/manifest.json" >/dev/null
  COPIED=1
  ev "- CD-3: copied $((N_FILES + 2)) files · manifest.json last"
fi

# ---------- CD-4 ----------
log "CD-4 copy back + verify"
databricks fs cp -r "$DEST" "$WORK/back" >/dev/null
VERIFY_OUT="$(verify "$WORK/back")" || die CD-4 "Volume copy failed verification"
printf '%s\n' "$VERIFY_OUT"
BACK_SHA="$(sha "$WORK/back/manifest.json")"
[ "$BACK_SHA" = "$LOCAL_SHA" ] || die CD-4 "Volume manifest ${BACK_SHA:0:12}… ≠ local ${LOCAL_SHA:0:12}…"
ev "- CD-4: copy-back verify OK · manifest_sha256 matches CD-2"
CD4_WARN="$(printf '%s\n' "$VERIFY_OUT" | grep -F '[WARN]' | sed 's/^[[:space:]]*//' || true)"
[ -n "$CD4_WARN" ] && ev "- CD-4: ${CD4_WARN}"
ev ""
ev "\`\`\`"
ev "\$ databricks fs ls ${DEST}"
databricks fs ls "$DEST" | mask >> "$EVIDENCE"
ev "\`\`\`"

# ---------- CD-5 ----------
log "CD-5 bundle deploy -t $TARGET"
databricks bundle deploy -t "$TARGET" 2>&1 | mask
ev "- CD-5: bundle deploy -t ${TARGET} OK"

run_job() { # mode
  local out
  out="$(databricks bundle run -t "$TARGET" mdf_release_register_dev \
    --params "release_id=${RELEASE_ID},mode=$1,actor=${ACTOR},github_release_url=${RELEASE_URL}" 2>&1)" \
    || { printf '%s\n' "$out" | mask; die "CD-$2" "job mdf_release_register_dev ($1) failed"; }
  printf '%s\n' "$out" | mask
  local url
  url="$(printf '%s\n' "$out" | grep -Eo 'https://[^ ]+' | head -1 || true)"
  ev "- CD-$2: job run (${1}) OK · run: ${url:-n/a}"
}

# ---------- CD-6 ----------
log "CD-6 register job"
run_job register 6

# ---------- CD-7 ----------
sql() { # statement -> prints JSON rows (data_array)
  local wh="${MDF_WAREHOUSE_ID:-}"
  if [ -z "$wh" ]; then
    wh="$(databricks warehouses list --output json | json_get 'd[0]["id"]')"
  fi
  local payload resp state sid
  payload="$(STMT="$1" RID="$RELEASE_ID" WH="$wh" "${PY[@]}" -c '
import json, os
print(json.dumps({"statement": os.environ["STMT"], "warehouse_id": os.environ["WH"],
  "wait_timeout": "50s", "on_wait_timeout": "CONTINUE",
  "parameters": [{"name": "rid", "value": os.environ["RID"], "type": "STRING"}]}))')"
  resp="$(databricks api post /api/2.0/sql/statements --json "$payload")"
  state="$(printf '%s' "$resp" | json_get 'd["status"]["state"]')"
  sid="$(printf '%s' "$resp" | json_get 'd.get("statement_id","")')"
  while [ "$state" = "PENDING" ] || [ "$state" = "RUNNING" ]; do
    sleep "$POLL"
    resp="$(databricks api get "/api/2.0/sql/statements/${sid}")"
    state="$(printf '%s' "$resp" | json_get 'd["status"]["state"]')"
  done
  [ "$state" = "SUCCEEDED" ] || die SQL "statement ${state}: $(printf '%s' "$resp" | json_get '(d["status"].get("error") or {}).get("message","")' | mask)"
  printf '%s' "$resp" | json_get 'json.dumps((d.get("result") or {}).get("data_array") or [])'
}

log "CD-7 smoke query registry"
ROWS="$(sql "SELECT event, manifest_sha256, CAST(file_count AS STRING) FROM ${CATALOG}.ops.release_registry WHERE release_id = :rid ORDER BY event_ts")"
CHECK="$(ROWS="$ROWS" SHA="$LOCAL_SHA" FC="$FILE_COUNT" "${PY[@]}" -c '
import json, os
rows = json.loads(os.environ["ROWS"])
reg = [r for r in rows if r[0] == "REGISTERED"]
ok = len(reg) == 1 and reg[0][1] == os.environ["SHA"] and reg[0][2] == os.environ["FC"]
print("OK" if ok else "BAD registered=%d" % len(reg))')"
[ "$CHECK" = "OK" ] || die CD-7 "registry check failed ($CHECK) rows=$ROWS"
ev "- CD-7: registry has exactly 1 REGISTERED row · manifest_sha256 + file_count match"

# ---------- CD-8 ----------
if [ "$ACTIVATE" = "1" ]; then
  log "CD-8 activate"
  run_job activate 8
  databricks bundle deploy -t "$TARGET" --var "active_release_id=${RELEASE_ID}" 2>&1 | mask
  LATEST="$(sql "SELECT release_id FROM ${CATALOG}.ops.release_registry WHERE event = 'ACTIVATED' AND :rid IS NOT NULL ORDER BY event_ts DESC LIMIT 1")"
  [ "$LATEST" = "[[\"${RELEASE_ID}\"]]" ] || die CD-8 "latest ACTIVATED is $LATEST, expected $RELEASE_ID"
  ev "- CD-8: latest ACTIVATED = ${RELEASE_ID} · bundle var active_release_id set"
else
  ev "- CD-8: skipped (--no-activate)"
fi

FINAL="$(sql "SELECT event, manifest_sha256, CAST(file_count AS STRING), volume_path, actor, CAST(event_ts AS STRING) FROM ${CATALOG}.ops.release_registry WHERE release_id = :rid ORDER BY event_ts")"
ev ""
ev "\`\`\`"
ev "registry rows for ${RELEASE_ID}: ${FINAL}"
ev "\`\`\`"
ev "- copied_this_run: ${COPIED} · finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "✅ delivered ${RELEASE_ID} · evidence: ${EVIDENCE}"
