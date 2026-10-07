# Implementation decisions

The attached MASTER_PLAN and root AGENTS supersede earlier product specifications.

- Keep the existing production application until the new application and Phase 3 pass. No destructive migration of legacy data.
- Free services only. Missing paid historical options data is not replaced by synthetic production data.
- A directional probability is not a profit probability. Variable option payoffs require a payoff distribution and transaction costs; no invented expected-value ranking from direction alone.
- Shares with stops have gap risk. Without an approved account budget, show per-share or one-contract exposure, never a quantity recommendation.
- Alpaca IEX is a partial equity feed and indicative options are not executable quotes. Preserve feed labels and source rights; no artificial liquidity or calibrated probability claims.
- GitHub Actions schedules perform analysis; Vercel renders cached Supabase data. Live broker execution remains disabled.
