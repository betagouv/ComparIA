#!/usr/bin/env python3
"""
Smoke test for CompaRAG prod stack.

Usage:
    BACKEND_URL=https://your-backend.railway.app \\
    FRONTEND_URL=https://your-frontend.vercel.app \\
    python scripts/smoke_test.py

    # Or with CLI args:
    python scripts/smoke_test.py \\
        --backend-url https://your-backend.railway.app \\
        --frontend-url https://your-frontend.vercel.app \\
        --verbose

Checks (in order, per D-09):
  1. GET /health -> 200 with status ok
  2. GET FRONTEND_URL -> 200
  3. POST /tool-arena/compare -> 200, both error_a and error_b are null
  4. POST /tool-arena/vote -> 200 (uses X-Session-Hash from compare response)
  5. Verify reveal response contains non-empty tool_a.name and tool_b.name

Exit code: 0 if all checks pass, 1 if any check fails.
"""

import argparse
import os
import sys

import httpx


def check(label: str, condition: bool, verbose: bool = False, detail: str = "") -> bool:
    """Print [PASS] or [FAIL] for a check, optionally with detail."""
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    if verbose and detail:
        print(f"       {detail}")
    return condition


def run_smoke_test(backend_url: str, frontend_url: str, verbose: bool) -> int:
    """
    Run all smoke test checks against the deployed stack.

    Returns 0 if all checks pass, 1 if any fail.
    """
    all_passed = True
    client = httpx.Client(timeout=30.0)

    try:
        # Step 1 — Backend health (per D-09 check 1)
        try:
            r = client.get(f"{backend_url}/health")
            ok = r.status_code == 200 and r.json().get("status") == "ok"
            all_passed &= check("GET /health -> 200", ok, verbose, r.text)
        except Exception as exc:
            all_passed &= check("GET /health -> 200", False, verbose, str(exc))

        # Step 2 — Frontend loads (per D-09 check 2)
        try:
            r = client.get(frontend_url, follow_redirects=True)
            ok = r.status_code == 200
            all_passed &= check("GET FRONTEND_URL -> 200", ok, verbose, str(r.status_code))
        except Exception as exc:
            all_passed &= check("GET FRONTEND_URL -> 200", False, verbose, str(exc))

        # Step 3 — Compare / MCP reachability (per D-07, D-09 check 3)
        # MCP dispatch + LLM mediation requires a longer timeout (D-09)
        session_hash = ""
        try:
            r = client.post(
                f"{backend_url}/tool-arena/compare",
                json={
                    "task": "Summarize the key concepts of retrieval-augmented generation",
                    "goal": "A concise 3-sentence summary that covers indexing, retrieval, and generation steps",
                },
                timeout=120.0,
            )
            ok_status = r.status_code == 200
            if ok_status:
                body = r.json()
                error_a = body.get("error_a")
                error_b = body.get("error_b")
                ok_errors = error_a is None and error_b is None
                session_hash = body.get("session_hash", "")
            else:
                ok_errors = False
                body = {}
            detail = r.text[:300] if verbose else str(r.status_code)
            all_passed &= check(
                "POST /tool-arena/compare -> 200, no MCP errors",
                ok_status and ok_errors,
                verbose,
                detail,
            )
        except Exception as exc:
            all_passed &= check(
                "POST /tool-arena/compare -> 200, no MCP errors",
                False,
                verbose,
                str(exc),
            )

        if not session_hash:
            print("[SKIP] Vote and reveal checks skipped (no session_hash from compare)")
            return 1

        # Step 4 — Vote (per D-08, D-09 check 4)
        vote_ok = False
        try:
            r = client.post(
                f"{backend_url}/tool-arena/vote",
                json={"chosen": "a"},
                headers={"X-Session-Hash": session_hash},
            )
            vote_ok = r.status_code == 200
            detail = r.text[:300] if verbose else str(r.status_code)
            all_passed &= check("POST /tool-arena/vote -> 200", vote_ok, verbose, detail)
        except Exception as exc:
            all_passed &= check("POST /tool-arena/vote -> 200", False, verbose, str(exc))

        # Step 5 — Reveal identity verification (per D-09 check 5)
        # Vote response IS the ToolRevealResponse (router.py returns _build_reveal_response)
        if vote_ok:
            try:
                reveal = r.json()
                tool_a_name = reveal.get("tool_a", {}).get("name", "")
                tool_b_name = reveal.get("tool_b", {}).get("name", "")
                has_identities = bool(tool_a_name) and bool(tool_b_name)
                detail = str(reveal) if verbose else f"tool_a.name={tool_a_name!r}, tool_b.name={tool_b_name!r}"
                all_passed &= check(
                    "Reveal returns MCP identities (tool_a.name, tool_b.name)",
                    has_identities,
                    verbose,
                    detail,
                )
            except Exception as exc:
                all_passed &= check(
                    "Reveal returns MCP identities (tool_a.name, tool_b.name)",
                    False,
                    verbose,
                    str(exc),
                )
    finally:
        client.close()

    if all_passed:
        print("\nAll checks passed.")
    else:
        print("\nOne or more checks failed.")

    return 0 if all_passed else 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CompaRAG prod smoke test — exercises the full arena cycle against live URLs.",
        epilog=(
            "Set BACKEND_URL and FRONTEND_URL env vars, or pass --backend-url and --frontend-url. "
            "Exit code 0 = all checks pass, 1 = any failure."
        ),
    )
    parser.add_argument(
        "--backend-url",
        default=os.getenv("BACKEND_URL"),
        required=not bool(os.getenv("BACKEND_URL")),
        help="Backend root URL (e.g. https://your-app.railway.app). Default: $BACKEND_URL.",
    )
    parser.add_argument(
        "--frontend-url",
        default=os.getenv("FRONTEND_URL"),
        required=not bool(os.getenv("FRONTEND_URL")),
        help="Frontend root URL (e.g. https://your-app.vercel.app). Default: $FRONTEND_URL.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print request/response detail for each check.",
    )
    args = parser.parse_args()

    # Strip trailing slashes so URL construction is consistent
    backend_url = args.backend_url.rstrip("/")
    frontend_url = args.frontend_url.rstrip("/")

    sys.exit(run_smoke_test(backend_url, frontend_url, args.verbose))


if __name__ == "__main__":
    main()
