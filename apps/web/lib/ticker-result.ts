export type MoveInputs = {
  compression: number | null;
  volumeMultiple: number | null;
  rangeMultiple: number | null;
  impliedMove: number | null;
};

export type LeanInputs = {
  favored: string | null;
  return20: number | null;
  sampleSize: number | null;
};

export type CrowdInputs = {
  bullPosts: number;
  bearPosts: number;
  forumCount: number;
};

export function moveSizeCopy(input: MoveInputs): string[] {
  const lines: string[] = [];
  if (input.compression == null) {
    lines.push(
      "A full volatility comparison is not saved for this company yet.",
    );
  } else if (input.compression < 1) {
    lines.push(
      `Recent prices have been quieter than this stock's longer window. The 10-session volatility is ${input.compression.toFixed(2)} times the 60-session volatility.`,
    );
  } else {
    lines.push(
      `Recent prices have been jumpier than this stock's longer window. The 10-session volatility is ${input.compression.toFixed(2)} times the 60-session volatility.`,
    );
  }
  if (input.volumeMultiple != null) {
    lines.push(
      `The latest session's volume is ${input.volumeMultiple.toFixed(1)} times this stock's typical volume over the prior 20 sessions.`,
    );
  }
  if (input.rangeMultiple != null) {
    lines.push(
      `The latest session's price range is ${input.rangeMultiple.toFixed(1)} times the typical range over those sessions.`,
    );
  }
  if (input.impliedMove != null) {
    lines.push(
      `Saved option prices are about ${(input.impliedMove * 100).toFixed(1)}% either way. That is what options were pricing, not a promise.`,
    );
  } else {
    lines.push("A saved options move is not available yet.");
  }
  lines.push(
    "This is not a published chance of a large move or of making money.",
  );
  return lines;
}

export function leanCopy(input: LeanInputs): string[] {
  const lines: string[] = [];
  if (input.favored === "BULL" || input.favored === "MORE") {
    lines.push("The saved research lean is up.");
  } else if (input.favored === "BEAR" || input.favored === "LESS") {
    lines.push("The saved research lean is down.");
  } else {
    lines.push("No direction lean is saved yet.");
  }
  if (input.return20 != null) {
    const percent = Math.abs(input.return20 * 100).toFixed(1);
    lines.push(
      input.return20 >= 0
        ? `Over the last 20 sessions, the price rose about ${percent}%.`
        : `Over the last 20 sessions, the price fell about ${percent}%.`,
    );
  }
  lines.push(
    input.sampleSize != null
      ? `The sample behind this case is ${input.sampleSize} cases. No chance of profit is published.`
      : "No chance of profit is published.",
  );
  lines.push("A lean is not a forecast that the price keeps moving that way.");
  return lines;
}

export function crowdCopy(input: CrowdInputs): string[] {
  const lines: string[] = [];
  if (input.forumCount === 0) {
    lines.push(
      "No Stocktwits sample is saved for this company. Missing posts are not treated as neutral.",
    );
  } else if (input.bullPosts > input.bearPosts) {
    lines.push("In this sample, more posts were tagged bullish than bearish.");
  } else if (input.bearPosts > input.bullPosts) {
    lines.push("In this sample, more posts were tagged bearish than bullish.");
  } else {
    lines.push(
      "In this sample, bullish and bearish tags are tied, or most posts have no tag.",
    );
  }
  if (input.forumCount > 0) {
    lines.push(
      `${input.bullPosts} bullish tags, ${input.bearPosts} bearish tags, ${input.forumCount} recent sampled posts.`,
    );
  }
  lines.push("Reddit is not connected.");
  lines.push(
    "This sample is not every retail investor, and it is not a chance of profit.",
  );
  return lines;
}
