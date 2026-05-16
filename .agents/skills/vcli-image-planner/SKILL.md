---
name: vcli-image-planner
description: "Use when Codex needs to decide whether a Velog post would benefit from screenshots, diagrams, or a thumbnail and prepare image requirements before using image generation."
---

# vcli: Image Planner

Decide whether the article needs visuals and what kind.

## Output

Provide:

1. Whether an image is needed at all
2. Image type: screenshot, diagram, illustration, or thumbnail
3. Purpose of the image in the article
4. Where it should appear
5. A concrete brief for image generation

## Rules

- Do not force images into posts that do not need them.
- Prefer screenshots for real product or code flows, diagrams for concepts, and thumbnails only when they add value.
- If an image should actually be generated, hand off to the existing `imagegen` skill with the prepared brief.
