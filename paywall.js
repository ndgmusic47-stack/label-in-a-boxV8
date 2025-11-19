/**
 * Paywall helper utilities
 * Handles upgrade_required responses from the API
 */

export function handlePaywall(response, openUpgradeModal) {
  if (response && response.error === "upgrade_required") {
    openUpgradeModal(response.feature);
    return false;
  }
  return true;
}

