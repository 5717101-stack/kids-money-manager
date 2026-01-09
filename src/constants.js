// Centralized constants - single source of truth
// Version is read from package.json at build time via Vite

import packageJson from '../package.json';

export const APP_VERSION = packageJson.version;
