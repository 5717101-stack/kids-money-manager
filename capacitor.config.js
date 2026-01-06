const { defineConfig } = require('@capacitor/cli');

module.exports = defineConfig({
  appId: 'com.bachar.kidsmoneymanager',
  appName: 'Kids Money Manager',
  webDir: 'dist',
  server: {
    androidScheme: 'https'
  }
});

