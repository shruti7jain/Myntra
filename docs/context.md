# Strategic Context: AI-Powered Discovery Engine for Myntra Wishlist Conversion

---

## 1. Executive Overview & Problem Definition

### 1.1 Product & Industry Context
* **Platform**: **Myntra** — India’s leading fashion e-commerce platform with millions of users.
* **Core Phenomenon**: Users browse products and save their favorite items to their **Wishlist**, marking a strong high-intent signal (they are explicitly interested, but haven't purchased).
* **The Conversion Paradox**: Users accumulate numerous saved items, yet only a small fraction translate into an actual checkout. 

### 1.2 The Strategic Business Goal
```
Increase the percentage of users who purchase at least one item from their wishlist within 30 days of adding it.
```

### 1.3 The Non-Negotiable Constraints
> [!IMPORTANT]
> **Strictly NO Monetary Incentives**: The solution cannot offer direct monetary incentives (discounts, coupons, subsidies) to users. The engine must focus on discovering the underlying user problems—psychological, experiential, informational, and cognitive.

> [!WARNING]
> **Research Source Constraint**: The Discovery Engine must use **ONLY** the following four source types:
> 1. Apple App Store reviews
> 2. Google Play Store reviews
> 3. Reddit discussions/comments
> 4. YouTube comments
> 
> **Text-Data Only**: The system processes exclusively textual data from these sources. No noise, sound, audio, or image data is used.

---

## 2. Core Discovery Questions

The AI Discovery Engine should investigate the following core questions:
1. Why do users add fashion products to their wishlist?
2. What prevents wishlisted products from eventually being purchased?
3. What uncertainties remain after a user has identified a product they like?
4. What causes users to postpone a purchase?
5. How do users compare multiple shortlisted or wishlisted products?
6. What information do users seek outside Myntra before purchasing?
7. What role do fit and size, styling, price, reviews, occasion, and social validation play in purchase decisions?
8. When is the wishlist used as genuine purchase intent versus simple bookmarking or saving for later?
9. How do these behaviors differ across meaningful user segments?
10. What unmet needs appear repeatedly across user conversations?
11. Which opportunity areas appear most likely to influence wishlist-to-purchase conversion?

---

## 3. What the Engine Should Do

The system needs to establish a repeatable workflow covering:

1. **Source Collection**: Ingesting from the four allowed sources.
2. **Data Cleaning**: Normalizing text while preserving the original evidence.
3. **Relevance Filtering**: Identifying conversations relating to fashion, wishlisting, hesitations, etc.
4. **User Intent/Behavior Extraction**: Extracting intent, blockers, current workarounds, etc.
5. **Thematic Clustering**: Clustering recurring problems into coherent opportunity themes.
6. **Intent Distinction**: Differentiating high-intent purchase vs. bookmarking.
7. **Meaningful Segmentation**: Segmenting insights appropriately, avoiding unsupported demographics.
8. **Evidence Quantification**: Quantifying opportunity areas using interpretable calculations.
9. **Opportunity Comparison**: Comparing opportunities based on evidence and relevance.
10. **Traceability**: Preserving a link from insights back to underlying source evidence.
11. **Structured Output**: Producing output for Product Managers to validate via primary user research.

### Recommended Analysis Pipeline
`Source Collection → Data Cleaning → Relevance Filtering → User Intent/Behavior Extraction → Problem & Pain-Point Extraction → Thematic Clustering → User/Need Segmentation → Evidence Quantification → Opportunity Comparison/Prioritization → Evidence-Backed Discovery Report`

---

## 4. Important Distinctions & Opportunity Areas

### Important Distinctions
The engine must avoid simple assumptions, distinguishing between:
- *"User likes the product"* vs. *"User intends to purchase the product"*
- *"User is postponing purchase"* vs. *"User has no purchase intent"*
- *"User needs more information"* vs. *"User simply wants a bookmark"*
- *"Price is mentioned"* vs. *"Price uncertainty is actually preventing purchase"*

It must also avoid treating sentiment alone as the problem; negative reviews do not automatically equal a wishlist-to-purchase problem.

### Opportunity Areas to Investigate (Hypotheses)
- Fit and size confidence
- Product quality confidence
- Price uncertainty or waiting for a better price
- Difficulty comparing shortlisted products
- Lack of styling, outfit context, or occasion-based uncertainty
- Insufficient reviews, social proof, or trustworthy user-generated info
- Availability/size/color uncertainty
- Wishlist overload & saving products primarily for bookmarking
- Need for off-platform information before purchase

---

## 5. Expected Output & Success Criteria

### Expected Output
The structured discovery output should contain at minimum:
1. Executive summary of strongest findings.
2. Top recurring user problems/themes & their evidence volume.
3. Relative prevalence or estimated share.
4. Representative source evidence, associated user intent/behavior, and existing workarounds.
5. Relevant user segments or contexts.
6. Estimated relationship to wishlist-to-purchase conversion.
7. Opportunity prioritization and recommended areas for primary user research.
8. A clear list of unresolved questions requiring interview validation.

### Evidence and Trust Requirements
- Keep source attribution and store source text.
- Separate observed evidence from AI-generated interpretation.
- Label assumptions clearly, avoid fabricating feedback, and avoid presenting unsupported percentages as facts.

### Success Criteria (Part 1 MVP)
Build the simplest functional version of the Discovery Engine. It succeeds when it can process relevant conversations from the four sources, identify barriers, distinguish intents, quantify prevalence, prioritize opportunities, show source-level evidence, and produce a shortlist for validation.

> [!CAUTION]
> **Out of Scope for Part 1**: Do NOT design the final product solution before discovery. Do NOT assume root causes without evidence. Do NOT rely only on sentiment analysis or use external sources outside of the 4 allowed ones.
