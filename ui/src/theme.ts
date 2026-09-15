// TRUSTEQ design tokens — DO NOT change these values (CLAUDE.md §8).
// The UI screenshots go into the deck.
export const theme = {
  navy: "#003366",
  navy2: "#1A4775",
  navy3: "#335C85",
  navyDark: "#001733",
  gold: "#AE9966",
  light: "#F2F2F2",
  font: "'Karla', system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
} as const;

// Ordered onboarding spine for the state-machine ribbon.
export const STATE_SPINE = [
  "DISCOVERED",
  "MANDATE_VALID",
  "IDENTIFIED",
  "SCREENED",
  "TAX_CONFIRMED",
  "APPROPRIATENESS_DONE",
  "INFORMED",
  "CUSTOMER_CONFIRMED",
  "BANK_ACCEPTED",
  "PROVISIONING",
  "DEPOT_OPENED",
] as const;

export const SERVICE_MODE_DE: Record<string, string> = {
  account_only: "Nur Kontoeröffnung (keine Prüfpflicht)",
  non_advised: "Beratungsfrei (Angemessenheit)",
  advised: "Mit Beratung",
};

export const STATE_LABEL_DE: Record<string, string> = {
  DISCOVERED: "Anbieter verifiziert",
  MANDATE_VALID: "Mandat gültig",
  IDENTIFIED: "Identifiziert",
  SCREENED: "Geprüft (AML)",
  TAX_CONFIRMED: "Steuer bestätigt",
  APPROPRIATENESS_DONE: "Angemessenheit",
  INFORMED: "Unterlagen",
  CUSTOMER_CONFIRMED: "Kunde bestätigt",
  BANK_ACCEPTED: "Bank angenommen",
  PROVISIONING: "Einrichtung",
  DEPOT_OPENED: "Depot eröffnet",
  CUSTOMER_REQUIRED: "Kunde gefragt",
  REVIEW_REQUIRED: "In Prüfung",
  RECONCILING: "Abgleich",
  ADVISED_HANDOFF: "An Berater übergeben",
  REJECTED: "Abgelehnt",
  EXPIRED: "Abgelaufen",
  CANCELLED: "Abgebrochen",
};
