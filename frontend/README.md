# sv

Everything you need to build a Svelte project, powered by [`sv`](https://github.com/sveltejs/cli).

## Creating a project

If you're seeing this, you've probably already done this step. Congrats!

```bash
# create a new project in the current directory
npx sv create

# create a new project in my-app
npx sv create my-app
```

## Developing

Once you've created a project and installed dependencies with `npm install` (or `pnpm install` or `yarn`), start a development server:

```bash
npm run dev

# or start the server and open the app in a new browser tab
npm run dev -- --open
```

## Building

To create a production version of your app:

```bash
npm run build
```

You can preview the production build with `npm run preview`.

> To deploy your app, you may need to install an [adapter](https://svelte.dev/docs/kit/adapters) for your target environment.

## Accessibility

The arena is held to [RGAA 4.1.2](https://accessibilite.numerique.gouv.fr/), the French
public-sector standard. Two suites guard it.

**Structure, in CI.** Runs with the rest of the unit tests, no backend needed:

```bash
yarn vitest run
```

These are the `*.a11y.svelte.test.ts` files plus the helpers in `src/lib/testing/a11y.ts`.
jsdom has no layout, so colour and reflow rules are off here; what it checks is labels,
ARIA, roles and ids. Several cases render a component twice on purpose — the ids that
collided in production were unique inside their component and only clashed once two of
them were on screen.

**Whole pages, in a browser.** Needs the app running, so it is not in CI:

```bash
# with the backend and frontend up
PLAYWRIGHT_BASE_URL=http://localhost:5173 yarn test:a11y
```

This one does check colour contrast, reflow at 320px, dark mode and the skip link.
`e2e/a11y.test.ts` holds one documented accepted failure; the comment says what it is
and when to delete it.

**Neither is a substitute for a screen reader.** Automated rules catch roughly a third of
real barriers. A green run means nothing obvious regressed.
