# Real-user outreach kit

Goal: 10 people generate an API on the live site, you watch what breaks, you
collect quotes. Time-box: 3 evenings, then stop and fix what you found.

## Where to post

Hackathon Discords (MLH, Major League Hacking affiliates, hackathon servers
you've actually been in) and student CS Discords (your university, Pakistani
dev communities). Post where you're a member, not a stranger. One post per
server, no cross-posting spam.

## Post draft: hackathon Discords

> Built something for hackathons and I'm looking for 10 people to break it.
> Spec2Run: you type what your API should do in plain English, it generates
> the OpenAPI spec, the FastAPI code with working JWT auth, and boots it in a
> live sandbox with a real Postgres DB. Takes about 2 minutes.
>
> Try it: https://spec2run.fluxyai.codes
>
> Tell me the prompt you tried and where it confused you. Brutal feedback
> welcome, that's the whole point.

## Post draft: student Discords

> Hey everyone, I built a tool for our kind of projects and I need testers.
> You describe an API in plain English ("a library API with books and
> members"), and it generates the spec, the backend code, and a live URL you
> can actually call. No setup.
>
> https://spec2run.fluxyai.codes
>
> Try one prompt and reply with what broke or what felt off. Takes 2 minutes
> and it genuinely helps my final-year project.

## What to watch for (the actual job)

Don't watch the successes. Watch for these:

- The prompt they type before they simplify it. That first, messy version is
  your real input distribution.
- Where they hesitate: the auth toggle, the import dialog, the diff tab.
  Hesitation is a bug report.
- Anything they paste from elsewhere (an existing Swagger file, a class
  assignment spec). That's the import flow being tested for free.
- Exact error text they hit. Screenshot it, don't paraphrase.

## Asking for a quote

After someone gets a working API, one message:

> Glad it worked. Can I quote you on the repo? One line is enough, like
> "generated my hackathon backend in 2 minutes".

Log name (or handle), quote, date. Ask before using a real name.

## Session log

| # | Where | Prompt tried | Broke? | Quote? |
|---|-------|--------------|--------|--------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |
| 6 | | | | |
| 7 | | | | |
| 8 | | | | |
| 9 | | | | |
| 10 | | | | |

Fill this in as sessions happen. Ten rows, then the item is done and the
fixes go on the roadmap.
