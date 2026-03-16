import nextConfig from 'eslint-config-next/core-web-vitals';

const eslintConfig = [
  ...nextConfig,
  {
    rules: {
      // React 19 compiler rules — downgrade to warn until codebase is migrated
      'react-hooks/set-state-in-effect': 'warn',
      'react-hooks/rules-of-hooks': 'error',
      'react/no-impure-render': 'warn',
    },
  },
];

export default eslintConfig;
