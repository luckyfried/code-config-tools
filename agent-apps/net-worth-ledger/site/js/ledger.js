// The ledger as the page uses it: accounts with their colors, and one point per snapshot with its totals.
const HEX = /^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/;

export const monthIndex = (month) => {
  const [y, m] = month.split("-").map(Number);
  return y * 12 + (m - 1);
};

export function readLedger() {
  const config = window.__APP_CONFIG__ || {};
  const data = window.__LEDGER__ || config;
  const accounts = (data.accounts || []).map((account) => ({
    id: account.id,
    label: account.label || account.id,
    kind: account.kind === "liability" ? "liability" : "asset",
    color: typeof account.color === "string" && HEX.test(account.color) ? account.color : null,
  }));
  let assetN = 0;
  let debtN = 0;
  for (const account of accounts) {
    if (account.color) continue;
    account.color = account.kind === "asset" ? `var(--asset-${(assetN++ % 5) + 1})` : `var(--debt-${(debtN++ % 4) + 1})`;
  }
  const assets = accounts.filter((account) => account.kind === "asset");
  const debts = accounts.filter((account) => account.kind === "liability");
  const points = [...(data.snapshots || [])]
    .sort((a, b) => (a.month < b.month ? -1 : 1))
    .map((snapshot) => {
      const balances = {};
      for (const account of accounts) balances[account.id] = Math.abs(Number(snapshot.balances?.[account.id]) || 0);
      const assetTotal = assets.reduce((sum, account) => sum + balances[account.id], 0);
      const debtTotal = debts.reduce((sum, account) => sum + balances[account.id], 0);
      return { month: snapshot.month, idx: monthIndex(snapshot.month), balances, assets: assetTotal, debts: debtTotal, net: assetTotal - debtTotal };
    });
  const milestones = (data.milestones || config.milestones || [])
    .filter((milestone) => milestone && typeof milestone.label === "string" && Number.isFinite(Number(milestone.value)))
    .map((milestone) => ({ label: milestone.label, value: Number(milestone.value) }));
  return {
    title: config.title || data.title || "",
    currency: data.currency || config.currency || "USD",
    accounts,
    assets,
    debts,
    points,
    milestones,
  };
}
