// Deux projets : la logique pure (Node) et les écrans (React Native), comme Bustro.
module.exports = {
  projects: [
    {
      displayName: 'logique',
      testEnvironment: 'node',
      testMatch: ['<rootDir>/test/**/*.test.ts'],
      testPathIgnorePatterns: ['/node_modules/', '<rootDir>/test/integration/'],
      transform: { '^.+\\.[tj]sx?$': ['babel-jest', { presets: ['babel-preset-expo'] }] },
    },
    {
      displayName: 'ecrans',
      preset: 'jest-expo',
      testMatch: ['<rootDir>/test/**/*.test.tsx'],
      transformIgnorePatterns: [
        '/node_modules/(?!(react-native|@react-native|@react-native-community|expo|@expo|expo-router|react-navigation|@react-navigation|standard-navigation|react-native-svg))',
      ],
    },
  ],
};
