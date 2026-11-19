import { createApp, analytics, genie, lakebase, server } from '@databricks/appkit';
import { setupCaseRoutes } from './routes/cases/case-routes';

createApp({
  plugins: [
    analytics(),
    lakebase(),
    genie({ spaces: { voc: process.env.DATABRICKS_GENIE_SPACE_ID ?? '' } }),
    server(),
  ],
  async onPluginsReady(appkit) {
    await setupCaseRoutes(appkit);
  },
}).catch(console.error);
