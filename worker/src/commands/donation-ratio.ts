/** Zero received donations is defined as zero for both display and ranking. */
export function donationRatio(donated: number, received: number): number {
  return received > 0 ? donated / received : 0;
}

// The leading zero counts toward the three-digit display budget as well.
const fractionalRatioNumber = new Intl.NumberFormat('en', { maximumFractionDigits: 2, useGrouping: false });
const ratioNumber = new Intl.NumberFormat('en', { maximumSignificantDigits: 3, useGrouping: false });
const largeRatioNumber = new Intl.NumberFormat('en', { maximumSignificantDigits: 3, notation: 'compact' });
export function formatDonationRatio(value: number): string {
  if (value < 1) return fractionalRatioNumber.format(value);
  const formatted = ratioNumber.format(value);
  // Rounding 999.5 can produce 1000; compact that instead of showing four digits.
  return formatted.replace(/\D/gu, '').length > 3 ? largeRatioNumber.format(value) : formatted;
}
