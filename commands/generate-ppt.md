---
name: generate-ppt
description: "Generate a PowerPoint presentation from a source file (plan, markdown, text) or topic, following user instructions for style and content."
---

# /generate-ppt — PowerPoint Generator

Generate a `.pptx` presentation from a source file or topic. Uses AI to structure content into slides, then renders via `python-pptx`.

## Usage

```
/generate-ppt <source> [instructions]
/generate-ppt                          # Uses user's follow-up message for topic/instructions
```

- `<source>` — path to a file (markdown, plan, text, code) OR a topic/description string
- `[instructions]` — optional styling/content instructions (audience, tone, slide count, language, etc.)

## Examples

```
/generate-ppt .tracking/plans/auth-redesign.md Make it executive-friendly, 10 slides max
/generate-ppt src/services/README.md Technical onboarding deck for new engineers
/generate-ppt "AI in Education" 15 slides, bilingual EN/CN, for conference keynote
```

## Execution

### Step 1: Resolve source content

- If `<source>` is a file path → read the file
- If `<source>` is a string/topic → use it as the content seed
- If no source given → ask the user what the presentation should be about

### Step 2: Plan the slide deck

Based on the source content and user instructions, create a structured slide plan as a JSON array. Each slide should have:

```json
[
  {
    "layout": "title",
    "title": "Presentation Title",
    "subtitle": "Optional subtitle"
  },
  {
    "layout": "section",
    "title": "Section Name"
  },
  {
    "layout": "content",
    "title": "Slide Title",
    "bullets": ["Point 1", "Point 2", "Point 3"],
    "notes": "Speaker notes here"
  },
  {
    "layout": "two_column",
    "title": "Comparison",
    "left_title": "Before",
    "left_bullets": ["Old way 1", "Old way 2"],
    "right_title": "After",
    "right_bullets": ["New way 1", "New way 2"]
  },
  {
    "layout": "table",
    "title": "Data Overview",
    "headers": ["Col A", "Col B", "Col C"],
    "rows": [["r1c1", "r1c2", "r1c3"], ["r2c1", "r2c2", "r2c3"]]
  },
  {
    "layout": "blank",
    "title": "Visual Slide",
    "text": "Centered text or quote"
  }
]
```

Guidelines for slide planning:
- Title slide is always first
- Use section headers to organize major themes
- Keep bullets to 3-5 per slide (less is more)
- Match the audience and tone from user instructions
- Default to 8-15 slides unless user specifies otherwise
- Use tables for structured comparisons/data
- Use two-column for before/after, pros/cons comparisons

### Step 3: Generate the presentation

Write the slide plan JSON to a temp file, then run the generator script:

```bash
.venv/Scripts/python ~/.claude/scripts/generate_ppt.py \
  --slides slides.json \
  --output <output_path>.pptx \
  [--title "Presentation Title"] \
  [--widescreen]
```

Default output path: `./<slugified-title>.pptx` in the current working directory.

### Step 4: Report results

Tell the user:
- Where the `.pptx` file was saved
- Number of slides generated
- Suggest they review and customize in PowerPoint/Google Slides

## Notes

- The generator script lives at `~/.claude/scripts/generate_ppt.py`
- Supports layouts: title, section, content, two_column, table, blank
- Default slide size: widescreen 16:9 (13.33" x 7.5")
- Text auto-sizes within placeholders
- Speaker notes are added when provided
- For best results, give specific instructions about audience, tone, and key messages
