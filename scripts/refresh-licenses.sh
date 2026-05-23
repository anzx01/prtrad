#!/usr/bin/env bash
# 重新生成第三方依赖授权清单 docs/compliance/third-party-notices.md
#
# 用法:
#   bash scripts/refresh-licenses.sh
#
# 依赖:
#   - Node.js + npx (随项目自带)
#   - Python .venv 已安装项目依赖
#   - pip install pip-licenses （首次运行会自动安装到 .venv）
#
# 注: 本脚本只输出原始 JSON 数据到 var/license-reports/，
#     由人工根据这些数据更新 docs/compliance/third-party-notices.md 表格。
#     不直接覆盖 third-party-notices.md，避免误删人工补充的说明文字。

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT_DIR}/var/license-reports"
DATE="$(date +%Y-%m-%d)"

mkdir -p "${OUT_DIR}"

echo "[1/3] 扫描 JavaScript 依赖授权 (npx license-checker)..."
cd "${ROOT_DIR}"
npx --yes license-checker --production --json --excludePrivatePackages \
  > "${OUT_DIR}/js-licenses-${DATE}.json"

echo "[2/3] 汇总 JS 许可证计数..."
node -e "
const data = require('${OUT_DIR}/js-licenses-${DATE}.json');
const counts = {};
for (const k of Object.keys(data)) {
  const lic = data[k].licenses || 'UNKNOWN';
  const key = Array.isArray(lic) ? lic.join(' OR ') : String(lic);
  counts[key] = (counts[key] || 0) + 1;
}
const sorted = Object.entries(counts).sort((a,b) => b[1] - a[1]);
console.log('JavaScript 许可证计数:');
for (const [lic, n] of sorted) console.log('  ' + n.toString().padStart(4) + '  ' + lic);
" | tee "${OUT_DIR}/js-license-summary-${DATE}.txt"

echo "[3/3] 扫描 Python 依赖授权 (pip-licenses)..."
if [[ -d "${ROOT_DIR}/.venv" ]]; then
  PY_BIN="${ROOT_DIR}/.venv/Scripts/python.exe"
  [[ -x "${PY_BIN}" ]] || PY_BIN="${ROOT_DIR}/.venv/bin/python"
else
  PY_BIN="python"
fi

"${PY_BIN}" -m pip install --quiet pip-licenses
"${PY_BIN}" -m piplicenses --format=json --with-urls --with-license-file \
  > "${OUT_DIR}/py-licenses-${DATE}.json"

"${PY_BIN}" -m piplicenses --format=markdown --order=license \
  > "${OUT_DIR}/py-licenses-${DATE}.md"

echo ""
echo "完成。输出位于:"
echo "  ${OUT_DIR}/js-licenses-${DATE}.json"
echo "  ${OUT_DIR}/js-license-summary-${DATE}.txt"
echo "  ${OUT_DIR}/py-licenses-${DATE}.json"
echo "  ${OUT_DIR}/py-licenses-${DATE}.md"
echo ""
echo "下一步: 人工核对 docs/compliance/third-party-notices.md，"
echo "       根据上述报告更新版本号、新增/移除依赖、变更许可证。"
