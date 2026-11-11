import { includeIgnoreFile } from '@eslint/compat'
import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import svelte from 'eslint-plugin-svelte'
import { globalIgnores } from 'eslint/config'
import globals from 'globals'
import { fileURLToPath } from 'node:url'
import ts from 'typescript-eslint'
import svelteConfig from './svelte.config.js'

const gitignorePath = fileURLToPath(new URL('./.gitignore', import.meta.url))

export default ts.config(
  includeIgnoreFile(gitignorePath),
  globalIgnores(['src/lib/i18n/*']),
  js.configs.recommended,
  ...ts.configs.recommended,
  ...svelte.configs.recommended,
  prettier,
  ...svelte.configs.prettier,
  {
    languageOptions: {
      globals: { ...globals.browser, ...globals.node }
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          args: 'all',
          argsIgnorePattern: '^_',
          caughtErrors: 'all',
          caughtErrorsIgnorePattern: '^_',
          destructuredArrayIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          ignoreRestSiblings: true
        }
      ],
      'svelte/valid-compile': 'warn',
      'svelte/no-at-html-tags': 'off'
    }
  },
  {
    // The app can be served under an Instance path: internal paths go through
    // `resolve` (routes) or `asset` (static files) from $app/paths, which add it.
    // no-navigation-without-resolve already covers <a href>, goto and friends.
    files: ['src/**/*.ts', 'src/**/*.svelte'],
    ignores: ['**/*.{test,spec}.ts', '**/*.svelte.{test,spec}.ts'],
    rules: {
      'no-restricted-syntax': [
        'error',
        {
          selector:
            "CallExpression[callee.name='redirect'] > Literal.arguments[value=/^\\/(?!\\/)/]",
          message: 'Wrap internal redirect targets in resolve() from $app/paths.'
        },
        {
          selector:
            "CallExpression[callee.name='redirect'] > TemplateLiteral.arguments[quasis.0.value.raw=/^\\/(?!\\/)/]",
          message: 'Wrap internal redirect targets in resolve() from $app/paths.'
        },
        {
          selector:
            'SvelteAttribute[key.name=/^(src|srcset|href|action|poster)$/] > SvelteLiteral[value=/^\\/(?!\\/)/]',
          message: 'Use resolve() or asset() from $app/paths for internal paths.'
        }
      ]
    }
  },
  {
    files: ['**/*.svelte', '**/*.svelte.ts', '**/*.svelte.js'],
    languageOptions: {
      parserOptions: {
        projectService: true,
        extraFileExtensions: ['.svelte'],
        parser: ts.parser,
        svelteConfig
      }
    }
  }
)
