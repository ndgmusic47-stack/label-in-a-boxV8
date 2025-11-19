export function requireAuth(user, openAuthModal) {
  if (!user) {
    openAuthModal();
    return false;
  }
  return true;
}

