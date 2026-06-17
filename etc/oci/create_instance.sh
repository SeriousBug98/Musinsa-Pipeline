#!/usr/bin/env bash
set -euo pipefail

export PATH="$HOME/bin:$PATH"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/oci.env"
LOG_FILE="$SCRIPT_DIR/oci_create.log"

# ────────────────────────────────────────────────
# 로깅
# ────────────────────────────────────────────────
log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg" | tee -a "$LOG_FILE"
}

# ────────────────────────────────────────────────
# 시그널 처리
# ────────────────────────────────────────────────
cleanup() {
  log "스크립트가 중단되었습니다."
  exit 0
}
trap cleanup SIGINT SIGTERM

# ────────────────────────────────────────────────
# Pre-flight 체크
# ────────────────────────────────────────────────
preflight_check() {
  if ! command -v oci &>/dev/null; then
    echo "오류: OCI CLI가 설치되어 있지 않습니다."
    echo "설치: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm"
    exit 1
  fi

  if [[ ! -f "$ENV_FILE" ]]; then
    echo "오류: $ENV_FILE 파일이 없습니다."
    echo "oci.env.example을 복사하여 oci.env를 만들고 값을 채워주세요."
    exit 1
  fi

  # shellcheck source=/dev/null
  source "$ENV_FILE"

  local missing=()
  [[ -z "${OCI_COMPARTMENT_ID:-}" ]] && missing+=("OCI_COMPARTMENT_ID")
  [[ -z "${OCI_AVAILABILITY_DOMAIN:-}" ]] && missing+=("OCI_AVAILABILITY_DOMAIN")
  [[ -z "${OCI_SUBNET_ID:-}" ]] && missing+=("OCI_SUBNET_ID")
  [[ -z "${OCI_IMAGE_ID:-}" ]] && missing+=("OCI_IMAGE_ID")
  [[ -z "${SSH_PUBLIC_KEY_PATH:-}" ]] && missing+=("SSH_PUBLIC_KEY_PATH")

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "오류: oci.env에 다음 값이 비어 있습니다: ${missing[*]}"
    exit 1
  fi

  local expanded_key_path
  expanded_key_path="${SSH_PUBLIC_KEY_PATH/#\~/$HOME}"
  if [[ ! -f "$expanded_key_path" ]]; then
    echo "오류: SSH 공개 키 파일을 찾을 수 없습니다: $expanded_key_path"
    exit 1
  fi

  # 기본값 설정
  INSTANCE_DISPLAY_NAME="${INSTANCE_DISPLAY_NAME:-musinsa-pipeline-2}"
  OCPU_COUNT="${OCPU_COUNT:-4}"
  MEMORY_GB="${MEMORY_GB:-24}"
  RETRY_INTERVAL_SEC="${RETRY_INTERVAL_SEC:-300}"
  MAX_ATTEMPTS_PER_RUN="${MAX_ATTEMPTS_PER_RUN:-100}"
  BACKOFF_MULTIPLIER="${BACKOFF_MULTIPLIER:-2}"
  MAX_BACKOFF_SEC="${MAX_BACKOFF_SEC:-3600}"
  WEBHOOK_URL="${WEBHOOK_URL:-}"

  log "Pre-flight 체크 완료."
  log "인스턴스명: $INSTANCE_DISPLAY_NAME | Shape: VM.Standard.A1.Flex (${OCPU_COUNT} OCPU / ${MEMORY_GB}GB)"
  log "재시도 간격: ${RETRY_INTERVAL_SEC}초 | 최대 시도: ${MAX_ATTEMPTS_PER_RUN}회"
}

# ────────────────────────────────────────────────
# 성공 알림
# ────────────────────────────────────────────────
notify_success() {
  local instance_id="$1"
  log "인스턴스 생성 성공! ID: $instance_id"

  if [[ -n "$WEBHOOK_URL" ]]; then
    curl -sf -X POST "$WEBHOOK_URL" \
      -H "Content-Type: application/json" \
      -d "{\"text\": \"OCI 인스턴스 생성 완료\\n이름: ${INSTANCE_DISPLAY_NAME}\\nID: ${instance_id}\"}" \
      && log "웹훅 알림 전송 완료." \
      || log "웹훅 알림 전송 실패 (무시)."
  fi
}

# ────────────────────────────────────────────────
# 인스턴스 생성 시도
# ────────────────────────────────────────────────
try_create_instance() {
  local expanded_key_path="${SSH_PUBLIC_KEY_PATH/#\~/$HOME}"

  oci compute instance launch \
    --availability-domain "$OCI_AVAILABILITY_DOMAIN" \
    --compartment-id "$OCI_COMPARTMENT_ID" \
    --shape "VM.Standard.A1.Flex" \
    --shape-config "{\"ocpus\":${OCPU_COUNT},\"memoryInGBs\":${MEMORY_GB}}" \
    --image-id "$OCI_IMAGE_ID" \
    --subnet-id "$OCI_SUBNET_ID" \
    --assign-public-ip true \
    --ssh-authorized-keys-file "$expanded_key_path" \
    --display-name "$INSTANCE_DISPLAY_NAME" \
    2>&1
}

# ────────────────────────────────────────────────
# 메인 루프
# ────────────────────────────────────────────────
main() {
  preflight_check

  local attempt=0
  local sleep_time="$RETRY_INTERVAL_SEC"

  log "인스턴스 자동 생성 시작."

  while [[ $attempt -lt $MAX_ATTEMPTS_PER_RUN ]]; do
    attempt=$((attempt + 1))
    log "시도 $attempt / $MAX_ATTEMPTS_PER_RUN ..."

    local result
    result=$(try_create_instance 2>&1) || true

    # 용량 부족 → 재시도
    if echo "$result" | grep -qiE "Out of host capacity|InternalError|host capacity"; then
      log "용량 부족. ${sleep_time}초 후 재시도..."
      sleep "$sleep_time"
      # 지수 백오프
      sleep_time=$(( sleep_time * BACKOFF_MULTIPLIER ))
      [[ $sleep_time -gt $MAX_BACKOFF_SEC ]] && sleep_time=$MAX_BACKOFF_SEC
      continue
    fi

    # 설정 오류 (인증 실패, 잘못된 OCID 등) → 즉시 종료
    if echo "$result" | grep -qiE "NotAuthenticated|NotAuthorized|InvalidParameter|NotFound|LimitExceeded"; then
      log "설정 오류로 인해 종료합니다."
      log "$result"
      exit 1
    fi

    # 성공 여부 확인 (JSON 응답에 instance id 포함)
    local instance_id
    if instance_id=$(echo "$result" | grep -o '"id": "ocid1\.instance\.[^"]*"' | head -1 | cut -d'"' -f4) \
        && [[ -n "$instance_id" ]]; then
      notify_success "$instance_id"
      exit 0
    fi

    # 알 수 없는 오류 → 로그 후 재시도
    log "알 수 없는 응답. ${sleep_time}초 후 재시도..."
    log "$result"
    sleep "$sleep_time"
  done

  log "최대 시도 횟수(${MAX_ATTEMPTS_PER_RUN}회)에 도달했습니다. 스크립트를 종료합니다."
  exit 1
}

main
