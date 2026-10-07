export function premiumExposure(
  premium: number,
  multiplier: number,
  approvedBudget?: number,
): { oneContract: number; quantity: number | null } {
  if (
    !Number.isFinite(premium) ||
    !Number.isFinite(multiplier) ||
    premium <= 0 ||
    multiplier <= 0
  )
    throw new Error("Invalid contract economics");
  if (
    approvedBudget !== undefined &&
    (!Number.isFinite(approvedBudget) || approvedBudget <= 0)
  )
    throw new Error("Invalid budget");
  const oneContract = premium * multiplier;
  return {
    oneContract,
    quantity:
      approvedBudget === undefined
        ? null
        : Math.floor((approvedBudget * 0.01) / oneContract),
  };
}
