export const ALERT_FORMS = new Set(['SC 13D', 'SC 13D/A']);

export function classify(entry) {
  return ALERT_FORMS.has(entry.formType) ? 'alert' : 'digest';
}
