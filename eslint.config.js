import js from '@eslint/js';
import prettier from 'eslint-config-prettier';
import globals from 'globals';

export default [
  {
    ignores: [
      'node_modules/**',
      'coverage/**',
      'dist/**',
      'course/**',
      'course/index.html',
      'openspec/**',
    ],
  },
  js.configs.recommended,
  {
    languageOptions: {
      ecmaVersion: 2023,
      sourceType: 'module',
      globals: {
        ...globals.node,
      },
    },
    rules: {
      // Correctness-only baseline (eslint:recommended). Formatting is owned by Prettier.
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      // Allow empty catch blocks: best-effort cleanup (e.g. rmSync in afterEach) is intentional.
      'no-empty': ['error', { allowEmptyCatch: true }],
    },
  },
  prettier,
];
