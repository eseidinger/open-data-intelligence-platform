import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { developmentIdentityInterceptor } from './core/development-identity/development-identity.interceptor';
import { platformCsrfInterceptor } from './core/security/platform-csrf.interceptor';

import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideHttpClient(withInterceptors([platformCsrfInterceptor, developmentIdentityInterceptor])),
    provideRouter(routes)
  ]
};
