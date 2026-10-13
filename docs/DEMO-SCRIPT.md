# Spec2Run demo script

One continuous take, 90-120 seconds, screen recording with voiceover. No cuts
if you can manage it. Record at 1080p, browser zoom 100%, dark UI as shipped.

## Setup before you hit record

- Open https://spec2run.fluxyai.codes in a clean window, prompt studio visible.
- Have a second tab ready with the repo: github.com/abdullah129026/spec2run.
- Close notifications. Mic check: one sentence, play it back.

## The take

**0:00 - 0:10, hook.** Show the headline. Say: "This is Spec2Run. I type
what I want, and I get a live API with a real database, not a code snippet."

**0:10 - 0:35, the prompt.** Type, don't paste (typing reads as real):

> Create an API for a bookstore with books, authors, and orders. Books have
> title and price. I need JWT auth.

Hit Generate. While it works, say: "It drafts an OpenAPI spec first, and
validates it before anything gets rendered. Vague prompts get questions back
instead of a guess."

**0:35 - 0:55, the spec.** Swagger tab is live. Scroll the endpoints, expand
one. Say: "There's the contract. And here's the part most demos fake."

**0:55 - 1:15, the code.** Switch to the Code tab. Show the auth routes,
register and login, real token verification. Say: "Working JWT auth, rendered
from templates, not hallucinated. Every file passes a syntax check before you
ever see it."

**1:15 - 1:40, the sandbox.** Boot the sandbox, show the live URL, run one
request in the Swagger "Try it out" panel: register, login, create a book.
Say: "It boots right here with its own Postgres database. This URL works."

**1:40 - 2:00, the diff.** In the prompt box type: "add reviews to books".
Show the Diff tab. Say: "Now I change my mind, and I get a diff of exactly
what moved, spec and code, like a pull request against my own idea."

**Outro, 5 seconds.** Repo link on screen. Say: "Spec2Run. Type your API into
existence."

## If something breaks mid-take

- Generation stalls: say "the model is thinking", keep the take, it usually
  lands within a minute on the free tier.
- Sandbox boot fails: cut, re-record from the 1:15 mark. Boot failures are a
  known cold-start issue on Render free, not a script problem.
- Never fake a step. If the sandbox won't boot, record without it and say so.

## Live-demo variant (5 minutes, projector)

Same beats, slower. Pause after the Swagger tab and take one prompt from the
audience. Audience prompts are the real test: if it handles theirs, the demo
lands harder than any scripted run.
