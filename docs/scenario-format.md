# Scenario Storage Format

Scenarios are stored below `data/scenarios`.

## Directory Layout

```text
data/scenarios/
  scenario-<id>/
    scenario.json
    trigger-content/
      <asset-file>
```

Legacy `*.json` files directly under `data/scenarios` remain readable. New and
updated scenarios use the directory layout.

## `scenario.json`

The file contains the normal scenario fields plus scene-level triggers:

```json
{
  "id": 123,
  "title": "Example",
  "scenes": [
    {
      "id": 1,
      "content": "Scene text",
      "marker": "AI-visible summary marker",
      "triggers": [
        {
          "id": 1,
          "keyword": "sealed letter",
          "content_mode": "text",
          "content": "Original trigger content"
        },
        {
          "id": 2,
          "keyword": "letter image",
          "content_mode": "image",
          "asset_name": "letter.png",
          "asset_path": "trigger-content/letter.png",
          "asset_mime": "image/png",
          "asset_size": 1024
        }
      ]
    }
  ]
}
```

The AI receives trigger IDs, keywords, and content modes in the room snapshot.
Trigger content is only loaded by `trigger.reveal_scenario_trigger` and is
returned to chat without AI rewriting. Image triggers render as images and
file triggers render as download links under `/assets/scenarios/`.

Attachment size is controlled by `[scenario].trigger_max_file_size` in
`data/config/general.toml`.
