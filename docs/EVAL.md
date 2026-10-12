# Spec2Run eval — 2026-10-12

Mode: **fixtures**.
SPEC2RUN_GROQ_API_KEY was unset, so the LLM generation stage was not measured. Each prompt ran validate -> render -> boot -> smoke over a hand-written fixture spec; prompts without a fixture are marked skipped. The full 50-prompt LLM run happens on the deployed backend where the key is configured.

## Summary

- prompts: 50
- measured: 6, passed: 6, failed: 0, skipped: 44
- spec-match issues (rendered service vs prompt intent): 0

## Results

| prompt | result | stages | failures |
| --- | --- | --- | --- |
| bookstore | passed | spec:ok, validate:ok, render:ok, boot:ok, smoke:ok | - |
| todo | passed | spec:ok, validate:ok, render:ok, boot:ok, smoke:ok | - |
| blog | passed | spec:ok, validate:ok, render:ok, boot:ok, smoke:ok | - |
| vague | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| gym | passed | spec:ok, validate:ok, render:ok, boot:ok, smoke:ok | - |
| recipes | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| notes | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| bookmarks | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| inventory | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| events | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| movies | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| contacts | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| library | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| pets | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| courses | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| playlists | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| expenses | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| fitness | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| chat | passed | spec:ok, validate:ok, render:ok, boot:ok, smoke:ok | - |
| journal | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| habits | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| urls | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| photos | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| school | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| clinic | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| ecommerce | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| restaurant | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| projects | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| forum | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| sensors | passed | spec:ok, validate:ok, render:ok, boot:ok, smoke:ok | - |
| flags | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| weather | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| jobs | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| realestate | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| tickets | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| newsletter | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| polls | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| kanban | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| podcast | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| garage | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| cafe | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| vague2 | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| vague3 | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| vague4 | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| single | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| many | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| donations | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| qna | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| hotels | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |
| fleet | skipped | - | no fixture; needs SPEC2RUN_GROQ_API_KEY for the LLM stage |

## Failures

None. Every measured prompt rendered, booted, and passed the smoke test (CRUD on all entities, auth flow where requested).

## Not measured (no LLM key in this environment)

`vague`, `recipes`, `notes`, `bookmarks`, `inventory`, `events`, `movies`, `contacts`, `library`, `pets`, `courses`, `playlists`, `expenses`, `fitness`, `journal`, `habits`, `urls`, `photos`, `school`, `clinic`, `ecommerce`, `restaurant`, `projects`, `forum`, `flags`, `weather`, `jobs`, `realestate`, `tickets`, `newsletter`, `polls`, `kanban`, `podcast`, `garage`, `cafe`, `vague2`, `vague3`, `vague4`, `single`, `many`, `donations`, `qna`, `hotels`, `fleet`
