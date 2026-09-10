"""
Onboarding Agent — local demo server.

Serves demo.html and proxies questions to the Anthropic API.
Session 1 uses the January 2026 knowledge base (old policy, old org).
Session 2 uses the May 2026 knowledge base (updated policy, re-org).

Usage:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python server.py
    open http://localhost:8001
"""

import json
import os
from pathlib import Path

import anthropic
from flask import Flask, Response, jsonify, request, send_file
from dotenv import load_dotenv

# Load .env from parent Basecamp-Exercises directory
load_dotenv(Path(__file__).parent.parent / ".env", override=True)

app = Flask(__name__)

# ── Session 1: January 2026 ─────────────────────────────────────────────────
# Old prod-access policy, old org chart.
SYSTEM_S1 = """\
You are the New-Hire Onboarding Agent for BTS-Synthetic Engineering.
Your knowledge reflects the state of the company as of January 2026.

Answer concisely and specifically. If you don't know something, say so.

## Organisation (January 2026)
- Head of Engineering: Anika Reddy (joined 2023, London, Slack @anika)
- Head of SRE: Carlos Mendes (Slack @carlosm) — owns the on-call rotation
- Head of Platform: Yuki Tanaka (Slack @yuki) — owns auth, signing, tenant-config
- Head of Security: Maya Singh (Slack @maya-s)
- Engineering Ops Lead: Tom Bryce (Slack @tomb) — "the person who knows where the bodies are buried"

## Service ownership
| Service            | Team     | Tech lead     |
|--------------------|----------|---------------|
| payment-service    | Payments | Tom Bryce     |
| auth-service       | Platform | Yuki Tanaka (day-to-day: Idris Patel) |
| signing-service    | Platform | Yuki Tanaka   |
| tenant-config      | Platform | Yuki Tanaka   |
| frontend           | Web      | Priya Shah    |

## Prod access (January 2026 policy)
1. Post in #sre-access-requests on Slack
2. Tag your direct manager AND the SRE on rota this week
3. SRE schedules a 30-minute pairing session ("within 2 working days")
4. After pairing, SRE files access via Okta — ~4 hours to provision
Tenure requirement: 2 weeks minimum before your request is processed.

## Git workflow
Trunk-based development. All changes via Pull Request. Two approvals required to merge.

## Post-mortems
Blameless culture. Written within 48 hours of any P0 or P1 incident.

## Day 1
Laptop, YubiKey, email, Slack, GitHub (org: bts-synthetic), read-only staging access.
No prod access on Day 1 — see prod access policy above.
"""

# ── Session 2: May 2026 ─────────────────────────────────────────────────────
# Updated prod-access policy, post-re-org org chart.
SYSTEM_S2 = """\
You are the New-Hire Onboarding Agent for BTS-Synthetic Engineering.
Your knowledge reflects the state of the company as of May 2026, after the April re-org.

Answer concisely and specifically. If something has changed since a previous policy,
lead your answer with: "⚠️ This changed — [old] → [new]"

## Organisation (May 2026 — post re-org)
- Head of Engineering: Yuki Tanaka (promoted April 2026; was Head of Platform)
- Anika Reddy: now Chief AI Officer (effective 2026-04-01) — no longer manages Engineering
- Head of Platform: Tom Bryce (promoted; was Engineering Ops Lead)
- Engineering Ops Lead: Priya Shah (moved from Web team lead)
- Head of SRE: Carlos Mendes — unchanged
- Head of Security: Maya Singh — unchanged

## Service ownership (post re-org)
| Service            | Team     | Tech lead     | Changed?    |
|--------------------|----------|---------------|-------------|
| payment-service    | Payments | Maya Patel    | ⚠️ was Tom Bryce |
| auth-service       | Platform | Idris Patel   | (Yuki now HoE; Idris runs it day-to-day) |
| frontend           | Web      | Daniel Okonkwo| ⚠️ was Priya Shah |
| signing-service    | Platform | unchanged     |             |
| tenant-config      | Platform | unchanged     |             |

## Prod access (UPDATED 2026-05-15 — supersedes January 2026 policy)
⚠️ Old process (Slack + SRE pairing) is GONE.
1. Complete "Prod Access Foundations" in the BTS Learning portal (~90 min, self-paced)
2. Request access via the IAM platform — link in your course completion email
3. Access granted as a 4-hour just-in-time window — re-request as needed
No Slack ticket. No SRE pairing session.
Tenure requirement: 3 working days (was 2 weeks). Most new hires are eligible from day 4.
Why it changed: the pairing-session backlog grew to 3 weeks. The model was built for 40 engineers; there are now 280.

## Git workflow
Trunk-based development. All changes via Pull Request. Two approvals required to merge. (unchanged)

## Post-mortems
Blameless culture. Written within 48 hours of any P0 or P1 incident. (unchanged)

## Day 1
Laptop, YubiKey, email, Slack, GitHub, read-only staging. Not prod. (unchanged)
"""


@app.route("/")
def index():
    return send_file("demo.html")


@app.route("/ask", methods=["POST"])
def ask():
    data = request.json or {}
    question = data.get("question", "").strip()
    session = int(data.get("session", 1))
    if not question:
        return jsonify({"error": "No question provided"}), 400

    system = SYSTEM_S1 if session == 1 else SYSTEM_S2

    def generate():
        try:
            client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY")
            )
            with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=600,
                system=system,
                messages=[{"role": "user", "content": question}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    key = os.environ.get("ANTHROPIC_API_KEY")
    print(f"\nOnboarding Agent — http://localhost:8001")
    print(f"ANTHROPIC_API_KEY: {'set ✓' if key else 'NOT SET ✗'}\n")
    app.run(port=8001, debug=False)
