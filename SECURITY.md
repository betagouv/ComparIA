# Reporting a vulnerability

If you find a security problem in compar:IA, in this code or on a running instance, write to us before telling anyone else. Please do not open a public issue or discussion for it.

- **ssi.snum@culture.gouv.fr**, the security team of the French Ministry of Culture, which hosts the service
- **contact@comparia.beta.gouv.fr**, the project team

Write in French or English. Say which instance or which commit is affected, what you did, and what you saw. A proof of concept helps; a working exploit is not needed.

We answer within five working days. We keep you posted while we fix the problem, and we credit you in the release notes if you want us to.

A machine-readable version of this page is served at `/.well-known/security.txt` on every instance ([RFC 9116](https://www.rfc-editor.org/rfc/rfc9116)).

## What to report

Anything that lets someone read data they should not, act as another user or an admin, run code on our servers, or take the service down. This includes the arena, the admin panel, the published datasets and the deployment files in this repository.

## What we ask

Do not read, change or delete data that is not yours, do not run tests that degrade the service for its users, and give us time to fix the problem before you publish anything about it.
