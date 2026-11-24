// Vérification du client contre une vraie API Wattou (make mobile-integration).
module.exports = {
  testEnvironment: 'node',
  testMatch: ['<rootDir>/test/integration/**/*.test.ts'],
  transform: { '^.+\\.[tj]sx?$': ['babel-jest', { presets: ['babel-preset-expo'] }] },
  testTimeout: 300_000,
};
