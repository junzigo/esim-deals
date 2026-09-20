# esim-deals

An independent, English-language directory of official travel eSIM promotions for US travelers. Built with Python's standard library. No runtime LLM, paid data API, database, server process or third-party Python dependency.

**Deployment status: live at https://esim-deals-apb.pages.dev/.** Public source: https://github.com/junzigo/esim-deals. GitHub Actions run [35482450665](https://github.com/junzigo/esim-deals/actions/runs/35482450665) completed successfully on 2026-09-20. Its observation commit `cfa5059ea7ee8a948beb5f08c728e5f60a6e0210` automatically triggered successful Cloudflare Pages deployment `d0bf4866-0302-4478-a583-e266451c6110`. The production page was browser-verified. The six-hour schedule is configured; this verifies the push-triggered pipeline, not a future scheduled run.

## Run

```sh
python -m unittest discover -s tests -v
python scraper.py
python build.py
python validate.py
```

Python 3.12 or later. Output: `site/`. Public observations: `data/offers.json`. Provider list, URLs, affiliate destinations, parser patterns, freshness and schedule are defined in `.ilang/site.ilang`. `scraper.py` and `build.py` both parse that file via `config.py`. Removing a provider removes it from the rendered site; the tests perform this actual mutation and rebuild in a temporary directory.

## Data integrity

- Read official public HTML only, after checking robots.txt; bounded requests and named user agent. HTTP denials, certificate failures and unavailable robots fail closed. No alternate identity, proxy rotation, CAPTCHA bypass or login scraping.
- Coupon codes and percentages require a matching visible-text pattern. Script data, navigation text without a match, generic savings claims and unmatched pages are not promoted into offers.
- Each observation includes source URL, UTC retrieval time, short evidence excerpt and SHA-256 of fetched HTML. This proves provenance of the observation, **not redemption success**.
- No last-known-good offer is carried forward after a failed scrape. Stale and expired records are excluded at build time. Unknown expiry and prices stay absent. A percentage discount is not a product price.
- Nomad and Saily currently have no approved extraction pattern. They remain monitored source entries, with no invented deal. Holafly has a parser but was unavailable during the first local run.
- Seasonal source pages may remain online after a promotion ends; the UI explicitly requires provider confirmation. Monitor parser changes. Automation is not a guarantee of perpetual accuracy.

## Deployment and automation

The public repository `junzigo/esim-deals` is connected to Cloudflare Pages project `esim-deals`, production branch `main`, build command `python build.py`, output directory `site`. Set the confirmed production domain and repository URL in `.ilang/site.ilang` before production deployment. The Cloudflare GitHub App must be authorized for this repository; a Cloudflare API token alone does not grant access to GitHub.

`.github/workflows/update.yml` runs every six hours at minute 23 UTC, plus manual dispatch and relevant source changes. It tests, scrapes, builds, validates and commits only source observations. It uses GitHub's automatic `GITHUB_TOKEN` to push; no manually created data API key is required. Pages Git integration is intended to deploy that commit. Verify an actual Actions run **and the subsequent Pages deployment** before calling this automated pipeline operational. A workflow-created push does not recursively trigger another GitHub Actions push workflow.

The workflow schedule is checked against the config by a test. GitHub reads cron from YAML before Python starts, so changing the schedule requires updating the YAML to match; provider/render changes only require the config.

## Costs and operational limits — checked against official docs

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions): standard GitHub-hosted runners for public repositories are free. This does not mean every runner type or every GitHub product is unlimited/free.
- [Cloudflare Pages limits](https://developers.cloudflare.com/pages/platform/limits/): Free allows 500 builds/month. The planned cadence is `24 / 6 = 4` runs/day and at most `4 × 31 = 124` scheduled builds in a 31-day month, excluding manual runs and extra pushes. This is a schedule calculation, not a usage measurement or promise of unchanged future pricing.
- [GitHub scheduled events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows): scheduled jobs can be delayed or dropped; public repositories can have schedules disabled after 60 days without repository activity. Do not promise unattended operation forever.
- No paid plan, credit-card setup, domain purchase or affiliate signup is performed by this repository.

## SEO without invented guarantees

Pages have canonical URLs, unique descriptive metadata, Open Graph cards, BreadcrumbList, Offer/Service and ItemList JSON-LD where appropriate. No fabricated stock, price, expiry, aggregate ratings or reviews. `validate.py` checks syntax and internal consistency only; it is **not** Google's Rich Results Test. Coupon-only Offer markup is not automatically eligible for a product price rich result. [Google explicitly does not guarantee rich results](https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data).

No claim is made that domain age, GitHub commits, a public repository link, or changing dates alone causes rankings. A custom domain can improve branding, ownership and portability; purchasing one immediately is not an SEO requirement. A Pages subdomain can host a useful indexable site. See [Google's SEO starter guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide).

## Monetization, when actually approved

Initial links go to the official sources, with no invented affiliate ID. Candidate official programs: [Airalo](https://partners.airalo.com/solutions/affiliates) and [RedteaGO](https://redteago.com/affiliates/). Approval, coupon-site eligibility, channel rules and commission terms must be checked for the actual account. Nothing here claims acceptance or recurring commission. Hosting-affiliate examples in the original brief do not apply to this eSIM niche.

After approval, put the real approved destination in the fourth provider column and update the public disclosure. Affiliate destinations receive `rel="sponsored nofollow noopener"`. Do not replace a coupon source with an unrelated generic referral landing page that fails to honor the published offer. No brand bidding, cookie injection, self-referral, fabricated offers or platform-rule evasion. Additional disclosed sponsorship placements can be considered only after an actual agreement; no sponsorship or revenue is claimed today. A sale valuation would need verifiable revenue and traffic, neither of which currently exists.

First release publishes only the website and repository; no X/Facebook account or automated messages. Credentials must stay outside the repository and public assets.

站点规则用 I-Lang 协议描述，见 `.ilang/site.ilang`，协议说明 ilang.ai。
