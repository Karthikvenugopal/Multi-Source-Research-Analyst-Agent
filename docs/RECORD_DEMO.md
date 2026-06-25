# Recording the demo GIF

A short screen recording of the app is the most reliable portfolio artifact (a
live public demo rate-limits on the free Gemini tier). Here's how to make one.

## 1. Run the app

```bash
source venv/bin/activate
python app.py            # opens http://localhost:7860
```

Ask **one** question — that's only ~3 Gemini calls, so it fits even a nearly
exhausted free-tier daily quota. Good choices:

- "What is retrieval-augmented generation and why is it used?"
- "How do solar and wind energy compare in cost and reliability?"

Let it finish so the recording shows the metrics panel and the cited report.

## 2. Record the screen

- **macOS:** `Cmd+Shift+5` to capture the browser region (or use [Kap](https://getkap.co)
  to record straight to GIF).
- Keep it short (~15–25s): type the question, hit submit, scroll the report.

## 3. Convert to GIF (if you recorded a video)

```bash
# with ffmpeg
ffmpeg -i recording.mov -vf "fps=10,scale=900:-1:flags=lanczos" docs/demo.gif
```

## 4. Embed it

Save the file as `docs/demo.gif`, then in `README.md` (the Demo section) replace
the commented placeholder with:

```markdown
![demo](docs/demo.gif)
```

Commit it:

```bash
git add docs/demo.gif README.md
git commit -m "Add demo recording"
```
