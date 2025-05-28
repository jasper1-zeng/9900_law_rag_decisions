const { defineConfig } = require("cypress");
const webpackConfig = require('./webpack.config.js');

module.exports = defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
  
  component: {
    devServer: {
      framework: "react",
      bundler: "webpack",
      webpackConfig
    },
    specPattern: "cypress/component/**/*.cy.{js,jsx,ts,tsx}",
  },

  viewportWidth: 1280,
  viewportHeight: 720,

  // Configure retry behavior
  retries: {
    runMode: 2,
    openMode: 0,
  },

  // Default command timeout
  defaultCommandTimeout: 5000,

  // Video recording configuration
  video: false,

  // Screenshot behavior
  screenshotOnRunFailure: true,
  
  // Environment variables for testing
  env: {
    TEST_EMAIL: "will.ren@student.unsw.edu.au",
    TEST_PASSWORD: "123456"
  }
});
