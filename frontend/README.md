# Frontend

SvelteKit, Vite, Tailwind, and the French Design System. Runs on port 5173.

`yarn dev` starts it, or `make dev-frontend` from the repository root, which is the same thing. On its own it has no backend to talk to; `make dev` starts both. See [CONTRIBUTING.md](../CONTRIBUTING.md) for the full setup.

```bash
yarn vitest run      # unit tests
yarn lint            # lint
yarn check           # type check
yarn build           # production build
```

## Accessibility

The arena is held to [RGAA 4.1.2](https://accessibilite.numerique.gouv.fr/), the French public-sector standard. Two suites guard it.

**Structure, in CI.** Runs with the rest of the unit tests, no backend needed:

```bash
yarn vitest run
```

These are the `*.a11y.svelte.test.ts` files plus the helpers in `src/lib/testing/a11y.ts`. jsdom has no layout, so colour and reflow rules are off here; what it checks is labels, ARIA, roles and ids. Several cases render a component twice on purpose, because the ids that collided in production were unique inside their component and only clashed once two of them were on screen.

**Whole pages, in a browser.** Needs the app running, so it is not in CI:

```bash
# with the backend and frontend up
PLAYWRIGHT_BASE_URL=http://localhost:5173 yarn test:a11y
```

This one does check colour contrast, reflow at 320px, dark mode and the skip link. `e2e/a11y.test.ts` holds one documented accepted failure; the comment says what it is and when to delete it.

**Neither is a substitute for a screen reader.** Automated rules catch roughly a third of real barriers. A green run means nothing obvious regressed.
